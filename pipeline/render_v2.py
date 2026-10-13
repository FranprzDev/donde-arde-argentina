"""Contar con Datos 2026 · Historia visual · v2 «¿Dónde arde Argentina?»
ONE continuous map of Argentina. Every VIIRS S-NPP 375 m hotspot (NASA FIRMS country archive 2012-2025, type 0, nominal+high
confidence) flares at its real place and date and leaves an ember. 14 years play month by month; the camera stops on five
places at the moment they burned (Delta/Entre Ríos 2020, Córdoba 2020, Corrientes 2022, Chubut 2025) and, once all 14 years are lit,
on Formosa. A bottom timeline (monthly hotspots, area curve drawn by a playhead) + a big year counter carry time.
Every number on screen comes from data/stats_v2.json (prep_v2.py + causas.py); none typed by hand: python3 render_v2.py --nums
Everything drawn with code (numpy/PIL/OpenCV). No photos, no AI imagery.
Usage: python3 render_v2.py --still t1 t2 ...   | frames are rendered by chunk_v2.py"""
import json, math, os, sys
import numpy as np, cv2, shapely
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fx_v2 import *
import fx_v2 as FX
D1 = os.path.join(HERE, "..", "data"); D2 = os.path.join(HERE, "data")
TOTAL = 59.9
WH = (242, 240, 236); MU = (176, 168, 160); AM = (255, 176, 60); OR = (255, 110, 30); RD = (255, 64, 40); HOT = (255, 226, 160)

# ---------------- numbers ----------------
V = json.load(open(os.path.join(D2, "stats_v2.json")))
def es_int(n): return f"{int(n):,}".replace(",", ".")
def es_dec(x, d=1): return f"{x:.{d}f}".replace(".", ",")
def pct(x): return f"{round(100 * x)} %"
MONTHLY = np.array(V["monthly"], np.float64)
R_LBL = es_dec(round(V["ratio_2020"], 1)); AS_10 = int(round(V["share_aug_sep"] * 10)); NORTE_10 = int(round(V["share_norte"] * 10))
CA = V["causas"]; HUM_10 = int(round(CA["humana_sobre_conocida"] * 10))
ER, CB, CO, CH, FO = V["er"], V["cba"], V["corr"], V["chubut"], V["formosa"]
CB_HA_FLOOR = 150000
CH_10 = int(round(CH["share_cordillera"] * 10))
assert ER["ratio"] > 10 and CB["ha_2020_ciam416"] >= CB_HA_FLOOR and CO["janfeb_2022"] > CO["max_year_2012_2019"] and FO["rank"] == 1
assert abs(V["share_aug_sep"] * 10 - AS_10) < 0.25 and abs(V["share_norte"] * 10 - NORTE_10) < 0.25 and abs(CA["humana_sobre_conocida"] * 10 - HUM_10) < 0.25
assert abs(CH["share_cordillera"] * 10 - CH_10) < 0.25

# ---------------- points + time warp (month index since 2012-01 -> video seconds) ----------------
P = np.load(os.path.join(D1, "points.npz"))
TL0 = 3.4
SEG = [(0, 84, 0.105), (84, 96, 0.17), (96, 102, 0.30), (102, 104, 2.0), (104, 106, 2.0), (106, 108, 0.30), (108, 120, 0.38),
       (120, 122, 1.9), (122, 156, 0.10), (156, 158, 1.9), (158, 168, 0.10)]
KN_M = [0]; KN_S = [TL0]
for a, b, s in SEG: KN_M.append(b); KN_S.append(KN_S[-1] + (b - a) * s)
TL1 = KN_S[-1]
def s_of_m(m): return np.interp(m, KN_M, KN_S)
def m_of_s(t): return float(np.interp(t, KN_S, KN_M))
_ps = s_of_m(P["t"]); o = np.argsort(_ps, kind="stable")
PS = _ps[o].astype(np.float32); LON = P["lon"][o].astype(np.float32); LAT = P["lat"][o].astype(np.float32)
TSORT = np.sort(P["t"]).astype(np.float64)

# ---------------- timeline of beats ----------------
T_A = 0.4                         # «14 AÑOS DE FUEGO, / VISTOS DESDE EL ESPACIO»
T_TITLE = 3.2                     # «¿DÓNDE ARDE ARGENTINA?» (hit 1)
T_AS = 7.0                        # «4 DE CADA 10 FOCOS: AGOSTO Y SEPTIEMBRE»
T_AS1 = 10.6
S1 = (float(s_of_m(102)), float(s_of_m(104)))       # Delta / Entre Ríos, Jul-Aug 2020 (DROP 2)
S2 = (float(s_of_m(104)), float(s_of_m(106)))       # Córdoba, Sep-Oct 2020
T_F = float(s_of_m(108))          # end of 2020 -> «400.953 FOCOS EN 2020»
T_G = T_F + 2.4                   # «2,5 VECES UN AÑO TÍPICO»
S3 = (float(s_of_m(120)), float(s_of_m(122)))       # Corrientes, Jan-Feb 2022
S4 = (float(s_of_m(156)), float(s_of_m(158)))       # Chubut, Jan-Feb 2025
T_ACC = TL1 + 0.3                 # every hotspot of 14 years at once (DROP 3)
S5 = (T_ACC + 3.0, T_ACC + 6.9)   # Formosa
T_CAUSE = S5[1] + 0.3             # «9 DE CADA 10 ... CAUSA HUMANA»
T_CL = T_CAUSE + 4.8              # «EL FUEGO VUELVE CADA AÑO.»
T_SRC = T_CL + 2.5                # sources card
STOPS = [S1, S2, S3, S4, S5]
REVEALS = [T_TITLE, S1[0], T_F, T_ACC, T_CAUSE]
SHAKES = [(T_TITLE, 6), (S1[0] + 0.15, 7), (T_F, 6), (T_ACC, 10)]
AUG = {y: float(s_of_m((y - 2012) * 12 + 7)) for y in range(2012, 2026)}

# ---------------- geography (INDEC Censo 2022 provinces; Natural Earth neighbours) ----------------
NG = json.load(open("../data/natgeo_v7.json"))
GEO = json.load(open("../data/geo_v2.json"))
def _bb(r, b=(-80, -58, -48, -18)):
    a = np.asarray(r); return a[:, 0].max() > b[0] and a[:, 0].min() < b[2] and a[:, 1].max() > b[1] and a[:, 1].min() < b[3]
NEIGH = [np.asarray(r, np.float32) for r in GEO["countries"] if _bb(r)]
PROVR = {k: [np.asarray(r, np.float32) for r in v] for k, v in NG["prov"].items()}
def outline(code):
    u = shapely.union_all([shapely.Polygon(r) for r in NG["prov"][code]]).buffer(0.01).buffer(-0.01).simplify(0.005)
    return [np.asarray(g.exterior.coords, np.float32) for g in (u.geoms if hasattr(u, "geoms") else [u]) if g.area > 0.01]
COS = math.cos(math.radians(38.0))

# ---------------- camera: (lon, lat, px per degree latitude, screen x, screen y) ----------------
CAM_IN = (-64.2, -38.6, 26.5, 1290, 560)
CAM0 = (-64.2, -38.6, 30.0, 1290, 548)
CAM_ACC = (-64.0, -38.4, 31.5, 1290, 548)
CAM_END = (-64.2, -38.6, 30.5, 1290, 548)
STOPCAM = [(-59.55, -32.25, 118, 1350, 520), (-64.1, -32.2, 82, 1350, 520), (-57.9, -28.85, 96, 1350, 520),
           (-68.3, -43.9, 92, 1380, 520), (-60.3, -24.6, 88, 1420, 500)]
STOPCODE = ["30", "14", "18", "26", "34"]
STOPOUT = {c: outline(c) for c in STOPCODE}
STOPDIM = [0.3, 0.45, 0.45, 0.45, 0.62]
def stop_w(t, i):
    t0, t1 = STOPS[i]; return clamp((t - t0 + 0.3) / 0.5) * (1 - clamp((t - t1 + 0.2) / 0.5))
def spotlight(A, t, c):
    """during a stop, everything outside the province is dimmed so the highlighted province reads first"""
    for i in range(5):
        w = stop_w(t, i)
        if w <= 0.003: continue
        m = Image.new('L', (W // 2, H // 2), 0); dm = ImageDraw.Draw(m)
        for r in STOPOUT[STOPCODE[i]]: dm.polygon([(x / 2, y / 2) for x, y in ring_px(r, c)], fill=255)
        m = cv2.resize(cv2.GaussianBlur(np.asarray(m, np.float32) / 255, (0, 0), 4), (W, H))[..., None]
        A = A * (1 - STOPDIM[i] * w * (1 - m) * np.array((0.8, 1.0, 1.12), np.float32))       # warm dim: dimmed whites go amber, not grey
    return A
FLY = 1.05
KEYS = [(0.0, CAM_IN), (T_TITLE, CAM0),
        (S1[0] - FLY, CAM0), (S1[0] + 0.1, STOPCAM[0]), (S1[1] - 0.75, STOPCAM[0]), (S2[0] + 0.15, STOPCAM[1]),
        (S2[1] - 0.2, STOPCAM[1]), (S2[1] + 0.9, CAM0),
        (S3[0] - FLY, CAM0), (S3[0] + 0.1, STOPCAM[2]), (S3[1] - 0.1, STOPCAM[2]), (S3[1] + 0.9, CAM0),
        (S4[0] - FLY, CAM0), (S4[0] + 0.1, STOPCAM[3]), (S4[1] - 0.1, STOPCAM[3]), (S4[1] + 0.95, CAM0),
        (T_ACC, CAM_ACC), (S5[0] - 0.9, CAM_ACC), (S5[0] + 0.15, STOPCAM[4]), (S5[1] - 0.15, STOPCAM[4]), (S5[1] + 1.1, CAM_END), (TOTAL, CAM_END)]
def cam_mix(a, b, k):
    # zoom interpolated in log space so flights feel even
    z = math.exp(lerp(math.log(a[2]), math.log(b[2]), k))
    return (lerp(a[0], b[0], k), lerp(a[1], b[1], k), z, lerp(a[3], b[3], k), lerp(a[4], b[4], k))
def cam_at(t):
    c = KEYS[-1][1]
    for (t0, c0), (t1, c1) in zip(KEYS, KEYS[1:]):
        if t0 <= t < t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            c = cam_mix(c0, c1, eout(k) if t0 == 0.0 else einout(k)); break
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
FIRE_TAU = 0.42; FIRE_WIN = 2.6
def fire_layers(t, c):
    n_prior = int(np.searchsorted(PS, t, side="right"))
    i0 = int(np.searchsorted(PS, t - FIRE_WIN))
    ember = splat(LON[:n_prior], LAT[:n_prior], None, c) if n_prior else np.zeros((H, W), np.float32)
    w = np.exp(-(t - PS[i0:n_prior]) / FIRE_TAU).astype(np.float32)
    fire = splat(LON[i0:n_prior], LAT[i0:n_prior], w, c) if n_prior > i0 else np.zeros((H, W), np.float32)
    k = c[2] / 30.0                                       # zoom factor: spread each detection so density reads the same
    if k > 1.15:
        s = 0.55 * k
        ember = cv2.GaussianBlur(ember, (0, 0), s) * (k * k) * 0.55
        fire = cv2.GaussianBlur(fire, (0, 0), s) * (k * k) * 0.55
    return ember, fire

def base_map(c, a_land=1.0):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im, "RGBA")
    for r in NEIGH: d.polygon(ring_px(r, c), fill=(13, 13, 17, int(255 * a_land)), outline=(34, 34, 40, int(255 * a_land)))
    for k, rs in PROVR.items():
        for r in rs: d.polygon(ring_px(r, c), fill=(20, 19, 22, int(255 * a_land)))
    for k, rs in PROVR.items():
        for r in rs: d.line(ring_px(r, c) + ring_px(r[:1], c), fill=(56, 54, 58, int(210 * a_land)), width=1)
    return im

# ---------------- timeline (bottom-left): monthly hotspots, drawn by a playhead ----------------
TLX0, TLX1, TLYB, TLH = 110, 1010, 1030, 190
MMAX = MONTHLY.max()
def tl_x(m): return TLX0 + (TLX1 - TLX0) * m / 168.0
def tl_y(v): return TLYB - TLH * v / MMAX
MES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
PEAKS = [(103, "AGO 2020", RD), (120, "ENE 2022", AM)]
def draw_timeline(fr, t, a):
    if a <= 0.003: return
    d = fr.d; mn = min(168.0, max(0.0, m_of_s(t)))
    # baseline + year ticks (whole span, faint)
    d.line([(TLX0, TLYB), (TLX1, TLYB)], fill=(120, 116, 110, int(150 * a)), width=2)
    fl = font("mono", 30, 700)
    for y in range(2012, 2027):
        x = tl_x((y - 2012) * 12); d.line([(x, TLYB), (x, TLYB + (12 if y % 4 == 0 else 6))], fill=(150, 146, 140, int(170 * a)), width=2)
        if y in (2012, 2016, 2020, 2024):
            s = str(y); put_text(fr, (x + 4, TLYB + 34), s, fl, RD if y == 2020 else MU, a)
    # area curve up to the playhead (month centres; the current month grows in as its detections arrive)
    n = int(mn)
    xs = [tl_x(0)]; ys = [TLYB]
    for i in range(n): xs.append(tl_x(i + 0.5)); ys.append(tl_y(MONTHLY[i]))
    if mn < 168:
        cur = np.searchsorted(TSORT, mn) - np.searchsorted(TSORT, n)            # detections of the current month seen so far
        frac = max(1e-3, mn - n)
        v_now = lerp(MONTHLY[n - 1] if n else 0, MONTHLY[n], clamp(cur / max(1, MONTHLY[n]) * 1.0))
        xs.append(tl_x(mn)); ys.append(tl_y(v_now))
    else:
        xs.append(tl_x(168)); ys.append(tl_y(MONTHLY[167]))
    pts = list(zip(xs, ys))
    if len(pts) > 1:
        d.polygon(pts + [(xs[-1], TLYB)], fill=(255, 120, 30, int(95 * a)))
        d.line(pts, fill=AM + (int(255 * a),), width=4); fr.glow_line(pts, mixc((0, 0, 0), OR, a), 8)
        # 2020 in red
        r20 = [(x, y) for x, y in pts if tl_x(96) <= x <= tl_x(108.5)]
        if len(r20) > 1: d.line(r20, fill=RD + (int(255 * a),), width=4); fr.glow_line(r20, mixc((0, 0, 0), RD, a), 9)
    # peak labels
    fp = font("inter", 34, 800)
    for m, s, col in PEAKS:
        if mn > m + 0.6:
            k = clamp((mn - m - 0.6) / 0.8) * a
            x, y = tl_x(m + 0.5), tl_y(MONTHLY[m])
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=col + (int(255 * k),))
            put_text(fr, (x + 12, y + 8), s, fp, col, k)
    # playhead
    if mn < 168:
        x = tl_x(mn); y = ys[-1]
        d.line([(x, TLYB + 4), (x, TLYB - TLH - 18)], fill=(255, 240, 220, int(120 * a)), width=2)
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=HOT + (int(255 * a),)); fr.gd.ellipse(((x - 16) / 2, (y - 16) / 2, (x + 16) / 2, (y + 16) / 2), fill=mixc((0, 0, 0), OR, a))
    put_text(fr, (TLX1 - tw("FOCOS POR MES", font("mono", 28, 700)), TLYB - TLH - 26), "FOCOS POR MES", font("mono", 28, 700), MU, a * 0.95)

def draw_year(fr, t, a):
    if a <= 0.003: return
    mn = min(167.99, max(0.0, m_of_s(t))); yy = 2012 + int(mn // 12); mm = int(mn % 12)
    fy = font("anton", 180)
    if t < TL1:
        put_text(fr, (FX.TX - 6, 236), str(yy), fy, RD if yy == 2020 else WH, a, cache=False)
        put_text(fr, (FX.TX, 300), MES[mm], font("inter", 44, 800), HOT, a)
    else:
        put_text(fr, (FX.TX - 6, 236), "2012–2025", fy, WH, a)

# ---------------- stop cards ----------------
STOPTXT = [
    dict(head="DELTA DEL PARANÁ · ENTRE RÍOS", num=ER["y2020"], l1="FOCOS EN 2020", l2="MÁS DE 10 VECES LO NORMAL", c2=OR,
         ctx="con el río Paraná en bajante histórica (INA)"),
    dict(head="SIERRAS DE CÓRDOBA · 2020", num=CB_HA_FLOOR, plus=True, l1="HECTÁREAS QUEMADAS", l2=f"RÉCORD DE FOCOS: {es_int(CB['y2020'])}", c2=AM,
         ctx=f"Córdoba: {pct(CA['prov']['Córdoba']['humana_sobre_conocida'])} causa humana, si se conoce"),
    dict(head="CORRIENTES · ENE–FEB 2022", num=CO["janfeb_2022"], l1="FOCOS EN SÓLO DOS MESES", l2="MÁS QUE CUALQUIER AÑO 2012–2019", c2=AM,
         ctx="en plena sequía (SMN)"),
    dict(head="PATAGONIA ANDINA · CHUBUT 2025", num=CH["ha_2025_ciam416"], l1="HECTÁREAS QUEMADAS", l2=f"CON SÓLO {es_int(CH['y2025'])} FOCOS", c2=OR,
         ctx=f"{CH_10} de cada 10 focos, en la cordillera"),
    dict(head="FORMOSA · 2012–2025", num=FO["total"], l1="FOCOS: LA 1.ª DEL PAÍS", l2=f"EL NORTE: {NORTE_10} DE CADA 10", c2=AM,
         ctx="fuego para pasturas y cultivos (Ecología Austral)"),
]
def draw_stop(fr, t, i, c):
    t0, t1 = STOPS[i]; s = STOPTXT[i]
    if not (t0 - 0.2 <= t < t1 + 0.4): return
    a = clamp((t - t0 + 0.1) / 0.35) * (1 - clamp((t - t1 + 0.1) / 0.35))
    # province outline: glow + bright edge + faint fill
    if a > 0:
        d = fr.d
        for r in STOPOUT[STOPCODE[i]]:
            pts = ring_px(r, c)
            d.polygon(pts, fill=(255, 150, 40, int(22 * a)))
            col = HOT if i == 4 else AM
            d.line(pts + pts[:1], fill=col + (int(240 * a),), width=4 if i == 4 else 3); fr.glow_line(pts + pts[:1], mixc((0, 0, 0), AM, a), 10)
    cb = t0 + 0.12; ce = t1 - 0.25
    slam(fr, (FX.TX, 392), s["head"], font("mono", 36, 800), AM, t, cb, ce, big=False)
    num = count(t, cb + 0.1, s["num"], 1.1)
    txt = ("+" if s.get("plus") else "") + es_int(num)
    slam(fr, (FX.TX, 548), txt, font("anton", 150), HOT if i != 0 else RD, t, cb + 0.1, ce, glow=0.55, cache=False)
    slam(fr, (FX.TX, 626), s["l1"], font("anton", 64), WH, t, cb + 0.35, ce, big=False)
    slam(fr, (FX.TX, 704), s["l2"], font("anton", 64), s["c2"], t, cb + 0.75, ce, glow=0.3)
    slam(fr, (FX.TX, 762), s["ctx"], font("inter", 36, 600), MU, t, cb + 1.1, ce, big=False)

def render_at(t):
    c = cam_at(t)
    base = base_map(c, clamp(t / 1.4))
    A = np.asarray(base, np.float32)
    ember, fire = fire_layers(t, c)
    acc = 0.0
    if t >= T_ACC - 0.4:
        acc = clamp((t - T_ACC + 0.4) / 0.4) * (0.85 + 0.3 * decay(t, T_ACC, 0.6))
        if t >= T_CAUSE: acc *= 1 - 0.40 * clamp((t - T_CAUSE) / 0.8)
        if t >= T_SRC: acc *= 1 - 0.6 * clamp((t - T_SRC) / 0.6)
    em = np.clip(np.log1p(ember) / math.log1p(60), 0, 1)
    E = em[..., None] * np.array((120, 30, 10), np.float32) * 0.85 * (1 - clamp(acc))
    v = 1 - np.exp(-fire * 0.9)
    if acc > 0: v = np.maximum(v, np.clip(np.log1p(ember) / math.log1p(500 * max(1.0, c[2] / 30.0) ** 1.6), 0, 1) ** 1.1 * acc * 0.92)
    v = cv2.GaussianBlur(v, (0, 0), 0.7) * 1.25
    F = LUT[np.clip(v * 255, 0, 255).astype(np.uint8)]
    hs = cv2.resize(F, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    bloom = cv2.GaussianBlur(hs, (0, 0), 5) * 0.9 + cv2.GaussianBlur(hs, (0, 0), 18) * 0.9
    bloom = cv2.resize(bloom, (W, H), interpolation=cv2.INTER_LINEAR) * (1.0 + 0.6 * max(decay(t, S1[0], 0.7), decay(t, T_ACC, 0.9)))
    A = A + E
    A = 255 - (255 - A) * (255 - np.clip(F + bloom, 0, 255)) / 255
    A = spotlight(A, t, c)
    fr = Frame(left_shade(Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)), 0.92))
    for i in range(5): draw_stop(fr, t, i, c)
    # ---- time UI: big year + bottom timeline ----
    ui = clamp((t - TL0 + 0.2) / 0.5) * (1 - clamp((t - T_CAUSE + 0.3) / 0.5))
    in_stop = max((clamp((t - a0 + 0.2) / 0.4) * (1 - clamp((t - a1) / 0.4)) for a0, a1 in STOPS), default=0)
    draw_year(fr, t, ui * (1 - 0.35 * in_stop) * (1 - clamp((t - S5[0] + 0.3) / 0.4)) if t < S5[0] + 0.2 else 0)
    draw_timeline(fr, t, ui * (1 - 0.3 * in_stop))
    # ---- cards ----
    f1, fs = font("anton", 96), font("inter", 34, 600)
    if t < T_TITLE + 0.3:
        slam(fr, (FX.TX, 500), "14 AÑOS DE FUEGO,", font("anton", 88), WH, t, T_A, T_TITLE - 0.25, big=False)
        slam(fr, (FX.TX, 604), "VISTOS DESDE EL ESPACIO", font("anton", 88), WH, t, T_A + 0.25, T_TITLE - 0.25, big=False)
    if T_TITLE <= t < T_AS:
        slam(fr, (FX.TX, 540), "¿DÓNDE ARDE", font("anton", 140), WH, t, T_TITLE, T_AS - 0.3)
        slam(fr, (FX.TX, 690), "ARGENTINA?", font("anton", 140), OR, t, T_TITLE + 0.15, T_AS - 0.3, glow=0.6)
        slam(fr, (FX.TX, 770), "Cada punto: un foco de calor visto por satélite", fs, MU, t, T_TITLE + 0.9, T_AS - 0.3, big=False)
    if T_AS <= t < T_AS1 + 0.3:
        slam(fr, (FX.TX, 590), f"{AS_10} DE CADA 10", font("anton", 150), AM, t, T_AS, T_AS1, glow=0.5)
        slam(fr, (FX.TX, 690), "FOCOS: AGOSTO Y SEPTIEMBRE", font("anton", 80), WH, t, T_AS + 0.25, T_AS1, big=False)
    if T_F <= t < T_G:
        slam(fr, (FX.TX, 590), es_int(count(t, T_F, V["y2020"], 1.0)), font("anton", 150), RD, t, T_F, T_G - 0.3, glow=0.6, cache=False)
        slam(fr, (FX.TX, 690), "FOCOS EN 2020", f1, WH, t, T_F + 0.25, T_G - 0.3, big=False)
    if T_G <= t < S3[0] - 0.2:
        slam(fr, (FX.TX, 590), f"{R_LBL} VECES", font("anton", 150), RD, t, T_G, S3[0] - 0.55, glow=0.6)
        slam(fr, (FX.TX, 690), "UN AÑO TÍPICO", f1, WH, t, T_G + 0.2, S3[0] - 0.55, big=False)
        slam(fr, (FX.TX, 760), "vs. la mediana de los otros 13 años", fs, MU, t, T_G + 0.6, S3[0] - 0.55, big=False)
    if T_ACC <= t < S5[0]:
        slam(fr, (FX.TX, 590), es_int(count(t, T_ACC, V["total"], 1.5)), font("anton", 150), HOT, t, T_ACC, S5[0] - 0.3, glow=0.6, cache=False)
        slam(fr, (FX.TX, 690), "FOCOS EN 14 AÑOS", f1, WH, t, T_ACC + 0.3, S5[0] - 0.3, big=False)
    if T_CAUSE <= t < T_CL:
        slam(fr, (FX.TX, 470), "¿QUIÉN LOS PRENDE?", font("mono", 36, 800), AM, t, T_CAUSE, T_CL - 0.3, big=False)
        slam(fr, (FX.TX, 640), f"{HUM_10} DE CADA 10", font("anton", 190), OR, t, T_CAUSE + 0.1, T_CL - 0.3, glow=0.7)
        slam(fr, (FX.TX, 728), "INCENDIOS CON CAUSA CONOCIDA:", font("anton", 72), WH, t, T_CAUSE + 0.45, T_CL - 0.3, big=False)
        slam(fr, (FX.TX, 812), "CAUSA HUMANA", font("anton", 72), OR, t, T_CAUSE + 0.75, T_CL - 0.3, glow=0.4)
        slam(fr, (FX.TX, 878), f"Negligencia {pct(CA['negl_sobre_conocida'])} · intencional {pct(CA['int_sobre_conocida'])} · natural {pct(CA['natural_sobre_conocida'])}",
             fs, MU, t, T_CAUSE + 1.2, T_CL - 0.3, big=False)
        slam(fr, (FX.TX, 928), f"En el {pct(CA['desconocida_sobre_total'])} no se determinó la causa · 1993–2019", fs, MU, t, T_CAUSE + 1.5, T_CL - 0.3, big=False)
    if T_CL <= t < T_SRC:
        slam(fr, (FX.TX, 520), "EL FUEGO VUELVE", font("anton", 110), WH, t, T_CL, T_SRC - 0.3, big=False)
        slam(fr, (FX.TX, 636), "CADA AÑO.", font("anton", 110), OR, t, T_CL + 0.25, T_SRC - 0.3, glow=0.5)
    if t >= T_SRC: sources(fr, t)
    flash = min(1.0, sum(0.3 * decay(t, x, 0.11) for x in REVEALS))
    return finish(fr, t, flash=flash)

SRC = ["FUENTES",
       "Focos: NASA FIRMS, VIIRS S-NPP 375 m, Argentina 2012–2025 (vegetación, confianza nominal y alta).",
       "Un foco es una detección satelital de calor: no equivale a un incendio ni a hectáreas.",
       "Causas 1993–2019 y hectáreas 2017–2025: Ministerio de Ambiente (datos abiertos, CIAM).",
       "Bajante del Paraná: INA (2020). Sequía en Corrientes: SMN, vía NASA Earth Observatory (2022).",
       "Uso del fuego: Cavallero et al., Ecología Austral 33 (2023). Provincias: INDEC, Censo 2022.",
       "Mapa, animación y música hechos con código a partir de datos abiertos."]
def sources(fr, t):
    a = clamp((t - T_SRC) / 0.4)
    d = fr.d; d.rectangle((0, 0, W, H), fill=(6, 6, 9, int(205 * a)))
    put_text(fr, (FX.TX, 300), SRC[0], font("anton", 72), OR, a)
    fb = font("inter", 33, 500)
    for i, s in enumerate(SRC[1:]):
        put_text(fr, (FX.TX, 400 + i * 64), s, fb, WH if i != 1 else MU, a * clamp((t - T_SRC - 0.08 * i) / 0.35))

NUM = dict(total=V["total"], y2020=V["y2020"], ratio_2020=V["ratio_2020"], ratio_lbl=R_LBL, aug_sep_10=AS_10, norte_10=NORTE_10, er=ER, cba=CB,
           cba_floor=CB_HA_FLOOR, corr=CO, chubut=CH, chubut_cordillera_10=CH_10, formosa=FO, hum_10=HUM_10,
           causas={k: v for k, v in CA.items() if k != "prov"}, causas_prov=CA["prov"])
if __name__ == "__main__":
    if "--nums" in sys.argv:
        print(json.dumps(NUM, indent=1, ensure_ascii=False))
        print("times", json.dumps(dict(TL0=TL0, T_AS=T_AS, S1=S1, S2=S2, T_F=T_F, T_G=T_G, S3=S3, S4=S4, TL1=TL1, T_ACC=T_ACC, S5=S5, T_CAUSE=T_CAUSE, T_CL=T_CL, T_SRC=T_SRC, TOTAL=TOTAL)))
    if "--still" in sys.argv:
        os.makedirs(os.path.join(HERE, "qa"), exist_ok=True)
        import time
        for x in sys.argv[sys.argv.index("--still") + 1:]:
            t0 = time.time(); render_at(float(x)).save(os.path.join(HERE, "qa", f"still_{float(x):05.2f}.png")); print("still", x, round(time.time() - t0, 2), "s")
