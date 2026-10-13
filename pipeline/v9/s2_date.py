"""Copernicus Sentinel-2 L2A true colour (asset 'visual' = TCI, open data) for ONE acquisition date, via the Microsoft Planetary
Computer STAC mirror (collection sentinel-2-l2a). Mosaics every tile of that date over the bbox, reprojected to EPSG:4326.
usage: python3 s2_date.py name lon0 lat0 lon1 lat1 YYYY-MM-DD width_px"""
import sys, json, requests, rasterio, numpy as np
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from PIL import Image
name = sys.argv[1]; lon0, lat0, lon1, lat1 = map(float, sys.argv[2:6]); day = sys.argv[6]; Wpx = int(sys.argv[7])
tok = requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a").json()["token"]
r = requests.post("https://planetarycomputer.microsoft.com/api/stac/v1/search", json={"collections": ["sentinel-2-l2a"],
    "bbox": [lon0, lat0, lon1, lat1], "datetime": f"{day}T00:00:00Z/{day}T23:59:59Z", "limit": 50}).json()
its = r["features"]
# keep the newest processing baseline per tile
best = {}
for f in its:
    tile = f["properties"]["s2:mgrs_tile"]
    if tile not in best or f["id"] > best[tile]["id"]: best[tile] = f
its = list(best.values())
Hpx = int(Wpx * (lat1 - lat0) / ((lon1 - lon0) * np.cos(np.radians((lat0 + lat1) / 2))))
dst = np.zeros((3, Hpx, Wpx), np.uint8); dt = from_bounds(lon0, lat0, lon1, lat1, Wpx, Hpx)
for it in its:
    tmp = np.zeros_like(dst)
    with rasterio.open(it["assets"]["visual"]["href"] + "?" + tok) as s:
        for b in range(3):
            reproject(rasterio.band(s, b + 1), tmp[b], dst_transform=dt, dst_crs="EPSG:4326", resampling=Resampling.average)
    fill = (dst.sum(0) == 0) & (tmp.sum(0) > 0); dst[:, fill] = tmp[:, fill]
Image.fromarray(dst.transpose(1, 2, 0)).save(f"{name}.jpg", quality=93)
json.dump(dict(ids=sorted(i["id"] for i in its), date=its[0]["properties"]["datetime"], cloud={i["id"]: i["properties"]["eo:cloud_cover"] for i in its},
               bbox=[lon0, lat0, lon1, lat1], source="Copernicus Sentinel-2 L2A (ESA), via Microsoft Planetary Computer", license="Copernicus open data (free, full and open; attribution: 'Contains modified Copernicus Sentinel data <year>')"),
          open(f"{name}.json", "w"), indent=1)
print("saved", name, [i["id"] for i in its], Hpx, Wpx)
