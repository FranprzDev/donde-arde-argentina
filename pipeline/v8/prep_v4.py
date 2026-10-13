"""v4: gathers every number shown on screen into data/stats_v4.json, computed from saved open data, with asserts.
Inputs: ../data/points.npz (NASA FIRMS VIIRS, prep_data.py), data/stats_v2.json (v2/v3 numbers), data/burn_stats.json (prep_burn.py,
MODIS MCD64A1), data/tucuman_stats.json (prep_tucuman.py), data/patagonia_facts.json (official figures typed from cited pages)."""
import json, numpy as np
V = json.load(open("data/stats_v2.json")); B = json.load(open("data/burn_stats.json")); T = json.load(open("data/tucuman_stats.json"))
P = np.load("../data/points.npz"); codes = sorted(json.load(open("./contar-con-datos-agua/v7/data/natgeo_v7.json"))["prov"])
yr = 2012 + (P["t"] // 12).astype(int); mo = (P["t"] % 12).astype(int) + 1; lon, lat = P["lon"], P["lat"]
S = {}
# --- Entre Ríos 2020 vs explicit baselines
er = P["prov"] == codes.index("30")
ery = {y: int((er & (yr == y)).sum()) for y in range(2012, 2026)}
assert ery[2020] == V["er"]["y2020"]
S["er_2020"] = ery[2020]; S["er_median_2012_2019"] = float(np.median([ery[y] for y in range(2012, 2020)]))
S["er_median_other13"] = float(np.median([v for y, v in ery.items() if y != 2020]))
S["er_ratio_2012_2019"] = ery[2020] / S["er_median_2012_2019"]; S["er_ratio_other13"] = ery[2020] / S["er_median_other13"]
S["er_by_year"] = ery
# --- Andean Patagonia (Neuquén, Río Negro, Chubut, Santa Cruz west of 70.5 W; same meridian as v2's Chubut 'cordillera' box)
pat = np.isin(P["prov"], [codes.index(c) for c in ("58", "62", "26", "78")]) & (lon < -70.5)
S["cord_total"] = int(pat.sum()); S["cord_share_decmar"] = float((pat & np.isin(mo, [12, 1, 2, 3])).sum() / pat.sum())
S["cord_share_janfeb"] = float((pat & np.isin(mo, [1, 2])).sum() / pat.sum())
# --- national burned area (MODIS MCD64A1)
S["burn_total_ha"] = B["total_ha_2012_2025"]; S["burn_unique_ha"] = B["unique_ha_2012_2025"]
S["land_ha"] = sum(v for c, v in B["prov_area_ha"].items())
S["unique_share_land"] = B["unique_ha_2012_2025"] / S["land_ha"]
S["pitch_every_s"] = B["pitch_every_s"]; S["n_caba_total"] = B["n_caba_total"]
S["corr_janfeb_2022_ha"] = B["corr_janfeb_2022_ha"]; S["n_caba_corr"] = B["n_caba_corr"]; S["caba_ha"] = B["caba_ha"]
S["corr_focos_janfeb_2022"] = V["corr"]["janfeb_2022"]
S["er_2020_ha"] = B["er_2020_ha"]
S["comarca_2025_ha"] = B["comarca_2025_q1_ha"]; S["comarca_2026_ha"] = B["comarca_2026_q1_ha"]
S["comarca_ratio"] = B["comarca_2026_q1_ha"] / B["comarca_2025_q1_ha"]
# --- Tucumán
S["tuc"] = {k: T[k] for k in ("total", "zafra", "cane_zafra", "share_zafra", "share_cane_zafra", "cane_ha_tucuman")}
# --- official human figures (not computed: typed from the cited official pages, see sources.md)
S["pat_facts"] = json.load(open("data/patagonia_facts.json"))
# --- causes, total, shares (v2/v3)
S["total_focos"] = V["total"]; S["share_aug_sep"] = V["share_aug_sep"]; S["share_norte"] = V["share_norte"]; S["causas"] = V["causas"]
json.dump(S, open("data/stats_v4.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in S.items() if k not in ("causas", "er_by_year")}, ensure_ascii=False, indent=1)); print(ery)
