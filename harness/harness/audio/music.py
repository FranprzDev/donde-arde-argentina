"""Procedural score (numpy synthesis, fixed seed: no samples, no AI). Every cue comes from the beats' timing, so the
music always lands on the picture:

  - drone + rumble across the whole video, pads on a chord loop (story `music.chords`, MIDI notes)
  - per-beat cues: hits / booms / braams on reveals, whooshes on camera moves, ticks per year (timeline) and per
    region (ranking), impacts on satellite zooms, a dip of silence + big hit + bell on the closing line
  - a data-driven crackle layer that follows the amount of points glowing on screen (Renderer.activity)

story.yaml:
    music: {seed: 23, root: 38, bpm: 100, chords: [[50,57,62,65],[46,58,62,65],[43,58,62,67],[45,57,61,64]], crackle: 0.22}
    music: {file: assets/my_score.wav}       # or bring your own (still normalised to -14 LUFS)
    music: false                             # silent"""
import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000


def make_music(story, R, out, log=print):
    cfg = story.cfg.get("music", {})
    if cfg is False:
        return None
    if isinstance(cfg, dict) and cfg.get("file"):
        return os.path.join(story.dir, cfg["file"])
    cfg = cfg or {}
    T = story.total; N = int(T * SR) + SR; t = np.arange(N) / SR
    rng = np.random.default_rng(int(cfg.get("seed", 23)))

    def hz(m): return 440 * 2 ** ((m - 69) / 12)
    def lp(x, f, o=2): return sosfilt(butter(o, min(f, SR / 2 - 100), fs=SR, output="sos"), x)
    def hp(x, f, o=2): return sosfilt(butter(o, f, btype="high", fs=SR, output="sos"), x)
    def bp(x, a, b, o=2): return sosfilt(butter(o, [a, min(b, SR / 2 - 100)], btype="band", fs=SR, output="sos"), x)
    def tt_(d): return np.arange(max(1, int(d * SR))) / SR
    def env_pts(pts):
        xs, ys = zip(*sorted(pts)); return np.interp(t, xs, ys)
    DRY = np.zeros((2, N)); WET = np.zeros((2, N))

    def add(x, sig, g=1.0, pan=0.0, wet=0.3):
        a = int(round(x * SR))
        if a >= N or len(sig) == 0:
            return
        if a < 0:
            sig = sig[-a:]; a = 0
        b = min(N, a + len(sig)); s = sig[:b - a] * g
        l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
        DRY[0, a:b] += s * l; DRY[1, a:b] += s * r; WET[0, a:b] += s * l * wet; WET[1, a:b] += s * r * wet

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
        tt = tt_(dur); s = np.zeros(len(tt))
        for m in (root, root + 7, root + 12, root + 15, root + 19):
            for det in (-0.12, 0, 0.11):
                ph = (hz(m + det) * tt) % 1.0; s += (2 * ph - 1) * (0.9 if m == root else 0.6)
        env = np.minimum(tt / 0.04, 1) * np.exp(-tt * 0.7)
        out = lp(s * env, 900, 2)
        out = np.tanh(out * 0.35) * 1.2
        sub = np.sin(2 * np.pi * np.cumsum(30 + 30 * np.exp(-tt * 3)) / SR) * np.exp(-tt * 0.9) * 0.9
        return out + sub

    def whoosh(dur, f0, f1, rev=False):
        tt = tt_(dur); n = rng.standard_normal(len(tt)); out = np.zeros(len(tt)); blk = 1200
        fc = f0 * (f1 / f0) ** (tt / max(dur, 1e-3))
        for a in range(0, len(tt), blk):
            b = min(len(tt), a + blk); f = float(fc[a]); out[a:b] = bp(n[max(0, a - 1200):b], max(30, f * 0.6), min(f * 1.6, 20000))[-(b - a):]
        e = (tt / dur) ** 2.5 if not rev else (1 - tt / dur) ** 1.5 * np.minimum(tt / 0.05, 1)
        return out * e

    def rev_swell(dur):
        tt = tt_(dur); return hp(rng.standard_normal(len(tt)), 1500) * (tt / dur) ** 3

    def tick(f=3200):
        tt = tt_(0.05); return (np.sin(2 * np.pi * f * tt) * 0.6 + bp(rng.standard_normal(len(tt)), 2500, 7000) * 0.6) * np.exp(-tt * 140)

    def blip(m, d=0.12):
        tt = tt_(d); return np.sin(2 * np.pi * hz(m) * tt) * np.exp(-tt * 30) * 0.5

    def snare(g=1.0):
        tt = tt_(0.35); n = bp(rng.standard_normal(len(tt)), 900, 8000) * np.exp(-tt * 16)
        return (n + np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 25) * 0.6) * g

    def hat():
        tt = tt_(0.06); return hp(rng.standard_normal(len(tt)), 7000) * np.exp(-tt * 80)

    def pad(midis, dur, bright=1.0, att=0.8, rel=1.2):
        tt = tt_(dur + rel); s = np.zeros(len(tt))
        for m in midis:
            for det in (-0.07, 0.0, 0.08):
                ph = np.cumsum(hz(m + det) * (1 + 0.003 * np.sin(2 * np.pi * 5.1 * tt + rng.random() * 6))) / SR
                for k in range(1, 7):
                    s += np.sin(2 * np.pi * k * ph) / k ** (1.6 - 0.5 * bright)
        return s * np.minimum(tt / att, 1) * np.clip((dur + rel - tt) / rel, 0, 1) / (len(midis) * 3)

    def choir(midis, dur, att=1.2, rel=2.0):
        tt = tt_(dur + rel); s = np.zeros(len(tt))
        for m in midis:
            f0 = hz(m)
            for det in (-0.1, 0.1):
                ph = np.cumsum(f0 * 2 ** (det / 12) * (1 + 0.006 * np.sin(2 * np.pi * 5.5 * tt + rng.random() * 6))) / SR
                for k in range(1, 14):
                    fk = k * f0; w = np.exp(-((fk - 700) / 260) ** 2) + 0.6 * np.exp(-((fk - 1150) / 300) ** 2) + 0.15 / k
                    s += w * np.sin(2 * np.pi * k * ph)
        return s * np.minimum(tt / att, 1) * np.clip((dur + rel - tt) / rel, 0, 1) / (len(midis) * 2)

    PAT = [(0, 1.0), (3, 0.55), (6, 0.7), (8, 0.95), (10, 0.5), (11, 0.6), (12, 0.8), (14, 0.6)]
    bar = 4 * 60.0 / float(cfg.get("bpm", 100))

    def drums(t0, t1, g=1.0, full=False, b=bar):
        st = b / 16
        for bx in np.arange(t0, t1 - 0.01, b):
            for step, a in PAT:
                x = bx + step * st
                if x < t1 - 0.01:
                    add(x, taiko(a * g), 1, (-0.35, 0.35)[step % 2], 0.35)
            if full:
                for s_ in (4, 12):
                    if bx + s_ * st < t1:
                        add(bx + s_ * st, snare(0.55 * g), 1, 0.1, 0.4)
                for s_ in range(0, 16, 1 if b < 2 else 2):
                    if bx + s_ * st < t1:
                        add(bx + s_ * st, hat(), 0.18 * g, 0.5, 0.1)

    root = int(cfg.get("root", 38))
    chords = cfg.get("chords") or [[root + 12, root + 19, root + 24, root + 27], [root + 8, root + 20, root + 24, root + 27],
                                   [root + 5, root + 20, root + 24, root + 29], [root + 7, root + 19, root + 23, root + 26]]

    def hit(x, g=1.0, big=False):
        add(x, boom(2.6 if big else 2.0, 140, 28, 1.2, 2.2), (1.1 if big else 0.8) * g, 0, 0.6); add(x, taiko(1.0 * g), 1, 0, 0.5)
        if big:
            add(x, braam(root, 4.0), 1.1 * g, 0, 0.6)

    # ---------------- bed: drone + pads ----------------
    starts = [b.start for b in story.beats]
    dr = env_pts([(0, 0.0), (0.5, 0.6)] + [(s, 0.85) for s in starts[1:]] + [(max(0.6, T - 3), 0.7), (T, 0.0)])
    drone = (np.sin(2 * np.pi * hz(root) * t) + 0.5 * np.sin(2 * np.pi * hz(root + 12) * t + 1) + 0.25 * np.sin(2 * np.pi * hz(root + 7) * t + 2)) * dr
    rumble = lp(rng.standard_normal(N), 90, 4) * 3.0 * dr
    for ch in (0, 1):
        DRY[ch] += 0.42 * drone + 0.25 * rumble; WET[ch] += 0.1 * drone
    x = 0.6; i = 0
    while x < T - 0.5:
        d = min(bar, T - x); add(x, pad(chords[i % len(chords)], d, 1.0, 0.5, 1.0), 0.8, -0.3 if i % 2 else 0.3, 0.6); i += 1; x += bar

    # ---------------- cues from the beats ----------------
    for b in story.beats:
        for c in b.cues():
            x, kind, v = c[0], c[1], (c[2] if len(c) > 2 else 1.0)
            if x is None or x >= T:
                continue
            if kind == "space":
                roar = bp(rng.standard_normal(N), 60, 900) * env_pts([(0, 0.9), (x + 1.0, 0.7), (x + 2.2, 0.15), (x + 3.0, 0)]) * 1.4
                for ch in (0, 1):
                    DRY[ch] += 0.5 * np.roll(roar, ch * 61); WET[ch] += 0.3 * roar
                add(x, boom(3.0, 70, 28, 0.8, 1.2), 0.55, 0, 0.7); add(x, choir([root + 24, root + 31, root + 36], 3.7, 0.5, 1.2), 0.45, 0, 0.9)
                add(x + 0.2, whoosh(1.25, 2500, 300, rev=True), 0.45, -0.4, 0.5); add(x + 1.1, whoosh(2.0, 200, 3000), 0.35, 0.3, 0.4)
            elif kind == "hook":
                add(x, taiko(0.55, 130, 55), 1, 0, 0.5); add(x, boom(1.6, 110, 36, 2.4, 1.4), 0.45, 0, 0.6)
            elif kind == "land_map":
                add(x - 2.0, whoosh(2.0, 300, 9000), 0.6, 0, 0.4)
            elif kind == "glint":
                tt = tt_(0.18); m = 86 + int(x * 37) % 12
                add(x, np.sin(2 * np.pi * hz(m) * tt) * np.exp(-tt * 28) * 0.5, v, (-0.6, 0.6)[int(x * 100) % 2], 0.6)
            elif kind == "cool":
                add(x - 0.1, whoosh(0.6, 4000, 300, rev=True), 0.35, 0, 0.6)
            elif kind == "spark":
                tt = tt_(0.35); strike = bp(rng.standard_normal(len(tt)), 1800, 7000) * np.exp(-tt * 14) * (1 - np.exp(-tt * 300))
                add(x - 0.04, strike, 1.0, 0.1, 0.5); add(x, boom(1.6, 90, 40, 2.5, 1.4), 0.5, 0, 0.6)
                add(x, pad([root, root + 7, root + 12], 2.6, 0.5, 0.6, 0.6), 0.6, 0, 0.8)
            elif kind == "landing":
                add(x - 1.6, rev_swell(1.6), 0.8, 0, 0.5); add(x - 1.2, whoosh(1.2, 300, 8000), 0.5, 0, 0.4)
                for k in range(10):
                    add(x - 0.5 + k * 0.05, snare(0.15 + 0.05 * k), 1, 0, 0.3)
            elif kind == "big_hit":
                hit(x, v, True)
            elif kind == "hit":
                hit(x, v)
            elif kind == "boom":
                add(x, boom(4.0, 80, 24, 0.7, 1.6), 1.0 * v, 0, 0.8)
            elif kind == "braam":
                add(x, braam(root - 2, 4.4), 1.25 * v, 0, 0.6); add(x, boom(3.2, 150, 26, 0.9, 2.6), 1.2 * v, 0, 0.6)
            elif kind == "braam_low":
                add(x, braam(root - 5, 4.0), 0.8 * v, 0, 0.7)
            elif kind == "drums_fast":
                drums(x, v, 0.9, True, bar / 2)
            elif kind in ("drums", "drums_full"):
                drums(x, v, 0.55 if kind == "drums" else 0.7, kind == "drums_full")
            elif kind == "tick_up":
                m = root + 36 + int(v * 14); add(x, blip(m), 0.45, (-0.3, 0.3)[int(v * 14) % 2], 0.2); add(x, tick(), 0.45, 0, 0.2)
            elif kind == "tick_rank":
                add(x, blip(root + 31 + int(v * 12), 0.09), 0.4 + 0.3 * v, 0, 0.25); add(x, tick(2400) * 0.5, 0.4 + 0.3 * v, 0, 0.25)
            elif kind == "swell":
                add(x, rev_swell(max(0.2, v)), 0.35, 0, 0.5)
            elif kind == "whoosh":
                if v > 0.2:
                    add(x, whoosh(v, 300, 6000), 0.5, 0.2, 0.4)
            elif kind == "whoosh_down":
                add(x, whoosh(max(0.2, v), 6000, 250), 0.45, 0, 0.4)
            elif kind == "impact":
                add(x - 0.45, rev_swell(0.45), 0.55, 0, 0.5); add(x, boom(2.2, 150, 30, 1.6, 2.2), 0.95, 0, 0.6); add(x, taiko(1.0), 1, 0, 0.5)
                tt = tt_(v + 0.3); e = np.minimum(tt / 0.03, 1) * np.exp(-tt * 1.2)
                add(x, (lp(rng.standard_normal(len(tt)), 700, 2) * 2.2 + bp(rng.standard_normal(len(tt)), 1500, 6000) * 0.35) * e, 0.35, 0, 0.4)
            elif kind == "choir":
                add(x, choir([root + 12, root + 19, root + 24, root + 27], max(0.5, v), 1.5, 2.0), 0.55, 0, 0.9)
            elif kind == "roll_in":
                roll = np.arange(x, x + max(0.1, v), 0.075)
                for j, y in enumerate(roll):
                    add(y, snare(0.1 + 0.45 * j / max(1, len(roll))), 1, 0, 0.4)
            elif kind == "close_boom":
                add(x, boom(4.0, 130, 27, 0.8, 2.2), 1.2, 0, 0.8); add(x, taiko(1.0), 1, 0, 0.6)
                add(x, pad([root, root + 12, root + 19, root + 24, root + 27, root + 31], max(1, T - x), 1.4, 0.6, 2.0), 1.2, 0, 0.7)
            elif kind == "close_hit":
                add(x, boom(3.2, 140, 27, 0.9, 2.4), 1.2, 0, 0.8); add(x, taiko(1.0), 1, 0, 0.6); add(x + 0.25, taiko(0.85), 1, 0, 0.6)
                add(x, braam(root, 3.0), 0.7, 0, 0.7)
                tt = tt_(3.5); bell = sum(np.sin(2 * np.pi * hz(m) * tt) for m in (root + 36, root + 39, root + 43, root + 48)) / 4 * np.exp(-tt * 1.2)
                add(x + 0.25, bell, 0.22, 0, 0.8)
            elif kind == "outro":
                add(x, taiko(0.45, 120, 50), 1, 0, 0.6)
    # ---------------- crackle that follows the points on screen ----------------
    if float(cfg.get("crackle", 0.22)) > 0:
        FT = np.arange(0, T, 1 / story.fps)
        act = np.array([R.activity(x) for x in FT])
        if (act > 0).any():
            act = np.minimum(act, np.percentile(act[act > 0], 99)); act = act / max(1e-9, act.max())
            ACT = np.interp(t, FT, act)
            cr = np.zeros(N); u = rng.random(N) < (40 + 1100 * ACT ** 0.7) / SR
            cr[u] = rng.uniform(0.3, 1.0, u.sum()) * rng.choice([-1, 1], u.sum())
            crk = (bp(cr, 1500, 9000) * 1.6 + lp(rng.standard_normal(N), 400) * 0.10 * ACT) * (0.25 + 0.75 * ACT) * (ACT > 0.001)
            for ch in (0, 1):
                DRY[ch] += float(cfg.get("crackle", 0.22)) * np.roll(crk, ch * 37); WET[ch] += 0.05 * crk
    # ---------------- dips (closing: a breath of silence before the line) ----------------
    gain = np.ones(N)
    for b in story.beats:
        for c in b.cues():
            if c[1] == "dip":
                x = c[0]; d = c[2]
                gain = np.minimum(gain, env_pts([(0, 1), (x, 1), (x + 0.2, 0.063), (x + d - 0.02, 0.063), (x + d, 1), (T + 1, 1)]))
    irn = int(2.6 * SR); ti = np.arange(irn) / SR
    IR = [lp(rng.standard_normal(irn), 5000) * np.exp(-ti * 2.4) * np.minimum(ti / 0.01, 1) for _ in range(2)]
    IR = [x / np.sqrt((x ** 2).sum()) for x in IR]
    wet = np.stack([fftconvolve(WET[i], IR[i])[:N] for i in range(2)])
    mix = hp(DRY + 0.55 * wet, 25)
    mix = mix * np.clip(np.minimum(t / 0.3, (T - t) / 1.6), 0, 1) * gain
    mix = mix[:, :int(T * SR)]
    mix = np.tanh(mix / max(1e-9, np.abs(mix).max()) * 0.5 * 1.3) / 1.3
    os.makedirs(os.path.dirname(out), exist_ok=True)
    wavfile.write(out, SR, (np.clip(mix, -1, 1).T * 32767).astype(np.int16))
    log(f"music: {out} ({T:.2f}s, {len(story.beats)} beats of cues)")
    return out
