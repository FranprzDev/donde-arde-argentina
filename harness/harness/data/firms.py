"""Adapter: NASA FIRMS active-fire / hotspot archive (open data, no key needed for the yearly country files).

  python -m harness.data.firms download --country Chile --years 2020-2024 --sensor viirs-snpp --out stories/x/data/raw
  python -m harness.data.firms points --csv 'stories/x/data/raw/viirs-snpp_*_Chile.csv' --origin 2020-01 \
         --regions stories/x/data/regiones.geojson --id code --out stories/x/data/raw/points.npz

`points` keeps type == 0 (presumed vegetation fire) and confidence nominal/high (drops low confidence), computes
t = fractional months since --origin (acq_date + acq_time), assigns each point to a region (point in polygon, nearest
polygon for points just outside a simplified coast) and saves lon/lat/t/prov (+ conf) in the NPZ format the
`points` loader reads (`region: {column: prov, codes: sorted}`).
Credit on screen: "NASA FIRMS, VIIRS 375 m" (FIRMS data are free to use with attribution)."""
import argparse
import glob
import os
import sys
import urllib.request

import numpy as np

URL = "https://firms.modaps.eosdis.nasa.gov/data/country/{sensor}/{year}/{sensor}_{year}_{country}.csv"


def download(country, years, sensor="viirs-snpp", out="."):
    os.makedirs(out, exist_ok=True); paths = []
    for y in years:
        url = URL.format(sensor=sensor, year=y, country=country.replace(" ", "_"))
        p = os.path.join(out, os.path.basename(url))
        if not os.path.exists(p):
            print("GET", url, flush=True)
            urllib.request.urlretrieve(url, p + ".part"); os.replace(p + ".part", p)
        paths.append(p)
    return paths


def to_points(csv_glob, origin="2020-01", regions=None, id_field="code", out="points.npz", keep_low=False):
    import pandas as pd
    files = sorted(glob.glob(csv_glob))
    if not files:
        raise FileNotFoundError(csv_glob)
    d = pd.concat([pd.read_csv(f, dtype={"acq_time": str}) for f in files], ignore_index=True)
    n_all = len(d)
    m = d["type"] == 0
    if not keep_low:
        m &= d["confidence"].astype(str) != "l"
    d = d[m].copy()
    dt = pd.to_datetime(d.acq_date); o = pd.Timestamp(origin)
    t = (dt.dt.year - o.year) * 12 + (dt.dt.month - o.month) + (dt.dt.day - 1) / dt.dt.days_in_month \
        + d.acq_time.astype(int) // 100 / 24 / 30
    lon, lat = d.longitude.values.astype(np.float64), d.latitude.values.astype(np.float64)
    arrays = dict(lon=lon.astype(np.float32), lat=lat.astype(np.float32), t=t.values.astype(np.float32),
                  conf=d.confidence.map({"l": 0, "n": 1, "h": 2}).fillna(1).values.astype(np.int8))
    if regions:
        from ..core.geo import World
        from .loaders import assign_regions
        w = World.from_geojson(regions, id_field)
        codes = sorted(w.regions)
        reg = assign_regions(lon, lat, w)
        arrays["prov"] = np.array([codes.index(c) for c in reg], np.int8)
    np.savez_compressed(out, **arrays)
    print(f"{out}: {len(d)} points kept of {n_all} (type 0, conf {'all' if keep_low else 'n/h'})")
    return out


def _years(s):
    if "-" in s:
        a, b = s.split("-"); return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="harness.data.firms")
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("download"); a.add_argument("--country", required=True); a.add_argument("--years", required=True)
    a.add_argument("--sensor", default="viirs-snpp"); a.add_argument("--out", default=".")
    b = sp.add_parser("points"); b.add_argument("--csv", required=True); b.add_argument("--origin", default="2020-01")
    b.add_argument("--regions"); b.add_argument("--id", default="code"); b.add_argument("--out", default="points.npz")
    b.add_argument("--keep-low", action="store_true")
    x = ap.parse_args(argv)
    if x.cmd == "download":
        download(x.country, _years(x.years), x.sensor, x.out)
    else:
        to_points(x.csv, x.origin, x.regions, x.id, x.out, x.keep_low)


if __name__ == "__main__":
    sys.exit(main())
