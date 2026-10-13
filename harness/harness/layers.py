"""Persistent map layers. A beat lists the layers it shows:

    layers:
      - {id: events, mode: lit}                    # points: static | lit | burnout | accumulate  (+ select: "<numpy expr>")
      - {id: area_raster, appear: 0.8, strength: 1.0}   # raster: style fill (default) | event | outline ; color
      - {id: s2_2024}                              # image: drawn in place at its bbox
      - {id: provincias, kind: choropleth, values: fact_name}   # region values -> colour ramp

A layer present in consecutive beats stays on without flicker; it fades in where it first appears (after `appear`
seconds) and fades out at the end of the last beat that lists it. Timelapse/replay of points are beat behaviours
(timeline, big_number `replay:`), not layer modes."""
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .core.fx import clamp, decay, eout, screen
from .core.geo import GeoImage, RasterPyramid
from .data.loaders import Points


_KER = {}


def splat(world, lon, lat, w, cam, W, H, r=0.0):
    """points -> (H, W) count/weight field. r = dot radius in REAL px (dilated with a disc so sparse data stays visible)"""
    x, y = world.proj(lon, lat, cam); xi = np.round(x).astype(np.int32); yi = np.round(y).astype(np.int32)
    m = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
    idx = yi[m] * W + xi[m]
    f = np.bincount(idx, weights=None if w is None else np.asarray(w)[m], minlength=W * H).reshape(H, W).astype(np.float32)
    ri = int(round(r))
    if ri >= 1:
        if ri not in _KER:
            _KER[ri] = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ri + 1, 2 * ri + 1))
        f = cv2.dilate(f, _KER[ri])
    return f


def dot_r(R, pts):
    """dot radius in real px for a points dataset (data spec `point_px`, design px; default 0 = single pixel)"""
    return float(pts.meta.get("point_px", 0)) * R.S


def fire_rgb(v, lut, S, bloom_k=1.0):
    """value field 0..1 -> colour ramp + two-scale bloom (real-pixel sigmas scale with S)"""
    H, W = v.shape
    F = lut[np.clip(v * 255, 0, 255).astype(np.uint8)]
    hs = cv2.resize(F, (max(1, W // 2), max(1, H // 2)), interpolation=cv2.INTER_AREA)
    bloom = cv2.resize(cv2.GaussianBlur(hs, (0, 0), max(0.5, 5 * S)) * 0.9 + cv2.GaussianBlur(hs, (0, 0), max(0.5, 18 * S)) * 0.9, (W, H))
    return F + bloom * bloom_k


def lit_field(R, pts, idx, cam, norm=500.0):
    """accumulated 'everything lit' field: log density normalised so it reads at any zoom"""
    W, H = R.W, R.H
    ember = splat(R.world, pts.lon[idx], pts.lat[idx], None, cam, W, H, dot_r(R, pts)) if len(idx) else np.zeros((H, W), np.float32)
    zr = max(1.0, cam[2] / R.ref_zoom)
    v = np.clip(np.log1p(ember) / math.log1p(norm * zr ** 1.6 * R.density_k), 0, 1) ** 1.1 * 0.92
    return cv2.GaussianBlur(v, (0, 0), 0.7) * 1.25, ember


class LayerSet:
    def __init__(self, R):
        self.R = R
        self._sel = {}

    def ids(self, beat):
        return [l["id"] for l in beat.layers]

    def alpha(self, beat, spec, t):
        lid = spec["id"]
        a = 1.0
        appear = float(spec.get("appear", 0.0))
        fin = float(spec.get("fade_in", 0.4)); fout = float(spec.get("fade_out", 0.4))
        if beat.prev is None or lid not in self.ids(beat.prev) or "appear" in spec:
            a *= clamp((t - beat.start - appear) / fin)
        if beat.next is None or lid not in self.ids(beat.next):
            a *= 1 - clamp((t - beat.end + fout) / fout)
        return a

    def select(self, name, pts, expr):
        k = (name, expr or "")
        if k not in self._sel:
            self._sel[k] = pts.select(expr)
        return self._sel[k]

    def draw(self, A, beat, t, cam):
        for spec in beat.layers:
            a = self.alpha(beat, spec, t)
            if a <= 0.003:
                continue
            kind = spec.get("kind")
            if kind == "choropleth":
                A = self.choropleth(A, spec, beat, a, cam); continue
            data = self.R.story.dataset(spec["id"]) if spec.get("data") is None else self.R.story.dataset(spec["data"])
            if isinstance(data, Points):
                A = self.points(A, spec, data, beat, t, a, cam)
            elif isinstance(data, RasterPyramid):
                A = self.raster(A, spec, data, beat, t, a, cam)
            elif isinstance(data, GeoImage):
                im, m = data.layer(self.R.world, cam, self.R.W, self.R.H)
                k = a * float(spec.get("opacity", 0.9))
                A = A * (1 - m * k) + im * m * k
        return A

    # ---------------- points ----------------
    def points(self, A, spec, pts, beat, t, a, cam):
        R = self.R; mode = spec.get("mode", "lit"); u = t - beat.start
        idx = self.select(spec.get("data", spec["id"]), pts, spec.get("select"))
        if mode == "accumulate":
            hk = clamp((u - float(spec.get("appear", 0.1))) / float(spec.get("over", 1.5)))
            tmin, tmax = (pts.t[idx].min(), pts.t[idx].max()) if len(idx) else (0, 0)
            n = int(np.searchsorted(pts.t[idx], tmin + (tmax - tmin) * eout(hk), side="right")) if hk > 0 else 0
            v, _ = lit_field(R, pts, idx[:n], cam, spec.get("norm", 500))
            v = v * a * float(spec.get("strength", 1.0))
            return screen(A, fire_rgb(v, R.theme.lut, R.S, 0.78))
        if mode in ("lit", "burnout", "static"):
            v, ember = lit_field(R, pts, idx, cam, spec.get("norm", 500))
            if mode == "static":
                em = np.clip(np.log1p(ember) / math.log1p(60), 0, 1)
                return A + em[..., None] * np.array((120, 30, 10), np.float32) * 0.85 * a
            ash_k = gone = 0.0
            if mode == "burnout":
                ash_k = clamp((u - 0.5) / 0.9); gone = clamp((u - 1.3) / 0.6)
            F = fire_rgb(v * a, R.theme.lut, R.S) * (1 - ash_k)
            ASHL = (np.clip(v, 0, 1) ** 0.8)[..., None] * np.array(R.theme.c["ash"], np.float32) * 0.75 * ash_k * (1 - gone) * a
            return screen(A + ASHL, F)
        raise ValueError(f"layer '{spec['id']}': unknown points mode '{mode}' (static|lit|burnout|accumulate)")

    # ---------------- rasters ----------------
    def raster(self, A, spec, pyr, beat, t, a, cam):
        R = self.R; style = spec.get("style", "fill")
        style = "fill" if style == "scar" else style
        interp = cv2.INTER_NEAREST if style == "outline" else cv2.INTER_LINEAR
        v = pyr.warp(R.world, cam, R.W, R.H, interp)
        k = a * float(spec.get("strength", 1.0))
        zf = spec.get("recede_zoom")
        if zf:
            k *= 1 - 0.75 * clamp((cam[2] - zf) / (1.6 * zf))
        if style == "fill":
            col = np.array(beat.c(spec.get("color", "ash")) if spec.get("color") else (205, 190, 172), np.float32)
            warm = np.array(R.theme.c["accent"], np.float32)
            kw = 0.5 * decay(t, beat.start + float(spec.get("appear", 0)), 0.8) if spec.get("warm_flash", True) and "appear" in spec else 0.0
            vv = np.clip(v, 0, 1) ** 0.55
            return A * (1 - 0.6 * vv[..., None] * a) + vv[..., None] * (col * (1 - kw) + warm * kw) * k
        if style == "event":
            edge = np.clip(v - cv2.GaussianBlur(v, (0, 0), 2.5 * R.S), 0, 1) * 3
            col = np.array(beat.c(spec.get("color", "accent2")), np.float32)
            return A * (1 - 0.35 * v[..., None] * k) + v[..., None] * col * 0.45 * k + np.clip(edge, 0, 1)[..., None] * col * k * 0.8
        if style == "outline":
            edge = np.clip(v - cv2.erode(v, np.ones((3, 3), np.uint8)), 0, 1)
            col = np.array(beat.c(spec.get("color", "accent2")), np.float32)
            return A * (1 - 0.25 * v[..., None] * k) + v[..., None] * col * 0.28 * k + edge[..., None] * col * k
        raise ValueError(f"layer '{spec['id']}': unknown raster style '{style}' (fill|event|outline)")

    # ---------------- choropleth ----------------
    def choropleth(self, A, spec, beat, a, cam):
        R = self.R
        vals = R.story.facts[spec["values"]] if isinstance(spec.get("values"), str) else spec["values"]
        if isinstance(vals, list):
            vals = {str(r["code"]): float(r["value"]) for r in vals}
        vmax = max(vals.values()) or 1
        lay = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for code, v in vals.items():
            if code not in R.world.regions:
                continue
            col = tuple(int(x) for x in R.theme.lut[int(70 + 140 * (v / vmax) ** spec.get("gamma", 0.55))])
            for ring in R.world.regions[code]:
                d.polygon(R.world.ring_px(ring, cam), fill=col + (int(255 * 0.78 * a),))
        L = np.asarray(lay, np.float32); al = L[..., 3:4] / 255
        return A * (1 - al) + L[..., :3] * al

    def legends(self, beat):
        out = []
        for spec in beat.layers:
            lid = spec.get("data", spec["id"])
            txt = spec.get("legend", R_legend(self.R, lid))
            if txt:
                out.append((spec, txt))
        return out


def R_legend(R, lid):
    return (R.story.data_spec(lid) or {}).get("legend")
