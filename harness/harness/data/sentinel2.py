"""Adapter: Copernicus Sentinel-2 L2A true colour for ONE date over a bbox (open data), via the Microsoft Planetary
Computer STAC mirror (collection sentinel-2-l2a, asset 'visual' = TCI). Mosaics every tile of that date, reprojected
to EPSG:4326, and writes NAME.jpg + NAME.json (bbox, date, tile ids, cloud cover, licence) — exactly what the
`image` loader and the satellite_zoom / before_after beats read.

  python -m harness.data.sentinel2 --name stories/x/data/s2/tuc_2025-09-23 --bbox -64.9 -26.8 -64.5 -26.5 \
         --date 2025-09-23 --width 1800

  python -m harness.data.sentinel2 --search --bbox ... --from 2025-09-01 --to 2025-09-30   # list dates + cloud cover

Credit on screen: "Contiene datos Copernicus Sentinel-2 modificados (AÑO)"."""
import argparse
import json
import sys

import numpy as np

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a"


def search(bbox, start, end, limit=100):
    import requests
    r = requests.post(STAC, json={"collections": ["sentinel-2-l2a"], "bbox": list(bbox),
                                  "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z", "limit": limit}, timeout=60).json()
    return r.get("features", [])


def fetch(name, bbox, day, width):
    import rasterio
    import requests
    from PIL import Image
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject
    lon0, lat0, lon1, lat1 = bbox
    tok = requests.get(TOKEN, timeout=60).json()["token"]
    its = search(bbox, day, day, 50)
    if not its:
        raise SystemExit(f"no Sentinel-2 L2A scene over {bbox} on {day}; try --search")
    best = {}
    for f in its:
        tile = f["properties"]["s2:mgrs_tile"]
        if tile not in best or f["id"] > best[tile]["id"]:
            best[tile] = f
    its = list(best.values())
    Hpx = int(width * (lat1 - lat0) / ((lon1 - lon0) * np.cos(np.radians((lat0 + lat1) / 2))))
    dst = np.zeros((3, Hpx, width), np.uint8); dt = from_bounds(lon0, lat0, lon1, lat1, width, Hpx)
    for it in its:
        tmp = np.zeros_like(dst)
        with rasterio.open(it["assets"]["visual"]["href"] + "?" + tok) as s:
            for b in range(3):
                reproject(rasterio.band(s, b + 1), tmp[b], dst_transform=dt, dst_crs="EPSG:4326", resampling=Resampling.average)
        fill = (dst.sum(0) == 0) & (tmp.sum(0) > 0); dst[:, fill] = tmp[:, fill]
    Image.fromarray(dst.transpose(1, 2, 0)).save(f"{name}.jpg", quality=93)
    meta = dict(ids=sorted(i["id"] for i in its), date=its[0]["properties"]["datetime"],
                cloud={i["id"]: i["properties"]["eo:cloud_cover"] for i in its}, bbox=[lon0, lat0, lon1, lat1],
                source="Copernicus Sentinel-2 L2A (ESA), via Microsoft Planetary Computer",
                license="Copernicus open data (free, full and open; attribution: 'Contains modified Copernicus Sentinel data <year>')")
    json.dump(meta, open(f"{name}.json", "w"), indent=1)
    print("saved", name, meta["ids"], Hpx, width)
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(prog="harness.data.sentinel2")
    ap.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--name"); ap.add_argument("--date"); ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--search", action="store_true"); ap.add_argument("--from", dest="start"); ap.add_argument("--to", dest="end")
    x = ap.parse_args(argv)
    if x.search:
        for f in sorted(search(x.bbox, x.start, x.end), key=lambda f: f["properties"]["datetime"]):
            p = f["properties"]; print(p["datetime"][:10], p["s2:mgrs_tile"], f"cloud {p['eo:cloud_cover']:.1f}%", f["id"])
        return
    if not (x.name and x.date):
        ap.error("--name and --date are required (or use --search)")
    fetch(x.name, x.bbox, x.date, x.width)


if __name__ == "__main__":
    sys.exit(main())
