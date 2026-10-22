"""Fetch NASA FIRMS VIIRS S-NPP country archive (Argentina, 2012-2025) and build data/raw/viirs_all.parquet.

Migrated from the (now removed) generic Python harness adapter `harness/harness/data/firms.py`.
This is the data-acquisition step of the pipeline; everything downstream reads `data/raw/viirs_all.parquet`.

Usage (from the repo root):
    python pipeline/fetch_firms.py --years 2012-2025 --out data/raw
    # then
    cd pipeline && python prep_data.py
"""
import argparse
import glob
import os
import sys
import urllib.request

import pandas as pd

URL = "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{year}/viirs-snpp_{year}_Argentina.csv"


def _years(s):
    if "-" in s:
        a, b = s.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in s.split(",")]


def download(years, out):
    os.makedirs(out, exist_ok=True)
    paths = []
    for y in years:
        url = URL.format(year=y)
        p = os.path.join(out, f"viirs-snpp_{y}_Argentina.csv")
        if not os.path.exists(p):
            print("GET", url, flush=True)
            urllib.request.urlretrieve(url, p + ".part")
            os.replace(p + ".part", p)
        else:
            print("SKIP (exists)", p, flush=True)
        paths.append(p)
    return paths


def build_parquet(csv_dir, out_parquet):
    files = sorted(glob.glob(os.path.join(csv_dir, "viirs-snpp_*_Argentina.csv")))
    if not files:
        raise FileNotFoundError(f"no CSVs found in {csv_dir}; run --download first")
    d = pd.concat([pd.read_csv(f, dtype={"acq_time": str}) for f in files], ignore_index=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_parquet)), exist_ok=True)
    d.to_parquet(out_parquet, index=False)
    print(f"{out_parquet}: {len(d)} rows from {len(files)} files")
    return out_parquet


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fetch_firms")
    ap.add_argument("--years", default="2012-2025")
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "raw"))
    ap.add_argument("--parquet", default=None, help="output parquet path (default: <out>/viirs_all.parquet)")
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("--parquet-only", action="store_true")
    args = ap.parse_args(argv)

    years = _years(args.years)
    parquet = args.parquet or os.path.join(args.out, "viirs_all.parquet")

    if not args.parquet_only:
        download(years, args.out)
    if not args.download_only:
        build_parquet(args.out, parquet)


if __name__ == "__main__":
    sys.exit(main())
