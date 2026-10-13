"""Map world: regions, projection, camera moves, raster pyramids and georeferenced images.

Projection = equirectangular with a fixed cos(ref_lat) correction. A camera is a tuple
(lon, lat, zoom, ox, oy): the map point (lon, lat) is drawn at design pixel (ox, oy), with `zoom` design pixels per
degree of latitude. `World.proj` returns REAL pixels (design * S)."""
import json
import math
import os

import cv2
import numpy as np
import shapely
from PIL import Image, ImageDraw

from .fx import clamp, einout, lerp


def _rings_of(geom):
    """GeoJSON geometry -> list of exterior rings (np.float32 (n, 2)); holes are ignored (choropleth fill is per ring)"""
    t = geom["type"]; cs = geom["coordinates"]
    polys = [cs] if t == "Polygon" else cs if t == "MultiPolygon" else []
    return [np.asarray(p[0], np.float32)[:, :2] for p in polys if len(p[0]) >= 3]


class World:
    def __init__(self, regions, names=None, neighbours=None, ref_lat=None, S=1.0, extra_shapes=None):
        """regions: {code: [rings]}, names: {code: name}, neighbours: [rings] drawn as dark context"""
        self.regions = regions
        self.names = names or {k: k for k in regions}
        self.neighbours = neighbours or []
        self.shapes = extra_shapes or {}
        allr = np.concatenate([r for rs in regions.values() for r in rs])
        self.bbox = (float(allr[:, 0].min()), float(allr[:, 1].min()), float(allr[:, 0].max()), float(allr[:, 1].max()))
        self.ref_lat = ref_lat if ref_lat is not None else (self.bbox[1] + self.bbox[3]) / 2
        self.COS = math.cos(math.radians(self.ref_lat))
        self.S = S
        self._union = None
        self._label = {}

    # ---------- loading ----------
    @classmethod
    def from_geojson(cls, path, id_field, name_field=None, neighbours=None, ref_lat=None, S=1.0, only=None):
        g = json.load(open(path))
        regions, names = {}, {}
        for f in g["features"]:
            k = str(f["properties"][id_field])
            if only and k not in only:
                continue
            regions.setdefault(k, []).extend(_rings_of(f["geometry"]))
            names[k] = str(f["properties"].get(name_field, k)) if name_field else k
        nb = []
        if neighbours:
            for f in json.load(open(neighbours))["features"]:
                nb.extend(_rings_of(f["geometry"]))
        return cls(regions, names, nb, ref_lat, S)

    # ---------- geometry helpers ----------
    def union(self, codes=None):
        codes = list(self.regions) if codes is None else codes
        key = tuple(sorted(codes))
        if codes is None or key == tuple(sorted(self.regions)):
            if self._union is None:
                self._union = shapely.union_all([shapely.Polygon(r) for c in self.regions for r in self.regions[c]]).buffer(0)
            return self._union
        return shapely.union_all([shapely.Polygon(r) for c in codes for r in self.regions[c]]).buffer(0)

    def outline(self, codes=None, simplify=0.005, min_area=0.01):
        u = self.union(codes).buffer(0.01).buffer(-0.01).simplify(simplify)
        return [np.asarray(g.exterior.coords, np.float32) for g in (u.geoms if hasattr(u, "geoms") else [u]) if g.area > min_area]

    def rings(self, ref):
        """ref: region code, list of codes, or name of an extra shape -> list of rings"""
        if isinstance(ref, str) and ref in self.shapes:
            return self.shapes[ref]
        codes = [ref] if isinstance(ref, str) else list(ref)
        missing = [c for c in codes if c not in self.regions]
        if missing:
            raise KeyError(f"unknown region code(s) {missing}; known: {sorted(self.regions)[:30]}")
        return [r for c in codes for r in self.regions[c]]

    def label_point(self, code):
        if code not in self._label:
            u = shapely.union_all([shapely.Polygon(r) for r in self.regions[code]])
            g = max(u.geoms, key=lambda g: g.area) if hasattr(u, "geoms") else u
            p = g.representative_point(); self._label[code] = (p.x, p.y)
        return self._label[code]

    def bbox_of(self, ref):
        a = np.concatenate(self.rings(ref)); return (float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max()))

    def random_points_in(self, codes, n, seed=3):
        u = self.union(codes); rg = np.random.default_rng(seed); out = []
        from shapely import prepared
        pr = prepared.prep(u); x0, y0, x1, y1 = u.bounds
        while len(out) < n:
            x, y = rg.uniform(x0, x1), rg.uniform(y0, y1)
            if pr.contains(shapely.Point(x, y)):
                out.append((x, y))
        return np.array(out, np.float32)

    # ---------- projection ----------
    def projd(self, lon, lat, c):
        """design-unit projection"""
        return c[3] + (np.asarray(lon) - c[0]) * c[2] * self.COS, c[4] - (np.asarray(lat) - c[1]) * c[2]

    def proj(self, lon, lat, c):
        x, y = self.projd(lon, lat, c); return x * self.S, y * self.S

    def ring_px(self, r, c):
        x, y = self.proj(r[:, 0], r[:, 1], c); return list(zip(x.tolist(), y.tolist()))

    # ---------- cameras ----------
    def fit(self, bbox, anchor=(1290, 548), size=(900, 760), pad=1.08):
        """camera that fits bbox (lon0, lat0, lon1, lat1) into a design-pixel box `size` centred on `anchor`"""
        lon0, lat0, lon1, lat1 = bbox
        z = min(size[1] / max(1e-6, (lat1 - lat0) * pad), size[0] / max(1e-6, (lon1 - lon0) * self.COS * pad))
        return ((lon0 + lon1) / 2, (lat0 + lat1) / 2, z, anchor[0], anchor[1])

    def camera(self, spec, default_anchor=(1290, 548)):
        """camera from a story spec: {center: [lon, lat], zoom, anchor} | {fit: code(s)|shape|[lon0,lat0,lon1,lat1], size, anchor}"""
        if spec is None:
            return None
        anchor = tuple(spec.get("anchor", default_anchor))
        if "center" in spec:
            return (float(spec["center"][0]), float(spec["center"][1]), float(spec.get("zoom", 30)), anchor[0], anchor[1])
        if "fit" in spec:
            f = spec["fit"]
            bbox = tuple(map(float, f)) if isinstance(f, (list, tuple)) and len(f) == 4 and all(isinstance(v, (int, float)) for v in f) \
                else self.bbox if f in ("all", "*") else self.bbox_of(f)
            return self.fit(bbox, anchor, tuple(spec.get("size", (900, 760))), spec.get("pad", 1.08))
        raise ValueError(f"camera spec needs 'center' or 'fit': {spec}")

    def cam_mix(self, a, b, k):
        z = math.exp(lerp(math.log(a[2]), math.log(b[2]), k))
        kk = k if abs(math.log(b[2] / a[2])) < 1.5 else (z - a[2]) / (b[2] - a[2]) if b[2] != a[2] else k
        return (lerp(a[0], b[0], kk), lerp(a[1], b[1], kk), z, lerp(a[3], b[3], k), lerp(a[4], b[4], k))

    def cam_fly(self, a, b, u):
        """region -> region: pan straight from a to b; the zoom dips only as much as needed to keep both ends on screen"""
        k = einout(u)
        dist = math.hypot((b[0] - a[0]) * self.COS, b[1] - a[1])
        la, lb = math.log(a[2]), math.log(b[2]); lm = lerp(la, lb, 0.5)
        zfit = 1000.0 / max(dist, 1e-3)
        dip = max(0.0, lm - math.log(zfit))
        lz = lerp(la, lb, k) - dip * 4 * k * (1 - k)
        return (lerp(a[0], b[0], k), lerp(a[1], b[1], k), math.exp(lz), lerp(a[3], b[3], k), lerp(a[4], b[4], k))

    def cam_zoomto(self, a, b, u):
        """clean direct zoom: the close end's centre travels on a straight screen line while the zoom is log-interpolated"""
        k = einout(u)
        anc = b if b[2] >= a[2] else a
        z = math.exp(lerp(math.log(a[2]), math.log(b[2]), k)); ox = lerp(a[3], b[3], k); oy = lerp(a[4], b[4], k)
        pa = self.projd(anc[0], anc[1], a); pb = self.projd(anc[0], anc[1], b)
        px = lerp(pa[0], pb[0], k); py = lerp(pa[1], pb[1], k)
        return (anc[0] - (px - ox) / (z * self.COS), anc[1] + (py - oy) / z, z, ox, oy)

    def cam_move(self, a, b, u, mode):
        if mode == "cut" or a is None:
            return b
        if mode == "fly":
            return self.cam_fly(a, b, u)
        if mode == "zoomto":
            return self.cam_zoomto(a, b, u)
        if mode == "auto":
            r = abs(math.log(b[2] / a[2]))
            dist = math.hypot((b[0] - a[0]) * self.COS, b[1] - a[1]) * min(a[2], b[2])
            return self.cam_zoomto(a, b, u) if r > 1.2 else self.cam_fly(a, b, u) if dist > 400 else self.cam_mix(a, b, einout(u))
        return self.cam_mix(a, b, einout(u))

    # ---------- drawing ----------
    def base_map(self, c, W, H, theme, land=None):
        im = Image.new("RGB", (W, H), theme.c["bg"]); d = ImageDraw.Draw(im, "RGBA")
        nb, nbo = theme.c["neighbour"], tuple(min(255, v + 20) for v in theme.c["neighbour"])
        for r in self.neighbours:
            d.polygon(self.ring_px(r, c), fill=nb + (255,), outline=nbo + (255,))
        lc = land or theme.c["land"]
        for rs in self.regions.values():
            for r in rs:
                d.polygon(self.ring_px(r, c), fill=lc + (255,))
        bc = theme.c["border"]
        for rs in self.regions.values():
            for r in rs:
                d.line(self.ring_px(r, c) + self.ring_px(r[:1], c), fill=bc + (210,), width=max(1, int(self.S)))
        return im

    def mask(self, rings, c, W, H, blur=4):
        m = Image.new('L', (W // 2, H // 2), 0); dm = ImageDraw.Draw(m)
        for r in rings:
            dm.polygon([(x / 2, y / 2) for x, y in self.ring_px(r, c)], fill=255)
        m = np.asarray(m, np.float32) / 255
        if blur:
            m = cv2.GaussianBlur(m, (0, 0), blur)
        return cv2.resize(m, (W, H))


# ---------------- rasters ----------------
class RasterPyramid:
    """A lat/lon grid raster (values 0..1) with 6 area-averaged levels, warped into the camera view each frame."""

    def __init__(self, arr, lon0, lat1, d):
        a = np.asarray(arr)
        if a.dtype != np.uint8:
            a = (np.clip(a.astype(np.float32), 0, 1) * 255).astype(np.uint8)
        self.levels = [a]
        for _ in range(5):
            p = self.levels[-1]
            self.levels.append(cv2.resize(p, (max(1, p.shape[1] // 2), max(1, p.shape[0] // 2)), interpolation=cv2.INTER_AREA))
        self.lon0, self.lat1, self.d = float(lon0), float(lat1), float(d)

    @classmethod
    def load(cls, path, grid=None):
        """.npz with arrays l0..l5 (pyramid format) + a grid json {LON0, LAT1, D}; or .npy + grid; or a GeoTIFF"""
        if path.endswith((".tif", ".tiff")):
            import rasterio
            with rasterio.open(path) as s:
                a = s.read(1).astype(np.float32); tr = s.transform
            if a.max() > 1:
                a = a / a.max()
            return cls(a, tr.c, tr.f, tr.a)
        g = grid if isinstance(grid, dict) else json.load(open(grid))
        lon0, lat1, d = g.get("LON0", g.get("lon0")), g.get("LAT1", g.get("lat1")), g.get("D", g.get("d"))
        if path.endswith(".npz"):
            z = np.load(path)
            if "l0" in z:
                obj = cls.__new__(cls); obj.levels = [z[f"l{k}"] for k in range(6) if f"l{k}" in z]
                obj.lon0, obj.lat1, obj.d = float(lon0), float(lat1), float(d); return obj
            a = z[list(z.keys())[0]]
        else:
            a = np.load(path)
        a = a.astype(np.float32)
        if a.max() > 1:
            a = a / a.max()
        return cls(a, lon0, lat1, d)

    def warp(self, world, c, W, H, interp=cv2.INTER_LINEAR):
        zr = c[2] * world.COS * world.S                         # real px per degree (x)
        k = int(max(0, min(len(self.levels) - 1, math.floor(math.log2(max(1e-6, (1 / zr) / self.d))))))
        src = self.levels[k]; Dk = self.d * (self.levels[0].shape[1] / src.shape[1])
        ax = Dk * c[2] * world.COS * world.S; ay = Dk * c[2] * world.S
        bx = (c[3] + (self.lon0 + 0.5 * Dk - c[0]) * c[2] * world.COS) * world.S
        by = (c[4] - (self.lat1 - 0.5 * Dk - c[1]) * c[2]) * world.S
        M = np.float32([[ax, 0, bx], [0, ay, by]])
        return cv2.warpAffine(src, M, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float32) / 255


class GeoImage:
    """An RGB image with a lon/lat bbox (e.g. a Sentinel-2 crop) drawn in place on the map."""

    def __init__(self, path, bbox=None, meta=None):
        self.path = path
        self.img = np.asarray(Image.open(path).convert("RGB"), np.float32)
        if meta is None:
            mp = os.path.splitext(path)[0] + ".json"
            meta = json.load(open(mp)) if os.path.exists(mp) else {}
        self.meta = meta
        self.bbox = tuple(bbox or meta.get("bbox"))
        if not self.bbox or len(self.bbox) != 4:
            raise ValueError(f"{path}: needs a bbox (in the story or in the sidecar .json)")

    def layer(self, world, c, W, H):
        img = self.img; h, w = img.shape[:2]; l0, b0, l1, b1 = self.bbox
        ax = (l1 - l0) / w * c[2] * world.COS * world.S; ay = (b1 - b0) / h * c[2] * world.S
        bx = (c[3] + (l0 - c[0]) * c[2] * world.COS) * world.S; by = (c[4] - (b1 - c[1]) * c[2]) * world.S
        M = np.float32([[ax, 0, bx], [0, ay, by]])
        out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA if ax < 1 else cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        m = cv2.warpAffine(np.ones((h, w), np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        return out, m[..., None]

    def corners(self, world, c):
        l0, b0, l1, b1 = self.bbox; x0, y0 = world.proj(l0, b1, c); x1, y1 = world.proj(l1, b0, c); return x0, y0, x1, y1

    def camera(self, world, fill_px=900, anchor=(1390, 540)):
        l0, b0, l1, b1 = self.bbox
        return ((l0 + l1) / 2, (b0 + b1) / 2, fill_px / (b1 - b0), anchor[0], anchor[1])
