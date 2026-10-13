"""Beat base class + shared pieces (camera moves, text blocks, the big-number card, highlights, flags, spotlight).

Lifecycle (driven by Story.prepare and the renderer):
  __init__(story, cfg, index)   parse the YAML of one beat
  text_templates()              raw strings (before facts) -> hand-typed-number check
  resolve()                     fill {placeholders} from facts.json
  plan(start, prev)             set start/end, camera target, absolute text blocks (readability is checked on these)
  camera_at(t)                  camera for a frame inside the beat
  draw_map(A, t, cam, R)        map-space effects on the float image (before text shading)
  draw_ui(fr, t, cam, R)        text and overlays on the Canvas (may run past `end` until `ui_end`)
  cues()                        music cues [(time, kind, strength)]
To add a beat type: subclass Beat, set `type`, implement the methods you need, and decorate with @register."""
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..core.fx import clamp, count, decay, eout, mixc, put_text, slam
from ..errors import StoryError
from ..rules import TextBlock

REGISTRY = {}


def register(cls):
    REGISTRY[cls.type] = cls
    return cls


class Beat:
    type = "base"
    is_map = True                   # drawn on the shared map (False: full-frame card, e.g. sources)
    exempt_readability = False
    legend_default = True
    transition_default = 0.0
    text_delay_default = 0.12

    def __init__(self, story, cfg, index):
        self.story, self.cfg, self.index = story, cfg, index
        self.theme, self.world = story.theme, story.world
        self.id = str(cfg.get("id", f"{index + 1:02d}-{self.type}"))
        self.layers = list(cfg.get("layers") or [])
        tr = cfg.get("transition") or {}
        if isinstance(tr, (int, float)):
            tr = {"dur": tr}
        self.tmode = tr.get("mode", "auto"); self.tin = float(tr.get("dur", self.transition_default))
        self.text_delay = float(cfg.get("text_delay", self.text_delay_default))
        self.legend = cfg.get("legend", self.legend_default)
        self.flash = float(cfg.get("flash", 0.3)); self.shake = float(cfg.get("shake", 0))
        self.prev = self.next = None
        self.blocks = []
        self.start = self.end = self.ui_end = 0.0
        self.cam = self.cam_from = None

    # ---------------- text ----------------
    def text_templates(self):
        """every on-screen string of this beat, before facts are filled in"""
        return []

    def resolve(self):
        pass

    def need(self, *lines):
        from ..rules import words
        return self.story.rules.need(sum(words(x) for x in lines))

    def c(self, name, default="text"):
        """colour from the theme palette by name (or a hex string)"""
        if name is None:
            name = default
        if isinstance(name, str) and name in self.theme.c:
            return self.theme.c[name]
        from ..core.fx import hexrgb
        return hexrgb(name)

    # ---------------- schedule ----------------
    def text_need(self):
        """seconds the beat's main text must stay on screen"""
        return 0.0

    def plan(self, start, prev):
        self.start = start
        self.cam_from = prev.end_camera() if prev is not None else None
        spec = self.cfg.get("camera")
        if spec == "previous" or spec is None:
            self.cam = None
        elif spec == "home":
            self.cam = self.world.camera(self.story.cfg["map"].get("home_camera"))
        else:
            self.cam = self.world.camera(spec)
        if self.cam_from is None:
            self.tin = 0.0
        need = self.text_need()
        dur = self.cfg.get("duration", "auto")
        auto = self.tin + (self.text_delay + need + 0.05 if need > 0 else 0.0) + float(self.cfg.get("pad", 0.0))
        self.dur = max(auto, float(self.cfg.get("min_duration", 0.0))) if dur in ("auto", None) else float(dur)
        self.end = start + self.dur
        self.text_t0 = start + self.tin + self.text_delay
        self.text_t1 = self.end - 0.05
        self.ui_end = self.end
        self.make_blocks()

    def make_blocks(self):
        self.blocks = []

    def end_camera(self):
        return self.cam if self.cam is not None else self.cam_from

    def camera_at(self, t):
        a, b = self.cam_from, self.cam
        if b is None:
            return a
        if a is None or self.tin <= 0:
            return b
        u = (t - self.start) / self.tin
        return b if u >= 1 else self.world.cam_move(a, b, max(0.0, u), self.tmode)

    # ---------------- drawing (override) ----------------
    def draw_map(self, A, t, cam, R):
        return A

    def draw_ui(self, fr, t, cam, R):
        pass

    def draw_pre(self, A, t, cam, R):
        """called while the PREVIOUS beat is on screen (announce something in place). Default: nothing."""
        return A

    def draw_post(self, A, t, cam, R):
        """called while the NEXT beat is on screen (let something fade out). Default: nothing."""
        return A

    def shade(self, t):
        """left text-zone darkening (0..1)"""
        return 0.92

    def full_frame(self, t, R):
        """return a Canvas to bypass the map compositor for this frame (globe phase, cards); None = use the map"""
        return None

    def cues(self):
        return [(self.text_t0, "hit", 0.9)] if self.blocks else []

    def activity(self, t):
        return 0.0

    def reveals(self):
        return [self.text_t0] if self.blocks and self.flash > 0 else []


# ---------------- shared drawing helpers ----------------
_FLAGS = {}


def load_flag(path, h=54):
    k = (path, h)
    if k in _FLAGS:
        return _FLAGS[k]
    im = Image.open(path).convert("RGBA")
    w = max(1, round(h * im.width / im.height)); im = im.resize((w, h), Image.LANCZOS)
    pad = max(2, int(h * 0.26)); out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0); ImageDraw.Draw(sh).rectangle((pad + 3, pad + 5, pad + w + 3, pad + h + 5), fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(5)); out.paste(Image.new("RGBA", out.size, (0, 0, 0, 255)), (0, 0), sh)
    out.alpha_composite(im, (pad, pad))
    ImageDraw.Draw(out).rectangle((pad - 1, pad - 1, pad + w, pad + h), outline=(235, 230, 222, 200), width=2)
    _FLAGS[k] = (out, pad)
    return out, pad


def draw_flags(fr, paths, x, y_mid, a, sc=1.0):
    """flags left-to-right from design x, vertically centred on y_mid; returns the design x after the last flag"""
    if a <= 0.003 or not paths:
        return x
    for p in paths:
        im, pad = load_flag(p, max(8, int(round(54 * fr.S))))
        if abs(sc - 1) > 0.004:
            im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
        al = im.getchannel("A").point(lambda v: int(v * a))
        fr.im.paste(im.convert("RGB"), (int(x * fr.S - pad * sc), int(y_mid * fr.S - im.height / 2)), al)
        x += (im.width - 2 * pad * sc) / fr.S + 14
    return x


def resolve_paths(story, paths):
    out = []
    for p in paths or []:
        q = os.path.join(story.dir, p)
        if not os.path.exists(q):
            raise StoryError(f"file not found: {q}")
        out.append(q)
    return out


def draw_outline(fr, world, rings, cam, col, a, width=3, glow=10):
    if a <= 0.003:
        return
    for r in rings:
        pts = world.ring_px(r, cam)
        fr.d.line(pts + pts[:1], fill=tuple(col) + (int(230 * a),), width=max(1, int(width * fr.S)))
        if glow:
            fr.glow_line(pts + pts[:1], mixc((0, 0, 0), col, a), glow)


def spotlight(A, world, rings, cam, k, W, H):
    """dim everything outside `rings` by k (0..1), slightly cool"""
    if k <= 0.003:
        return A
    m = world.mask(rings, cam, W, H)[..., None]
    return A * (1 - k * (1 - m) * np.array((0.8, 1.0, 1.12), np.float32))


class Card:
    """The big-number card: [flags] HEAD / NUMBER unit / subline. Layout in design units, left text zone."""

    def __init__(self, beat, cfg):
        self.beat = beat; s = beat.story
        self.head_t = cfg.get("head"); self.number_t = cfg.get("number"); self.unit_t = cfg.get("unit")
        self.sub_t = cfg.get("subline"); self.count_t = cfg.get("count_to")
        self.flags = resolve_paths(s, cfg.get("flags"))
        self.x = cfg.get("x", 110)
        self.y_head, self.y_num, self.y_sub = cfg.get("y", [430, 600, 700])
        self.size_num = cfg.get("number_size", 150); self.size_unit = cfg.get("unit_size", 80)
        self.size_sub = cfg.get("subline_size", 66); self.size_head = cfg.get("head_size", 52)
        self.col_num = beat.c(cfg.get("number_color", "hot")); self.col_sub = beat.c(cfg.get("subline_color", "accent2"))
        self.col_head = beat.c(cfg.get("head_color", "accent2")); self.col_unit = beat.c(cfg.get("unit_color", "text"))
        self.glow = cfg.get("glow", 0.55)

    def templates(self):
        return [x for x in (self.head_t, self.number_t, self.unit_t, self.sub_t) if x]

    def resolve(self):
        T = self.beat.story.tpl
        self.head, self.number, self.unit, self.sub = (T(x) if x else "" for x in (self.head_t, self.number_t, self.unit_t, self.sub_t))
        self.count_to = None
        if self.count_t is not None:
            v = T(self.count_t) if isinstance(self.count_t, str) else self.count_t
            self.count_to = int(float(str(v).replace(self.beat.story.locale.tsep, "").replace(self.beat.story.locale.dsep, ".")))

    def lines(self):
        return [x for x in (self.head, self.number, self.unit, self.sub) if x]

    def sizes(self):
        return [s for s, x in ((self.size_head, self.head), (self.size_num, self.number), (self.size_unit, self.unit), (self.size_sub, self.sub)) if x]

    def draw(self, fr, t, cb, ce):
        th = self.beat.theme; loc = self.beat.story.locale
        if t < cb - 0.05 or t > ce + 0.4:
            return
        u = t - cb; fa = clamp(u / 0.2) * (1 - clamp((t - ce) / 0.3)); fsc = 1 + 0.12 * (1 - eout(u / 0.35))
        xe = self.x
        if self.flags:
            xe = draw_flags(fr, self.flags, self.x, self.y_head - 17 + (1 - eout(u / 0.35)) * 18, fa, fsc) + 10
        if self.head:
            slam(fr, (xe, self.y_head), self.head, th.font("mono", self.size_head, 800), self.col_head, t, cb, ce, big=False)
        if self.number:
            fN = th.font("display", self.size_num); fU = th.font("display", self.size_unit)
            s = loc.int(count(t, cb + 0.2, self.count_to, 1.0)) if self.count_to is not None else self.number
            slam(fr, (self.x, self.y_num), s, fN, self.col_num, t, cb + 0.2, ce, glow=self.glow)
            if self.unit:
                slam(fr, (self.x + fr.tw(self.number, fN) + 26, self.y_num), self.unit, fU, self.col_unit, t, cb + 0.5, ce, big=False)
        if self.sub:
            slam(fr, (self.x, self.y_sub), self.sub, th.font("display", self.size_sub), self.col_sub, t, cb + 0.6, ce, glow=0.3)


def highlights(beat, fr, t, cam):
    """beat.cfg.highlight: [{regions: [...]} | {shape: name}, color, width, glow, from (s after start)]"""
    for h in beat.cfg.get("highlight") or []:
        rings = beat.world.rings(h["shape"]) if "shape" in h else beat.world.rings(h.get("regions", []))
        t0 = beat.start + float(h.get("from", 0)) - (beat.tin if h.get("during_flight", True) and "from" not in h else 0)
        a = clamp((t - t0) / 0.45) * (1 - clamp((t - beat.end + 0.1) / 0.35))
        draw_outline(fr, beat.world, rings, cam, beat.c(h.get("color", "accent2")), a, h.get("width", 3), 10 if h.get("glow", True) else 0)
