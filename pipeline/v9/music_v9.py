"""v9: v8 score re-cut to the v9 picture (no photo cuts or headline ticks: an impact when each Sentinel-2 zoom fills the frame;
shorter ranking; later landing at 8,3 s). All cue times are read from render_v9.py.
v8: v7 score re-cut to the v8 picture: stops Tucumán -> Entre Ríos -> Comarca, an impact + fire roar on each hard cut to a photo,
a paper tick per headline card, a swell while the whole-country fire history fills in; the 911 hit and its bell are gone (bell moves to
«FALTA RESPONSABILIDAD.»).
v7: = v6 score + a soft hit under the hook title (0,45 s); ranking ticks follow the v7 (distinct-area) ranks.
Procedural score for v6 (v5 score re-timed to the v6 picture: slower space opening with sun rays + glints, a match-strike spark and a
breath before the 14-year blaze, a tick per province in the ranking sweep, province-to-province whooshes; causes card removed).
v5 notes: Procedural score for v5 (= v4 score; v5 changes only the close: a music dip before «YA NO FALTAN DATOS. FALTA RESPONSABILIDAD.», hits on it and on the 911 line; limiter ceiling lowered so the AAC file stays <= -1.5 dBTP)
Original v4 notes: «¿Dónde arde Argentina?» (numpy synthesis, fixed seed; no samples, no AI). 48 kHz stereo -> build/music_v9.wav,
mastered to ~-14 LUFS, true peak <= -1 dBTP. Instruments + master chain reused from v1/v2. Every cue time is read from render_v9.py.
Data-driven layer: fire crackle follows the hotspots glowing on screen (same glow law as the picture).
Arc: solar roar + riser/whooshes for the Sun->Earth->Argentina pull -> landing hit (title) -> frantic double-time drums, rising 16th ostinato,
a tick per January for the 14-year blaze -> braam hit on «2.550.467» and a breath -> tape-stop rewind -> slow half-time breakdown with a hit
per stop (Delta drop, 2020 recap, Corrientes, Formosa) -> drums stop on the causes card -> roll -> D-minor resolution + choir on the close."""
import numpy as np, os, sys, subprocess, json, re
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
from scipy.ndimage import minimum_filter1d
from scipy.io import wavfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); os.chdir(HERE)
import render_v9 as RV
SR = 48000; T = RV.TOTAL; N = int(T * SR); t = np.arange(N) / SR
rng = np.random.default_rng(23)
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, f, o=2): return sosfilt(butter(o, f, fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, btype="high", fs=SR, output="sos"), x)
def bp(x, a, b, o=2): return sosfilt(butter(o, [a, b], btype="band", fs=SR, output="sos"), x)
def env_pts(pts):
    xs, ys = zip(*pts); return np.interp(t, xs, ys)
def put(buf, x, sig, g=1.0):
    a = int(round(x * SR)); b = min(N, a + len(sig))
    if a < 0: sig = sig[-a:]; a = 0
    if a < N: buf[a:b] += g * sig[:b - a]
def tt_(d): return np.arange(int(d * SR)) / SR

BEAT = 0.6; BAR = 2.4
DRY = np.zeros((2, N)); WET = np.zeros((2, N))          # WET goes through the reverb
def add(x, sig, g=1.0, pan=0.0, wet=0.3):
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    for ch, k in ((0, l), (1, r)):
        tmp = np.zeros(N); put(tmp, x, sig, g * k * 1.414)
        DRY[ch] += tmp; WET[ch] += tmp * wet

# ---------------- instruments ----------------
def boom(dur=2.2, f0=120, f1=34, dec=2.0, drive=1.8):
    tt = tt_(dur); f = f1 + (f0 - f1) * np.exp(-tt * 9)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * dec)
# ---------------- instruments ----------------
def boom(dur=2.2, f0=120, f1=34, dec=2.0, drive=1.8):
    tt = tt_(dur); f = f1 + (f0 - f1) * np.exp(-tt * 9)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * dec)
    click = lp(rng.standard_normal(len(tt)), 2500) * np.exp(-tt * 60) * 0.5
    return np.tanh(drive * (s + click)) / np.tanh(drive)
def taiko(g=1.0, f0=150, f1=58):
    tt = tt_(0.9); f = f1 + (f0 - f1) * np.exp(-tt * 28)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 6.5)
    skin = bp(rng.standard_normal(len(tt)), 120, 900) * np.exp(-tt * 30) * 0.9
    slap = hp(rng.standard_normal(len(tt)), 2000) * np.exp(-tt * 90) * 0.25
    return np.tanh(1.5 * (body + skin + slap)) * g
def braam(root=33, dur=4.0):
    """the big brass-like 'braam': stacked detuned saws through an opening/closing low-pass, saturated, + sub drop"""
    tt = tt_(dur); s = np.zeros(len(tt))
    for m in (root, root + 7, root + 12, root + 15, root + 19):
        for det in (-0.12, 0, 0.11):
            ph = (hz(m + det) * tt) % 1.0; s += (2 * ph - 1) * (0.9 if m == root else 0.6)
    env = np.minimum(tt / 0.04, 1) * np.exp(-tt * 0.7)
    cut = 250 + 2600 * np.exp(-tt * 1.4) * np.minimum(tt / 0.15, 1)
    out = np.zeros(len(tt)); blk = 2400
    for a in range(0, len(tt), blk):
        b = min(len(tt), a + blk); seg = s[max(0, a - 1200):b]
        out[a:b] = lp(seg, float(cut[a]), 2)[-(b - a):]
    out = np.tanh(out * env * 0.35) * 1.2
    sub = np.sin(2 * np.pi * np.cumsum(30 + 30 * np.exp(-tt * 3)) / SR) * np.exp(-tt * 0.9) * 0.9
    return out + sub
def whoosh(dur, f0, f1, rev=False):
    tt = tt_(dur); n = rng.standard_normal(len(tt)); out = np.zeros(len(tt)); blk = 1200
    fc = f0 * (f1 / f0) ** (tt / dur)
    for a in range(0, len(tt), blk):
        b = min(len(tt), a + blk); f = float(fc[a]); out[a:b] = bp(n[max(0, a - 1200):b], f * 0.6, min(f * 1.6, 20000))[-(b - a):]
    e = (tt / dur) ** 2.5 if not rev else (1 - tt / dur) ** 1.5 * np.minimum(tt / 0.05, 1)
    return out * e
def rev_swell(dur):
    tt = tt_(dur); n = hp(rng.standard_normal(len(tt)), 1500); return n * (tt / dur) ** 3
def tick(hi=True):
    tt = tt_(0.05); f = 3200 if hi else 2400
    return (np.sin(2 * np.pi * f * tt) * 0.6 + bp(rng.standard_normal(len(tt)), 2500, 7000) * 0.6) * np.exp(-tt * 140)
def snare(g=1.0):
    tt = tt_(0.35); n = bp(rng.standard_normal(len(tt)), 900, 8000) * np.exp(-tt * 16)
    body = np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 25) * 0.6
    return (n + body) * g
def hat():
    tt = tt_(0.06); return hp(rng.standard_normal(len(tt)), 7000) * np.exp(-tt * 80)
def pad_voice(midis, dur, bright=1.0, att=0.8, rel=1.2):
    tt = tt_(dur + rel); s = np.zeros(len(tt))
    for m in midis:
        for det in (-0.07, 0.0, 0.08):
            f = hz(m + det); vib = 1 + 0.003 * np.sin(2 * np.pi * 5.1 * tt + rng.random() * 6)
            ph = np.cumsum(f * vib) / SR
            for k in range(1, 7):
                s += np.sin(2 * np.pi * k * ph) / k ** (1.6 - 0.5 * bright)
    e = np.minimum(tt / att, 1) * np.clip((dur + rel - tt) / rel, 0, 1)
    return s * e / (len(midis) * 3)
def choir(midis, dur, att=1.2, rel=2.0):
    """vowel-ish 'aah' pad: harmonics weighted by two formants (~700 and ~1150 Hz)"""
    tt = tt_(dur + rel); s = np.zeros(len(tt))
    for m in midis:
        f0 = hz(m)
        for det in (-0.1, 0.1):
            vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * tt + rng.random() * 6); ph = np.cumsum(f0 * 2 ** (det / 12) * vib) / SR
            for k in range(1, 14):
                fk = k * f0; w = np.exp(-((fk - 700) / 260) ** 2) + 0.6 * np.exp(-((fk - 1150) / 300) ** 2) + 0.15 / k
                s += w * np.sin(2 * np.pi * k * ph)
    e = np.minimum(tt / att, 1) * np.clip((dur + rel - tt) / rel, 0, 1)
    return s * e / (len(midis) * 2)

# ---------------- data-driven: fire activity per frame (same glow law as the picture) ----------------
FT = np.arange(0, T, 1 / 30)
act = np.array([RV.fire_activity(x) if x >= RV.T_SPARK else 0.0 for x in FT])
act = np.minimum(act, np.percentile(act[act > 0], 99) if (act > 0).any() else 1)
act = act / act.max()
ACT = np.interp(t, FT, act)

TL, TA1, TASH, TSCAR, TD1 = RV.T_LAND, RV.T_A1, RV.T_ASH, RV.T_SCAR, RV.T_D1
STU, SER, SPA = RV.S_TU, RV.S_ER, RV.S_PA; PHS = RV.PHOTOS
TRK, TRK2, TRKE = RV.T_RK, RV.T_RK2, RV.T_RK_END
TCL, TSRC = RV.T_CL, RV.T_SRC
K = RV.SPACE_K; TSP = RV.T_SPARK; TCOOL = RV.T_COOL

# ---------------- 1. drone ----------------
dr_amp = env_pts([(0, 0.0), (0.4 * K, 0.55), (TCOOL, 0.8), (TSP, 0.35), (TL - 0.01, 0.7), (TL, 1.0), (TA1, 1.0), (TASH, 0.6), (TSCAR, 0.3), (TD1, 0.5),
                  (TRK2, 0.8), (TRKE, 0.75), (STU[0], 0.85), (STU[1], 0.8), (SER[0], 0.85), (SER[1], 0.8), (SPA[0], 1.0), (SPA[1], 0.9), (TCL, 1.0), (TSRC, 0.6), (T, 0)])
drone = (np.sin(2 * np.pi * hz(38) * t) + 0.5 * np.sin(2 * np.pi * hz(50) * t + 1) + 0.25 * np.sin(2 * np.pi * hz(45) * t + 2)) * dr_amp
rumble = lp(rng.standard_normal(N), 90, 4) * 3.0 * dr_amp
for ch in (0, 1): DRY[ch] += 0.42 * drone + 0.25 * rumble; WET[ch] += 0.1 * drone

# ---------------- 2. space: solar roar, the rays (one glint per hit), heat, the cool-down ----------------
roar = bp(rng.standard_normal(N), 60, 900) * env_pts([(0, 0.9), (0.8 * K, 0.7), (1.8 * K, 0.15), (2.4 * K, 0)]) * 1.4
shimmer = hp(rng.standard_normal(N), 6000) * env_pts([(0, 0.0), (0.6 * K, 0.12), (2.6 * K, 0.25), (TCOOL, 0.18), (TCOOL + 0.3, 0.0)])
for ch in (0, 1): DRY[ch] += 0.5 * np.roll(roar, ch * 61) + 0.3 * np.roll(shimmer, ch * 23); WET[ch] += 0.3 * roar + 0.4 * shimmer
add(0.0, boom(3.0, 70, 28, 0.8, 1.2), 0.55, 0, 0.7)
add(0.0, choir([62, 69, 74], 3.0 * K, 0.5, 1.2), 0.45, 0, 0.9)
add(0.2, whoosh(1.0 * K, 2500, 300, rev=True), 0.45, -0.4, 0.5)
add(0.9 * K, whoosh(1.6 * K, 200, 3000), 0.35, 0.3, 0.4)
add(2.1 * K, whoosh(RV.T_MAP - 2.1 * K, 300, 9000), 0.6, 0, 0.4)
for j, (te, kind, p1, p2) in enumerate(RV.RAYS):                       # a glass-like glint where each ray lands
    x = te + RV.RAY_TRAVEL
    if x > TCOOL + 0.2: continue
    tt = tt_(0.18); m = 86 + (j * 7) % 12
    add(x, np.sin(2 * np.pi * hz(m) * tt) * np.exp(-tt * 28) * 0.5, 0.10 if kind == 1 else 0.16, (-0.6, 0.6)[j % 2], 0.6)
heat = lp(rng.standard_normal(N), 500) * env_pts([(0, 0), (2.9, 0), (4.4, 0.5), (TCOOL, 0.6), (TCOOL + 0.4, 0.0)])
for ch in (0, 1): DRY[ch] += 0.5 * heat; WET[ch] += 0.2 * heat
add(TCOOL - 0.1, whoosh(0.6, 4000, 300, rev=True), 0.35, 0, 0.6)          # the heat drops away

# ---------------- 3. pads ----------------
def chord_seq(t0, t1, chords, step=BAR, g=1.0, bright=1.0, wet=0.6):
    i = 0; x = t0
    while x < t1 - 0.05:
        d = min(step, t1 - x); add(x, pad_voice(chords[i % len(chords)], d, bright, 0.3 if step < 2 else 0.5, 1.0), g, -0.3 if i % 2 else 0.3, wet); i += 1; x += step
Dm, Bb, F, C, A, Gm = [50, 57, 62, 65], [46, 58, 62, 65], [41, 57, 60, 65], [48, 55, 60, 64], [45, 57, 61, 64], [43, 58, 62, 67]
chord_seq(0.6, TCOOL, [[50, 57, 62]], TCOOL - 0.6, 0.45, 0.4)
add(TSP, pad_voice([38, 45, 50], TL - TSP, 0.5, 0.6, 0.6), 0.6, 0, 0.8)    # the spark: low, held breath
chord_seq(TL, TA1, [Dm, Bb, Gm, A], 0.6, 0.75, 1.3)
add(TA1, pad_voice([38, 50, 57, 62, 65], TASH - TA1 + 0.5, 1.2, 0.05, 1.5), 1.1, 0, 0.7)
add(TASH, pad_voice([38, 45, 50, 53], TD1 - TASH + 1.0, 0.6, 1.0, 2.0), 1.0, 0, 0.8)
chord_seq(TD1, TCL, [Dm, Bb, Gm, A], BAR, 0.9, 1.0)
add(TCL, pad_voice([38, 50, 57, 62, 65, 69], TSRC - TCL + 2.0, 1.4, 0.6, 3.0), 1.4, 0, 0.7)
add(TCL, choir([57, 62, 65, 69], TSRC - TCL + 1.6, 1.0, 3.0), 0.9, 0, 0.9)
add(SPA[0], choir([50, 57, 62, 65], SPA[1] - SPA[0], 1.5, 2.0), 0.55, 0, 0.9)

# ---------------- 4. fire crackle (follows the hotspots on screen) ----------------
cr = np.zeros(N); dens = 40 + 1100 * ACT ** 0.7
u = rng.random(N) < dens / SR
cr[u] = rng.uniform(0.3, 1.0, u.sum()) * rng.choice([-1, 1], u.sum())
cr = bp(cr, 1500, 9000) * 1.6 + lp(rng.standard_normal(N), 400) * 0.10 * ACT
crk = cr * (0.25 + 0.75 * ACT) * np.clip((t - TSP) / 0.3, 0, 1)
crk = crk * (1 - np.clip((t - TSRC) / 1.0, 0, 1) * 0.8)
for ch, g in ((0, 1.0), (1, 0.9)): DRY[ch] += 0.22 * np.roll(crk, ch * 37); WET[ch] += 0.05 * crk

# ---------------- percussion helpers ----------------
PAT = [(0, 1.0), (3, 0.55), (6, 0.7), (8, 0.95), (10, 0.5), (11, 0.6), (12, 0.8), (14, 0.6)]
def drums(t0, t1, g=1.0, full=False, bar=BAR):
    st = bar / 16
    for bx in np.arange(t0, t1 - 0.01, bar):
        for step, a in PAT:
            x = bx + step * st
            if x < t1 - 0.01: add(x, taiko(a * g), 1, (-0.35, 0.35)[step % 2], 0.35)
        if full:
            for s_ in (4, 12):
                if bx + s_ * st < t1: add(bx + s_ * st, snare(0.55 * g), 1, 0.1, 0.4)
            for s_ in range(0, 16, 1 if bar < 2 else 2):
                if bx + s_ * st < t1: add(bx + s_ * st, hat(), 0.18 * g, 0.5, 0.1)
def hit(x, g=1.0, root=38, big=False):
    add(x, boom(2.6 if big else 2.0, 140, 28, 1.2, 2.2), (1.1 if big else 0.8) * g, 0, 0.6); add(x, taiko(1.0 * g), 1, 0, 0.5)
    if big: add(x, braam(root, 4.0), 1.1 * g, 0, 0.6)

# ---------------- 5. the spark: a match strike, then a riser into the landing ----------------
tt = tt_(0.35); strike = bp(rng.standard_normal(len(tt)), 1800, 7000) * np.exp(-tt * 14) * (1 - np.exp(-tt * 300))
flare = lp(rng.standard_normal(len(tt_(1.2))), 900) * np.exp(-tt_(1.2) * 3) * np.minimum(tt_(1.2) / 0.05, 1)
add(TSP - 0.04, strike, 1.0, 0.1, 0.5); add(TSP + 0.02, flare, 0.6, 0, 0.6); add(TSP, boom(1.6, 90, 40, 2.5, 1.4), 0.5, 0, 0.6)
add(TL - 1.6, rev_swell(1.6), 0.8, 0, 0.5); add(TL - 1.2, whoosh(1.2, 300, 8000), 0.5, 0, 0.4)
for k in range(10): add(TL - 0.5 + k * 0.05, snare(0.15 + 0.05 * k), 1, 0, 0.3)

# v7: the hook title slams at T_HOOK[0]: a soft taiko + low boom under it
add(RV.T_HOOK[0], taiko(0.55, 130, 55), 1, 0, 0.5); add(RV.T_HOOK[0], boom(1.6, 110, 36, 2.4, 1.4), 0.45, 0, 0.6)
# ---------------- 6. landing + the frantic 14-year blaze ----------------
hit(TL, 1.0, 38, True); add(TL + 0.15, taiko(0.7), 1, 0.2, 0.4)
drums(TL + 0.3, TA1 - 0.05, 0.9, True, bar=1.2)
for y in range(14):
    x = float(np.interp(y * 12, RV.KA_M, RV.KA_S)); tt = tt_(0.12)
    add(x, np.sin(2 * np.pi * hz(74 + y) * tt) * np.exp(-tt * 30) * 0.5, 0.45, (-0.3, 0.3)[y % 2], 0.2); add(x, tick(True), 0.45, (-0.3, 0.3)[y % 2], 0.2)
arp = [62, 65, 69, 74]; x = TL + 0.3; k = 0
while x < TA1 - 0.05:
    up = int(12 * (x - TL) / (TA1 - TL)); tt = tt_(0.07); m = arp[k % 4] + up
    add(x, (2 * ((hz(m) * tt) % 1) - 1) * np.exp(-tt * 40) * 0.35, 0.5, (-0.4, 0.4)[k % 2], 0.25); x += 0.075; k += 1
tt = tt_(2.5); e = (tt / tt[-1]) ** 2
add(TA1 - 2.5, np.sin(2 * np.pi * np.cumsum(hz(50) * (1 + 1.0 * e)) / SR) * e * 0.35 + hp(rng.standard_normal(len(tt)), 3000) * e * 0.3, 1.0, 0, 0.5)
# ---------------- 7. the total, the ash, the scars ----------------
add(TA1, braam(36, 4.4), 1.25, 0, 0.6); add(TA1, boom(3.2, 150, 26, 0.9, 2.6), 1.2, 0, 0.6); add(TA1, taiko(1.0), 1, 0, 0.5)
add(TASH - 0.1, whoosh(1.2, 5000, 200), 0.55, 0, 0.6)
add(TSCAR, boom(4.0, 80, 24, 0.7, 1.6), 1.0, 0, 0.8); add(TSCAR, braam(33, 4.0), 0.8, 0, 0.7)
# ---------------- 8. the ranking: one rising tick per province, then the top-5 hit ----------------
for r in RV.ROWS:
    x = RV.rk_t_row(r["rank"]); tt = tt_(0.09); m = 69 + (24 - r["rank"]) // 2
    add(x, np.sin(2 * np.pi * hz(m) * tt) * np.exp(-tt * 40) * 0.5, 0.4 + 0.3 * (24 - r["rank"]) / 23, 0, 0.25); add(x, tick(False) * 0.5, 0.4 + 0.3 * (24 - r["rank"]) / 23, (-0.3, 0.3)[r["rank"] % 2], 0.25)
add(TRK + 0.4, rev_swell(TRK2 - TRK - 0.4), 0.35, 0, 0.5)
hit(TRK2 + 0.1, 1.0, 38, True); drums(TRK2 + 0.7, TRKE - 0.2, 0.6, True)
# ---------------- 9. the stops (province -> province) ----------------
add(STU[0] - 1.0, whoosh(1.0, 300, 6000), 0.5, -0.2, 0.4); hit(STU[0], 0.9, 38); drums(STU[0] + 0.6, STU[1] - 0.1, 0.55)
add(SER[0] - 1.2, whoosh(1.2, 300, 6000), 0.5, 0.2, 0.4); hit(SER[0], 0.9, 41); drums(SER[0] + 0.6, SER[1] - 0.1, 0.55)
add(SPA[0] - 1.4, whoosh(1.4, 200, 7000), 0.55, 0.2, 0.4); add(SPA[0] - 1.0, rev_swell(1.0), 0.7, 0, 0.6)
hit(SPA[0], 1.0, 36, True); drums(SPA[0] + 0.6, SPA[1] - 0.1, 0.75, True)
# v9: the zoom into each Sentinel-2 view — a whoosh down, a reverse swell into an impact as the image fills the frame, then a low
# roar of fire under the smoke plumes (PHOTOS = (zoom end, hold end) in render_v9.py)
for j, (z0, z1, z2) in enumerate(RV.S2Z): add(z0, whoosh(z1 - z0, 6000, 250), 0.45, 0, 0.4)
for j, (p0, p1) in enumerate(PHS):
    add(p0 - 0.45, rev_swell(0.45), 0.55, 0, 0.5)
    add(p0, boom(2.2, 150, 30, 1.6, 2.2), 0.95, 0, 0.6); add(p0, taiko(1.0), 1, 0, 0.5)
    tt = tt_(p1 - p0 + 0.3); env = np.minimum(tt / 0.03, 1) * np.exp(-tt * 1.2)
    roar = (lp(rng.standard_normal(len(tt)), 700, 2) * 2.2 + bp(rng.standard_normal(len(tt)), 1500, 6000) * 0.35) * env
    add(p0, roar, 0.35, (-0.2, 0.2)[j % 2], 0.4)
# v8: a dry paper tick when each headline card lands
for name, h0, h1, *_ in RV.SEQ:
    tt = tt_(0.06); add(h0, hp(rng.standard_normal(len(tt)), 2500) * np.exp(-tt * 70) * 0.6, 0.5, -0.3, 0.2)
# ---------------- 10. into the close ----------------
add(SPA[1] - 0.3, whoosh(1.0, 6000, 300, rev=True), 0.4, 0, 0.6)
roll = np.arange(SPA[1] - 0.2, TCL - 0.02, 0.075)
for j, x in enumerate(roll): add(x, snare(0.1 + 0.45 * j / max(1, len(roll))), 1, 0, 0.4)
add(TCL - 0.9, rev_swell(0.9), 0.6, 0, 0.6)
add(TCL, boom(4.0, 130, 27, 0.8, 2.2), 1.2, 0, 0.8); add(TCL, taiko(1.0), 1, 0, 0.6)
L2, DIP = RV.CL_L2, RV.CL_DIP
add(TCL + 0.2, rev_swell(DIP - TCL - 0.2), 0.45, 0, 0.7)          # v8: the whole-country fire history fills in
add(L2, boom(3.2, 140, 27, 0.9, 2.4), 1.2, 0, 0.8); add(L2, taiko(1.0), 1, 0, 0.6); add(L2 + 0.25, taiko(0.85), 1, 0, 0.6)
add(L2, braam(38, 3.0), 0.7, 0, 0.7)
tt = tt_(3.5); bell = sum(np.sin(2 * np.pi * hz(m) * tt) for m in (74, 77, 81, 86)) / 4 * np.exp(-tt * 1.2)
add(L2 + 0.25, bell, 0.22, 0, 0.8)
add(TSRC, taiko(0.45, 120, 50), 1, 0, 0.6)

# ---------------- reverb + mix ----------------
irn = int(2.6 * SR); ti = np.arange(irn) / SR
IR = [lp(rng.standard_normal(irn), 5000) * np.exp(-ti * 2.4) * np.minimum(ti / 0.01, 1) for _ in range(2)]
for i in range(2): IR[i] /= np.sqrt((IR[i] ** 2).sum())
wet = np.stack([fftconvolve(WET[i], IR[i])[:N] for i in range(2)])
mix = DRY + 0.55 * wet
mix = hp(mix, 25)
fade = np.clip(np.minimum(t / 0.3, (T - t) / 1.6), 0, 1)
mix = mix * fade
# v5 dip: everything falls to -24 dB over 0.2 s, ~0.25 s of near-silence, then the line-2 hit comes in clean
dip = env_pts([(0, 1), (DIP, 1), (DIP + 0.2, 0.063), (L2 - 0.02, 0.063), (L2, 1), (T, 1)])
mix = mix * dip

# ---------------- master: gain to ~-14 LUFS + true-peak limiter (4x oversampled, look-ahead) ----------------
CEIL = float(os.environ.get("CEIL_DB", "-2.8"))   # v4 used -1.6 and the AAC encode overshot to -0.8 dBFS
# v6: the landing hit + snare roll at ~8.2 s overshoots ~2 dB in the AAC encode (everything else ~0.6 dB): local ceiling -5 dBTP there
CEIL_ENV = CEIL + env_pts([(0, 0), (RV.T_LAND - 0.4, 0), (RV.T_LAND - 0.2, -2.2), (RV.T_LAND + 0.8, -2.2), (RV.T_LAND + 1.0, 0), (T, 0)])
def limit(x, ceil_db=None):
    c = np.repeat(10 ** (CEIL_ENV / 20), 4); up = resample_poly(x, 4, 1, axis=1); pk = np.max(np.abs(up), axis=0)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    la = 4 * int(0.025 * SR)                 # hold +-25 ms then a 25 ms box average: gain never exceeds what each sample needs
    g = minimum_filter1d(need, size=2 * la + 1)
    g = np.convolve(g, np.ones(la) / la, mode="same")
    return resample_poly(up * g, 1, 4, axis=1)
def lufs(x):
    wavfile.write("/tmp/_m.wav", SR, (np.clip(x, -1, 1).T * 32767).astype(np.int16))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", "/tmp/_m.wav", "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    lra = float(re.findall(r"LRA:\s+(-?[\d.]+) LU", r)[-1]); return I, tp, lra
x = mix / np.max(np.abs(mix)) * 0.5
x = np.tanh(x * 1.3) / 1.3 * 1.0            # gentle glue saturation
for it in range(6):
    I, tp, lra = lufs(limit(x))
    if abs(I + 13.95) < 0.08: break      # v5: tighter (v4 tolerance 0.25 left the AAC file at -14.3)
    x = x * 10 ** ((-13.95 - I) / 20)
y = limit(x)
gr = 20 * np.log10(np.maximum(np.abs(y).max(0), 1e-6) / np.maximum(np.abs(x).max(0), 1e-6)); print('limiter: >3 dB GR on %.1f%% of samples, max %.1f dB at %.2f s' % (100 * (gr < -3).mean(), gr.min(), np.argmin(gr) / SR)); pk = np.abs(mix).max(0); [print('peak window', round(s0, 1), round(float(pk[int(s0*SR):int((s0+1)*SR)].max()), 3)) for s0 in np.arange(0, T - 1, 1.0)]
I, tp, lra = lufs(y)
os.makedirs("build", exist_ok=True); wavfile.write("build/music_v9.wav", SR, (np.clip(y, -1, 1).T * 32767).astype(np.int16))
print(json.dumps({"seconds": N / SR, "I_LUFS": I, "TP_dBTP": tp, "LRA": lra}))
