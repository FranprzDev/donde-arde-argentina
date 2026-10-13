"""Contar con Datos 2026 · Historia visual · v7 «¿Dónde arde Argentina?» (v6 + critical review, 13-10-2026)
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
Usage: python3 render_v7.py --nums | --still t1 t2 ..."""
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
GRAY_PX = 40

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
CO_HA = S["corr_janfeb_2022_ha"]; assert 0.9e6 < CO_HA < 1e6                         # «casi 1 millón de hectáreas»
N_CABA = int(S["n_caba_corr"]); assert N_CABA == 46 and S["n_caba_corr"] > 46        # «más de 46 Capitales» (46,63)
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
CO_RANK = [r["rank"] for r in ROWS if r["code"] == "18"][0]; assert CO_RANK == 4
VMAX = ROWS[0]["ha_unique"]
def mha(x): return es_dec(x / 1e6, 1)
TOP5_TXT = [(r["name"].upper(), mha(r["ha_unique"])) for r in ROWS[:5]]
assert TOP5_TXT == [("FORMOSA", "3,2"), ("LA PAMPA", "3,0"), ("SANTA FE", "2,8"), ("CORRIENTES", "2,7"), ("SANTIAGO DEL ESTERO", "2,5")], TOP5_TXT
TUS = json.load(open(os.path.join(D2, "tucuman_stats.json"))); assert TUS["cane_zafra"] == 53625; TU_ZONE_PCT = round(100 * TUS["area_cane12_km2"] / TUS["area_tuc_km2"]); assert TU_ZONE_PCT == 69                  # the 12 cane departments = 69 % of Tucumán
FEATURED = {"18", "90", "26", "62"}          # Corrientes, Tucumán, Chubut, Río Negro (the stops)

# ---------------- points ----------------
P = np.load(os.path.join(D1, "points.npz"))
o = np.argsort(P["t"], kind="stable")
TS = P["t"][o].astype(np.float64); LON = P["lon"][o].astype(np.float32); LAT = P["lat"][o].astype(np.float32); PRV = P["prov"][o]
CODES = sorted(json.load(open("../data/natgeo_v7.json"))["prov"])
def pidx(c): return CODES.index(c)
def warp(t0, segs):
    km = [segs[0][0]]; ks = [t0]
    for a, b, s in segs: km.append(b); ks.append(ks[-1] + (b - a) * s)
    return np.array(km, float), np.array(ks, float)

# ---------------- timeline ----------------
SPACE_K = 1.25                             # the v5 space opening, played 1.25x slower (room for the rays)
T_X0 = 3.2 * SPACE_K                       # 4.0: globe -> flat map crossfade
T_MAP = 3.7 * SPACE_K                      # 4.625: flat map
T_TXT1 = 4.45                              # «EL SOL CALIENTA.»
T_COOL = 5.45                              # rays stop, heat fades
T_SPARK = 5.55                             # the spark; «LA CHISPA ES HUMANA.»
T_LAND = 7.9                               # the spark becomes 14 years of hotspots + title
KA_M, KA_S = warp(T_LAND, [(0, 12, 0.042), (12, 156, 0.0262), (156, 168, 0.036)])
T_A1 = float(KA_S[-1])                     # ~12.7: all 14 years lit -> «2.550.467 FOCOS»
T_ASH = T_A1 + 1.8
T_SCAR = T_ASH + 0.8
T_D1 = T_ASH + 3.5                         # end of «44 MILLONES DE HA»
T_RK = T_D1                                # ranking: sweep through all 24 jurisdictions
RK_STEP = 0.12
T_RK2 = T_RK + 0.4 + 23 * RK_STEP + 0.6    # collapse to the top 5
T_RK_END = T_RK2 + 4.3
S_CO = (T_RK_END + 1.0, T_RK_END + 1.0 + 5.6)
S_TU = (S_CO[1] + 1.2, S_CO[1] + 1.2 + 5.3)
S_PA = (S_TU[1] + 1.4, S_TU[1] + 1.4 + 6.8)
T_CL = S_PA[1] + 1.0
T_SRC = T_CL + 6.1
TOTAL = round(T_SRC + 5.4, 2)
CL_L1, CL_NOTE, CL_DIP, CL_L2, CL_L3 = T_CL, T_CL + 0.6, T_CL + 1.55, T_CL + 2.0, T_CL + 3.7
FLYIN = [1.0, 1.2, 1.4]
STOPS = [S_CO, S_TU, S_PA]                # stop index: 0 Corrientes, 1 Tucumán, 2 Comarca Andina
REVEALS = [T_SPARK, T_LAND, T_A1, T_SCAR, T_RK2 + 0.1, S_CO[0], S_TU[0], S_PA[0], T_CL + 2.0]
SHAKES = [(T_LAND, 7), (T_A1, 10), (T_SCAR, 5), (S_PA[0] + 0.1, 5)]
assert 59.0 <= TOTAL <= 60.0, TOTAL

def m_now(t):
    if t < T_LAND: return 0.0
    if t < T_A1: return float(np.interp(t, KA_S, KA_M))
    return 168.0
PS_A = np.interp(TS, KA_M, KA_S).astype(np.float32)

def ev(mask): return np.where(mask)[0]
EV_CO = ev((PRV == pidx("18")) & (TS >= 120) & (TS < 122))
EV_TU = ev((PRV == pidx("90")) & ((TS % 12) >= 4) & ((TS % 12) < 11))
EV_PA = ev(np.isin(PRV, [pidx("26"), pidx("62")]) & (LON < -70.9) & (TS >= 156) & (TS < 159))
EVENTS = [EV_CO, EV_TU, EV_PA]
def ev_times(i, t0, dur):
    idx = EVENTS[i]; tt = TS[idx]; k = (tt - tt.min()) / max(1e-6, tt.max() - tt.min()) if len(tt) > 1 else np.zeros(len(tt))
    if i == 1: k = ((tt % 12) - 4) / 7.0 * 0.85                 # Tucumán: one zafra, May -> Nov, all years stacked
    return (t0 + 0.3 + k * dur).astype(np.float32)
EVT = [ev_times(i, STOPS[i][0], 2.4 if i == 1 else 2.2) for i in range(3)]

# ---------------- geography ----------------
NG = json.load(open("../data/natgeo_v7.json"))
GEO = json.load(open("../data/geo_v2.json"))
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
STOPCAM = [(-57.85, -28.75, 175, 1370, 560), (-65.25, -27.05, 230, 1440, 560), (-71.43, -42.18, 760, 1400, 560)]
NORTE = ["10", "18", "22", "34", "38", "46", "54", "66", "86", "90"]
STOPOUT = [outline(["18"]), outline(["90"]), outline(["26", "62"])]
NORTE_OUT = outline(NORTE)
def _cord():
    u = shapely.union_all([shapely.Polygon(r) for c in ("58", "62", "26", "78") for r in NG["prov"][c]]).buffer(0.01).buffer(-0.01)
    u = u.intersection(shapely.box(-76, -56, -70.5, -36)).simplify(0.01)
    return [np.asarray(g.exterior.coords, np.float32) for g in (u.geoms if hasattr(u, "geoms") else [u]) if g.area > 0.05]
CORD_OUT = _cord()
STOPDIM = [0.45, 0.45, 0.3]
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
    w = close_w(t)
    if w > 0.003: A = _dim(A, NORTE_OUT + CORD_OUT, c, 0.55 * w)
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
SEG = [(0.0, T_LAND, CAM_IN, CAM_IN, "hold"), (T_LAND, T_A1, CAM_IN, CAM0, "ease"), (T_A1, T_A1 + 0.4, CAM0, CAM_ACC, "ease"),
       (T_A1 + 0.4, T_RK - 0.2, CAM_ACC, CAM_ACC, "hold"), (T_RK - 0.2, T_RK + 0.5, CAM_ACC, CAM_RK, "ease"),
       (T_RK + 0.5, T_RK_END - 0.2, CAM_RK, CAM_RK, "hold"),
       (T_RK_END - 0.2, S_CO[0] + 0.15, CAM_RK, STOPCAM[0], "zoomto"), (S_CO[0] + 0.15, S_CO[1] - 0.15, STOPCAM[0], STOPCAM[0], "hold"),
       (S_CO[1] - 0.15, S_TU[0] + 0.15, STOPCAM[0], STOPCAM[1], "fly"), (S_TU[0] + 0.15, S_TU[1] - 0.15, STOPCAM[1], STOPCAM[1], "hold"),
       (S_TU[1] - 0.15, S_PA[0] + 0.15, STOPCAM[1], STOPCAM[2], "fly"), (S_PA[0] + 0.15, S_PA[1] - 0.15, STOPCAM[2], STOPCAM[2], "hold")]
CAM_CL = (-64.2, -38.6, 28.0, 1500, 548)
SEG += [(S_PA[1] - 0.15, T_CL + 0.4, STOPCAM[2], CAM_CL, "zoomto"), (T_CL + 0.4, 999, CAM_CL, CAM_CL, "hold")]
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
            m = (tt <= t) & (tt > t - 2.0); return float(np.exp(-(t - tt[m]) / 0.4).sum()) * (60 if i == 2 else 3 if i == 1 else 1)
    if T_SPARK <= t < T_LAND: return 0.15
    return 0.0

# ---------------- MODIS scars ----------------
GR = json.load(open(os.path.join(D2, "scar_grid.json")))
def _pyr(name):
    z = np.load(os.path.join(AS, name + ".npz")); return [z[f"l{k}"] for k in range(6)]
SCAR = _pyr("scar_all"); SC_CO = _pyr("scar_corr_2022")
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
    fl = font("mono", 36, 700)
    for y in range(2012, 2027):
        x = tl_x((y - 2012) * 12); d.line([(x, TLYB), (x, TLYB + (12 if y % 4 == 0 else 6))], fill=(150, 146, 140, int(170 * a)), width=2)
        if y in (2012, 2016, 2020, 2024): put_text(fr, (x + 4, TLYB + 40), str(y), fl, MU, a)
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
    put_text(fr, (TLX0, TLYB - TLH - 26), "FOCOS POR MES", font("mono", 36, 700), MU, a * 0.95)
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
FLAGS = {n: _flag(n) for n in ("corrientes", "chubut", "rio_negro", "tucuman")}
STOPFLAGS = [["corrientes"], ["tucuman"], ["chubut", "rio_negro"]]
def draw_flags(fr, names, x, y_mid, a, sc):
    if a <= 0.003: return x
    for n in names:
        im, pad = FLAGS[n]
        if abs(sc - 1) > 0.004: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
        al = im.getchannel("A").point(lambda v: int(v * a))
        fr.im.paste(im.convert("RGB"), (int(x - pad * sc), int(y_mid - im.height / 2)), al)
        x += im.width - 2 * pad * sc + 14
    return x

# ---------------- pinned photo flashes (no text) ----------------
def _ld(n): return Image.open(os.path.join(AS, n + ".png")).convert("RGBA")
CARDS = {"ph_corr": _ld("ph_corr"), "ph_brig": _ld("ph_brig"), "ph_forest": _ld("ph_forest")}
PINS = {"ph_corr": (-57.35, -28.15), "ph_brig": (-71.55, -42.32), "ph_forest": (-71.40, -42.06)}
def _seq():
    c0, p0 = S_CO[0], S_PA[0]
    X, Y = FX.TX - 18, 22
    return [("ph_corr", c0 + 4.2, c0 + 4.75, X, Y, "ph"),
            ("ph_brig", p0 + 4.5, p0 + 5.05, X, Y, "ph"), ("ph_forest", p0 + 5.15, p0 + 5.7, X, Y, "ph")]
SEQ = _seq()
def draw_card(fr, name, t, t0, t1, x, y, kind, c):
    if not (t0 - 0.05 <= t < t1 + 0.12): return
    u = t - t0; a = clamp(u / 0.06) * (1 - clamp((t - t1) / 0.1))
    if a <= 0.003: return
    im = CARDS[name]; sc = 1 + 0.10 * (1 - eout(u / 0.25)) + 0.03 * clamp(u / max(0.1, t1 - t0))
    if abs(sc - 1) > 0.004: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
    px, py = proj(*PINS[name], c)
    cx0, cy0 = x + CARDS[name].width - 18, y + CARDS[name].height / 2
    d = fr.d; d.line([(cx0, cy0), (px, cy0), (px, py)], fill=(242, 240, 236, int(200 * a)), width=2)
    d.ellipse((px - 9, py - 9, px + 9, py + 9), outline=(242, 240, 236, int(255 * a)), width=3); d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=OR + (int(255 * a),))
    al = im.getchannel("A").point(lambda v: int(v * a))
    fr.im.paste(im.convert("RGB"), (int(x - (im.width - CARDS[name].width) / 2), int(y - (im.height - CARDS[name].height) / 2)), al)
def draw_cards(fr, t, c):
    for name, t0, t1, x, y, kind in SEQ: draw_card(fr, name, t, t0, t1, x, y, kind, c)

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

# CABA silhouettes over the Corrientes scar (real scale, IGN boundary)
CT = json.load(open(os.path.join(AS, "caba_tiles.json"))); CREL = np.asarray(CT["rel"], np.float32)
assert CT["N"] == N_CABA
def caba_n(t):
    t0 = S_CO[0] + 1.4; return int(clamp((t - t0) / 2.4) * N_CABA)
def draw_caba(fr, t, c, a):
    n = caba_n(t)
    if a <= 0.003 or n <= 0: return
    d = fr.d
    for i, (lon, lat) in enumerate(CT["tiles"][:n]):
        pts = ring_px(CREL + np.float32([lon, lat]), c)
        fresh = clamp(1 - (n - 1 - i) / 3.0)
        d.polygon(pts, fill=(242, 240, 236, int((150 + 80 * fresh) * a)))
        d.line(pts + pts[:1], fill=(20, 18, 18, int(200 * a)), width=2)
        if fresh > 0.3: fr.glow_line(pts + pts[:1], mixc((0, 0, 0), WH, a * fresh * 0.6), 6)

# ---------------- stop cards (v6: header, one big number, one line; a grey note only where a caveat is required) ----------------
STOPTXT = [
    dict(head=f"CORRIENTES · PUESTO {CO_RANK} · ENE–FEB 2022", num="CASI 1 MILLÓN", unit="DE HA", line=f"MÁS DE {N_CABA} CIUDADES DE BUENOS AIRES",
         foot=None, cn=HOT, cl=WH),
    dict(head="TUCUMÁN · ZAFRA DE CAÑA (MAY–NOV) · 2012–2025", num=f"{TU_PCT} %", unit="DE SUS FOCOS", line="EN LA ZONA CAÑERA, EN PLENA ZAFRA",
         foot=f"Esos departamentos = {TU_ZONE_PCT} % de la provincia", foot2="Quemar está prohibido (Ley 6253)", cn=HOT, cl=AM),
    dict(head="COMARCA ANDINA · CHUBUT Y RÍO NEGRO", num=es_int(PA26), unit="HA EN 2026", line=f"{PA_X} VECES MÁS QUE EN 2025",
         foot=None, line2=f"2025: {HOUSES} CASAS PERDIDAS Y {DEATHS} MUERTO", cn=HOT, cl=AM),
]
def number_line(fr, t, t0, t1, y, num, col, unit, dur=1.0, glow=0.55, count_to=None, size=150):
    fN = font("anton", size); fU = font("anton", 76)
    s = es_int(count(t, t0, count_to, dur)) if count_to is not None else num
    slam(fr, (FX.TX, y), s, fN, col, t, t0, t1, glow=glow, cache=count_to is None)
    slam(fr, (FX.TX + tw(num, fN) + 26, y), unit, fU, WH, t, t0 + 0.3, t1, big=False)
def draw_stop(fr, t, i, c):
    t0, t1 = STOPS[i]; s = STOPTXT[i]
    fly = FLYIN[i]
    # v6: the destination lights up while the camera is still flying to it (province outline; Sentinel-2 frame for the Comarca)
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
    if i == 1 and a > 0:
        for r in TUC_ZONE:
            pts = ring_px(r, c); fr.d.line(pts + pts[:1], fill=HOT + (int(255 * a),), width=4)
    cb = t0 + 0.12; ce = t1 - 0.25
    u = t - cb; fa = clamp(u / 0.2) * (1 - clamp((t - ce) / 0.3)); fsc = 1 + 0.12 * (1 - eout(u / 0.35))
    xe = draw_flags(fr, STOPFLAGS[i], FX.TX, 430 - 13 + (1 - eout(u / 0.35)) * 18, fa, fsc)
    slam(fr, (xe + 10, 430), s["head"], font("mono", 36, 800), AM, t, cb, ce, big=False)
    if i == 0:   # Corrientes: the line counts the Capitals as they tile the scar
        n = caba_n(t)
        slam(fr, (FX.TX, 600), s["num"], font("anton", 150), s["cn"], t, cb + 0.2, ce, glow=0.55)
        slam(fr, (FX.TX + tw(s["num"], font("anton", 150)) + 26, 600), s["unit"], font("anton", 76), WH, t, cb + 0.5, ce, big=False)
        if t >= S_CO[0] + 1.4:
            line = f"= {n} CIUDADES DE BUENOS AIRES" if n < N_CABA else s["line"]
            put_text(fr, (FX.TX, 690), line, font("anton", 60), WH, a * clamp((t - S_CO[0] - 1.4) / 0.2), cache=False)
    else:
        number_line(fr, t, cb + 0.2, ce, 600, s["num"], s["cn"], s["unit"], count_to=PA26 if i == 2 else None)
        slam(fr, (FX.TX, 690), s["line"], font("anton", 60), s["cl"], t, cb + 0.8, ce, glow=0.3)
    if s.get("foot"): slam(fr, (FX.TX, 760), s["foot"], font("inter", GRAY_PX, 600), MU, t, cb + 1.3, ce, big=False)
    if s.get("foot2"): slam(fr, (FX.TX, 812), s["foot2"], font("inter", GRAY_PX, 600), MU, t, cb + 1.45, ce, big=False)
    if s.get("line2"): slam(fr, (FX.TX, 775), s["line2"], font("anton", 54), WH, t, cb + 2.0, ce, big=False)

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
def draw_ranking(fr, t, c):
    if not (T_RK <= t < T_RK_END + 0.4): return
    d = fr.d
    out = 1 - clamp((t - T_RK_END + 0.3) / 0.35)
    k2 = clamp((t - T_RK2) / 0.45)
    # province flash outlines as they land
    for r in ROWS:
        tr = rk_t_row(r["rank"]); e = decay(t, tr, 0.25) if t >= tr else 0
        top = r["rank"] <= 5
        w = max(e, (k2 if top else 0)) * out
        if w > 0.02:
            for ring in RK_POLYS[r["code"]]:
                pts = ring_px(ring, c); d.line(pts + pts[:1], fill=(HOT if e > 0.5 else AM) + (int(230 * w),), width=3 if top else 2)
                fr.glow_line(pts + pts[:1], mixc((0, 0, 0), AM, w), 8)
    hdr = "SUPERFICIE QUE ARDIÓ AL MENOS UNA VEZ · MODIS 2012–2025"
    slam(fr, (FX.TX, 128), hdr, font("mono", 36, 800), AM, t, T_RK, T_RK_END - 0.3, big=False)
    # phase 1: 24 rows (rank, name, bar), bottom-up
    a1 = 1 - k2
    if a1 > 0.003:
        fn = font("inter", 28, 600); fr_ = font("mono", 26, 700)
        for r in ROWS:
            rank = r["rank"]; tr = rk_t_row(rank)
            if t < tr: continue
            u = t - tr; a = clamp(u / 0.1) * a1 * out
            y = RK_Y0 + (rank - 1) * RK_PITCH
            feat = r["code"] in FEATURED
            put_text(fr, (FX.TX, y), f"{rank:>2}", fr_, MU, a)
            put_text(fr, (FX.TX + 52, y), r["name"], fn, AM if feat else WH, a)
            bw = RK_BW * r["ha_unique"] / VMAX * eout(u / 0.25)
            col = rk_col(r["ha_unique"]) if r["ha_unique"] > 0 else (60, 58, 60)
            if bw > 0.5: d.rectangle((RK_BX0, y - 20, RK_BX0 + bw, y - 2), fill=col + (int(255 * a),))
    # phase 2: top 5, big
    if k2 > 0.003:
        fN = font("anton", 64); fV = font("anton", 64); fR = font("anton", 64)
        for j, (name, val) in enumerate(TOP5_TXT):
            y = 300 + j * 100; t0 = T_RK2 + 0.05 + j * 0.09
            if t < t0: continue
            u = t - t0; a = clamp(u / 0.15) * out
            col = AM if ROWS[j]["code"] == "18" else WH
            slam(fr, (FX.TX, y), str(j + 1), fR, OR, t, t0, None, big=False)
            slam(fr, (FX.TX + 60, y), name, fN, col, t, t0, None, big=False)
            v = f"{val} M HA"; slam(fr, (1000 - tw(v, fV), y), v, fV, HOT, t, t0 + 0.05, None, big=False)
            bw = (1000 - FX.TX - 60) * ROWS[j]["ha_unique"] / VMAX * eout(u / 0.4)
            d.rectangle((FX.TX + 60, y + 16, FX.TX + 60 + bw, y + 24), fill=rk_col(ROWS[j]["ha_unique"]) + (int(255 * a),))
        if out < 0.999:
            for name, t0, t1, x, y, kind in []: pass
        slam(fr, (FX.TX, 850), f"5 PROVINCIAS = {TOP5_PCT} % DE TODO LO QUEMADO", font("anton", 64), OR, t, T_RK2 + 0.9, T_RK_END - 0.3, glow=0.4)
        # rank numbers on the map
        for j, r in enumerate(ROWS[:5]):
            lx, ly = proj(*LABEL_PT[r["code"]], c); s = str(j + 1); f = font("anton", 52)
            aa = k2 * out * clamp((t - T_RK2 - 0.1 - j * 0.09) / 0.2)
            for ox, oy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
                put_text(fr, (lx - tw(s, f) / 2 + ox, ly + 18 + oy), s, f, (12, 10, 10), aa)
            put_text(fr, (lx - tw(s, f) / 2, ly + 18), s, f, WH, aa)

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
            if g is None or g[2] < 6 or sa < 0.05: continue
            cx, cy, R = g[0], g[1], g[2]
            d = np.array((cx - sx, cy - sy), np.float32); dist = float(np.linalg.norm(d)); d /= max(dist, 1e-3); pp = np.array((-d[1], d[0]))
            b = p1 * 0.92
            hit = np.array((cx, cy)) + pp * b * R - d * math.sqrt(1 - b * b) * R
            start = np.array((sx, sy)) + pp * p1 * Rs * 0.5
            n3 = np.array(((hit[0] - cx) / R, -(hit[1] - cy) / R, 0.0))
            n3[2] = math.sqrt(max(0.0, 1 - n3[0] ** 2 - n3[1] ** 2)) * 0.35; n3 /= np.linalg.norm(n3)
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
    for k in range(18):
        t0 = T_SPARK + rg.uniform(0, 1.8); vx, vy = rg.uniform(-30, 30), rg.uniform(-110, -50)
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
        k_warm = 0.5 * decay(t, T_SCAR, 0.8)
        A = A * (1 - 0.6 * (np.clip(sv, 0, 1) ** 0.55)[..., None] * sk) + scar_rgb(sv, k_warm) * sk * dimk
        w = stop_w(t, 0)
        if w > 0.003:
            ev_ = warp_raster(SC_CO, c); edge = np.clip(ev_ - cv2.GaussianBlur(ev_, (0, 0), 2.5), 0, 1) * 3
            A = A * (1 - 0.35 * ev_[..., None] * w) + ev_[..., None] * np.array((150, 46, 18), np.float32) * w + np.clip(edge, 0, 1)[..., None] * np.array((255, 140, 50), np.float32) * w * 0.8
    A = ranking_fill(A, t, c)
    # ---- 3. Comarca Andina: Sentinel-2 in place, then MODIS 2025 / 2026 scars
    wpa = stop_w(t, 2)
    if wpa > 0.003:
        p0 = S_PA[0]
        y_from, y_to, k = (2024, 2025, clamp((t - p0 - 0.9) / 0.5)) if t < p0 + 2.3 else (2025, 2026, clamp((t - p0 - 2.4) / 0.5))
        im0, m = s2_layer(c, y_from); im1, _ = s2_layer(c, y_to)
        x0, y0, x1, y1 = s2_corners(c); wipe = x0 + (x1 - x0) * k
        sel = (np.arange(W)[None, :, None] < wipe).astype(np.float32)
        img = im1 * sel + im0 * (1 - sel)
        A = A * (1 - m * wpa) + img * 0.9 * m * wpa
        for pyr, y_on, col in ((SC_P25, p0 + 1.4, (255, 176, 60)), (SC_P26, p0 + 2.9, (255, 64, 40))):
            kk = clamp((t - y_on) / 0.4) * wpa
            if kk > 0:
                ev_ = warp_raster(pyr, c, cv2.INTER_NEAREST); edge = np.clip(ev_ - cv2.erode(ev_, np.ones((3, 3), np.uint8)), 0, 1)
                A = A * (1 - 0.25 * ev_[..., None] * kk) + ev_[..., None] * np.array(col, np.float32) * 0.28 * kk + edge[..., None] * np.array(col, np.float32) * kk
    # ---- 4. event hotspots replayed inside each stop
    for i in range(3):
        s0, s1 = STOPS[i]
        if not (s0 - 0.3 <= t < s1 + 0.5): continue
        idx = EVENTS[i]; tt = EVT[i]; on = tt <= t
        if not on.any(): continue
        wv = np.where(on, 0.25 + 1.6 * np.exp(-(t - tt) / 0.35), 0).astype(np.float32) * (1 - clamp((t - s1 + 0.2) / 0.5))
        if i == 0: wv *= 1 - 0.75 * clamp((t - S_CO[0] - 1.3) / 0.6)
        if i == 2: fire = cv2.GaussianBlur(splat(LON[idx], LAT[idx], wv, c), (0, 0), 2.2) * 9
        else: fire = zoom_blur(splat(LON[idx], LAT[idx], wv, c), c) * (0.5 if i == 1 else 1.0)
        v = 1 - np.exp(-fire * 0.8)
        F = LUT[np.clip(v * 255, 0, 255).astype(np.uint8)]
        hs = cv2.resize(F, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        bloom = cv2.resize(cv2.GaussianBlur(hs, (0, 0), 6) * 0.8, (W, H))
        A = 255 - (255 - A) * (255 - np.clip(F + bloom, 0, 255)) / 255
    A = spotlight(A, t, c)
    shade = clamp((t - T_X0 - 0.2) / 0.5)
    if t < T_MAP:
        kx = einout((t - T_X0) / (T_MAP - T_X0)); A = space_frame(t) * (1 - kx) + A * kx
    fr = Frame(left_shade(Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)), 0.92 * shade))
    if wpa > 0.003:
        x0, y0, x1, y1 = s2_corners(c); a = wpa * clamp((t - S_PA[0] - 0.4) / 0.3)
        fr.d.rectangle((x0, y0, x1, y1), outline=(242, 240, 236, int(200 * a)), width=2)
        lab = "DIC 2024" if t < S_PA[0] + 1.15 else "ABR 2025" if t < S_PA[0] + 2.65 else "ABR 2026"
        put_text(fr, (x1 + 16, y0 + 40), lab, font("mono", 40, 800), WH, a, cache=True)
        put_text(fr, (x1 + 16, y0 + 90), "Sentinel-2", font("inter", 36, 600), MU, a)
        if t > S_PA[0] + 1.4: put_text(fr, (x1 + 16, y1 - 70), "■ 2025", font("mono", 36, 800), AM, a * clamp((t - S_PA[0] - 1.4) / 0.3))
        if t > S_PA[0] + 2.9: put_text(fr, (x1 + 16, y1 - 20), "■ 2026", font("mono", 36, 800), RD, a * clamp((t - S_PA[0] - 2.9) / 0.3))
    for i in range(3): draw_stop(fr, t, i, c)
    draw_caba(fr, t, c, stop_w(t, 0))
    cw = close_w(t)
    if cw > 0.003:
        for r in NORTE_OUT + CORD_OUT:
            pts = ring_px(r, c); fr.d.line(pts + pts[:1], fill=AM + (int(230 * cw),), width=3); fr.glow_line(pts + pts[:1], mixc((0, 0, 0), AM, cw), 10)
    draw_cards(fr, t, c)
    draw_ranking(fr, t, c)
    ui = clamp((t - T_LAND) / 0.4) * (1 - clamp((t - T_ASH + 0.2) / 0.5))
    draw_year(fr, t, ui); draw_timeline(fr, t, ui)
    # ---- legend (bottom-right): what a point and what the grey are (hidden under the ranking)
    fl = font("inter", 36, 600)
    la = clamp((t - T_LAND - 0.3) / 0.4) * (1 - clamp((t - T_CL + 0.3) / 0.4)) * (1 - clamp((t - T_RK) / 0.3) * (1 - clamp((t - T_RK_END) / 0.4)))
    la *= legend_gap(t)                     # v7: hidden while the Sentinel-2 frame flies in under it
    if la > 0.003:
        l1 = "1 punto = 1 foco de calor satelital (VIIRS 375 m)"
        put_text(fr, (W - 90 - tw(l1, fl), H - 70), l1, fl, MU, la)
        if sk > 0:
            l2 = "■ gris: área quemada (MODIS 500 m)"; put_text(fr, (W - 90 - tw(l2, fl), H - 118), l2, fl, ASH, la * sk)
    # ---- text cards
    draw_hook(fr, t)
    if T_TXT1 <= t < T_LAND:
        e = T_LAND - 0.3
        slam(fr, (FX.TX, 420), "EL SOL CALIENTA.", font("anton", 96), WH, t, T_TXT1, e, big=False)
        slam_tight(fr, (FX.TX, 575), "LA CHISPA ES HUMANA.", font("anton", 106), OR, t, T_SPARK + 0.1, e, glow=0.55)
        slam(fr, (FX.TX, 665), f"EN {HUM_10} DE CADA 10 INCENDIOS CON CAUSA CONOCIDA", font("anton", 46), WH, t, T_SPARK + 0.6, e, big=False)
        slam(fr, (FX.TX, 725), "Ministerio de Ambiente, 1993–2019", font("inter", 36, 600), MU, t, T_SPARK + 0.8, e, big=False)
    if T_LAND <= t < T_A1:
        e = T_A1 - 0.5
        slam(fr, (FX.TX, 490), "¿DÓNDE ARDE", font("anton", 140), WH, t, T_LAND, e)
        slam(fr, (FX.TX, 640), "ARGENTINA?", font("anton", 140), OR, t, T_LAND + 0.15, e, glow=0.6)
    if T_A1 <= t < T_ASH + 0.2:
        number_line(fr, t, T_A1, T_ASH - 0.2, 600, es_int(S["total_focos"]), HOT, "FOCOS", count_to=S["total_focos"], glow=0.6)
        slam(fr, (FX.TX, 690), "EN 14 AÑOS · 2012–2025", font("anton", 70), WH, t, T_A1 + 0.35, T_ASH - 0.2, big=False)
    if T_ASH + 0.3 <= t < T_D1:
        e = T_D1 - 0.3; t0 = T_ASH + 0.3
        slam(fr, (FX.TX, 430), "ARDIÓ AL MENOS UNA VEZ · MODIS 2012–2025", font("mono", 40, 800), AM, t, t0, e, big=False)
        number_line(fr, t, T_SCAR, e, 600, f"{UNIQ_TXT} MILLONES", WH, "DE HA", glow=0.4)          # v7: slams on the scar boom
        slam(fr, (FX.TX, 690), "= CASI 1 DE CADA 10 HECTÁREAS DEL PAÍS", font("anton", 60), OR, t, T_SCAR + 0.6, e, glow=0.3)
    if T_CL <= t < T_SRC:
        e = T_SRC - 0.3
        slam(fr, (FX.TX, 300), "SABEMOS DÓNDE Y CUÁNDO ARDE.", font("anton", 76), WH, t, CL_L1, e, big=False)
        slam(fr, (FX.TX, 362), "Norte: ago–sep · Cordillera: dic–mar", font("inter", GRAY_PX, 600), MU, t, CL_NOTE, e, big=False)
        slam_tight(fr, (FX.TX, 530), "YA NO FALTAN DATOS.", font("anton", 120), WH, t, CL_L2, e, glow=0.35)
        slam_tight(fr, (FX.TX, 670), "FALTA RESPONSABILIDAD.", font("anton", 120), OR, t, CL_L2 + 0.25, e, glow=0.6)
        slam(fr, (FX.TX, 800), "NO QUEMES. SI VES FUEGO, LLAMÁ AL 911.", font("anton", 64), AM, t, CL_L3, e, glow=0.4)
    if t >= T_SRC: sources(fr, t)
    flash = min(1.0, sum(0.3 * decay(t, x, 0.11) for x in REVEALS))
    return finish(fr, t, flash=flash)

def slam_tight(fr, xy, s, f, col, t, t0, t1, glow=0.0, over=0.08):
    if t < t0: return
    u = t - t0; sc = 1 + over * (1 - eout5(u / 0.28)); a = clamp(u / 0.09); flare = 1 + 1.6 * decay(t, t0, 0.18)
    o = clamp((t - t1) / 0.3); a *= 1 - o; sc *= 1 + 0.03 * o
    if a > 0: put_text(fr, xy, s, f, col, a, sc, glow * flare)
SRC = ["FUENTES",
       "Focos: NASA FIRMS, VIIRS S-NPP 375 m, 2012–2025. Un foco no es un incendio.",
       "Área quemada: NASA MODIS MCD64A1 C6.1 (500 m, UMD), 2012–2026.",
       "Ranking y total: superficie que ardió al menos una vez, 2012–2025.",
       "Causas 1993–2019: Ministerio de Ambiente. Caña: EEAOC. Límites: INDEC, IGN.",
       "Comarca 2025: Gob. de Río Negro (casas), Infobae (víctima).",
       "Fotos: NASA Earth Observatory (dominio público), Gob. de Santa Fe",
       "y CatrielGB (CC BY-SA, Wikimedia Commons). Banderas: Wikimedia Commons.",
       "Satélite: Copernicus Sentinel-2 (2024–2026). Sol, Tierra y mapa: con código.",
       f"Capital: límite IGN, {es_int(round(BS['caba_ha']))} ha. País: {es_dec(RK['country_area_ha'] / 1e6, 1)} M ha (INDEC); cada píxel cuenta una vez.",
       "Avisar es obligatorio (Ley 26.815). Animación y música: con código."]
def sources(fr, t):
    a = clamp((t - T_SRC) / 0.4)
    d = fr.d; d.rectangle((0, 0, W, H), fill=(6, 6, 9, int(215 * a)))
    put_text(fr, (FX.TX, 180), SRC[0], font("anton", 72), OR, a)
    fb = font("inter", GRAY_PX, 500)
    for i, s in enumerate(SRC[1:]):
        put_text(fr, (FX.TX, 270 + i * 64), s, fb, WH, a * clamp((t - T_SRC - 0.06 * i) / 0.35))

NUM = dict(total=S["total_focos"], burn_M=BURN_M, pitches_per_min=PITCH_PER_MIN, corr_ha=CO_HA, n_caba=S["n_caba_corr"], co_rank=CO_RANK,
           comarca_2025=S["comarca_2025_ha"], comarca_2026=S["comarca_2026_ha"], houses=HOUSES, deaths=DEATHS, tuc_pct=TU_PCT,
           hum_10=HUM_10, hum_share_known=CA["humana_sobre_conocida"], top5_pct=TOP5_PCT, top5=[(r["name"], round(r["ha_unique"])) for r in ROWS[:5]], uniq=UNIQ, share_ar=SHARE_AR, tu_zone_pct=TU_ZONE_PCT)
TIMES = dict(T_X0=T_X0, T_MAP=T_MAP, T_TXT1=T_TXT1, T_COOL=T_COOL, T_SPARK=T_SPARK, T_LAND=T_LAND, T_A1=T_A1, T_ASH=T_ASH, T_SCAR=T_SCAR,
             T_D1=T_D1, T_RK=T_RK, T_RK2=T_RK2, T_RK_END=T_RK_END, S_CO=S_CO, S_TU=S_TU, S_PA=S_PA,
             T_CL=T_CL, CL_L2=CL_L2, CL_L3=CL_L3, T_SRC=T_SRC, TOTAL=TOTAL)
if __name__ == "__main__":
    if "--nums" in sys.argv:
        print(json.dumps(NUM, indent=1, ensure_ascii=False)); print("times", json.dumps({k: (round(v, 2) if isinstance(v, float) else [round(x, 2) for x in v]) for k, v in TIMES.items()}))
    if "--still" in sys.argv:
        os.makedirs(os.path.join(HERE, "qa"), exist_ok=True)
        import time
        for x in sys.argv[sys.argv.index("--still") + 1:]:
            t0 = time.time(); render_at(float(x)).save(os.path.join(HERE, "qa", f"still_{float(x):05.2f}.png")); print("still", x, round(time.time() - t0, 2), "s", flush=True)
