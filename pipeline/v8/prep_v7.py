"""v7 · province ranking by DISTINCT burned area (each 500 m pixel counted once if it burned at least once in 2012-2025; v6 counted repeat burns).
v6 docstring: province ranking (all 24 jurisdictions). Inputs already in the project, nothing new downloaded:
- MODIS MCD64A1 C6.1 burned area per province and month (data/burn_stats.json, built by prep_burn.py; repeat burns counted)
- data/scar_count.npy (months burned per 500 m pixel, 2012-2025) + the same INDEC province raster -> distinct burned ha per province
- VIIRS S-NPP 375 m hotspots 2012-2025 (../data/points.npz, prov assigned with the INDEC polygons) -> focos per province
Output: data/ranking_v7.json"""
import json, math, os, numpy as np, shapely
from rasterio.features import rasterize
from rasterio.transform import Affine
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
BS = json.load(open("data/burn_stats.json")); GR = json.load(open("data/scar_grid.json"))
NG = json.load(open("./contar-con-datos-agua/v7/data/natgeo_v7.json")); codes = sorted(NG["prov"])
NAMES = {f["properties"]["id"]: f["properties"]["nombre"] for f in json.load(open("data/provincias.geojson"))["features"]}
NAMES["94"] = "Tierra del Fuego"; NAMES["02"] = "CABA"
H, W, D = GR["H"], GR["W"], GR["D"]
TR = Affine(D, 0, GR["LON0"], 0, -D, GR["LAT1"])
PROV = rasterize([(shapely.Polygon(r), i + 1) for i, c in enumerate(codes) for r in NG["prov"][c]], out_shape=(H, W), transform=TR, fill=0, dtype="uint8")
lat_c = GR["LAT1"] - (np.arange(H) + 0.5) * D
PIXHA = ((6371007.181 * math.radians(D)) ** 2 * np.cos(np.radians(lat_c)) / 1e4)
CNT = np.load("data/scar_count.npy")
pixha = np.broadcast_to(PIXHA[:, None], (H, W))
uniq = np.bincount(PROV[CNT > 0], weights=pixha[CNT > 0], minlength=len(codes) + 1)
area = np.bincount(PROV.ravel(), weights=pixha.ravel(), minlength=len(codes) + 1)
P = np.load("../data/points.npz"); PRV = P["prov"]; TS = P["t"]
foc = np.bincount(PRV[TS < 168], minlength=len(codes))
rows = []
for i, c in enumerate(codes):
    rows.append(dict(code=c, name=NAMES[c], ha_total=BS["by_prov_total_ha_2012_2025"][c], ha_unique=float(uniq[i + 1]), area_ha=float(area[i + 1]),
                     focos=int(foc[i])))
for r in rows:
    r["share_unique"] = r["ha_unique"] / r["area_ha"] if r["area_ha"] else 0
    r["focos_per_1000km2"] = r["focos"] / (r["area_ha"] / 1e5) if r["area_ha"] else 0
tot = sum(r["ha_total"] for r in rows)
assert abs(tot - BS["total_ha_2012_2025"]) / tot < 1e-6, (tot, BS["total_ha_2012_2025"])
assert sum(r["focos"] for r in rows) == 2550467, sum(r["focos"] for r in rows)
for k in ("ha_total", "ha_unique", "focos", "share_unique", "focos_per_1000km2"):
    for j, r in enumerate(sorted(rows, key=lambda r: -r[k])): r["rank_" + k] = j + 1
rows.sort(key=lambda r: r["rank_ha_unique"])
for r in rows: r["rank"] = r["rank_ha_unique"]
tot_u = sum(r["ha_unique"] for r in rows); tot_area = sum(r["area_ha"] for r in rows)
assert abs(tot_u - float(pixha[CNT > 0].sum())) / tot_u < 1e-3, (tot_u, float(pixha[CNT > 0].sum()))   # every burned pixel falls in some province
top5 = sum(r["ha_unique"] for r in rows[:5])
out = dict(metric="MODIS MCD64A1 C6.1, distinct area burned at least once 2012-2025 (500 m pixels, geodesic pixel area), ha", rows=rows,
           total_ha_unique=tot_u, total_ha_repeat=tot, country_area_ha=tot_area, share_country_burned=tot_u / tot_area, top5_share=top5 / tot_u,
           top5_share_repeat_metric=sum(r["ha_total"] for r in sorted(rows, key=lambda r: -r["ha_total"])[:5]) / tot,
           top5_focos_share=sum(r["focos"] for r in sorted(rows, key=lambda r: -r["focos"])[:5]) / 2550467)
json.dump(out, open("data/ranking_v7.json", "w"), ensure_ascii=False, indent=1)
print(f"{'#':>2} {'prov':22} {'ha_total':>10} {'ha_uniq':>10} {'%terr':>6} {'focos':>8} {'#f':>3} {'f/1000km2':>9} {'#d':>3}")
for r in rows:
    print(f"{r['rank']:>2} {r['name'][:22]:22} {r['ha_total']:>10.0f} {r['ha_unique']:>10.0f} {100*r['share_unique']:>6.1f} {r['focos']:>8} {r['rank_focos']:>3} {r['focos_per_1000km2']:>9.0f} {r['rank_focos_per_1000km2']:>3}")
print("top5 share uniq", out["top5_share"], "tot_u", tot_u, "share country", tot_u / tot_area, "top5 repeat", out["top5_share_repeat_metric"], "top5 share focos", out["top5_focos_share"], "uniq sum", sum(r['ha_unique'] for r in rows))
