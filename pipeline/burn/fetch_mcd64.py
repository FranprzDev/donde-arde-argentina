"""MODIS MCD64A1 v6.1 (500 m monthly burned area), Argentina tiles, 2012-01..latest, from the open Microsoft Planetary Computer
mirror (COG copy of the LP DAAC product, collection modis-64A1-061, anonymous SAS token). Saves every burned pixel
(tile h,v, row, col, burn day-of-year) per month -> raw/YYYY-MM.npz"""
import requests, rasterio, numpy as np, os, sys, json, time
from concurrent.futures import ThreadPoolExecutor
os.makedirs("raw", exist_ok=True)
BBOX = [-74, -55.2, -53.5, -21.7]
def token(): return requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/token/modiseuwest/modis-061-cogs").json()["token"]
TOK = [token(), time.time()]
def tok():
    if time.time() - TOK[1] > 1800: TOK[0] = token(); TOK[1] = time.time()
    return TOK[0]
def items(y, m):
    import calendar
    d1 = f"{y}-{m:02d}-01"; d2 = f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]}"
    r = requests.post("https://planetarycomputer.microsoft.com/api/stac/v1/search", json={"collections": ["modis-64A1-061"], "bbox": BBOX, "datetime": f"{d1}/{d2}", "limit": 100}).json()
    return r["features"]
def read(f):
    for k in range(4):
        try:
            with rasterio.open(f["assets"]["Burn_Date"]["href"] + "?" + tok()) as s: a = s.read(1)
            r, c = np.nonzero(a > 0)
            hv = f["id"].split(".")[2]
            return hv, r.astype(np.int16), c.astype(np.int16), a[r, c].astype(np.int16)
        except Exception as e:
            err = e; time.sleep(3)
    raise err
def month(ym):
    y, m = ym; out = f"raw/{y}-{m:02d}.npz"
    if os.path.exists(out): return
    fs = items(y, m)
    if not fs: print("none", y, m, flush=True); return
    res = [read(f) for f in fs]
    np.savez_compressed(out, hv=np.array([x[0] for x in res]), **{f"{x[0]}_{k}": x[i + 1] for x in res for i, k in enumerate("rcd")}, ids=np.array([f["id"] for f in fs]))
    print(y, m, len(fs), sum(len(x[1]) for x in res), flush=True)
yms = [(y, m) for y in range(2012, 2027) for m in range(1, 13) if (y, m) <= (2026, 9)]
with ThreadPoolExecutor(12) as ex: list(ex.map(month, yms))
print("FETCH_DONE")
