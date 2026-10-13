"""v2 numbers: every figure shown on screen is computed here from the open data files and written to data/stats_v2.json.
Inputs
  ../data/stats.json, ../data/points.npz  (NASA FIRMS VIIRS S-NPP 375 m, Argentina 2012-2025, type 0, conf n/h; built by ../prep_data.py)
  ../data/ciam_416.csv  (Min. Ambiente / CIAM: «Superficie afectada por incendios reportados, por jurisdicción», 2017-2026, hectáreas)
  data/causas_stats.json (built by causas.py from «Causas y cantidad de incendios por provincia», Min. Ambiente, 1993-2019)
Run: python3 causas.py && python3 prep_v2.py"""
import json, os, csv, statistics
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); D1 = os.path.join(HERE, "..", "data"); D2 = os.path.join(HERE, "data")
S = json.load(open(os.path.join(D1, "stats.json")))
C = json.load(open(os.path.join(D2, "causas_stats.json")))
P = np.load(os.path.join(D1, "points.npz"))
CODES = sorted(json.load(open(os.path.join(HERE, "..", "..", "data", "natgeo_v7.json")))["prov"])
t, lon, lat, pr = P["t"], P["lon"], P["lat"], P["prov"]
yr = (2012 + t // 12).astype(int); mo = (t % 12).astype(int)
def pmask(code): return pr == CODES.index(code)
BY = {int(k): v for k, v in S["by_year"].items()}; BPY = S["by_prov_year"]
# ---- CIAM hectares by jurisdiction (dt_id=416) ----
HA = {}
with open(os.path.join(D1, "ciam_416.csv"), encoding="utf-8") as f:
    for row in csv.DictReader(f, delimiter=";"):
        HA[row["jurisdicción"]] = {int(k.split("_")[1]): (None if v in ("s/d", "") else float(v)) for k, v in row.items() if k.startswith("hect")}
out = {}
# ---- national ----
monthly = np.bincount(np.floor(t).astype(int), minlength=168)[:168]
assert monthly.sum() == S["total_used"] == 2550467
assert all(int(monthly[(y - 2012) * 12:(y - 2011) * 12].sum()) == BY[y] for y in BY)
out["monthly"] = monthly.tolist()
out["total"] = S["total_used"]; out["y2020"] = BY[2020]; out["median_others"] = S["median_excl_2020"]
out["ratio_2020"] = BY[2020] / S["median_excl_2020"]
out["share_aug_sep"] = S["share_aug_sep"]; out["share_norte"] = S["share_norte_NEA_NOA"]
# ---- stop 1: Entre Ríos (Delta del Paraná) 2020 ----
er = {int(k): v for k, v in BPY["Entre Ríos"].items()}
er_med = statistics.median([er[y] for y in range(2012, 2020)])
out["er"] = dict(y2020=er[2020], median_2012_2019=er_med, ratio=er[2020] / er_med, jul_aug_2020=int((pmask("30") & (yr == 2020) & ((mo == 6) | (mo == 7))).sum()),
                 max_2012_2019=max(er[y] for y in range(2012, 2020)))
# ---- stop 2: Córdoba 2020 ----
cb = {int(k): v for k, v in BPY["Córdoba"].items()}
out["cba"] = dict(y2020=cb[2020], prev_max=max(v for y, v in cb.items() if y != 2020), ha_2020_ciam416=HA["Córdoba"][2020],
                  ha_max_2017_2025=max(v for y, v in HA["Córdoba"].items() if v and y <= 2025),
                  sep_oct_2020=int((pmask("14") & (yr == 2020) & ((mo == 8) | (mo == 9))).sum()))
# ---- stop 3: Corrientes Jan-Feb 2022 ----
co = {int(k): v for k, v in BPY["Corrientes"].items()}
jf = int((pmask("18") & (yr == 2022) & (mo <= 1)).sum())
out["corr"] = dict(janfeb_2022=jf, y2022=co[2022], max_year_2012_2019=max(co[y] for y in range(2012, 2020)), ha_2022_ciam416=HA["Corrientes"][2022])
assert jf > out["corr"]["max_year_2012_2019"]
# ---- stop 4: Chubut 2025 ----
ch = {int(k): v for k, v in BPY["Chubut"].items()}
m = pmask("26") & (yr == 2025)
out["chubut"] = dict(y2025=ch[2025], ha_2025_ciam416=HA["Chubut"][2025], cordillera_2025=int((m & (lon < -70.5)).sum()),
                     share_cordillera=float((m & (lon < -70.5)).sum() / m.sum()), ha_per_foco=HA["Chubut"][2025] / ch[2025],
                     formosa_2025_focos=int(S["by_prov_year"]["Formosa"]["2025"]), formosa_2025_ha=HA["Formosa"][2025])
# ---- stop 5: Formosa ----
bp = S["by_prov"]; rank = sorted(bp, key=bp.get, reverse=True)
out["formosa"] = dict(total=bp["Formosa"], rank=rank.index("Formosa") + 1, share=bp["Formosa"] / S["total_used"], second=rank[1], second_val=bp[rank[1]])
# ---- causes (1993-2019) ----
a = C["all_1993_2019"]
out["causas"] = dict(total=a["total"], humana=a["negligencia"] + a["intencional"], negligencia=a["negligencia"], intencional=a["intencional"],
                     natural=a["natural"], desconocida=a["desconocida"], conocida=a["conocida"],
                     humana_sobre_conocida=a["humana_sobre_conocida"], natural_sobre_conocida=a["natural_sobre_conocida"],
                     desconocida_sobre_total=a["desconocida_sobre_total"], humana_sobre_total=a["humana_sobre_total"],
                     negl_sobre_conocida=a["negligencia"] / a["conocida"], int_sobre_conocida=a["intencional"] / a["conocida"],
                     prov={p: dict(humana_sobre_conocida=C["by_prov"][p]["humana_sobre_conocida"], desconocida_sobre_total=C["by_prov"][p]["desconocida_sobre_total"])
                           for p in ("Entre Ríos", "Córdoba", "Corrientes", "Chubut", "Formosa", "La Pampa")})
json.dump(out, open(os.path.join(D2, "stats_v2.json"), "w"), indent=1, ensure_ascii=False)
if __name__ == "__main__":
    for k, v in out.items():
        if k != "monthly": print(k, v)
    print("monthly max", int(monthly.max()), "at", int(monthly.argmax()), "| top months", [(int(i), int(monthly[i])) for i in np.argsort(-monthly)[:6]])
