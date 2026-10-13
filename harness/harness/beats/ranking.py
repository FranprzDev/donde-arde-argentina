"""ranking — every region lights up on the map in rank order (choropleth sweep), then the top N with names, bars
and rank numbers on the map.

    - type: ranking
      rows: ranking_rows              # a fact: list of {code, name, value}, any order (sorted desc here)
      top: 5
      header: "{top_n} PROVINCIAS = {top5_pct} % DE LO QUEMADO"
      step: 0.045                     # seconds between regions in the sweep (bottom-up: last rank first)
      camera: {center: [-64.2, -38.6], zoom: 30, anchor: [1430, 548]}
      label_points: {"06": [-60.3, -36.9]}   # optional manual label positions for rank numbers on the map
Words counted for readability: header + the N names (rank digits are labels)."""
import numpy as np
from PIL import Image, ImageDraw

from ..core.fx import clamp, decay, eout, outlined_text, put_text, slam
from ..rules import TextBlock
from .base import Beat, register


@register
class Ranking(Beat):
    type = "ranking"
    legend_default = False
    transition_default = 0.7

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.top = int(cfg.get("top", 5)); self.step = float(cfg.get("step", 0.045))
        self.header_t = cfg.get("header", "")

    def text_templates(self):
        return [self.header_t] if self.header_t else []

    def resolve(self):
        rows = self.story.facts[self.cfg["rows"]] if isinstance(self.cfg["rows"], str) else self.cfg["rows"]
        self.rows = sorted([dict(r, code=str(r["code"]), value=float(r["value"])) for r in rows], key=lambda r: -r["value"])
        self.header = self.story.tpl(self.header_t) if self.header_t else ""
        up = self.cfg.get("upper", True)
        self.names = [(r["name"].upper() if up else r["name"]) for r in self.rows[:self.top]]
        self.vmax = self.rows[0]["value"] or 1

    def text_need(self):
        return self.need(self.header, *self.names)

    def plan(self, start, prev):
        n = len(self.rows)
        self.sweep = 0.3 + (n - 1) * self.step + 0.35
        tin = self.tin if prev is not None else 0.0
        self.text_delay = max(0.0, self.sweep - tin)       # the sweep runs while the camera settles
        super().plan(start, prev)
        self.T_RK = self.start
        self.T_RK2 = self.text_t0
        self.T_END = self.end

    def make_blocks(self):
        self.blocks = [TextBlock([self.header] + self.names, self.text_t0, self.text_t1, self.id, sizes=[72] * (1 + len(self.names)))]

    def t_row(self, rank):
        return self.T_RK + 0.4 + (len(self.rows) - rank) * self.step

    def col(self, v):
        return tuple(int(x) for x in self.theme.lut[int(70 + 140 * (max(0, v) / self.vmax) ** 0.55)])

    def draw_map(self, A, t, cam, R):
        out = 1 - clamp((t - self.T_END + 0.1) / 0.6)
        k2 = clamp((t - self.T_RK2) / 0.5)
        lay = Image.new("RGBA", (R.W, R.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for rank, r in enumerate(self.rows, 1):
            a = clamp((t - self.t_row(rank)) / 0.15)
            if a <= 0 or r["code"] not in R.world.regions:
                continue
            al = (0.78 if rank <= self.top else 0.78 + (0.22 - 0.78) * k2) * a * out
            col = self.col(r["value"]) if r["value"] > 0 else (40, 38, 40)
            for ring in R.world.regions[r["code"]]:
                d.polygon(R.world.ring_px(ring, cam), fill=col + (int(255 * al),))
        L = np.asarray(lay, np.float32); al = L[..., 3:4] / 255
        return A * (1 - al) + L[..., :3] * al

    def draw_ui(self, fr, t, cam, R):
        if not (self.start <= t < self.end + 0.4):
            return
        th = self.theme; d = fr.d; W = R.world
        out = 1 - clamp((t - self.T_END + 0.3) / 0.35)
        k2 = clamp((t - self.T_RK2) / 0.45)
        HOT, AM, OR, WH = th.c["hot"], th.c["accent2"], th.c["accent"], th.c["text"]
        from ..core.fx import mixc
        for rank, r in enumerate(self.rows, 1):
            if r["code"] not in W.regions:
                continue
            tr = self.t_row(rank); e = decay(t, tr, 0.25) if t >= tr else 0
            top = rank <= self.top
            w = max(e, (k2 if top else 0)) * out
            if w > 0.02:
                for ring in W.regions[r["code"]]:
                    pts = W.ring_px(ring, cam)
                    d.line(pts + pts[:1], fill=(HOT if e > 0.5 else AM) + (int(230 * w),), width=max(1, int((3 if top else 2) * fr.S)))
                    fr.glow_line(pts + pts[:1], mixc((0, 0, 0), AM, w), 8)
        if k2 <= 0.003:
            return
        e_ = self.T_END - 0.3
        slam(fr, (110, 250), self.header, th.font("display", 72), OR, t, self.T_RK2 + 0.05, e_, glow=0.4)
        f = th.font("display", 72)
        lp = {k: tuple(v) for k, v in (self.cfg.get("label_points") or {}).items()}
        for j, name in enumerate(self.names):
            y = 400 + j * 112; t0 = self.T_RK2 + 0.25 + j * 0.09
            if t < t0:
                continue
            u = t - t0; a = clamp(u / 0.15) * out
            slam(fr, (110, y), str(j + 1), f, OR, t, t0, e_, big=False)
            slam(fr, (180, y), name, f, WH, t, t0, e_, big=False)
            bw = (960 - 180) * self.rows[j]["value"] / self.vmax * eout(u / 0.4)
            d.rectangle((180 * fr.S, (y + 18) * fr.S, (180 + bw) * fr.S, (y + 28) * fr.S),
                        fill=self.col(self.rows[j]["value"]) + (int(255 * a * (1 - clamp((t - e_) / 0.3))),))
        fl = th.font("display", 60)
        for j, r in enumerate(self.rows[:self.top]):
            if r["code"] not in W.regions:
                continue
            lx, ly = W.projd(*(lp.get(r["code"]) or W.label_point(r["code"])), cam)
            s_ = str(j + 1); aa = k2 * out * clamp((t - self.T_RK2 - 0.25 - j * 0.09) / 0.2)
            outlined_text(fr, (lx - fr.tw(s_, fl) / 2, ly + 20), s_, fl, WH, aa, r=3)

    def reveals(self):
        return [self.T_RK2 + 0.1]

    def cues(self):
        c = [(self.t_row(rank), "tick_rank", 1 - (rank - 1) / max(1, len(self.rows) - 1)) for rank in range(1, len(self.rows) + 1)]
        c += [(self.T_RK + 0.4, "swell", self.T_RK2 - self.T_RK - 0.4), (self.T_RK2 + 0.1, "big_hit", 1.0), (self.T_RK2 + 0.7, "drums_full", self.T_END - 0.2)]
        return c
