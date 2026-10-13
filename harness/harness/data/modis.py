"""Adapter (example): NASA MODIS MCD64A1 C6.1 monthly burned area, 500 m.

Source: University of Maryland public SFTP (fuoco.geog.umd.edu, user 'fire', password 'burnt' — published in the
MCD64A1 C6.1 User Guide). GeoTIFF 'windows' in lat/lon (0.00439453125 deg); value = burn day of year, 0 = unburned,
negative = unmapped/water.

  python -m harness.data.modis fetch --bbox LON0 LAT0 LON1 LAT1 --windows Win06 Win07 --from 2020-01 --to 2024-12 --out raw/umd
  python -m harness.data.modis grid  --src raw/umd --regions data/regiones.geojson --id code --to 2024-12 --out data/burned

`grid` writes  <out>_count.npy (months burned per pixel), <out>_grid.json {LON0, LAT1, D},
<out>_pyr.npz (l0..l5 display pyramid of "burned at least once"), and <out>_stats.json with the area burned per
month and per region (pixel area on the MODIS sphere, each pixel counted once for the distinct total).
The `raster` loader reads the pyramid + grid directly (kind: raster, path: <out>_pyr.npz, grid: <out>_grid.json).
MODIS 'windows' cover continents in tiles (e.g. Win06/Win07 = South America north/south); pick the ones over your bbox."""
import argparse
import calendar
import glob
import json
import math
import os
import sys

import numpy as np

D = 0.00439453125


def _months(a, b):
    y, m = map(int, a.split("-")); y1, m1 = map(int, b.split("-"))
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def fetch(bbox, windows, start, end, out):
    import paramiko
    import rasterio
    from rasterio.windows import Window, from_bounds
    os.makedirs(out, exist_ok=True)
    tr = paramiko.Transport(("fuoco.geog.umd.edu", 22)); tr.connect(username="fire", password="burnt")
    s = paramiko.SFTPClient.from_transport(tr)
    for y, m in _months(start, end):
        doy = sum(calendar.monthrange(y, k)[1] for k in range(1, m)) + 1
        dst = os.path.join(out, f"{y}-{m:02d}.npz")
        if os.path.exists(dst):
            continue
        res = {}
        for win in windows:
            fn = f"MCD64monthly.A{y}{doy:03d}.{win}.061.burndate.tif"
            tmp = os.path.join(out, "tmp.tif")
            try:
                s.get(f"/data/MODIS/C61/MCD64A1/TIFF/{win}/{y}/{fn}", tmp)
            except Exception as e:
                print("MISSING", y, m, win, e, flush=True); continue
            with rasterio.open(tmp) as r:
                w = from_bounds(*bbox, r.transform).round_offsets().round_lengths().intersection(Window(0, 0, r.width, r.height))
                res[win] = (r.read(1, window=w), np.array(r.window_transform(w))[:6], fn)
        if len(res) == len(windows):
            np.savez_compressed(dst, **{f"a_{k}": v[0] for k, v in res.items()}, **{f"t_{k}": v[1] for k, v in res.items()},
                                files=np.array([v[2] for v in res.values()]))
            print(y, m, "ok", flush=True)


def _common_grid(z):
    keys = [k[2:] for k in z.files if k.startswith("a_")]
    lon0 = min(float(z[f"t_{k}"][2]) for k in keys); lat1 = max(float(z[f"t_{k}"][5]) for k in keys)
    H = W = 0; place = {}
    for k in keys:
        a, t = z[f"a_{k}"], z[f"t_{k}"]
        r0, c0 = int(round((lat1 - t[5]) / D)), int(round((t[2] - lon0) / D))
        place[k] = (r0, c0); H = max(H, r0 + a.shape[0]); W = max(W, c0 + a.shape[1])
    return keys, lon0, lat1, H, W, place


def grid(src, regions=None, id_field="code", end="2099-12", out="burned"):
    import cv2
    files = sorted(glob.glob(os.path.join(src, "*.npz")))
    files = [f for f in files if os.path.basename(f)[:7] <= end]
    z0 = np.load(files[0]); keys, lon0, lat1, H, W, place = _common_grid(z0)
    lat_c = lat1 - (np.arange(H) + 0.5) * D; R = 6371007.181
    pixha = ((R * math.radians(D)) ** 2 * np.cos(np.radians(lat_c)) / 1e4)
    reg = None; codes = []
    if regions:
        import shapely
        from rasterio.features import rasterize
        from rasterio.transform import Affine
        from ..core.geo import World
        w = World.from_geojson(regions, id_field); codes = sorted(w.regions)
        reg = rasterize([(shapely.Polygon(r), i + 1) for i, c in enumerate(codes) for r in w.regions[c]], out_shape=(H, W),
                        transform=Affine(D, 0, lon0, 0, -D, lat1), fill=0, dtype="uint8")
    count = np.zeros((H, W), np.uint8); monthly = {}; by_region = {}
    for f in files:
        z = np.load(f); g = np.zeros((H, W), np.int16)
        for k in keys:
            r0, c0 = place[k]; a = z[f"a_{k}"]; sub = g[r0:r0 + a.shape[0], c0:c0 + a.shape[1]]
            sub[:] = np.where(a != 0, a, sub)
        b = g > 0
        if reg is not None:
            b &= reg > 0
        ym = os.path.basename(f)[:7]
        monthly[ym] = float((b.sum(1) * pixha).sum())
        if reg is not None:
            pm = np.bincount(reg[b], weights=np.broadcast_to(pixha[:, None], (H, W))[b], minlength=len(codes) + 1)
            by_region[ym] = {codes[i - 1]: float(pm[i]) for i in range(1, len(codes) + 1) if pm[i] > 0}
        count[b] = np.minimum(255, count[b].astype(int) + 1)
    once = count > 0
    stats = dict(months=sorted(monthly), monthly_ha=monthly, by_region_month_ha=by_region,
                 total_ha_repeat=float(sum(monthly.values())), total_ha_distinct=float((once.sum(1) * pixha).sum()))
    if reg is not None:
        pm = np.bincount(reg[once], weights=np.broadcast_to(pixha[:, None], (H, W))[once], minlength=len(codes) + 1)
        stats["distinct_ha_by_region"] = {codes[i - 1]: float(pm[i]) for i in range(1, len(codes) + 1)}
    np.save(out + "_count.npy", count)
    json.dump(dict(LON0=lon0, LAT1=lat1, D=D), open(out + "_grid.json", "w"))
    lv = [(once * 255).astype(np.uint8)]
    for _ in range(5):
        p = lv[-1]; lv.append(cv2.resize(p, (max(1, p.shape[1] // 2), max(1, p.shape[0] // 2)), interpolation=cv2.INTER_AREA))
    np.savez_compressed(out + "_pyr.npz", **{f"l{k}": a for k, a in enumerate(lv)})
    json.dump(stats, open(out + "_stats.json", "w"), indent=1)
    print("burned distinct ha", round(stats["total_ha_distinct"]), "repeat ha", round(stats["total_ha_repeat"]))
    return stats


def main(argv=None):
    ap = argparse.ArgumentParser(prog="harness.data.modis")
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("fetch"); a.add_argument("--bbox", nargs=4, type=float, required=True)
    a.add_argument("--windows", nargs="+", default=["Win06", "Win07"]); a.add_argument("--from", dest="start", required=True)
    a.add_argument("--to", dest="end", required=True); a.add_argument("--out", required=True)
    b = sp.add_parser("grid"); b.add_argument("--src", required=True); b.add_argument("--regions"); b.add_argument("--id", default="code")
    b.add_argument("--to", default="2099-12"); b.add_argument("--out", required=True)
    x = ap.parse_args(argv)
    if x.cmd == "fetch":
        fetch(x.bbox, x.windows, x.start, x.end, x.out)
    else:
        grid(x.src, x.regions, x.id, x.to, x.out)


if __name__ == "__main__":
    sys.exit(main())
