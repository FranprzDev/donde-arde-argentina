"""timeline — a points timelapse with a sparkline and a big running label .

    - type: timeline
      data: events                   # a points dataset with a numeric time `t`
      range: [0, 120]                # data-time window (here: months since 2015-01)
      warp: [[0, 12, 0.05], [12, 108, 0.025], [108, 120, 0.04]]   # seconds per data unit by segment (or `duration`)
      bin: 1                         # sparkline bin width in data units (1 month)
      label: {origin: 2015, per: 12, final: "{year_first}–{year_last}"}   # big running year
      ticks: {every: 12, label_every: 36, origin: 2015}                    # axis ticks / labels
      camera: {center: [-64.2, -38.6], zoom: 30, anchor: [1290, 548]}
      transition: {mode: ease, dur: 3.9}      # e.g. a slow push-in during the whole timelapse
      glow_tau: 0.16
At the end of the beat every point is lit (a following beat can use the layer in mode lit / burnout)."""
import math

import cv2
import numpy as np

from ..core.fx import clamp, decay, lerp, mixc, put_text, screen
from ..layers import dot_r, fire_rgb, lit_field, splat
from ..rules import TextBlock
from .base import Beat, register


@register
class Timeline(Beat):
    type = "timeline"
    text_delay_default = 0.0

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.data = cfg["data"]
        self.r0, self.r1 = map(float, cfg.get("range", [None, None])) if cfg.get("range") else (None, None)
        self.lab = cfg.get("label") or {}
        self.ticks = cfg.get("ticks") or {}
        self.bin = float(cfg.get("bin", 1))

    def text_templates(self):
        return [self.lab["final"]] if self.lab.get("final") else []

    def resolve(self):
        self.final = self.story.tpl(self.lab["final"]) if self.lab.get("final") else None

    def plan(self, start, prev):
        self.pts = self.story.dataset(self.data)
        if self.r0 is None:
            self.r0, self.r1 = float(self.pts.t.min()), float(self.pts.t.max())
        warp = self.cfg.get("warp")
        if not warp:
            d = float(self.cfg.get("duration", 4.0)); warp = [[self.r0, self.r1, d / (self.r1 - self.r0)]]
        km = [warp[0][0]]; ks = [0.0]
        for a, b, s in warp:
            km.append(b); ks.append(ks[-1] + (b - a) * s)
        self.KA_M = np.array(km, float); self.KA_S0 = np.array(ks, float)
        self.cfg.setdefault("duration", float(ks[-1]))
        tr = self.cfg.get("transition") or {}
        super().plan(start, prev)
        self.KA_S = self.KA_S0 + start
        self.T_A1 = start + float(self.KA_S0[-1])
        m = (self.pts.t >= self.r0) & (self.pts.t <= self.r1)
        self.idx = np.where(m)[0]
        self.PS = np.interp(self.pts.t[self.idx], self.KA_M, self.KA_S).astype(np.float32)
        self.series = self.pts.binned(self.r0, self.r1, self.bin)
        self.blocks = [TextBlock([self.final or "0000"], start, self.end + 0.4, self.id, count=False, sizes=[180, 48])]
        self.ui_end = self.end + 0.6

    def m_now(self, t):
        if t < self.start:
            return self.r0
        if t < self.T_A1:
            return float(np.interp(t, self.KA_S, self.KA_M))
        return self.r1

    def draw_map(self, A, t, cam, R):
        pts = self.pts; idx = self.idx
        n_prior = int(np.searchsorted(self.PS, min(t, self.T_A1 + 1e-3), side="right"))
        sel = idx[:n_prior]
        H, W = A.shape[:2]
        ember = splat(R.world, pts.lon[sel], pts.lat[sel], None, cam, W, H, dot_r(R, pts)) if n_prior else np.zeros((H, W), np.float32)
        tau = float(self.cfg.get("glow_tau", 0.16))
        i0 = int(np.searchsorted(self.PS, t - 1.0))
        w = np.exp(-(t - self.PS[i0:n_prior]) / tau).astype(np.float32)
        fire = splat(R.world, pts.lon[idx[i0:n_prior]], pts.lat[idx[i0:n_prior]], w, cam, W, H, dot_r(R, pts)) if len(w) else np.zeros((H, W), np.float32)
        acc = clamp((t - self.T_A1 + 0.3) / 0.3) * (0.85 + 0.3 * decay(t, self.T_A1, 0.6)) if t >= self.T_A1 - 0.3 else 0.0
        em = np.clip(np.log1p(ember) / math.log1p(60), 0, 1)
        v = 1 - np.exp(-fire * 0.55)
        if acc > 0:
            lv, _ = lit_field(R, pts, sel, cam)
            v = np.maximum(v, lv / 1.25 * acc)
        v = cv2.GaussianBlur(v, (0, 0), 0.7) * 1.25
        F = fire_rgb(v, R.theme.lut, R.S, 1.0 + 0.6 * decay(t, self.T_A1, 0.9))
        E = em[..., None] * np.array((120, 30, 10), np.float32) * 0.85 * (1 - clamp(acc))
        return screen(A + E, F)

    # ---------------- sparkline + big label ----------------
    def draw_ui(self, fr, t, cam, R):
        a = clamp((t - self.start) / 0.4) * (1 - clamp((t - self.end + 0.2) / 0.5))
        if a <= 0.003:
            return
        th = self.theme; d = fr.d; S = fr.S
        X0, X1, YB, TH = self.cfg.get("spark_box", [110, 1010, 1018, 180])
        span = self.r1 - self.r0; MM = max(1.0, self.series.max())
        tx = lambda m: (X0 + (X1 - X0) * (m - self.r0) / span) * S
        ty = lambda v: (YB - TH * v / MM) * S
        mn = min(self.r1, max(self.r0, self.m_now(t)))
        muted = th.c["muted"]
        d.line([(X0 * S, YB * S), (X1 * S, YB * S)], fill=(120, 116, 110, int(150 * a)), width=max(1, int(2 * S)))
        tk = self.ticks; every = float(tk.get("every", 12)); lab_every = float(tk.get("label_every", 48)); org = tk.get("origin", self.lab.get("origin", 0))
        fl = th.font("mono", 48, 700)
        m = self.r0; k = 0
        while m <= self.r1 + 1e-6:
            x = tx(m); major = abs(((m - self.r0) / lab_every) - round((m - self.r0) / lab_every)) < 1e-6
            d.line([(x, YB * S), (x, (YB + (12 if major else 6)) * S)], fill=(150, 146, 140, int(170 * a)), width=max(1, int(2 * S)))
            if major and m < self.r1 - 1e-6:
                put_text(fr, (x / S + 4, YB + 52), str(int(org + (m - self.r0) / every)), fl, muted, a)
            m += every; k += 1
        n = int(round((mn - self.r0) / self.bin))
        xs = [tx(self.r0)]; ys = [YB * S]
        for i in range(min(n, len(self.series))):
            xs.append(tx(self.r0 + (i + 0.5) * self.bin)); ys.append(ty(self.series[i]))
        if mn < self.r1:
            nxt = self.series[min(n, len(self.series) - 1)]
            xs.append(tx(mn)); ys.append(ty(nxt * clamp((mn - self.r0 - n * self.bin) / self.bin)))
        else:
            xs.append(tx(self.r1)); ys.append(ty(self.series[-1]))
        pts = list(zip(xs, ys)); AM = th.c["accent2"]; OR = th.c["accent"]
        if len(pts) > 1:
            d.polygon(pts + [(xs[-1], YB * S)], fill=OR + (int(95 * a),)); d.line(pts, fill=AM + (int(255 * a),), width=max(1, int(4 * S)))
            fr.glow_line(pts, mixc((0, 0, 0), OR, a), 8)
        if mn < self.r1:
            x = tx(mn); y = ys[-1]
            d.line([(x, (YB + 4) * S), (x, (YB - TH - 18) * S)], fill=(255, 240, 220, int(120 * a)), width=max(1, int(2 * S)))
            r = 8 * S; d.ellipse((x - r, y - r, x + r, y + r), fill=th.c["hot"] + (int(255 * a),))
        if self.lab:
            per = float(self.lab.get("per", 12)); org = self.lab.get("origin", 0)
            yy = int(org + (min(self.r1 - 1e-3, mn) - self.r0) // per)
            s = self.final if (t >= self.T_A1 and self.final) else str(yy)
            put_text(fr, (104, self.cfg.get("label_y", 236)), s, th.font("display", self.cfg.get("label_size", 180)), th.c["text"], a)

    def activity(self, t):
        if not (self.start <= t < self.end):
            return 0.0
        a = int(np.searchsorted(self.PS, t - 1.0)); b = int(np.searchsorted(self.PS, t, side="right"))
        return float(np.exp(-(t - self.PS[a:b]) / 0.16).sum()) if b > a else 0.0

    def reveals(self):
        return [self.start, self.T_A1]

    def cues(self):
        c = [(self.start, "big_hit", 1.0), (self.start + 0.3, "drums_fast", self.T_A1 - 0.05), (self.T_A1, "braam", 1.0)]
        per = float(self.lab.get("per", 12)) if self.lab else 12.0
        m = self.r0
        while m < self.r1:
            c.append((float(np.interp(m, self.KA_M, self.KA_S)), "tick_up", (m - self.r0) / max(1, self.r1 - self.r0)))
            m += per
        return c
