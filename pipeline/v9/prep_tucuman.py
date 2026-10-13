"""Tucumán · quema en la zafra. FIRMS VIIRS points (../data/points.npz, same filter as the whole video) inside Tucumán (INDEC province
'90', same assignment as prep_data.py) -> department (IGN departments via georef, data/departamentos.geojson) -> cane zone =
the 12 departments with > 5.000 ha of harvestable sugarcane in EEAOC Reporte Agroindustrial 370 (zafra 2026, Table 1),
which together hold 99,85 % of the province's cane. Zafra months = May-November. Output data/tucuman_stats.json"""
import json, numpy as np, shapely, csv, unicodedata
ALIAS = {"jbalberdi": "juanbautistaalberdi"}
def norm(s): return ALIAS.get(unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(".", "").replace(" ", ""), unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(".", "").replace(" ", ""))
P = np.load("../data/points.npz"); codes = sorted(json.load(open(os.path.join(HERE, "..", "..", "data", "natgeo_v7.json")))["prov"])
iT = codes.index("90")
m = P["prov"] == iT
lon, lat, t = P["lon"][m].astype(float), P["lat"][m].astype(float), P["t"][m].astype(float)
year = 2012 + (t // 12).astype(int); month = (t % 12).astype(int) + 1
G = json.load(open("data/departamentos.geojson"))
deps = [f for f in G["features"] if f["properties"]["provincia"]["id"] == "90"]
cane = {norm(r["departamento"]): int(r["total_ha"]) for r in csv.DictReader(open("data/eeaoc_ra370_cana_departamentos.csv"))}
CANE12 = {k for k, v in cane.items() if v > 5000}
assert len(CANE12) == 12
dep_of = np.full(len(lon), "", object)
geoms = []
for f in deps:
    g = shapely.geometry.shape(f["geometry"]).buffer(0); shapely.prepare(g); geoms.append((f["properties"]["nombre"], g))
    dep_of[shapely.contains_xy(g, lon, lat) & (dep_of == "")] = f["properties"]["nombre"]
miss = dep_of == ""
if miss.any():                       # points on simplified edges -> nearest department
    pts = shapely.points(lon[miss], lat[miss]); d = np.stack([shapely.distance(g, pts) for _, g in geoms], 1)
    dep_of[np.where(miss)[0]] = [geoms[i][0] for i in d.argmin(1)]
names = sorted({n for n, _ in geoms}); assert {norm(n) for n in names} >= CANE12, ({norm(n) for n in names}, CANE12)
in_cane = np.array([norm(x) in CANE12 for x in dep_of])
zafra = (month >= 5) & (month <= 11)
cane_share = sum(cane[k] for k in CANE12) / sum(cane.values())
S = dict(total=int(m.sum()), zafra=int(zafra.sum()), cane=int(in_cane.sum()), cane_zafra=int((in_cane & zafra).sum()),
         share_zafra=float(zafra.mean()), share_cane=float(in_cane.mean()), share_cane_zafra=float((in_cane & zafra).mean()),
         cane_area_share_12=cane_share, cane_ha_tucuman=sum(cane.values()), by_month={int(k): int((month == k).sum()) for k in range(1, 13)},
         by_year={int(y): int((year == y).sum()) for y in range(2012, 2026)},
         by_year_cane_zafra={int(y): int(((year == y) & in_cane & zafra).sum()) for y in range(2012, 2026)},
         area_cane12_km2=None, area_tuc_km2=None, by_dep={n: int((dep_of == n).sum()) for n in names}, cane12=sorted(CANE12))
from pyproj import Geod
geod = Geod(ellps="WGS84")
def area(g): return abs(geod.geometry_area_perimeter(g)[0]) / 1e6
S["area_cane12_km2"] = sum(area(g) for n, g in geoms if norm(n) in CANE12); S["area_tuc_km2"] = sum(area(g) for _, g in geoms)
# context: density in the cane zone during the zafra vs the rest of the country (focos per 1000 km2 per year)
S["dens_cane_zafra_per1000km2_yr"] = S["cane_zafra"] / S["area_cane12_km2"] * 1000 / 14
json.dump(S, open("data/tucuman_stats.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in S.items() if k not in ("by_dep",)}, ensure_ascii=False, indent=1)); print(S["by_dep"])
