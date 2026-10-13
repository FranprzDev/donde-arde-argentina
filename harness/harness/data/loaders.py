"""Pluggable data loaders. A story's `data:` section names datasets; each entry has a `kind` and the loader turns it
into an object the beats and facts.py can use:

  kind: points   -> Points   (lon, lat, t, region + any extra columns), from CSV / Parquet / NPZ / GeoJSON points
  kind: raster   -> RasterPyramid  (lat/lon grid, values 0..1), from GeoTIFF / NPY / NPZ + grid
  kind: image    -> GeoImage (RGB + bbox), e.g. a Sentinel-2 crop made by tools/fetch_sentinel2.py
  kind: table    -> pandas.DataFrame, from CSV / Parquet / XLSX / JSON
  kind: json     -> dict / list
  kind: regions  -> World (normally declared once under `map:`), from GeoJSON or a shapefile

Adapters for specific open sources live next to this file (firms.py, modis.py, sentinel2.py) and produce files in the
formats above, so the renderer never needs to know where data came from."""
import json
import os

import numpy as np

from ..core.geo import GeoImage, RasterPyramid, World


class Points:
    """Point events sorted by time. `t` is a float in the dataset's own unit (e.g. fractional months since an origin).
    `region` holds region codes as strings (or None). Extra columns are kept in `cols`."""

    def __init__(self, lon, lat, t=None, region=None, cols=None, meta=None):
        lon = np.asarray(lon, np.float32); lat = np.asarray(lat, np.float32)
        t = np.zeros(len(lon), np.float64) if t is None else np.asarray(t, np.float64)
        o = np.argsort(t, kind="stable")
        self.lon, self.lat, self.t = lon[o], lat[o], t[o]
        self.region = None if region is None else np.asarray(region).astype(str)[o]
        self.cols = {k: np.asarray(v)[o] for k, v in (cols or {}).items()}
        self.meta = meta or {}

    def __len__(self):
        return len(self.lon)

    def namespace(self):
        ns = dict(lon=self.lon, lat=self.lat, t=self.t, np=np)
        if self.region is not None:
            ns["region"] = self.region
        ns.update(self.cols)
        return ns

    def select(self, expr):
        """indices of points matching a numpy expression over the columns, e.g. "(region == '30') & (t >= 96)" """
        if not expr:
            return np.arange(len(self))
        m = eval(expr, {"__builtins__": {}}, self.namespace())  # story files are trusted code, like facts.py
        return np.where(np.asarray(m, bool))[0]

    def binned(self, t0, t1, step=1.0):
        """counts per bin of t (e.g. per month) -> np.array"""
        n = int(round((t1 - t0) / step))
        h, _ = np.histogram(self.t, bins=n, range=(t0, t1))
        return h.astype(np.float64)


def _time_to_float(series, unit="month", origin=None):
    import pandas as pd
    dt = pd.to_datetime(series)
    o = pd.Timestamp(origin) if origin else dt.min().normalize().replace(day=1)
    if unit == "month":
        return ((dt.dt.year - o.year) * 12 + (dt.dt.month - o.month) + (dt.dt.day - 1) / dt.dt.days_in_month).values.astype(np.float64)
    if unit == "day":
        return ((dt - o).dt.total_seconds() / 86400).values
    if unit == "year":
        return (dt.dt.year - o.year + (dt.dt.dayofyear - 1) / 365.25).values
    raise ValueError(f"time unit {unit} (use month|day|year)")


def assign_regions(lon, lat, world, nearest=True):
    """point-in-polygon region code for each point (nearest region for points just outside, e.g. on the coast)"""
    import shapely
    codes = list(world.regions)
    polys = [shapely.MultiPolygon([shapely.Polygon(r) for r in world.regions[c]]).buffer(0) for c in codes]
    out = np.full(len(lon), -1)
    for i, p in enumerate(polys):
        shapely.prepare(p); m = (out < 0) & shapely.contains_xy(p, lon, lat); out[m] = i
    miss = np.where(out < 0)[0]
    if nearest and len(miss):
        pts = shapely.points(lon[miss], lat[miss])
        out[miss] = np.stack([shapely.distance(p, pts) for p in polys], 1).argmin(1)
    return np.array([codes[i] if i >= 0 else "" for i in out])


def load_points(spec, base, world=None):
    path = os.path.join(base, spec["path"])
    meta = {k: v for k, v in spec.items() if k not in ("path",)}
    if path.endswith(".npz"):
        z = np.load(path, allow_pickle=False)
        lon, lat = z[spec.get("lon", "lon")], z[spec.get("lat", "lat")]
        t = z[spec.get("time", "t")] if spec.get("time", "t") in z else None
        region = None
        rk = spec.get("region", "region")
        if isinstance(rk, dict):                      # integer index -> code list, e.g. {column: prov, codes: sorted}
            idx = z[rk["column"]]
            codes = rk.get("codes")
            if codes == "sorted" and world is not None:
                codes = sorted(world.regions)
            region = np.array(codes)[idx] if codes else idx.astype(str)
        elif rk in z:
            region = z[rk]
        cols = {k: z[k] for k in z.files if k not in (spec.get("lon", "lon"), spec.get("lat", "lat"), spec.get("time", "t"))}
        pts = Points(lon, lat, t, region, cols, meta)
    else:
        import pandas as pd
        if path.endswith(".parquet"):
            df = pd.read_parquet(path)
        elif path.endswith((".geojson", ".json")):
            g = json.load(open(path))
            rows = [dict(f["properties"], _lon=f["geometry"]["coordinates"][0], _lat=f["geometry"]["coordinates"][1]) for f in g["features"]]
            df = pd.DataFrame(rows); spec = dict(spec, lon="_lon", lat="_lat")
        else:
            df = pd.read_csv(path)
        if spec.get("filter"):
            df = df.query(spec["filter"], engine="python")
        tspec = spec.get("time")
        t = None
        if isinstance(tspec, dict):
            t = _time_to_float(df[tspec["column"]], tspec.get("unit", "month"), tspec.get("origin"))
        elif isinstance(tspec, str):
            t = df[tspec].values
        region = None
        if spec.get("region") == "assign":
            if world is None:
                raise ValueError("region: assign needs map.regions")
            region = assign_regions(df[spec.get("lon", "longitude")].values, df[spec.get("lat", "latitude")].values, world)
        elif spec.get("region"):
            region = df[spec["region"]].astype(str).values
        keep = spec.get("columns", [])
        pts = Points(df[spec.get("lon", "longitude")].values, df[spec.get("lat", "latitude")].values, t, region,
                     {k: df[k].values for k in keep}, meta)
    if spec.get("select"):
        idx = pts.select(spec["select"])
        pts = Points(pts.lon[idx], pts.lat[idx], pts.t[idx], None if pts.region is None else pts.region[idx],
                     {k: v[idx] for k, v in pts.cols.items()}, meta)
    return pts


def load_table(path):
    import pandas as pd
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    if path.endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    if path.endswith(".json"):
        return pd.read_json(path)
    return pd.read_csv(path)


def shapefile_to_geojson(shp_path, out_path=None):
    """convert a shapefile to GeoJSON (needs `pyshp`); returns the output path"""
    import shapefile  # pyshp
    r = shapefile.Reader(shp_path)
    fields = [f[0] for f in r.fields[1:]]
    feats = [dict(type="Feature", properties=dict(zip(fields, sr.record)), geometry=sr.shape.__geo_interface__) for sr in r.shapeRecords()]
    out_path = out_path or os.path.splitext(shp_path)[0] + ".geojson"
    json.dump(dict(type="FeatureCollection", features=feats), open(out_path, "w"))
    return out_path


def load_regions(spec, base, S=1.0):
    path = os.path.join(base, spec["path"])
    if path.endswith(".shp"):
        path = shapefile_to_geojson(path, os.path.join(base, ".cache_" + os.path.basename(path) + ".geojson"))
    nb = os.path.join(base, spec["neighbours"]) if spec.get("neighbours") else None
    w = World.from_geojson(path, spec.get("id", "id"), spec.get("name"), nb, spec.get("ref_lat"), S, spec.get("only"))
    for name, sp in (spec.get("shapes") or {}).items():
        g = json.load(open(os.path.join(base, sp)))
        if isinstance(g, list):
            w.shapes[name] = [np.asarray(r, np.float32) for r in g]
        else:
            from ..core.geo import _rings_of
            feats = g["features"] if g.get("type") == "FeatureCollection" else [g]
            w.shapes[name] = [r for f in feats for r in _rings_of(f["geometry"] if "geometry" in f else f)]
    return w


def load_dataset(name, spec, base, world=None):
    kind = spec.get("kind")
    path = os.path.join(base, spec["path"]) if "path" in spec else None
    if path and not os.path.exists(path):
        hint = spec.get("prepare", "see the story's README / prepare.py")
        raise FileNotFoundError(f"data '{name}': file not found: {path}\n  -> {hint}")
    if kind == "points":
        return load_points(spec, base, world)
    if kind == "raster":
        grid = spec.get("grid")
        if isinstance(grid, str):
            grid = os.path.join(base, grid)
        return RasterPyramid.load(path, grid)
    if kind == "image":
        return GeoImage(path, spec.get("bbox"))
    if kind == "table":
        return load_table(path)
    if kind == "json":
        return json.load(open(path))
    raise ValueError(f"data '{name}': unknown kind '{kind}' (points|raster|image|table|json)")
