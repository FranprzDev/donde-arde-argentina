"""Contar con Datos 2026 · Historia visual · v9 «¿Dónde arde Argentina?» (v8 + author's notes, 13-10-2026)
v9 changes:  1) intro: every sun ray (globe and flat map) lands ON Argentina and its streak visibly ends there;
             2) ONE visualization: no photo cuts and no headline cards. Tucumán and Entre Ríos end with a zoom INTO the same map down
                to a real Copernicus Sentinel-2 image (Burruyacú, Tucumán, 23/09/2025: smoke plumes in the cane zone in mid-zafra;
                islands of the Delta off Rosario, 23/09/2020), with that afternoon's VIIRS detections on top; the Comarca keeps its
                in-place Sentinel-2 before/after; 3) the Corrientes 2022 overlay (and its La Nación headline) is gone;
             4) much less text: <= ~12 words per beat, >= 48 px, every text held >= 0.35 s/word + 1 s (asserted); the «2.550.467
                focos» card, the second title, grey notes, ranking rows and the close header were removed rather than sped up.
(v8 header follows)
v8 changes:  structure = national overview (timelapse, total, ranking) -> 3 quick stops, each «map, then a hard cut to a real photo of
             that kind of fire»: Tucumán (cane / zafra) -> Entre Ríos, Delta del Paraná 2020 (grassland) -> Comarca Andina (forest).
             Close: «SABEMOS DÓNDE Y CUÁNDO ARDE» and the 911 line removed; the whole country (all 24 jurisdictions) is lit and the last
             map is everything that burned 2012-2025 (MODIS scar + every VIIRS hotspot) under «YA NO FALTAN DATOS. / FALTA RESPONSABILIDAD.».
             The 4 press headlines come back as verbatim quotes pinned to their place (Corrientes during the national scar card; the
             other three in their stops). Sources card credits every outlet, photo and flag.
(v7 header follows)
v7 changes:  ranking + national total by DISTINCT area burned at least once (26,6 M ha = 9,5 % of the country; top 5 = 53 %);
             hook title in the first second; direct zooms (cam_zoomto) ranking->Corrientes and Comarca->close; legend hidden while
             the Sentinel-2 frame flies in; Tucumán baseline (cane departments = 69 % of the province); area number slams on the boom.
(v6 header follows)
v6 changes:  1) province-to-province flights (no return to the national map between stops);
             2) a fast ranking of ALL 24 jurisdictions by MODIS burned area 2012-2025 (data/ranking_v7.json, prep_v6.py),
                collapsing to the top 5 (= 60 % of the national burned area); Corrientes (#4) opens the stops;
             3) much less text (no headlines, no grey footnotes except where a caveat is required, Entre Ríos stop and causes card
                removed); 4) intro with motion: sun rays reach the Earth, reflect, land on Argentina; then the turn:
                «EL SOL CALIENTA. / LA CHISPA ES HUMANA.» + «En 9 de cada 10 incendios con causa conocida» (Min. Ambiente 1993-2019)
                and a single code-drawn spark that ignites the 14-year VIIRS timelapse.
Close (v5) kept: «SABEMOS DÓNDE Y CUÁNDO ARDE.» -> «YA NO FALTAN DATOS. / FALTA RESPONSABILIDAD.» -> 911 line -> sources card.
Every number on screen is computed upstream (stats_v4.json, ranking_v7.json) and guarded by an assert. No AI imagery.
Usage: python3 render_v9.py --nums | --still t1 t2 ..."""
import json, math, os, sys
import numpy as np, cv2, shapely
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fx_v4 import *
import fx_v4 as FX
import space_v4 as SP
D1 = os.path.join(HERE, "..", "data"); D2 = os.path.join(HERE, "data"); AS = os.path.join(HERE, "assets")
WH = (242, 240, 236); MU = (190, 182, 172); AM = (255, 176, 60); OR = (255, 110, 30); RD = (255, 64, 40); HOT = (255, 226, 160)
ASH = (150, 142, 134)
GRAY_PX = 48

# ---------------- numbers (all computed upstream; asserts guard every wording) ----------------
S = json.load(open(os.path.join(D2, "stats_v4.json")))
RK = json.load(open(os.path.join(D2, "ranking_v7.json")))
def es_int(n): return f"{int(n):,}".replace(",", ".")
def es_dec(x, d=1): return f"{x:.{d}f}".replace(".", ",")
V = json.load(open(os.path.join(D2, "stats_v2.json")))
MONTHLY = np.array(V["monthly"], np.float64)
CA = S["causas"]; HUM_10 = int(round(CA["humana_sobre_conocida"] * 10)); assert HUM_10 == 9          # 90,2 % of fires with known cause
assert int(MONTHLY.sum()) == S["total_focos"]
BURN_M = int(S["burn_total_ha"] // 1e6); assert BURN_M == 44                        # v7: no longer on screen (repeat burns); kept for the record
PITCH_PER_MIN = 60 / S["pitch_every_s"]; PPM = int(PITCH_PER_MIN); assert PPM == 8      # v7: verified (8,39/min) but off screen, see sources.md
PA25 = int(S["comarca_2025_ha"] // 1000) * 1000; PA26 = int(S["comarca_2026_ha"] // 1000) * 1000
assert (PA25, PA26) == (6000, 42000)
PA_X = int(S["comarca_ratio"]); assert PA_X == 7 and S["comarca_ratio"] >= 7
PF = S["pat_facts"]; HOUSES = PF["elbolson_2025_viviendas_perdida_total"]["value"]; DEATHS = PF["elbolson_2025_muertes"]["value"]
assert HOUSES == 166 and DEATHS == 1
TU = S["tuc"]; TU_PCT = round(100 * TU["share_cane_zafra"]); assert TU_PCT == 89
# v7 ranking: DISTINCT area burned at least once 2012-2025 (MODIS MCD64A1 500 m pixels counted once), per INDEC province
ROWS = RK["rows"]; assert [r["rank"] for r in ROWS] == list(range(1, 25))
assert abs(RK["total_ha_repeat"] - S["burn_total_ha"]) < 1
UNIQ = RK["total_ha_unique"]; UNIQ_TXT = es_dec(UNIQ / 1e6, 1); assert UNIQ_TXT == "26,6"          # «26,6 MILLONES DE HA»
SHARE_AR = RK["share_country_burned"]; assert 0.09 < SHARE_AR < 0.10                                 # «casi 1 de cada 10 hectáreas del país» (9,5 %)
TOP5_PCT = round(100 * RK["top5_share"]); assert TOP5_PCT == 53
VMAX = ROWS[0]["ha_unique"]
def mha(x): return es_dec(x / 1e6, 1)
TOP5_TXT = [(r["name"].upper(), mha(r["ha_unique"])) for r in ROWS[:5]]
assert TOP5_TXT == [("FORMOSA", "3,2"), ("LA PAMPA", "3,0"), ("SANTA FE", "2,8"), ("CORRIENTES", "2,7"), ("SANTIAGO DEL ESTERO", "2,5")], TOP5_TXT
TUS = json.load(open(os.path.join(D2, "tucuman_stats.json"))); assert TUS["cane_zafra"] == 53625; TU_ZONE_PCT = round(100 * TUS["area_cane12_km2"] / TUS["area_tuc_km2"]); assert TU_ZONE_PCT == 69                  # the 12 cane departments = 69 % of Tucumán
FEATURED = {"90", "30", "26", "62"}          # v8 stops: Tucumán, Entre Ríos, Chubut, Río Negro
ER_N = S["er_2020"]; ER_R = S["er_ratio_other13"]; assert ER_N == 37506 and 6.5 < ER_R < 7.0          # «37.506 FOCOS» / «CASI 7 VECES SU MEDIANA 2012–2025»

# ---------------- points ----------------
P = np.load(os.path.join(D1, "points.npz"))
o = np.argsort(P["t"], kind="stable")
TS = P["t"][o].astype(np.float64); LON = P["lon"][o].astype(np.float32); LAT = P["lat"][o].astype(np.float32); PRV = P["prov"][o]
CODES = sorted(json.load(open(os.path.join(HERE, "..", "..", "data", "natgeo_v7.json")))["prov"])
def pidx(c): return CODES.index(c)
def warp(t0, segs):
    km = [segs[0][0]]; ks = [t0]
    for a, b, s in segs: km.append(b); ks.append(ks[-1] + (b - a) * s)
    return np.array(km, float), np.array(ks, float)

# ---------------- timeline (v9: every text held >= 0.35 s/word + 1 s, min 2.5 s; beats removed instead of speeding up) ----------------
SPACE_K = 1.25                             # the v5 space opening, played 1.25x slower (room for the rays)
T_X0 = 3.2 * SPACE_K                       # 4.0: globe -> flat map crossfade
T_MAP = 3.7 * SPACE_K                      # 4.625: flat map
T_TXT1 = 4.45; T_TXT1_END = 7.05           # «EL SOL CALIENTA.» (3 words, 2.6 s)
T_COOL = 5.45                              # rays stop, heat fades
T_SPARK = 5.55                             # the spark; «LA CHISPA ES HUMANA.» + «9 DE CADA 10 CON CAUSA CONOCIDA»
T_TXT2_END = T_SPARK + 0.1 + 4.95          # 11 words -> 4.95 s (stays on while the spark ignites the timelapse)
T_LAND = 8.3                               # the spark becomes 14 years of hotspots
KA_M, KA_S = warp(T_LAND, [(0, 12, 0.036), (12, 156, 0.0215), (156, 168, 0.03)])
T_A1 = float(KA_S[-1])                     # ~12.2: all 14 years lit
T_ASH = T_A1 + 0.5
T_SCAR = T_ASH + 0.8                       # «26,6 MILLONES DE HECTÁREAS» slams on the scar boom
T_D1 = T_SCAR + 5.25                       # 12 words -> 5.2 s
T_RK = T_D1                                # ranking: the 24 jurisdictions light up on the map (no row text in v9)
RK_STEP = 0.045
T_RK2 = T_RK + 0.3 + 23 * RK_STEP + 0.35   # collapse to the top 5
T_RK_END = T_RK2 + 5.4
# v9 stops: province card on the map (STOPS), then — for Tucumán and Entre Ríos — a zoom INTO the same map down to a real Copernicus
# Sentinel-2 image of that place (S2Z = (zoom start, zoom end, hold end)); no photo cuts. The Comarca keeps its in-place Sentinel-2 wipe.
FLYIN = [1.0, 1.0, 1.1]; ZOUT = 0.45
MAPDUR = [5.05, 4.7, 5.1]; ZIN = 1.0; ZHOLDS = [2.6, 3.1]
S_TU = (T_RK_END + FLYIN[0], T_RK_END + FLYIN[0] + MAPDUR[0]); Z_TU = (S_TU[1] - 0.1, S_TU[1] - 0.1 + ZIN, S_TU[1] - 0.1 + ZIN + ZHOLDS[0])
_s = Z_TU[2] + ZOUT + FLYIN[1]; S_ER = (_s, _s + MAPDUR[1]); Z_ER = (S_ER[1] - 0.1, S_ER[1] - 0.1 + ZIN, S_ER[1] - 0.1 + ZIN + ZHOLDS[1])
_s = Z_ER[2] + ZOUT + FLYIN[2]; S_PA = (_s, _s + MAPDUR[2])
T_CL = S_PA[1] + 0.7
CL_HDR, CL_DIP, CL_L2 = T_CL + 0.2, T_CL + 0.55, T_CL + 0.8      # whole country + full history -> dip -> the two lines
T_SRC = CL_L2 + 3.1                        # 5 words -> >= 2.75 s
TOTAL = round(T_SRC + 3.0, 2)
STOPS = [S_TU, S_ER, S_PA]
S2Z = [Z_TU, Z_ER]
PA_ON = (1.15, 2.3)                       # Comarca: MODIS 2025 / 2026 scars appear (s after S_PA[0])
PHOTOS = [(Z_TU[1], Z_TU[2]), (Z_ER[1], Z_ER[2])]          # kept for the score: the impact lands when the satellite image fills the frame
REVEALS = [T_SPARK, T_LAND, T_A1, T_SCAR, T_RK2 + 0.1, S_TU[0], S_ER[0], S_PA[0], Z_TU[1], Z_ER[1], CL_L2]
SHAKES = [(T_LAND, 7), (T_A1, 10), (T_SCAR, 5), (S_PA[0] + 0.1, 5)]
assert 58.5 <= TOTAL <= 59.95, TOTAL
def words(s): return len([w for w in s.replace("·", " ").replace("=", " ").split() if any(ch.isalnum() for ch in w)])
def need(*lines): return max(2.5, 0.35 * sum(words(x) for x in lines) + 1.0)
TXT_SOL = "EL SOL CALIENTA."; TXT_CHISPA = "LA CHISPA ES HUMANA."; TXT_CAUSA = f"{HUM_10} DE CADA 10, CON CAUSA CONOCIDA"
TXT_AREA = "QUEMADAS: CASI 1 DE CADA 10 DEL PAÍS"
LEG1 = "1 punto = 1 foco de calor (satélite)"; LEG2 = "gris = área quemada"
assert T_TXT1_END - T_TXT1 >= need(TXT_SOL)
assert T_TXT2_END - T_TXT1 >= need(TXT_SOL, TXT_CHISPA, TXT_CAUSA) and T_TXT2_END - (T_SPARK + 0.1) >= need(TXT_CHISPA, TXT_CAUSA) - 0.05
assert T_D1 - T_SCAR >= need("26,6 MILLONES DE HA", TXT_AREA) - 0.01
assert T_SRC - CL_L2 >= need("YA NO FALTAN DATOS. FALTA RESPONSABILIDAD.")

def m_now(t):
    if t < T_LAND: return 0.0
    if t < T_A1: return float(np.interp(t, KA_S, KA_M))
    return 168.0
PS_A = np.interp(TS, KA_M, KA_S).astype(np.float32)

def ev(mask): return np.where(mask)[0]
EV_ER = ev((PRV == pidx("30")) & (TS >= 96) & (TS < 108))                      # Entre Ríos, 2020
EV_TU = ev((PRV == pidx("90")) & ((TS % 12) >= 4) & ((TS % 12) < 11))
EV_PA = ev(np.isin(PRV, [pidx("26"), pidx("62")]) & (LON < -70.9) & (TS >= 156) & (TS < 159))
EVENTS = [EV_TU, EV_ER, EV_PA]
assert len(EV_ER) == ER_N, len(EV_ER)
def ev_times(i, t0, dur):
    idx = EVENTS[i]; tt = TS[idx]; k = (tt - tt.min()) / max(1e-6, tt.max() - tt.min()) if len(tt) > 1 else np.zeros(len(tt))
    if i == 0: k = ((tt % 12) - 4) / 7.0 * 0.85                 # Tucumán: one zafra, May -> Nov, all years stacked
    return (t0 + 0.3 + k * dur).astype(np.float32)
EVT = [ev_times(i, STOPS[i][0], 2.4 if i == 0 else 2.6 if i == 1 else 2.0) for i in range(3)]

# ---------------- geography ----------------
NG = json.load(open(os.path.join(HERE, "..", "..", "data", "natgeo_v7.json")))
GEO = json.load(open(os.path.join(HERE, "..", "..", "data", "geo_v2.json")))
def _bb(r, b=(-80, -58, -48, -18)):
    a = np.asarray(r); return a[:, 0].max() > b[0] and a[:, 0].min() < b[2] and a[:, 1].max() > b[1] and a[:, 1].min() < b[3]
NEIGH = [np.asarray(r, np.float32) for r in GEO["countries"] if _bb(r)]
PROVR = {k: [np.asarray(r, np.float32) for r in v] for k, v in NG["prov"].items()}
def outline(codes):
    u = shapely.union_all([shapely.Polygon(r) for c in codes for r in NG["prov"][c]]).buffer(0.01).buffer(-0.01).simplify(0.005)
    return [np.asarray(g.exterior.coords, np.float32) for g in (u.geoms if hasattr(u, "geoms") else [u]) if g.area > 0.01]
COS = math.cos(math.radians(38.0))
TUC_ZONE = [np.asarray(r, np.float32) for r in json.load(open(os.path.join(AS, "tuc_cane_zone.json")))]
BS = json.load(open(os.path.join(D2, "burn_stats.json")))
assert abs(BS["pitch_ha"] - 105 * 68 / 1e4) < 1e-9
def _label_pt(c):
    u = shapely.union_all([shapely.Polygon(r) for r in NG["prov"][c]]); g = max(u.geoms, key=lambda g: g.area) if hasattr(u, "geoms") else u
    p = g.representative_point(); return (p.x, p.y)
LABEL_PT = {r["code"]: _label_pt(r["code"]) for r in ROWS[:5]}
LABEL_PT["06"] = (-60.3, -36.9)
# random points inside Argentina (targets of the intro rays), fixed seed
_AR = shapely.union_all([shapely.Polygon(r) for c in NG["prov"] for r in NG["prov"][c]]).buffer(0)
def _ar_pts(n, seed=3):
    rg = np.random.default_rng(seed); out = []
    from shapely import prepared; pr = prepared.prep(_AR)
    while len(out) < n:
        x, y = rg.uniform(-73.5, -53.7), rg.uniform(-55.0, -21.8)
        if pr.contains(shapely.Point(x, y)): out.append((x, y))
    return np.array(out, np.float32)
AR_PTS = _ar_pts(400)
AR_OUT = outline(list(NG["prov"].keys()))

# ---------------- camera ----------------
CAM_IN = (-64.2, -38.6, 26.5, 1290, 560)
CAM0 = (-64.2, -38.6, 30.0, 1290, 548)
CAM_ACC = (-64.0, -38.4, 31.5, 1290, 548)
CAM_RK = (-64.2, -38.6, 30.0, 1430, 548)
STOPCAM = [(-65.25, -27.05, 230, 1440, 560), (-59.85, -32.75, 150, 1380, 560), (-71.43, -42.18, 760, 1400, 560)]
NORTE = ["10", "18", "22", "34", "38", "46", "54", "66", "86", "90"]
STOPOUT = [outline(["90"]), outline(["30"]), outline(["26", "62"])]
NORTE_OUT = outline(NORTE)
def _cord():
    u = shapely.union_all([shapely.Polygon(r) for c in ("58", "62", "26", "78") for r in NG["prov"][c]]).buffer(0.01).buffer(-0.01)
    u = u.intersection(shapely.box(-76, -56, -70.5, -36)).simplify(0.01)
    return [np.asarray(g.exterior.coords, np.float32) for g in (u.geoms if hasattr(u, "geoms") else [u]) if g.area > 0.05]
CORD_OUT = _cord()
STOPDIM = [0.25, 0.25, 0.0]               # v8: the rest of the country stays lit (whole Argentina marked)
def stop_w(t, i):
    t0, t1 = STOPS[i]; return clamp((t - t0 + 0.3) / 0.5) * (1 - clamp((t - t1 + 0.2) / 0.5))
def close_w(t): return clamp((t - T_CL - 0.2) / 0.8) * (1 - clamp((t - T_SRC) / 0.5))
def _dim(A, rings, c, k):
    m = Image.new('L', (W // 2, H // 2), 0); dm = ImageDraw.Draw(m)
    for r in rings: dm.polygon([(x / 2, y / 2) for x, y in ring_px(r, c)], fill=255)
    m = cv2.resize(cv2.GaussianBlur(np.asarray(m, np.float32) / 255, (0, 0), 4), (W, H))[..., None]
    return A * (1 - k * (1 - m) * np.array((0.8, 1.0, 1.12), np.float32))
def spotlight(A, t, c):
    for i in range(3):
        w = stop_w(t, i)
        if w > 0.003 and i != 2: A = _dim(A, STOPOUT[i], c, STOPDIM[i] * w)
    return A

# camera path: list of segments (t0, t1, camA, camB, mode); 'ease' = v5 zoom-anchored ease, 'fly' = direct flight with a mild zoom dip
def cam_mix(a, b, k):
    z = math.exp(lerp(math.log(a[2]), math.log(b[2]), k))
    kk = k if abs(math.log(b[2] / a[2])) < 1.5 else (z - a[2]) / (b[2] - a[2]) if b[2] != a[2] else k
    return (lerp(a[0], b[0], kk), lerp(a[1], b[1], kk), z, lerp(a[3], b[3], k), lerp(a[4], b[4], k))
def cam_fly(a, b, u):
    """province -> province: pan straight from a to b; zoom dips only as much as needed to keep both ends within ~1000 px"""
    k = einout5(u) if False else einout(u)
    dist = math.hypot((b[0] - a[0]) * COS, b[1] - a[1])
    la, lb = math.log(a[2]), math.log(b[2]); lm = lerp(la, lb, 0.5)
    zfit = 1000.0 / max(dist, 1e-3)
    dip = max(0.0, lm - math.log(zfit))
    lz = lerp(la, lb, k) - dip * 4 * k * (1 - k)
    # pan in "screen-normalised" space so the motion speed looks even while the zoom changes
    z = math.exp(lz)
    return (lerp(a[0], b[0], k), lerp(a[1], b[1], k), z, lerp(a[3], b[3], k), lerp(a[4], b[4], k))
def cam_zoomto(a, b, u):
    """v7: clean direct zoom between a wide and a close camera. The close end's centre (the anchor) travels on a straight screen line
    from where it sits in the wide view to its final spot while the zoom is log-interpolated, so the view never drifts over other
    regions (v6's zoom-anchored ease kept the national centre on screen first and swept over the south before reaching Corrientes)."""
    k = einout(u)
    anc = b if b[2] >= a[2] else a                          # the zoomed-in end
    z = math.exp(lerp(math.log(a[2]), math.log(b[2]), k)); ox = lerp(a[3], b[3], k); oy = lerp(a[4], b[4], k)
    pa = proj(anc[0], anc[1], a); pb = proj(anc[0], anc[1], b)
    px = lerp(pa[0], pb[0], k); py = lerp(pa[1], pb[1], k)
    return (anc[0] - (px - ox) / (z * COS), anc[1] + (py - oy) / z, z, ox, oy)
# v9: Sentinel-2 views zoomed INTO the same map (Tucumán: Burruyacú 23/09/2025; Entre Ríos: islands off Rosario 23/09/2020)
S2V = []
for _k, _fn in (("tuc", "tuc_2025-09-23"), ("er", "delta_2020-09-23")):
    _m = json.load(open(os.path.join(HERE, "s2zoom", _fn + ".json"))); _b = _m["bbox"]
    _img = np.asarray(Image.open(os.path.join(HERE, "s2zoom", _fn + ".jpg")).convert("RGB"), np.float32)
    _Z = 900.0 / (_b[3] - _b[1])                                     # the crop fills ~900 px of height
    S2V.append(dict(key=_k, img=_img, bbox=_b, meta=_m, cam=((_b[0] + _b[2]) / 2, (_b[1] + _b[3]) / 2, _Z, 1390, 540)))
assert S2V[0]["meta"]["date"].startswith("2025-09-23") and S2V[1]["meta"]["date"].startswith("2020-09-23")
HS = json.load(open(os.path.join(D2, "s2_day_hotspots.json")))
S2HS = [(np.asarray(HS[k]["lon"], np.float32), np.asarray(HS[k]["lat"], np.float32)) for k in ("tuc", "er")]
SEG = [(0.0, T_LAND, CAM_IN, CAM_IN, "hold"), (T_LAND, T_A1, CAM_IN, CAM0, "ease"), (T_A1, T_A1 + 0.4, CAM0, CAM_ACC, "ease"),
       (T_A1 + 0.4, T_RK - 0.2, CAM_ACC, CAM_ACC, "hold"), (T_RK - 0.2, T_RK + 0.5, CAM_ACC, CAM_RK, "ease"),
       (T_RK + 0.5, T_RK_END - 0.2, CAM_RK, CAM_RK, "hold"),
       (T_RK_END - 0.2, S_TU[0] + 0.15, CAM_RK, STOPCAM[0], "zoomto"), (S_TU[0] + 0.15, Z_TU[0], STOPCAM[0], STOPCAM[0], "hold"),
       (Z_TU[0], Z_TU[1], STOPCAM[0], S2V[0]["cam"], "zoomto"), (Z_TU[1], Z_TU[2], S2V[0]["cam"], S2V[0]["cam"], "hold"),
       (Z_TU[2], Z_TU[2] + ZOUT, S2V[0]["cam"], STOPCAM[0], "zoomto"), (Z_TU[2] + ZOUT, S_ER[0] + 0.15, STOPCAM[0], STOPCAM[1], "fly"),
       (S_ER[0] + 0.15, Z_ER[0], STOPCAM[1], STOPCAM[1], "hold"),
       (Z_ER[0], Z_ER[1], STOPCAM[1], S2V[1]["cam"], "zoomto"), (Z_ER[1], Z_ER[2], S2V[1]["cam"], S2V[1]["cam"], "hold"),
       (Z_ER[2], Z_ER[2] + ZOUT, S2V[1]["cam"], STOPCAM[1], "zoomto"), (Z_ER[2] + ZOUT, S_PA[0] + 0.15, STOPCAM[1], STOPCAM[2], "fly"),
       (S_PA[0] + 0.15, S_PA[1] - 0.1, STOPCAM[2], STOPCAM[2], "hold")]
CAM_CL = (-64.2, -38.6, 28.0, 1500, 548)
SEG += [(S_PA[1] - 0.1, T_CL + 0.3, STOPCAM[2], CAM_CL, "zoomto"), (T_CL + 0.3, 999, CAM_CL, CAM_CL, "hold")]
def cam_at(t):
    c = SEG[-1][3]
    for t0, t1, a, b, mode in SEG:
        if t0 <= t < t1:
            u = (t - t0) / (t1 - t0)
            c = a if mode == "hold" else cam_fly(a, b, u) if mode == "fly" else cam_zoomto(a, b, u) if mode == "zoomto" else cam_mix(a, b, einout(u)); break
    dx = dy = 0.0
    for t0, amp in SHAKES:
        e = decay(t, t0, 0.13)
        if e > 0.01: u = t - t0; dx += amp * e * math.sin(u * 83); dy += amp * e * math.cos(u * 67)
    return (c[0], c[1], c[2], c[3] + dx, c[4] + dy)
def proj(lon, lat, c):
    return c[3] + (lon - c[0]) * c[2] * COS, c[4] - (lat - c[1]) * c[2]
def ring_px(r, c):
    x, y = proj(r[:, 0], r[:, 1], c); return list(zip(x.tolist(), y.tolist()))

# ---------------- fire rendering ----------------
def _lut():
    st = [(0.0, (0, 0, 0)), (0.18, (90, 12, 4)), (0.42, (215, 56, 10)), (0.68, (255, 150, 34)), (0.88, (255, 214, 110)), (1.0, (255, 250, 225))]
    x = np.linspace(0, 1, 256); out = np.zeros((256, 3), np.float32)
    for ch in range(3): out[:, ch] = np.interp(x, [s[0] for s in st], [s[1][ch] for s in st])
    return out
LUT = _lut()
def splat(lon, lat, w, c):
    x, y = proj(lon, lat, c); xi = np.round(x).astype(np.int32); yi = np.round(y).astype(np.int32)
    m = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
    idx = yi[m] * W + xi[m]
    return np.bincount(idx, weights=None if w is None else w[m], minlength=W * H).reshape(H, W).astype(np.float32)
def zoom_blur(img, c):
    k = c[2] / 30.0
    if k > 1.15:
        s = min(6.0, 0.55 * k ** 0.8); img = cv2.GaussianBlur(img, (0, 0), s) * (k ** 1.25) * 0.55
    return img
def fire_activity(t):
    """hotspots glowing on screen (drives the crackle in the score)"""
    if T_LAND <= t < T_ASH:
        a = int(np.searchsorted(PS_A, t - 1.0)); b = int(np.searchsorted(PS_A, t, side="right"))
        return float(np.exp(-(t - PS_A[a:b]) / 0.16).sum()) if b > a else 0.0
    for i in range(3):
        tt = EVT[i]; s0, s1 = STOPS[i]
        if s0 - 0.2 <= t < s1:
            m = (tt <= t) & (tt > t - 2.0); return float(np.exp(-(t - tt[m]) / 0.4).sum()) * (60 if i == 2 else 3 if i == 0 else 0.15)
    if T_SPARK <= t < T_LAND: return 0.15
    return 0.0

# ---------------- MODIS scars ----------------
GR = json.load(open(os.path.join(D2, "scar_grid.json")))
def _pyr(name):
    z = np.load(os.path.join(AS, name + ".npz")); return [z[f"l{k}"] for k in range(6)]
SCAR = _pyr("scar_all"); SC_ER = _pyr("scar_er_2020")
SC_P25 = _pyr("scar_pat_2025"); SC_P26 = _pyr("scar_pat_2026")
def warp_raster(pyr, c, interp=cv2.INTER_LINEAR):
    z = c[2] * COS
    k = int(max(0, min(5, math.floor(math.log2(max(1e-6, (1 / z) / GR["D"]))))))
    src = pyr[k]; Dk = GR["D"] * (pyr[0].shape[1] / src.shape[1])
    ax = Dk * c[2] * COS; ay = Dk * c[2]
    bx = c[3] + (GR["LON0"] + 0.5 * Dk - c[0]) * c[2] * COS
    by = c[4] - (GR["LAT1"] - 0.5 * Dk - c[1]) * c[2]
    M = np.float32([[ax, 0, bx], [0, ay, by]])
    return cv2.warpAffine(src, M, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float32) / 255

def base_map(c, land=(20, 19, 22)):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im, "RGBA")
    for r in NEIGH: d.polygon(ring_px(r, c), fill=(13, 13, 17, 255), outline=(34, 34, 40, 255))
    for k, rs in PROVR.items():
        for r in rs: d.polygon(ring_px(r, c), fill=land + (255,))
    for k, rs in PROVR.items():
        for r in rs: d.line(ring_px(r, c) + ring_px(r[:1], c), fill=(62, 60, 64, 210), width=1)
    return im

# ---------------- timeline + year (fast part only) ----------------
TLX0, TLX1, TLYB, TLH = 110, 1010, 1018, 180
MMAX = MONTHLY.max()
def tl_x(m): return TLX0 + (TLX1 - TLX0) * m / 168.0
def tl_y(v): return TLYB - TLH * v / MMAX
def draw_timeline(fr, t, a):
    if a <= 0.003: return
    d = fr.d; mn = min(168.0, max(0.0, m_now(t)))
    d.line([(TLX0, TLYB), (TLX1, TLYB)], fill=(120, 116, 110, int(150 * a)), width=2)
    fl = font("mono", 48, 700)
    for y in range(2012, 2027):
        x = tl_x((y - 2012) * 12); d.line([(x, TLYB), (x, TLYB + (12 if y % 4 == 0 else 6))], fill=(150, 146, 140, int(170 * a)), width=2)
        if y in (2012, 2016, 2020, 2024): put_text(fr, (x + 4, TLYB + 52), str(y), fl, MU, a)
    n = int(mn); xs = [tl_x(0)]; ys = [TLYB]
    for i in range(n): xs.append(tl_x(i + 0.5)); ys.append(tl_y(MONTHLY[i]))
    if mn < 168:
        cur = np.searchsorted(TS, mn) - np.searchsorted(TS, n)
        v_now = lerp(MONTHLY[n - 1] if n else 0, MONTHLY[n], clamp(cur / max(1, MONTHLY[n]))); xs.append(tl_x(mn)); ys.append(tl_y(v_now))
    else: xs.append(tl_x(168)); ys.append(tl_y(MONTHLY[167]))
    pts = list(zip(xs, ys))
    if len(pts) > 1:
        d.polygon(pts + [(xs[-1], TLYB)], fill=(255, 120, 30, int(95 * a))); d.line(pts, fill=AM + (int(255 * a),), width=4); fr.glow_line(pts, mixc((0, 0, 0), OR, a), 8)
    if mn < 168:
        x = tl_x(mn); y = ys[-1]; d.line([(x, TLYB + 4), (x, TLYB - TLH - 18)], fill=(255, 240, 220, int(120 * a)), width=2)
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=HOT + (int(255 * a),))
def draw_year(fr, t, a):
    if a <= 0.003: return
    mn = min(167.99, max(0.0, m_now(t))); yy = 2012 + int(mn // 12)
    fy = font("anton", 180)
    put_text(fr, (FX.TX - 6, 236), "2012–2025" if t >= T_A1 else str(yy), fy, WH, a, cache=t >= T_A1)

# ---------------- flags ----------------
FLAG_H = 54
def _flag(fn):
    im = Image.open(os.path.join(HERE, "flags", fn + ".png")).convert("RGBA")
    w = round(FLAG_H * im.width / im.height); im = im.resize((w, FLAG_H), Image.LANCZOS)
    pad = 14; out = Image.new("RGBA", (w + 2 * pad, FLAG_H + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0); ImageDraw.Draw(sh).rectangle((pad + 3, pad + 5, pad + w + 3, pad + FLAG_H + 5), fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(5)); out.paste(Image.new("RGBA", out.size, (0, 0, 0, 255)), (0, 0), sh)
    out.alpha_composite(im, (pad, pad))
    ImageDraw.Draw(out).rectangle((pad - 1, pad - 1, pad + w, pad + FLAG_H), outline=(235, 230, 222, 200), width=2)
    return out, pad
FLAGS = {n: _flag(n) for n in ("chubut", "rio_negro", "tucuman", "entre_rios")}
STOPFLAGS = [["tucuman"], ["entre_rios"], ["chubut", "rio_negro"]]
def draw_flags(fr, names, x, y_mid, a, sc):
    if a <= 0.003: return x
    for n in names:
        im, pad = FLAGS[n]
        if abs(sc - 1) > 0.004: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
        al = im.getchannel("A").point(lambda v: int(v * a))
        fr.im.paste(im.convert("RGB"), (int(x - pad * sc), int(y_mid - im.height / 2)), al)
        x += im.width - 2 * pad * sc + 14
    return x

# ---------------- v9: no headline cards and no photo cuts (one visualization). SEQ kept empty for the score script. ----------------
SEQ = []

# ---------------- v9: Sentinel-2 views zoomed into the same map (Tucumán, Entre Ríos) ----------------
def s2v_layer(v, c):
    img = v["img"]; h, w = img.shape[:2]; l0, b0, l1, b1 = v["bbox"]
    ax = (l1 - l0) / w * c[2] * COS; ay = (b1 - b0) / h * c[2]
    bx = c[3] + (l0 - c[0]) * c[2] * COS; by = c[4] - (b1 - c[1]) * c[2]
    M = np.float32([[ax, 0, bx], [0, ay, by]])
    out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_AREA if ax < 1 else cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    m = cv2.warpAffine(np.ones((h, w), np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out, m[..., None]
def s2v_corners(v, c):
    l0, b0, l1, b1 = v["bbox"]; x0, y0 = proj(l0, b1, c); x1, y1 = proj(l1, b0, c); return x0, y0, x1, y1
def s2v_w(t, i):
    """visibility of Sentinel-2 view i: appears (small, framed) during its stop card, fills the frame on the zoom, goes on the fly-out"""
    z0, z1, z2 = S2Z[i]; s0 = STOPS[i][0]
    return clamp((t - s0 - 1.2) / 0.4) * (1 - clamp((t - z2 - ZOUT - 0.2) / 0.4))
def s2v_label_a(t, i):
    z0, z1, z2 = S2Z[i]; return clamp((t - z1 + 0.15) / 0.25) * (1 - clamp((t - z2 + 0.05) / 0.25))
S2LAB = [("BURRUYACÚ, TUCUMÁN", "23/09/2025 · Sentinel-2"), ("ISLAS DEL DELTA", "23/09/2020 · Sentinel-2")]
S2LAB_N = [0, 1]                           # extra on-image words: «ROSARIO» pin in the Delta view
ROSARIO = (-60.68, -32.95)
for _i in range(2): assert ZHOLDS[_i] >= need(*S2LAB[_i], *(["ROSARIO"] * S2LAB_N[_i])) - 0.01, (S2LAB[_i], need(*S2LAB[_i]))
def s2v_fire(t, i, c):
    """the VIIRS detections of that same afternoon, on top of the image (same law as every other point in the video)"""
    z0, z1, z2 = S2Z[i]; k = clamp((t - z1 - 0.2) / 0.5) * (1 - clamp((t - z2) / 0.4))
    if k <= 0.003: return None
    lon, lat = S2HS[i]; x, y = proj(lon, lat, c)
    L = np.zeros((H, W), np.float32)
    for j, (xx, yy) in enumerate(zip(x, y)):
        kk = clamp((t - z1 - 0.2 - 0.025 * j) / 0.2) * k
        if kk > 0: cv2.circle(L, (int(xx), int(yy)), 7, float(kk), -1, cv2.LINE_AA)
    return L

# Sentinel-2 crops drawn IN PLACE on the map: Dec 2024 -> Apr 2025 -> Apr 2026
S2_IMG = {y: np.asarray(Image.open(os.path.join(HERE, "s2", f"comarca_{y}.jpg")).convert("RGB"), np.float32) for y in (2024, 2025, 2026)}
S2_BOX = json.load(open(os.path.join(HERE, "s2", "comarca_2024.json")))["bbox"]
def s2_layer(c, y):
    img = S2_IMG[y]; h, w = img.shape[:2]; l0, b0, l1, b1 = S2_BOX
    ax = (l1 - l0) / w * c[2] * COS; ay = (b1 - b0) / h * c[2]
    bx = c[3] + (l0 - c[0]) * c[2] * COS; by = c[4] - (b1 - c[1]) * c[2]
    M = np.float32([[ax, 0, bx], [0, ay, by]])
    out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    m = cv2.warpAffine(np.ones((h, w), np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out, m[..., None]
def s2_corners(c):
    l0, b0, l1, b1 = S2_BOX; x0, y0 = proj(l0, b1, c); x1, y1 = proj(l1, b0, c); return x0, y0, x1, y1

# ---------------- stop cards (v9: header, one big number, one short line; >= 48 px; held >= 0.35 s/word + 1 s) ----------------
STOPTXT = [
    dict(head="TUCUMÁN", num=f"{TU_PCT} %", unit="DE SUS FOCOS", line="EN ZONA CAÑERA, EN PLENA ZAFRA", cn=HOT, cl=AM),
    dict(head="ENTRE RÍOS · 2020", num=es_int(ER_N), unit="FOCOS", line=f"CASI {round(ER_R)} VECES LO HABITUAL", cn=HOT, cl=AM),
    dict(head="COMARCA ANDINA · 2026", num=es_int(PA26), unit="HA", line=f"{PA_X} VECES MÁS QUE EN 2025", cn=HOT, cl=AM),
]
assert round(ER_R) == 7 and ER_R < 7                       # «casi 7 veces lo habitual» (6,96 x the median of the other 13 years)
for _i, _s in enumerate(STOPTXT):
    assert (STOPS[_i][1] - 0.05) - (STOPS[_i][0] + 0.12) >= need(_s["head"], _s["num"], _s["unit"], _s["line"]) - 0.02, (_i, need(_s["head"], _s["num"], _s["unit"], _s["line"]))
HEAD_F = ("mono", 52, 800)
def number_line(fr, t, t0, t1, y, num, col, unit, dur=1.0, glow=0.55, count_to=None, size=150):
    fN = font("anton", size); fU = font("anton", 80)
    s = es_int(count(t, t0, count_to, dur)) if count_to is not None else num
    slam(fr, (FX.TX, y), s, fN, col, t, t0, t1, glow=glow, cache=count_to is None)
    slam(fr, (FX.TX + tw(num, fN) + 26, y), unit, fU, WH, t, t0 + 0.3, t1, big=False)
def draw_stop(fr, t, i, c):
    t0, t1 = STOPS[i]; s = STOPTXT[i]
    fly = FLYIN[i]
    # the destination lights up while the camera is still flying to it (province outline; Sentinel-2 frame for the Comarca)
    ao = clamp((t - t0 + fly) / 0.45) * (1 - clamp((t - t1 + 0.1) / 0.35))
    if ao > 0 and t0 - fly <= t < t1 + 0.4:
        d = fr.d
        if i != 2:
            for r in STOPOUT[i]:
                pts = ring_px(r, c); d.line(pts + pts[:1], fill=AM + (int(220 * ao),), width=3); fr.glow_line(pts + pts[:1], mixc((0, 0, 0), AM, ao), 10)
        elif t < t0 + 0.3:
            x0, y0, x1, y1 = s2_corners(c); k = ao * (1 - clamp((t - t0) / 0.3))
            d.rectangle((x0, y0, x1, y1), outline=AM + (int(230 * k),), width=3); fr.glow_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], mixc((0, 0, 0), AM, k), 10)
    if not (t0 - 0.2 <= t < t1 + 0.4): return
    a = clamp((t - t0 + 0.1) / 0.35) * (1 - clamp((t - t1 + 0.1) / 0.35))
    if i == 0 and a > 0:
        for r in TUC_ZONE:
            pts = ring_px(r, c); fr.d.line(pts + pts[:1], fill=HOT + (int(255 * a),), width=4)
    cb = t0 + 0.12; ce = t1 - 0.05
    u = t - cb; fa = clamp(u / 0.2) * (1 - clamp((t - ce) / 0.3)); fsc = 1 + 0.12 * (1 - eout(u / 0.35))
    xe = draw_flags(fr, STOPFLAGS[i], FX.TX, 430 - 17 + (1 - eout(u / 0.35)) * 18, fa, fsc)
    slam(fr, (xe + 10, 430), s["head"], font(*HEAD_F), AM, t, cb, ce, big=False)
    number_line(fr, t, cb + 0.2, ce, 600, s["num"], s["cn"], s["unit"], count_to=PA26 if i == 2 else ER_N if i == 1 else None)
    slam(fr, (FX.TX, 700), s["line"], font("anton", 66), s["cl"], t, cb + 0.6, ce, glow=0.3)

def draw_country(fr, t, c):
    """v8: the whole of Argentina marked — every jurisdiction outlined and lit from the first stop on, brightest in the close"""
    k = clamp((t - S_TU[0] + FLYIN[0]) / 0.6)
    if k <= 0.003: return
    cw = close_w(t)
    al = int((70 + 150 * cw) * k); d = fr.d
    for code, rs in PROVR.items():
        for r in rs:
            if len(r) < 3: continue
            pts = ring_px(r, c); d.line(pts + pts[:1], fill=AM + (al,), width=2 if cw < 0.5 else 3)
    if cw > 0.003:
        for code, rs in PROVR.items():
            for r in rs: fr.glow_line(ring_px(r, c) + ring_px(r[:1], c), mixc((0, 0, 0), AM, 0.55 * cw), 6)
        for r in AR_OUT: pts = ring_px(r, c); d.line(pts + pts[:1], fill=HOT + (int(230 * cw),), width=3); fr.glow_line(pts + pts[:1], mixc((0, 0, 0), OR, cw), 12)

# ---------------- ranking: all 24 jurisdictions, then the top 5 ----------------
RK_Y0, RK_PITCH = 196, 35.5
RK_BX0, RK_BW = 520, 430
def rk_t_row(rank): return T_RK + 0.4 + (24 - rank) * RK_STEP            # bottom-up: #24 first, #1 last
def rk_col(v):
    return tuple(int(x) for x in LUT[int(70 + 140 * (v / VMAX) ** 0.55)])
RK_POLYS = {r["code"]: PROVR[r["code"]] for r in ROWS}
def ranking_fill(A, t, c):
    """choropleth: each province lights up when its row lands; in the top-5 phase the others dim"""
    if not (T_RK <= t < T_RK_END + 0.8): return A
    out = 1 - clamp((t - T_RK_END + 0.1) / 0.6)
    k2 = clamp((t - T_RK2) / 0.5)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for r in ROWS:
        tr = rk_t_row(r["rank"]); a = clamp((t - tr) / 0.15)
        if a <= 0: continue
        top = r["rank"] <= 5
        al = (0.78 if top else lerp(0.78, 0.22, k2)) * a * out
        col = rk_col(r["ha_unique"]) if r["ha_unique"] > 0 else (40, 38, 40)
        for ring in RK_POLYS[r["code"]]: d.polygon(ring_px(ring, c), fill=col + (int(255 * al),))
    L = np.asarray(lay, np.float32); al = L[..., 3:4] / 255
    return A * (1 - al) + L[..., :3] * al
RK_HDR = f"5 PROVINCIAS = {TOP5_PCT} % DE LO QUEMADO"
def draw_ranking(fr, t, c):
    """v9: the 24 jurisdictions light up on the map (no row text: it was unreadable at speed), then the top 5 — names only, big"""
    if not (T_RK <= t < T_RK_END + 0.4): return
    d = fr.d
    out = 1 - clamp((t - T_RK_END + 0.3) / 0.35)
    k2 = clamp((t - T_RK2) / 0.45)
    for r in ROWS:                                   # province flash outlines as they land
        tr = rk_t_row(r["rank"]); e = decay(t, tr, 0.25) if t >= tr else 0
        top = r["rank"] <= 5
        w = max(e, (k2 if top else 0)) * out
        if w > 0.02:
            for ring in RK_POLYS[r["code"]]:
                pts = ring_px(ring, c); d.line(pts + pts[:1], fill=(HOT if e > 0.5 else AM) + (int(230 * w),), width=3 if top else 2)
                fr.glow_line(pts + pts[:1], mixc((0, 0, 0), AM, w), 8)
    if k2 > 0.003:
        slam(fr, (FX.TX, 250), RK_HDR, font("anton", 72), OR, t, T_RK2 + 0.05, T_RK_END - 0.3, glow=0.4)
        fN = font("anton", 72); fR = font("anton", 72)
        for j, (name, val) in enumerate(TOP5_TXT):
            y = 400 + j * 112; t0 = T_RK2 + 0.25 + j * 0.09
            if t < t0: continue
            u = t - t0; a = clamp(u / 0.15) * out
            slam(fr, (FX.TX, y), str(j + 1), fR, OR, t, t0, T_RK_END - 0.3, big=False)
            slam(fr, (FX.TX + 70, y), name, fN, WH, t, t0, T_RK_END - 0.3, big=False)
            bw = (960 - FX.TX - 70) * ROWS[j]["ha_unique"] / VMAX * eout(u / 0.4)
            d.rectangle((FX.TX + 70, y + 18, FX.TX + 70 + bw, y + 28), fill=rk_col(ROWS[j]["ha_unique"]) + (int(255 * a * (1 - clamp((t - T_RK_END + 0.3) / 0.3))),))
        for j, r in enumerate(ROWS[:5]):             # rank numbers on the map
            lx, ly = proj(*LABEL_PT[r["code"]], c); s_ = str(j + 1); f = font("anton", 60)
            aa = k2 * out * clamp((t - T_RK2 - 0.25 - j * 0.09) / 0.2)
            for ox, oy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
                put_text(fr, (lx - tw(s_, f) / 2 + ox, ly + 20 + oy), s_, f, (12, 10, 10), aa)
            put_text(fr, (lx - tw(s_, f) / 2, ly + 20), s_, f, WH, aa)

# ---------------- opening: sun -> rays -> Earth -> Argentina; the turn: the spark is human ----------------
LIGHT = np.array((-0.55, 0.28, 0.79)); LIGHT = tuple(LIGHT / np.linalg.norm(LIGHT))
R_FINAL = CAM_IN[2] * 180 / math.pi
def _logkeys(t, keys):
    ts, vs = zip(*keys); return math.exp(float(np.interp(t, ts, np.log(vs))))
def sun_state(t):
    tau = t / SPACE_K
    Rs = 900 * math.exp(-2.5 * tau); k = eout(tau / 1.3)
    return lerp(960, 330, k), lerp(540, 250, k), Rs, 1 - clamp((tau - 1.9) / 0.5)
def globe_state(t):
    tau = t / SPACE_K
    if tau < 0.45: return None
    Re = _logkeys(tau, [(0.45, 3), (1.5, 70), (2.35, 420), (3.0, 1050), (3.7, R_FINAL)])
    kr = einout((tau - 0.45) / 2.6)
    return CAM_IN[3], CAM_IN[4], Re, lerp(18.0, CAM_IN[0], kr), lerp(12.0, CAM_IN[1], kr), clamp((tau - 2.55) / 0.75)
def ortho(lon, lat, g):
    cx, cy, R, lon0, lat0, _ = g
    p, l = np.radians(lat), np.radians(lon - lon0); p0 = math.radians(lat0)
    x = np.cos(p) * np.sin(l); y = math.cos(p0) * np.sin(p) - math.sin(p0) * np.cos(p) * np.cos(l)
    z = math.sin(p0) * np.sin(p) + math.cos(p0) * np.cos(p) * np.cos(l)
    return cx + R * x, cy - R * y, x, y, z
# rays: (emit time, kind, param). kind 0: sun -> sunlit face of the globe; kind 1: from the sun's direction onto Argentina
_rr = np.random.default_rng(41)
RAYS = []
for k in range(70):  RAYS.append((0.75 + k * 0.026 + _rr.uniform(0, 0.02), 0, _rr.uniform(-1, 1), _rr.uniform(0.15, 0.95)))
for k in range(150): RAYS.append((2.55 + k * 0.0185 + _rr.uniform(0, 0.015), 1, int(_rr.integers(0, len(AR_PTS))), _rr.uniform(-0.45, 0.45)))
RAY_TRAVEL = 0.32; RAY_REFL = 0.45
D_IN = np.array((-LIGHT[0], LIGHT[1]), np.float32); D_IN /= np.linalg.norm(D_IN)      # screen direction of the sunlight (down-right)
def _seg(L, p, q, v):
    cv2.line(L, (int(p[0] * 4), int(p[1] * 4)), (int(q[0] * 4), int(q[1] * 4)), float(v), 2, cv2.LINE_AA, shift=2)
def ray_layer(t, c=None):
    """additive light layer (H, W) for the rays at time t; c = flat-map camera (None while on the globe)"""
    L = np.zeros((H, W), np.float32); Hh = np.zeros((H, W), np.float32)
    if t > T_COOL + 0.4 or t < 0.7: return L, Hh
    sx, sy, Rs, sa = sun_state(t); g = globe_state(t)
    ray_a = 1 - clamp((t - T_COOL) / 0.35)
    for te, kind, p1, p2 in RAYS:
        u = (t - te) / RAY_TRAVEL
        if u < 0 or u > 1 + RAY_REFL / RAY_TRAVEL: continue
        if kind == 0:
            # v9: every ray from the Sun now lands ON ARGENTINA (v8 aimed them at random points of the sunlit face, so most of
            # them visibly missed the country). Target = a random point inside Argentina projected on the globe.
            if g is None or g[2] < 6 or sa < 0.05: continue
            cx, cy, R = g[0], g[1], g[2]
            lon, lat = AR_PTS[int(abs(p1) * (len(AR_PTS) - 1))]; X, Y, x3, y3, z3 = ortho(lon, lat, g)
            if z3 < 0.05: continue
            hit = np.array((float(X), float(Y)))
            start = np.array((sx, sy)) + np.array((-(cy - sy), cx - sx)) / max(1.0, math.hypot(cx - sx, cy - sy)) * p1 * Rs * 0.35
            n3 = np.array((float(x3), float(y3), float(z3))); n3 = n3 + np.array((p1 * 0.4, 0.3, 0.0)); n3 /= np.linalg.norm(n3)
            dd = (hit - start); dd = dd / max(1e-3, np.linalg.norm(dd))
            d3 = np.array((dd[0], -dd[1], -0.25)); d3 /= np.linalg.norm(d3)
            r3 = d3 - 2 * np.dot(d3, n3) * n3; rr = np.array((r3[0], -r3[1])); rr /= max(1e-3, np.linalg.norm(rr))
            v = 0.9 * sa * p2 + 0.3
        else:
            if c is None:
                if g is None: continue
                lon, lat = AR_PTS[p1]; X, Y, x3, y3, z3 = ortho(lon, lat, g)
                if z3 < 0.1: continue
                hit = np.array((float(X), float(Y)))
                n3 = np.array((float(x3), float(y3), float(z3)))
            else:
                lon, lat = AR_PTS[p1]; X, Y = proj(lon, lat, c); hit = np.array((X, Y)); n3 = np.array((0.0, 0.0, 1.0))
            d3 = -np.array(LIGHT)
            n3 = n3 + np.array((p2 * 0.6, 0.35, 0.0)); n3 /= np.linalg.norm(n3)                 # rough terrain: glints scatter
            r3 = d3 - 2 * np.dot(d3, n3) * n3; rr = np.array((r3[0], -r3[1])); nr = np.linalg.norm(rr); rr = rr / max(nr, 1e-3)
            start = hit - D_IN * 1500
            v = 0.85 * ray_a
        if v <= 0.01: continue
        if u <= 1:
            head = start + (hit - start) * u; tail = start + (hit - start) * max(0.0, u - 0.28)
            _seg(L, tail, head, v * (0.55 + 0.45 * u))
        else:
            w = (u - 1) * RAY_TRAVEL / RAY_REFL                                    # 0..1 along the reflection
            # v9: the incoming beam does not vanish on impact: its tail keeps sliding INTO the landing point, so every streak
            # visibly ends on Argentina
            tail = start + (hit - start) * min(1.0, 1 - 0.28 + 0.28 * eout(w * 1.6))
            if np.linalg.norm(hit - tail) > 1.5: _seg(L, tail, hit, v * (1 - 0.5 * w))
            ln = 260 if kind == 1 else 420
            head = hit + rr * ln * eout(w); tail = hit + rr * ln * max(0.0, eout(w) - 0.35)
            _seg(L, tail, head, v * 0.7 * (1 - w))
            cv2.circle(Hh, (int(hit[0]), int(hit[1])), int(4 + 26 * eout(w)), float(v * (1 - w) * 0.9), 2, cv2.LINE_AA)
            cv2.circle(Hh, (int(hit[0]), int(hit[1])), 3, float(v * 2.2 * (1 - w)), -1, cv2.LINE_AA)
    return L, Hh
def light_rgb(L, Hh):
    core = L + Hh
    gl = cv2.resize(cv2.GaussianBlur(cv2.resize(core, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), 6), (W, H))
    return (core[..., None] * np.array((255, 236, 190), np.float32) * 1.1 + gl[..., None] * np.array((255, 170, 70), np.float32) * 2.2)
def heat_level(t):
    """warm wash over Argentina while the rays land (context), cooling before the spark"""
    return clamp((t - 2.9) / 1.6) * (1 - clamp((t - T_COOL) / 0.5))
SPARK_LL = (float(LON[0]), float(LAT[0]))                                      # the first VIIRS hotspot of the series (Jan 2012)
def draw_spark(A, t, c):
    if not (T_SPARK - 0.05 <= t < T_LAND + 0.6): return A
    x, y = proj(*SPARK_LL, c); u = t - T_SPARK
    flick = 0.8 + 0.2 * math.sin(u * 37) * math.sin(u * 23 + 1)
    grow = eout(u / 0.25) * (1 - clamp((t - T_LAND - 0.1) / 0.5))
    burst = decay(t, T_SPARK, 0.12)
    L = np.zeros((H // 2, W // 2), np.float32)
    cv2.circle(L, (int(x / 2), int(y / 2)), 3, 1.0, -1, cv2.LINE_AA)
    g1 = cv2.GaussianBlur(L, (0, 0), 4) * 60; g2 = cv2.GaussianBlur(L, (0, 0), 22) * 420
    G = cv2.resize(g1 * (0.6 + 1.5 * burst) + g2 * (0.35 + 0.9 * burst), (W, H)) * grow * flick
    # embers rising from the spark (fixed seed)
    rg = np.random.default_rng(int(9))
    E = np.zeros((H, W), np.float32)
    for k in range(30):
        t0 = T_SPARK + rg.uniform(0, 2.7); vx, vy = rg.uniform(-30, 30), rg.uniform(-110, -50)
        uu = t - t0
        if 0 <= uu < 0.9: cv2.circle(E, (int(x + vx * uu + 6 * math.sin(uu * 9 + k)), int(y + vy * uu)), 2, float(1.2 * (1 - uu / 0.9)), -1, cv2.LINE_AA)
    E = E + cv2.GaussianBlur(E, (0, 0), 3) * 2.5
    col = G[..., None] * np.array((255, 150, 50), np.float32) + E[..., None] * np.array((255, 190, 90), np.float32) * grow
    core = np.zeros((H, W), np.float32); cv2.circle(core, (int(x), int(y)), 6, 1.0, -1, cv2.LINE_AA)
    col = col + core[..., None] * np.array((255, 250, 230), np.float32) * grow
    return 255 - (255 - A) * (255 - np.clip(col, 0, 255)) / 255
def space_frame(t):
    tau = t / SPACE_K
    A = np.zeros((H, W, 3), np.float32) + np.array(BG, np.float32)
    zk = [(0, 0.6), (1.0, 1.4), (2.0, 2.6), (3.4, 4.5)]
    zoom = _logkeys(tau, zk); vel = zoom - _logkeys(max(0, tau - 0.08), zk)
    SP.draw_stars(A, zoom, vel * 2.5, 0.9 * (1 - clamp((tau - 2.6) / 0.6)))
    sx, sy, Rs, sa = sun_state(t)
    SP.draw_sun(A, sx, sy, Rs, tau, sa)
    g = globe_state(t)
    if g is not None:
        SP.draw_globe(A, g[0], g[1], g[2], g[3], g[4], LIGHT, g[5], clamp((tau - 0.45) / 0.15))
        hk = heat_level(t) * (1 - g[5] * 0.3)
        if hk > 0.01 and g[2] > 200:                                        # Argentina warms on the globe as the rays land
            X, Y, _, _, z3 = ortho(AR_PTS[:, 0], AR_PTS[:, 1], g)
            Hm = np.zeros((H // 4, W // 4), np.float32); ok = z3 > 0.05
            for xx, yy in zip(X[ok] / 4, Y[ok] / 4):
                if 0 <= xx < W // 4 and 0 <= yy < H // 4: Hm[int(yy), int(xx)] += 1
            Hm = cv2.resize(cv2.GaussianBlur(Hm, (0, 0), max(2.0, g[2] / 160)), (W, H)); Hm /= max(1e-6, Hm.max())
            A = A + Hm[..., None] * np.array((120, 50, 10), np.float32) * hk
    L, Hh = ray_layer(t, None)
    A = A + light_rgb(L, Hh)
    return A

# ---------------- compositing ----------------
def scar_rgb(v, k_warm=0.0):
    base = np.array((205, 190, 172), np.float32); warm = np.array((235, 110, 45), np.float32)
    col = base * (1 - k_warm) + warm * k_warm
    return (np.clip(v, 0, 1) ** 0.55)[..., None] * col
def heat_wash(A, t, c):
    hk = heat_level(t)
    if hk <= 0.01: return A
    m = Image.new('L', (W // 2, H // 2), 0); dm = ImageDraw.Draw(m)
    for r in AR_OUT: dm.polygon([(x / 2, y / 2) for x, y in ring_px(r, c)], fill=255)
    m = cv2.resize(cv2.GaussianBlur(np.asarray(m, np.float32) / 255, (0, 0), 3), (W, H))
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    shimmer = 0.85 + 0.15 * np.sin(yy * 60 + t * 9)                          # heat haze bands drifting up
    return A + (m * shimmer)[..., None] * np.array((95, 38, 8), np.float32) * hk
def _s2_overlap(t):
    """does the flying Sentinel-2 frame (outline drawn from S_PA[0]-FLYIN) intersect the legend box (bottom-right, ~860x130 px)?"""
    x0, y0, x1, y1 = s2_corners(cam_at(t)); return x1 > W - 960 and x0 < W - 60 and y1 > H - 170 and y0 < H - 30
_TS = [x / 30 for x in range(int((S_PA[0] - FLYIN[2] - 0.2) * 30), int((S_PA[0] + 1.0) * 30))]
_OV = [x for x in _TS if _s2_overlap(x)]
LEG_GAP = (min(_OV), max(_OV)) if _OV else None
def legend_gap(t):
    if LEG_GAP is None: return 1.0
    g0, g1 = LEG_GAP; return max(clamp((g0 - 0.05 - t) / 0.25), clamp((t - g1 - 0.05) / 0.3))
T_HOOK = (0.45, 3.85)                       # v7: the question is asked in the first second (hook), answered by the data at T_LAND
def draw_hook(fr, t):
    h0, h1 = T_HOOK
    if not (h0 <= t < h1 + 0.4): return
    slam(fr, (FX.TX, HOOK_Y), "¿DÓNDE ARDE", font("anton", 132), WH, t, h0, h1, glow=0.25)
    slam(fr, (FX.TX, HOOK_Y + 142), "ARGENTINA?", font("anton", 132), OR, t, h0 + 0.12, h1, glow=0.6)
HOOK_Y = 820
def render_at(t):
    if t < T_X0:
        fr = Frame(Image.fromarray(np.clip(space_frame(t), 0, 255).astype(np.uint8))); draw_hook(fr, t); return finish(fr, t, flash=0.0)
    c = cam_at(t)
    A = np.asarray(base_map(c), np.float32)
    # ---- 0. intro on the flat map: heat wash, rays landing on Argentina, the spark
    if t < T_LAND + 0.7:
        A = heat_wash(A, t, c)
        L, Hh = ray_layer(t, c)
        A = A + light_rgb(L, Hh)
        A = draw_spark(A, t, c)
    # ---- 1. the fast 14 years (VIIRS points) and their burn-out to ash
    if T_LAND <= t < T_SCAR + 0.6:
        n_prior = int(np.searchsorted(PS_A, min(t, T_A1 + 1e-3), side="right"))
        ember = splat(LON[:n_prior], LAT[:n_prior], None, c) if n_prior else np.zeros((H, W), np.float32)
        i0 = int(np.searchsorted(PS_A, t - 1.0))
        w = np.exp(-(t - PS_A[i0:n_prior]) / 0.16).astype(np.float32) if t < T_A1 + 1 else np.zeros(0, np.float32)
        fire = splat(LON[i0:n_prior], LAT[i0:n_prior], w, c) if len(w) else np.zeros((H, W), np.float32)
        acc = clamp((t - T_A1 + 0.3) / 0.3) * (0.85 + 0.3 * decay(t, T_A1, 0.6)) if t >= T_A1 - 0.3 else 0.0
        ash_k = clamp((t - T_ASH) / 0.9)
        gone = clamp((t - T_SCAR) / 0.6)
        em = np.clip(np.log1p(ember) / math.log1p(60), 0, 1)
        v = 1 - np.exp(-fire * 0.55)
        if acc > 0: v = np.maximum(v, np.clip(np.log1p(ember) / math.log1p(500 * max(1.0, c[2] / 30.0) ** 1.6), 0, 1) ** 1.1 * acc * 0.92)
        v = cv2.GaussianBlur(v, (0, 0), 0.7) * 1.25
        F = LUT[np.clip(v * 255, 0, 255).astype(np.uint8)] * (1 - ash_k)
        hs = cv2.resize(F, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        bloom = cv2.resize(cv2.GaussianBlur(hs, (0, 0), 5) * 0.9 + cv2.GaussianBlur(hs, (0, 0), 18) * 0.9, (W, H)) * (1.0 + 0.6 * decay(t, T_A1, 0.9))
        E = em[..., None] * np.array((120, 30, 10), np.float32) * 0.85 * (1 - clamp(acc)) * (1 - ash_k)
        ASHL = (np.clip(v, 0, 1) ** 0.8)[..., None] * np.array(ASH, np.float32) * 0.75 * ash_k * (1 - gone)
        A = A + E + ASHL
        A = 255 - (255 - A) * (255 - np.clip(F + bloom, 0, 255)) / 255
    # ---- 2. MODIS burned area
    sk = clamp((t - T_SCAR + 0.3) / 0.9)
    if sk > 0:
        sv = warp_raster(SCAR, c)
        dimk = 1.0 if t < T_D1 else 0.5
        dimk *= 1 - 0.55 * clamp((t - T_RK) / 0.5) * (1 - clamp((t - T_RK_END) / 0.6))       # quieter under the ranking
        dimk = lerp(dimk, 1.0, clamp((t - T_CL + 0.4) / 1.0))                                  # v8 close: the full scar map, at full strength
        dimk *= 1 - 0.75 * clamp((c[2] - 900) / 1500)                                           # v9: MODIS 500 m blocks recede in the satellite zooms
        k_warm = 0.5 * decay(t, T_SCAR, 0.8)
        A = A * (1 - 0.6 * (np.clip(sv, 0, 1) ** 0.55)[..., None] * sk) + scar_rgb(sv, k_warm) * sk * dimk
        for pyr_, w in ((SC_ER, stop_w(t, 1)),):                                   # v9: Entre Ríos 2020 at its stop (Corrientes overlay removed)
          if w > 0.003:
            ev_ = warp_raster(pyr_, c); edge = np.clip(ev_ - cv2.GaussianBlur(ev_, (0, 0), 2.5), 0, 1) * 3
            A = A * (1 - 0.35 * ev_[..., None] * w) + ev_[..., None] * np.array((150, 46, 18), np.float32) * w + np.clip(edge, 0, 1)[..., None] * np.array((255, 140, 50), np.float32) * w * 0.8
    A = ranking_fill(A, t, c)
    # ---- 3. Comarca Andina: Sentinel-2 in place, then MODIS 2025 / 2026 scars
    wpa = stop_w(t, 2)
    if wpa > 0.003:
        p0 = S_PA[0]
        y_from, y_to, k = (2024, 2025, clamp((t - p0 - 0.7) / 0.45)) if t < p0 + 1.75 else (2025, 2026, clamp((t - p0 - 1.85) / 0.45))
        im0, m = s2_layer(c, y_from); im1, _ = s2_layer(c, y_to)
        x0, y0, x1, y1 = s2_corners(c); wipe = x0 + (x1 - x0) * k
        sel = (np.arange(W)[None, :, None] < wipe).astype(np.float32)
        img = im1 * sel + im0 * (1 - sel)
        A = A * (1 - m * wpa) + img * 0.9 * m * wpa
        for pyr, y_on, col in ((SC_P25, p0 + PA_ON[0], (255, 176, 60)), (SC_P26, p0 + PA_ON[1], (255, 64, 40))):
            kk = clamp((t - y_on) / 0.4) * wpa
            if kk > 0:
                ev_ = warp_raster(pyr, c, cv2.INTER_NEAREST); edge = np.clip(ev_ - cv2.erode(ev_, np.ones((3, 3), np.uint8)), 0, 1)
                A = A * (1 - 0.25 * ev_[..., None] * kk) + ev_[..., None] * np.array(col, np.float32) * 0.28 * kk + edge[..., None] * np.array(col, np.float32) * kk
    # ---- 3b. v9: Sentinel-2 views of Tucumán and the Delta, in place on the same map (the camera zooms into them)
    for i, v in enumerate(S2V):
        w2 = s2v_w(t, i)
        if w2 > 0.003:
            im, m = s2v_layer(v, c)
            A = A * (1 - m * w2) + im * m * w2
            Lf = s2v_fire(t, i, c)
            if Lf is not None:
                Lb = cv2.GaussianBlur(Lf, (0, 0), 6) * 1.6
                A = 255 - (255 - A) * (255 - np.clip(Lf[..., None] * np.array((255, 236, 170), np.float32) + Lb[..., None] * np.array((255, 110, 30), np.float32), 0, 255)) / 255
    # ---- 4. event hotspots replayed inside each stop
    for i in range(3):
        s0, s1 = STOPS[i]
        if not (s0 - 0.3 <= t < s1 + 0.5): continue
        idx = EVENTS[i]; tt = EVT[i]; on = tt <= t
        if not on.any(): continue
        wv = np.where(on, 0.25 + 1.6 * np.exp(-(t - tt) / 0.35), 0).astype(np.float32) * (1 - clamp((t - s1 + 0.2) / 0.5))
        if i == 2: fire = cv2.GaussianBlur(splat(LON[idx], LAT[idx], wv, c), (0, 0), 2.2) * 9
        else: fire = zoom_blur(splat(LON[idx], LAT[idx], wv, c), c) * (0.5 if i == 0 else 0.6)
        v = 1 - np.exp(-fire * 0.8)
        F = LUT[np.clip(v * 255, 0, 255).astype(np.uint8)]
        hs = cv2.resize(F, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        bloom = cv2.resize(cv2.GaussianBlur(hs, (0, 0), 6) * 0.8, (W, H))
        A = 255 - (255 - A) * (255 - np.clip(F + bloom, 0, 255)) / 255
    # ---- 5. v8 close: everything that burned 2012-2025 — every VIIRS hotspot accumulates over the MODIS scar map
    if t >= T_CL - 0.6:
        hk = clamp((t - T_CL - 0.1) / 1.5); n = int(np.searchsorted(TS, 168.0 * eout(hk), side="right"))
        if n:
            ember = splat(LON[:n], LAT[:n], None, c)
            v = np.clip(np.log1p(ember) / math.log1p(500 * max(1.0, c[2] / 30.0) ** 1.6), 0, 1) ** 1.1 * 0.92
            v = cv2.GaussianBlur(v, (0, 0), 0.7) * 1.25 * clamp((t - T_CL + 0.6) / 0.6) * (1 - 0.35 * clamp((t - T_SRC) / 0.5))
            F = LUT[np.clip(v * 255, 0, 255).astype(np.uint8)]
            hs = cv2.resize(F, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
            bloom = cv2.resize(cv2.GaussianBlur(hs, (0, 0), 5) * 0.7 + cv2.GaussianBlur(hs, (0, 0), 18) * 0.7, (W, H)) * (1 + 0.5 * decay(t, T_CL + 1.6, 0.8))
            A = 255 - (255 - A) * (255 - np.clip(F + bloom, 0, 255)) / 255
    A = spotlight(A, t, c)
    shade = clamp((t - T_X0 - 0.2) / 0.5)
    if t < T_MAP:
        kx = einout((t - T_X0) / (T_MAP - T_X0)); A = space_frame(t) * (1 - kx) + A * kx
    fr = Frame(left_shade(Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)), 0.92 * shade))
    if wpa > 0.003:
        x0, y0, x1, y1 = s2_corners(c); a = wpa * clamp((t - S_PA[0] - 0.4) / 0.3)
        fr.d.rectangle((x0, y0, x1, y1), outline=(242, 240, 236, int(200 * a)), width=2)
        lab = "DIC 2024" if t < S_PA[0] + 0.92 else "ABR 2025" if t < S_PA[0] + 2.07 else "ABR 2026"
        put_text(fr, (x1 + 16, y0 + 48), lab, font("mono", 48, 800), WH, a, cache=True)
        put_text(fr, (x1 + 16, y0 + 106), "Sentinel-2", font("inter", 48, 600), MU, a)
        if t > S_PA[0] + PA_ON[0]: put_text(fr, (x1 + 16, y1 - 76), "■ 2025", font("mono", 48, 800), AM, a * clamp((t - S_PA[0] - PA_ON[0]) / 0.3))
        if t > S_PA[0] + PA_ON[1]: put_text(fr, (x1 + 16, y1 - 14), "■ 2026", font("mono", 48, 800), RD, a * clamp((t - S_PA[0] - PA_ON[1]) / 0.3))
    for i, v in enumerate(S2V):
        w2 = s2v_w(t, i)
        if w2 > 0.003:
            x0, y0, x1, y1 = s2v_corners(v, c)
            if t < S2Z[i][1]: fr.d.rectangle((x0 - 3, y0 - 3, x1 + 3, y1 + 3), outline=(8, 6, 6, int(200 * w2)), width=3)
            fr.d.rectangle((x0, y0, x1, y1), outline=(HOT if t < S2Z[i][1] else WH) + (int(240 * w2),), width=3 if t < S2Z[i][1] else 2)
            if t < S2Z[i][1]: fr.glow_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], mixc((0, 0, 0), AM, w2), 10)
        la2 = s2v_label_a(t, i)
        if la2 > 0.003:
            x0, y0, x1, y1 = s2v_corners(v, c); l1, l2 = S2LAB[i]
            put_text(fr, (FX.TX, 470), l1, font(*HEAD_F), AM, la2)
            put_text(fr, (FX.TX, 550), l2, font("inter", 52, 600), WH, la2)
            if i == 1:
                px, py = proj(*ROSARIO, c)
                fr.d.ellipse((px - 10, py - 10, px + 10, py + 10), outline=WH + (int(255 * la2),), width=3)
                f = font("mono", 48, 800)
                for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)): put_text(fr, (px + 22 + ox, py + 16 + oy), "ROSARIO", f, (10, 8, 8), la2)
                put_text(fr, (px + 22, py + 16), "ROSARIO", f, WH, la2)
    draw_country(fr, t, c)
    for i in range(3): draw_stop(fr, t, i, c)
    draw_ranking(fr, t, c)
    ui = clamp((t - T_LAND) / 0.4) * (1 - clamp((t - T_ASH + 0.2) / 0.5))
    draw_year(fr, t, ui); draw_timeline(fr, t, ui)
    # ---- legend (bottom-right): what a point and what the grey are (hidden under the ranking and the satellite zooms)
    fl = font("inter", 48, 600)
    la = clamp((t - T_LAND - 0.3) / 0.4) * (1 - clamp((t - T_CL + 0.3) / 0.4)) * (1 - clamp((t - T_RK) / 0.3) * (1 - clamp((t - T_RK_END) / 0.4)))
    la *= legend_gap(t)                     # v7: hidden while the Comarca Sentinel-2 frame flies in under it
    for z0, z1, z2 in S2Z: la *= 1 - clamp((t - z0 + 0.3) / 0.3) * (1 - clamp((t - z2 - ZOUT) / 0.3))
    if la > 0.003:
        put_text(fr, (W - 80 - tw(LEG1, fl), H - 60), LEG1, fl, MU, la)
        if sk > 0: put_text(fr, (W - 80 - tw(LEG2, fl), H - 122), LEG2, fl, ASH, la * sk)
    # ---- text cards (v9: fewer words, >= 48 px, each held >= 0.35 s/word + 1 s)
    draw_hook(fr, t)
    if T_TXT1 <= t < T_TXT2_END + 0.4:
        slam(fr, (FX.TX, 420), TXT_SOL, font("anton", 100), WH, t, T_TXT1, T_TXT1_END, big=False)
        slam_tight(fr, (FX.TX, 590), TXT_CHISPA, font("anton", 116), OR, t, T_SPARK + 0.1, T_TXT2_END, glow=0.55)
        slam(fr, (FX.TX, 690), TXT_CAUSA, font("anton", 66), WH, t, T_SPARK + 0.5, T_TXT2_END, big=False)
    if T_SCAR - 0.05 <= t < T_D1:
        e = T_D1 - 0.3
        number_line(fr, t, T_SCAR, e, 600, f"{UNIQ_TXT} MILLONES", WH, "DE HA", glow=0.4)          # slams on the scar boom
        slam(fr, (FX.TX, 700), TXT_AREA, font("anton", 66), OR, t, T_SCAR + 0.35, e, glow=0.3)
    if CL_L2 - 0.05 <= t < T_SRC:
        e = T_SRC - 0.3
        slam_tight(fr, (FX.TX, 560), "YA NO FALTAN DATOS.", font("anton", 124), WH, t, CL_L2, e, glow=0.35)
        slam_tight(fr, (FX.TX, 704), "FALTA RESPONSABILIDAD.", font("anton", 124), OR, t, CL_L2 + 0.25, e, glow=0.6)
    if t >= T_SRC: sources(fr, t)
    flash = min(1.0, sum(0.3 * decay(t, x, 0.11) for x in REVEALS))
    return finish(fr, t, flash=flash)

def slam_tight(fr, xy, s, f, col, t, t0, t1, glow=0.0, over=0.08):
    if t < t0: return
    u = t - t0; sc = 1 + over * (1 - eout5(u / 0.28)); a = clamp(u / 0.09); flare = 1 + 1.6 * decay(t, t0, 0.18)
    o = clamp((t - t1) / 0.3); a *= 1 - o; sc *= 1 + 0.03 * o
    if a > 0: put_text(fr, xy, s, f, col, a, sc, glow * flare)
SRC = ["FUENTES",
       "Focos: NASA FIRMS, VIIRS 375 m, 2012–2025 (1 foco ≠ 1 incendio).",
       "Área quemada: NASA MODIS MCD64A1, 500 m; cada píxel cuenta 1 vez.",
       "Causas: Min. de Ambiente, 1993–2019. Caña: EEAOC. Límites: INDEC.",
       "«Lo habitual»: mediana de los otros 13 años. Comarca: ene–mar.",
       "Imágenes: datos Copernicus Sentinel-2 modificados (2020–2026).",
       "Banderas: Wikimedia Commons (DP; CC BY 4.0: Chubut, R. V. Jones /",
       "Gob. del Chubut; Río Negro, D. Cuomo y Hellerick).",
       "Sol, Tierra, mapas, animación y música: hechos con código."]
def sources(fr, t):
    a = clamp((t - T_SRC) / 0.4)
    d = fr.d; d.rectangle((0, 0, W, H), fill=(6, 6, 9, int(215 * a)))
    put_text(fr, (FX.TX, 170), SRC[0], font("anton", 80), OR, a)
    fb = font("inter", 48, 500)
    for i, s in enumerate(SRC[1:]):
        put_text(fr, (FX.TX, 272 + i * 92), s, fb, WH, a * clamp((t - T_SRC - 0.04 * i) / 0.3))

NUM = dict(total=S["total_focos"], burn_M=BURN_M, pitches_per_min=PITCH_PER_MIN,
           comarca_2025=S["comarca_2025_ha"], comarca_2026=S["comarca_2026_ha"], houses=HOUSES, deaths=DEATHS, tuc_pct=TU_PCT,
           hum_10=HUM_10, hum_share_known=CA["humana_sobre_conocida"], top5_pct=TOP5_PCT, top5=[(r["name"], round(r["ha_unique"])) for r in ROWS[:5]], uniq=UNIQ, share_ar=SHARE_AR, tu_zone_pct=TU_ZONE_PCT, er=ER_N, er_ratio_other13=ER_R, er_median_other13=S["er_median_other13"])
TIMES = dict(T_X0=T_X0, T_MAP=T_MAP, T_TXT1=T_TXT1, T_COOL=T_COOL, T_SPARK=T_SPARK, T_LAND=T_LAND, T_A1=T_A1, T_ASH=T_ASH, T_SCAR=T_SCAR,
             T_D1=T_D1, T_RK=T_RK, T_RK2=T_RK2, T_RK_END=T_RK_END, S_TU=S_TU, Z_TU=Z_TU, S_ER=S_ER, Z_ER=Z_ER, S_PA=S_PA,
             T_CL=T_CL, CL_DIP=CL_DIP, CL_L2=CL_L2, T_SRC=T_SRC, TOTAL=TOTAL)
if __name__ == "__main__":
    if "--nums" in sys.argv:
        print(json.dumps(NUM, indent=1, ensure_ascii=False)); print("times", json.dumps({k: (round(v, 2) if isinstance(v, float) else [round(x, 2) for x in v]) for k, v in TIMES.items()}))
    if "--still" in sys.argv:
        os.makedirs(os.path.join(HERE, "qa"), exist_ok=True)
        import time
        for x in sys.argv[sys.argv.index("--still") + 1:]:
            t0 = time.time(); render_at(float(x)).save(os.path.join(HERE, "qa", f"still_{float(x):05.2f}.png")); print("still", x, round(time.time() - t0, 2), "s", flush=True)
