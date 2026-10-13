"""Map beats with text: big_number, statement, closing, map.

big_number — a number card over the map (optionally after flying the camera somewhere):

    - type: big_number
      camera: {fit: ["66"], size: [700, 640], anchor: [1440, 560]}    # or {center: [lon, lat], zoom: 230}
      transition: {mode: zoomto, dur: 1.0}         # camera move BEFORE the text (auto | fly | zoomto | ease | cut)
      head: "SALTA"                                # small mono header (optional), flags: [assets/flags/salta.png]
      number: "{share|pct} %"                      # big number; count_to: "{total}" makes it count up
      unit: "DE LOS SISMOS"
      subline: "EN UNA SOLA PROVINCIA"
      highlight: [{shape: my_zone, color: hot, width: 4}, {regions: ["66"], color: accent2}]
      spotlight: {regions: ["66"], dim: 0.25}      # dim the rest of the map
      replay: {data: events, select: "(region == '66')", time: "(t % 12) / 12", over: 2.4, gain: 0.5}   # time: optional 0..1 order
      layers: [...]                                # see harness/layers.py
      outline_all: dim                             # dim | glow: every region outlined

statement / closing — one to three lines of display type over the map. `closing` defaults: text after 0.8 s (the
map fills first), every region outlined with glow, no legend, big bell in the score.

    - type: closing
      lines: [{text: "MÁS DE LA MITAD,"}, {text: "EN EL NOROESTE.", color: accent, delay: 0.25}]
      size: 124
      layers: [{id: area_raster}, {id: events, mode: accumulate}]

map — no text, just layers/camera (a breathing beat or a camera move). Needs an explicit `duration`."""
import cv2
import numpy as np

from ..core.fx import clamp, decay, mixc, screen, slam, slam_tight
from ..layers import dot_r, fire_rgb, splat
from ..rules import TextBlock
from .base import Beat, Card, draw_outline, highlights, register


class Replay:
    """re-play a subset of points inside a beat: each point flares when its (normalised) time comes"""

    def __init__(self, beat, cfg):
        self.beat = beat; self.cfg = cfg

    def setup(self, t0):
        b = self.beat; c = self.cfg
        self.pts = b.story.dataset(c["data"])
        self.idx = self.pts.select(c.get("select"))
        tt = self.pts.t[self.idx]
        if c.get("time"):
            ns = {k: (v[self.idx] if hasattr(v, "__len__") and len(v) == len(self.pts) else v) for k, v in self.pts.namespace().items()}
            k = np.asarray(eval(c["time"], {"__builtins__": {}}, ns), np.float64)
        else:
            k = (tt - tt.min()) / max(1e-6, tt.max() - tt.min()) if len(tt) > 1 else np.zeros(len(tt))
        self.T = (t0 + float(c.get("delay", 0.3)) + k * float(c.get("over", 2.4))).astype(np.float32)

    def draw(self, A, t, cam, R, t_end):
        on = self.T <= t
        if not on.any():
            return A
        c = self.cfg; H, W = A.shape[:2]
        wv = np.where(on, 0.25 + 1.6 * np.exp(-(t - self.T) / 0.35), 0).astype(np.float32) * (1 - clamp((t - t_end + 0.2) / 0.5))
        f = splat(R.world, self.pts.lon[self.idx], self.pts.lat[self.idx], wv, cam, W, H, dot_r(R, self.pts))
        blur = c.get("blur", "zoom")
        if blur == "zoom":
            k = cam[2] / R.ref_zoom
            if k > 1.15:
                s = min(6.0, 0.55 * k ** 0.8) * R.S; f = cv2.GaussianBlur(f, (0, 0), s) * (k ** 1.25) * 0.55
        elif blur:
            f = cv2.GaussianBlur(f, (0, 0), float(blur) * R.S)
        f = f * float(c.get("gain", 0.5))
        v = 1 - np.exp(-f * 0.8)
        F = R.theme.lut[np.clip(v * 255, 0, 255).astype(np.uint8)]
        hs = cv2.resize(F, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        bloom = cv2.resize(cv2.GaussianBlur(hs, (0, 0), 6 * R.S) * 0.8, (W, H))
        return screen(A, F + bloom)

    def activity(self, t, scale=1.0):
        m = (self.T <= t) & (self.T > t - 2.0)
        return float(np.exp(-(t - self.T[m]) / 0.4).sum()) * scale


class MapBeat(Beat):
    """shared: highlight, spotlight, replay, outline_all"""
    type = "map"

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.replay = Replay(self, cfg["replay"]) if cfg.get("replay") else None

    def plan(self, start, prev):
        super().plan(start, prev)
        if self.replay:
            self.replay.setup(self.start + self.tin)

    def draw_map(self, A, t, cam, R):
        if self.replay:
            A = self.replay.draw(A, t, cam, R, self.end)
        return A

    def spot(self):
        return self.cfg.get("spotlight")

    def activity(self, t):
        return self.replay.activity(t, float(self.replay.cfg.get("activity_scale", 1.0))) if self.replay else 0.0


@register
class MapOnly(MapBeat):
    type = "map"


@register
class BigNumber(MapBeat):
    type = "big_number"
    transition_default = 1.0

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.card = Card(self, cfg)

    def text_templates(self):
        return self.card.templates()

    def resolve(self):
        self.card.resolve()

    def text_need(self):
        return self.need(*self.card.lines())

    def make_blocks(self):
        self.blocks = [TextBlock(self.card.lines(), self.text_t0, self.text_t1, self.id, sizes=self.card.sizes())]

    def draw_ui(self, fr, t, cam, R):
        highlights(self, fr, t, cam)
        self.card.draw(fr, t, self.text_t0, self.text_t1)

    def cues(self):
        return [(self.start, "whoosh", self.tin), (self.text_t0, "hit", 0.9), (self.text_t0 + 0.6, "drums", self.text_t1 - 0.1)] if self.tin > 0.3 \
            else [(self.text_t0, "boom", 1.0), (self.text_t0, "braam_low", 0.8)]


@register
class Statement(MapBeat):
    type = "statement"
    tight = False

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.lines_t = [l if isinstance(l, dict) else {"text": l} for l in cfg.get("lines", [])]
        self.size = cfg.get("size", 100)

    def text_templates(self):
        return [l["text"] for l in self.lines_t]

    def resolve(self):
        self.lines = [dict(l, text=self.story.tpl(l["text"])) for l in self.lines_t]

    def text_need(self):
        return self.need(*[l["text"] for l in self.lines])

    def make_blocks(self):
        self.blocks = [TextBlock([l["text"] for l in self.lines], self.text_t0, self.text_t1, self.id,
                                 sizes=[l.get("size", self.size) for l in self.lines])]

    def draw_ui(self, fr, t, cam, R):
        highlights(self, fr, t, cam)
        th = self.theme
        y = self.cfg.get("y", 560); e = self.text_t1 - 0.25
        for i, l in enumerate(self.lines):
            size = l.get("size", self.size)
            col = self.c(l.get("color", "text" if i == 0 else "accent"))
            t0 = self.text_t0 + float(l.get("delay", 0.25 * i))
            f = th.font("display", size)
            yy = l.get("y", y + i * (size + 20))
            if self.tight or l.get("tight"):
                slam_tight(fr, (110, yy), l["text"], f, col, t, t0, e, glow=0.35 if i == 0 else 0.6)
            else:
                slam(fr, (110, yy), l["text"], f, col, t, t0, e, glow=0.35 if i == 0 else 0.6)


@register
class Closing(Statement):
    type = "closing"
    legend_default = False
    text_delay_default = 0.8
    transition_default = 0.7
    tight = True

    def __init__(self, story, cfg, index):
        cfg.setdefault("outline_all", "glow")
        cfg.setdefault("size", 124)
        cfg.setdefault("y", 560)
        super().__init__(story, cfg, index)
        self.size = cfg["size"]

    def cues(self):
        return [(self.start, "roll_in", self.tin), (self.start + self.tin, "close_boom", 1.0), (self.text_t0 - 0.25, "dip", 0.25),
                (self.text_t0, "close_hit", 1.0)]
