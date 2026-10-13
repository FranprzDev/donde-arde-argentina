"""Copernicus Sentinel-2 L2A true-colour crops (open data, via the Microsoft Planetary Computer mirror, collection sentinel-2-l2a,
asset 'visual' = TCI). usage: python3 s2.py name lon0 lat0 lon1 lat1 date_from date_to [maxcloud]"""
import sys, requests, rasterio, numpy as np, json
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.transform import from_bounds
from PIL import Image
name, lon0, lat0, lon1, lat1, d0, d1 = sys.argv[1], *map(float, sys.argv[2:6]), sys.argv[6], sys.argv[7]
mc = float(sys.argv[8]) if len(sys.argv) > 8 else 20
tok = requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a").json()["token"]
r = requests.post("https://planetarycomputer.microsoft.com/api/stac/v1/search", json={"collections": ["sentinel-2-l2a"], "bbox": [lon0, lat0, lon1, lat1],
    "datetime": f"{d0}/{d1}", "limit": 200, "query": {"eo:cloud_cover": {"lt": mc}}}).json()
fs = r["features"]
from shapely.geometry import shape, box
bb = box(lon0, lat0, lon1, lat1)
cov = [(f, shape(f["geometry"]).intersection(bb).area / bb.area) for f in fs]
from shapely.ops import unary_union
bydate = {}
for f, c in cov: bydate.setdefault(f["properties"]["datetime"][:10], []).append(f)
cand = []
for dte, its in bydate.items():
    u = unary_union([shape(f["geometry"]) for f in its]).intersection(bb).area / bb.area
    if u > 0.995: cand.append((max(f["properties"]["eo:cloud_cover"] for f in its), dte, its))
cand.sort(key=lambda x: x[0])
print(len(fs), "items;", [(d, round(cc, 1), len(i)) for cc, d, i in cand[:6]])
ITEMS = cand[0][2]; f = ITEMS[0]
Wpx = 1400; Hpx = int(Wpx * (lat1 - lat0) / ((lon1 - lon0) * np.cos(np.radians((lat0 + lat1) / 2))))
dst = np.zeros((3, Hpx, Wpx), np.uint8); dt = from_bounds(lon0, lat0, lon1, lat1, Wpx, Hpx)
for it in ITEMS:
    tmp = np.zeros_like(dst)
    with rasterio.open(it["assets"]["visual"]["href"] + "?" + tok) as s:
        for b in range(3):
            reproject(rasterio.band(s, b + 1), tmp[b], dst_transform=dt, dst_crs="EPSG:4326", resampling=Resampling.average)
    fill = (dst.sum(0) == 0) & (tmp.sum(0) > 0)
    dst[:, fill] = tmp[:, fill]
Image.fromarray(dst.transpose(1, 2, 0)).save(f"{name}.jpg", quality=92)
json.dump(dict(ids=[i["id"] for i in ITEMS], id=f["id"], date=f["properties"]["datetime"], cloud=f["properties"]["eo:cloud_cover"], bbox=[lon0, lat0, lon1, lat1]), open(f"{name}.json", "w"))
print("saved", name, f["id"], f["properties"]["datetime"], Hpx, Wpx)
