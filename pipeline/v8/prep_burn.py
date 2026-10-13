"""v4 · burned area. MODIS MCD64A1 Collection 6.1 (500 m, monthly), UMD 'Win06'+'Win07' GeoTIFF windows (lat/lon grid
0.00439453125 deg), fetched by burn/fetch_umd.py -> burn/umd/YYYY-MM.npz (2012-01 .. 2026-07).
A pixel counts as burned in a month when burndate > 0. Pixel area = (R*d)^2 * cos(lat), R = 6371007.181 m (MODIS sphere).
Only pixels inside Argentina (INDEC Censo 2022 province polygons, same as the hotspot assignment) are counted.
Outputs: data/burn_stats.json (every number the video uses), data/scar_*.npy rasters for the renderer."""
import json, os, glob, math, numpy as np, shapely
from rasterio.features import rasterize
from rasterio.transform import Affine
from pyproj import Geod
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
D = 0.00439453125
files = sorted(glob.glob("burn/umd/20*.npz"))
months = [os.path.basename(f)[:7] for f in files]
z0 = np.load(files[0])
LON0, LAT1 = float(min(z0["t6"][2], z0["t7"][2])), float(z0["t6"][5])      # common grid: west edge, north edge (Win06/Win07 differ by 0.1 px)
def place(a, t):
    """column/row offset of a window array inside the common grid"""
    c0 = int(round((t[2] - LON0) / D)); r0 = int(round((LAT1 - t[5]) / D)); return r0, c0
r6, c6 = place(z0["a6"], z0["t6"]); r7, c7 = place(z0["a7"], z0["t7"])
H = max(r6 + z0["a6"].shape[0], r7 + z0["a7"].shape[0]); W = max(c6 + z0["a6"].shape[1], c7 + z0["a7"].shape[1])
TR = Affine(D, 0, LON0, 0, -D, LAT1)
lat_c = LAT1 - (np.arange(H) + 0.5) * D
R = 6371007.181
PIXHA = ((R * math.radians(D)) ** 2 * np.cos(np.radians(lat_c)) / 1e4).astype(np.float64)      # ha per pixel, by row
NG = json.load(open("./contar-con-datos-agua/v7/data/natgeo_v7.json"))
codes = sorted(NG["prov"])
PROV = rasterize([(shapely.Polygon(r), i + 1) for i, c in enumerate(codes) for r in NG["prov"][c]], out_shape=(H, W), transform=TR, fill=0, dtype="uint8")
def grid(f):
    z = np.load(f); g = np.zeros((H, W), np.int16)
    g[r6:r6 + z["a6"].shape[0], c6:c6 + z["a6"].shape[1]] = z["a6"]
    a7 = z["a7"]; g[r7:r7 + a7.shape[0], c7:c7 + a7.shape[1]] = np.where(a7 != 0, a7, g[r7:r7 + a7.shape[0], c7:c7 + a7.shape[1]])
    return g
COUNT = np.zeros((H, W), np.uint8)                # number of months burned, 2012-2025 (repeat burns counted)
LASTY = np.zeros((H, W), np.uint8)                # last burn year - 2000
monthly_ha = {}; prov_month_ha = {}
EV = {"corr_2022": np.zeros((H, W), bool), "er_2020": np.zeros((H, W), bool), "pat_2025": np.zeros((H, W), bool), "pat_2026": np.zeros((H, W), bool)}
COMARCA = (-71.80, -42.62, -71.05, -41.75)       # Comarca Andina box: El Bolsón, Mallín Ahogado, Lago Puelo, El Hoyo, Epuyén, Cholila
cb = (int((LAT1 - COMARCA[3]) / D), int((LAT1 - COMARCA[1]) / D), int((COMARCA[0] - LON0) / D), int((COMARCA[2] - LON0) / D))
CMASK = np.zeros((H, W), bool); CMASK[cb[0]:cb[1], cb[2]:cb[3]] = True
iCO, iER = codes.index("18") + 1, codes.index("30") + 1
for f, ym in zip(files, months):
    y, m = int(ym[:4]), int(ym[5:])
    b = (grid(f) > 0) & (PROV > 0)
    ha_rows = b.sum(1) * PIXHA
    monthly_ha[ym] = float(ha_rows.sum())
    pm = np.bincount(PROV[b], weights=np.broadcast_to(PIXHA[:, None], (H, W))[b], minlength=len(codes) + 1)
    prov_month_ha[ym] = {codes[i - 1]: float(pm[i]) for i in range(1, len(codes) + 1) if pm[i] > 0}
    if y <= 2025:
        COUNT[b] = np.minimum(255, COUNT[b].astype(int) + 1); LASTY[b] = y - 2000
    if (y, m) in ((2022, 1), (2022, 2)): EV["corr_2022"] |= b & (PROV == iCO)
    if y == 2020: EV["er_2020"] |= b & (PROV == iER)
    if y == 2025 and m <= 3: EV["pat_2025"] |= b & CMASK
    if y == 2026 and m <= 3: EV["pat_2026"] |= b & CMASK
    print(ym, round(monthly_ha[ym]), flush=True)
def ha(mask): return float((mask.sum(1) * PIXHA).sum())
yrs = range(2012, 2026)
S = {}
S["months"] = months
S["missing_months"] = [f"{y}-{m:02d}" for y in range(2012, 2027) for m in range(1, 13) if (y, m) <= (2026, 7) and f"{y}-{m:02d}" not in months]
S["total_ha_2012_2025"] = sum(v for k, v in monthly_ha.items() if int(k[:4]) <= 2025)          # repeat burns counted
S["unique_ha_2012_2025"] = ha(COUNT > 0)                                                           # burned at least once
S["by_year_ha"] = {y: sum(v for k, v in monthly_ha.items() if int(k[:4]) == y) for y in range(2012, 2027)}
S["ha_2026_jan_jul"] = S["by_year_ha"][2026]
S["corr_janfeb_2022_ha"] = sum(prov_month_ha[k].get("18", 0) for k in ("2022-01", "2022-02"))
S["corr_unique_janfeb_2022_ha"] = ha(EV["corr_2022"])
S["er_2020_ha"] = sum(prov_month_ha[k].get("30", 0) for k in months if k.startswith("2020"))
S["er_unique_2020_ha"] = ha(EV["er_2020"])
S["comarca_2025_q1_ha"] = ha(EV["pat_2025"]); S["comarca_2026_q1_ha"] = ha(EV["pat_2026"])
S["comarca_box"] = COMARCA
S["by_prov_total_ha_2012_2025"] = {c: sum(prov_month_ha[k].get(c, 0) for k in months if int(k[:4]) <= 2025) for c in codes}
S["prov_area_ha"] = {c: float(np.bincount(PROV.ravel(), weights=np.broadcast_to(PIXHA[:, None], (H, W)).ravel(), minlength=len(codes) + 1)[i + 1]) for i, c in enumerate(codes)}
# CABA, IGN boundary (georef, data/provincias.geojson): real-scale silhouette + area
G = json.load(open("data/provincias.geojson"))
caba = shapely.geometry.shape([f for f in G["features"] if f["properties"]["id"] == "02"][0]["geometry"])
S["caba_ha"] = abs(Geod(ellps="WGS84").geometry_area_perimeter(caba)[0]) / 1e4
S["caba_ring"] = [list(map(float, p)) for p in caba.exterior.coords]
S["pitch_ha"] = 105 * 68 / 1e4                                       # FIFA recommended pitch 105 x 68 m = 0,714 ha
seconds_14y = (np.datetime64("2026-01-01") - np.datetime64("2012-01-01")).astype("timedelta64[s]").astype(float)
S["seconds_2012_2025"] = seconds_14y
S["pitch_every_s"] = seconds_14y / (S["total_ha_2012_2025"] / S["pitch_ha"])
secs_cf = (np.datetime64("2022-03-01") - np.datetime64("2022-01-01")).astype("timedelta64[s]").astype(float)
S["corr_pitch_every_s"] = secs_cf / (S["corr_janfeb_2022_ha"] / S["pitch_ha"])
S["n_caba_corr"] = S["corr_janfeb_2022_ha"] / S["caba_ha"]
S["n_caba_total"] = S["total_ha_2012_2025"] / S["caba_ha"]
S["n_caba_er2020"] = S["er_2020_ha"] / S["caba_ha"]
json.dump(S, open("data/burn_stats.json", "w"), ensure_ascii=False, indent=1)
# rasters for the renderer (uint8), pyramid built at load time
np.save("data/scar_count.npy", COUNT); np.save("data/scar_lasty.npy", LASTY)
for k, v in EV.items(): np.save(f"data/scar_{k}.npy", np.packbits(v, axis=None)); 
json.dump(dict(H=H, W=W, D=D, LON0=LON0, LAT1=LAT1), open("data/scar_grid.json", "w"))
print(json.dumps({k: v for k, v in S.items() if k not in ("months", "caba_ring", "by_prov_total_ha_2012_2025", "prov_area_ha", "by_year_ha")}, indent=1))
print({k: round(v) for k, v in S["by_year_ha"].items()})
