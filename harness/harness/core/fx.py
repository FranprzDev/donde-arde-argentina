"""Drawing, kinetic type and finishing (bloom, flash, vignette, grain).

Everything is laid out in DESIGN UNITS: a 1920x1080 canvas.
`Canvas.S` scales design units to the real output resolution, so a story can render a fast 640x360 preview or the
1080p master with the same numbers. Font sizes are design units too, and `Theme.font()` refuses any size below the
story's `rules.min_font_px` (that is how the minimum text size is enforced in code, not by convention)."""
import functools
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..errors import ReadabilityError

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
DESIGN_W, DESIGN_H = 1920, 1080


# ---------------- easing / helpers ----------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def eout(x):
    x = clamp(x); return 1 - (1 - x) ** 3


def eout5(x):
    x = clamp(x); return 1 - (1 - x) ** 5


def einout(x):
    x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, k):
    return a + (b - a) * k


def mixc(a, b, k):
    return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))


def decay(t, t0, tau):
    return math.exp(-(t - t0) / tau) if t >= t0 else 0.0


def count(t, t0, target, dur=0.9):
    """integer that counts up from 0 and lands exactly on target"""
    return int(round(target * eout((t - t0) / dur)))


def hexrgb(c):
    if isinstance(c, (list, tuple)):
        return tuple(int(v) for v in c[:3])
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def make_lut(stops):
    """stops: [(pos 0..1, color), ...] -> (256, 3) float32 colour ramp"""
    x = np.linspace(0, 1, 256); out = np.zeros((256, 3), np.float32)
    ps = [float(s[0]) for s in stops]; cs = [hexrgb(s[1]) for s in stops]
    for ch in range(3):
        out[:, ch] = np.interp(x, ps, [c[ch] for c in cs])
    return out


# ---------------- theme ----------------
DEFAULT_PALETTE = dict(bg="#060609", text="#F2F0EC", muted="#BEB6AC", accent="#FF6E1E", accent2="#FFB03C",
                       hot="#FFE2A0", red="#FF4028", ash="#968E86", land="#141316", neighbour="#0D0D11",
                       border="#3E3C40", cool="#5AA0FF")
DEFAULT_LUT = [(0.0, "#000000"), (0.18, "#5A0C04"), (0.42, "#D7380A"), (0.68, "#FF9622"), (0.88, "#FFD66E"), (1.0, "#FFFAE1")]
DEFAULT_FONTS = dict(display="Anton.ttf", body="Inter.ttf", mono="JetBrainsMono.ttf")


class Theme:
    def __init__(self, palette=None, fonts=None, lut=None, min_font_px=48, story_dir=None):
        p = dict(DEFAULT_PALETTE); p.update(palette or {})
        self.hex = p
        self.c = {k: hexrgb(v) for k, v in p.items()}
        self.lut = make_lut(lut or DEFAULT_LUT)
        f = dict(DEFAULT_FONTS); f.update(fonts or {})
        self.font_paths = {}
        for k, v in f.items():
            cands = [v, os.path.join(story_dir or "", v), os.path.join(ASSETS, "fonts", v)]
            path = next((c for c in cands if c and os.path.isfile(c)), None)
            if path is None:
                raise FileNotFoundError(f"font '{v}' for '{k}' not found (looked in the story folder and harness/assets/fonts)")
            self.font_paths[k] = path
        self.min_font_px = float(min_font_px)
        self.S = 1.0
        self._fc = {}
        self.sizes_used = set()

    def font(self, kind, size, wt=None):
        """size in design units. Raises ReadabilityError below rules.min_font_px."""
        if size < self.min_font_px - 1e-6:
            raise ReadabilityError(f"font '{kind}' at {size}px is below the minimum text size of {self.min_font_px:g}px "
                                   f"(design units at 1080p). Make the text bigger or shorter.")
        self.sizes_used.add((kind, size))
        k = (kind, size, wt, self.S)
        if k in self._fc:
            return self._fc[k]
        f = ImageFont.truetype(self.font_paths[kind], max(6, int(round(size * self.S))))
        try:
            axes = f.get_variation_axes()
            if len(axes) == 2:
                f.set_variation_by_axes([min(32, max(14, size)), wt or 400])
            elif len(axes) == 1:
                f.set_variation_by_axes([wt or 400])
        except Exception:
            pass
        f.design_size = size
        self._fc[k] = f
        return f


def tw(s, f):
    """text width in REAL pixels"""
    b = f.getbbox(s); return b[2] - b[0]


# ---------------- canvas ----------------
class Canvas:
    """One frame being composed. `im` is the RGB image (real pixels), `d` an RGBA drawer on it, `g` a half-res glow
    buffer that `finish()` blurs and screens on top."""

    def __init__(self, W, H, theme, base=None):
        self.W, self.H, self.S, self.theme = W, H, H / DESIGN_H, theme
        self.im = base if base is not None else Image.new("RGB", (W, H), theme.c["bg"])
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.g = Image.new("RGB", (W // 2, H // 2), (0, 0, 0)); self.gd = ImageDraw.Draw(self.g)

    def p(self, v):
        return v * self.S

    def glow_line(self, pts, col, w):
        self.gd.line([(x / 2, y / 2) for x, y in pts], fill=col, width=max(1, int(w * self.S / 2)))

    def tw(self, s, f):
        """text width in DESIGN units"""
        return tw(s, f) / self.S


_LAYERS = {}


def _text_layer_obj(s, fid, f, col):
    k = (s, fid, col)
    v = _LAYERS.get(k)
    if v is not None:
        return v
    bb = f.getbbox(s, anchor="ls"); pad = 6
    lay = Image.new("RGBA", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), col + (0,))
    ImageDraw.Draw(lay).text((pad - bb[0], pad - bb[1]), s, font=f, fill=col + (255,), anchor="ls")
    v = (lay, bb[0] - pad, bb[1] - pad)
    if len(_LAYERS) > 2000:
        _LAYERS.clear()
    _LAYERS[k] = v
    return v


def put_text(fr, xy, s, f, col, a=1.0, scale=1.0, glow=0.0):
    """paste text anchored at its left baseline (xy in design units), scaled around its left-middle"""
    if a <= 0.003 or not s:
        return
    lay, ox, oy = _text_layer_obj(s, id(f), f, tuple(col))
    w0, h0 = lay.size
    if abs(scale - 1) > 0.004:
        lay = lay.resize((max(1, int(w0 * scale)), max(1, int(h0 * scale))), Image.BILINEAR)
    X, Y = xy[0] * fr.S, xy[1] * fr.S
    cy = Y + oy + h0 / 2
    x0 = int(round(X + ox)); y0 = int(round(cy - lay.size[1] / 2))
    al = lay.getchannel("A")
    if a < 0.999:
        al = al.point(lambda v: int(v * a))
    fr.im.paste(lay.convert("RGB"), (x0, y0), al)
    if glow > 0:
        gl = lay.resize((max(1, lay.size[0] // 2), max(1, lay.size[1] // 2)), Image.BILINEAR)
        ga = gl.getchannel("A").point(lambda v: int(v * clamp(glow * a)))
        fr.g.paste(Image.new("RGB", gl.size, tuple(col)), (x0 // 2, y0 // 2), ga)


def outlined_text(fr, xy, s, f, col, a=1.0, halo=(10, 8, 8), r=2):
    for ox, oy in ((-r, 0), (r, 0), (0, -r), (0, r), (-r, -r), (r, r), (-r, r), (r, -r)):
        put_text(fr, (xy[0] + ox, xy[1] + oy), s, f, halo, a)
    put_text(fr, xy, s, f, col, a)


def slam(fr, xy, s, f, col, t, t0, t1=None, glow=0.0, big=True, outd=0.3):
    """kinetic text: slams in (scale 1.45 -> 1, hard ease, glow flare), holds, fades out with a slight lift"""
    if t < t0:
        return 0
    u = t - t0
    if big:
        sc = 1 + 0.45 * (1 - eout5(u / 0.28)); a = clamp(u / 0.09)
    else:
        sc = 1 + 0.12 * (1 - eout(u / 0.35)); a = clamp(u / 0.18)
    flare = 1 + 1.6 * decay(t, t0, 0.18) if big else 1
    if t1 is not None:
        o = clamp((t - t1) / outd); a *= 1 - o; sc *= 1 + 0.05 * o
    if a <= 0:
        return 0
    yy = xy[1] if big else xy[1] + (1 - eout(u / 0.35)) * 18
    put_text(fr, (xy[0], yy), s, f, col, a, sc, glow * flare if glow else (0.35 * (flare - 1) if big else 0))
    return a


def slam_tight(fr, xy, s, f, col, t, t0, t1, glow=0.0, over=0.08):
    """like slam() but with a small overshoot: for long statement lines that would clip at 1.45x"""
    if t < t0:
        return
    u = t - t0; sc = 1 + over * (1 - eout5(u / 0.28)); a = clamp(u / 0.09); flare = 1 + 1.6 * decay(t, t0, 0.18)
    o = clamp((t - t1) / 0.3); a *= 1 - o; sc *= 1 + 0.03 * o
    if a > 0:
        put_text(fr, xy, s, f, col, a, sc, glow * flare)


# ---------------- finishing ----------------
@functools.lru_cache(maxsize=8)
def _finish_assets(W, H, text_zone):
    yy, xx = np.mgrid[0:H, 0:W]; r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    vig = np.clip(1 - 0.55 * np.clip(r - 0.45, 0, 1) ** 1.5, 0, 1)[..., None].astype(np.float32)
    x = np.linspace(0, 1, W)
    lsh = (1 - np.clip(1 - (x / text_zone) ** 4, 0, 1) * 0.94)[None, :, None].astype(np.float32)
    gr = np.random.default_rng(7)
    grain = [np.asarray(Image.fromarray(gr.normal(128, 30, (max(1, H // 2), max(1, W // 2))).clip(0, 255).astype(np.uint8))
                        .resize((W, H), Image.BICUBIC), np.float32)[..., None] - 128 for _ in range(6)]
    return vig, lsh, grain


def left_shade(A, k=1.0, text_zone=0.54):
    """darken the left text zone of float image A (H, W, 3)"""
    H, W = A.shape[:2]
    _, lsh, _ = _finish_assets(W, H, text_zone)
    return A * (1 - (1 - lsh) * k)


def finish(fr, t, fps, flash=0.0, grain=0.11):
    W, H = fr.W, fr.H
    vig, _, gr = _finish_assets(W, H, 0.54)
    g = fr.g.filter(ImageFilter.GaussianBlur(9 * fr.S)); g2 = fr.g.filter(ImageFilter.GaussianBlur(26 * fr.S))
    gg = np.asarray(g, np.float32) * 0.9 + np.asarray(g2, np.float32) * 0.8
    gg = np.asarray(Image.fromarray(np.clip(gg, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
    a = np.asarray(fr.im, np.float32)
    a = 255 - (255 - a) * (255 - gg) / 255
    if flash > 0.002:
        a = a + (255 - a) * (0.55 * flash) * (0.35 + a / 400)
    a = a * vig + gr[int(t * fps) % len(gr)] * grain
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def screen(A, F):
    """screen-blend light layer F onto float image A"""
    return 255 - (255 - A) * (255 - np.clip(F, 0, 255)) / 255
