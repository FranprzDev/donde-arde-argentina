"""Generic drawing / kinetic-type / finishing helpers, copied from the author's previous entry
(../contar-con-datos-agua/v8/render_v8.py) so this entry has the same visual language. Code only, no imagery."""
import math, os, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H, FPS = 1920, 1080, 30
FONTS = "../fonts"
BG = (6, 6, 9)
# ---------------- helpers ----------------
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def eout(x): x = clamp(x); return 1 - (1 - x) ** 3
def eout5(x): x = clamp(x); return 1 - (1 - x) ** 5
def einout(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def einout5(x): x = clamp(x); return 16 * x ** 5 if x < .5 else 1 - (-2 * x + 2) ** 5 / 2
def prog(t, a, d): return eout((t - a) / d)
def lerp(a, b, k): return a + (b - a) * k
def mixc(a, b, k): return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))
def decay(t, t0, tau): return math.exp(-(t - t0) / tau) if t >= t0 else 0.0
_fc = {}
def font(kind, size, wt=None):
    k = (kind, size, wt)
    if k in _fc: return _fc[k]
    p = {"anton": "Anton.ttf", "inter": "Inter.ttf", "mono": "JetBrainsMono.ttf"}[kind]
    f = ImageFont.truetype(os.path.join(FONTS, p), size)
    try:
        if kind == "inter": f.set_variation_by_axes([min(32, max(14, size)), wt or 400])
        elif kind == "mono": f.set_variation_by_axes([wt or 400])
    except Exception: pass
    _fc[k] = f; return f
def tw(s, f): b = f.getbbox(s); return b[2] - b[0]

TX = 110          # the one text zone: left third

class Frame:
    def __init__(s, base=None):
        s.im = base if base is not None else Image.new("RGB", (W, H), BG)
        s.d = ImageDraw.Draw(s.im, "RGBA")
        s.g = Image.new("RGB", (W // 2, H // 2), (0, 0, 0)); s.gd = ImageDraw.Draw(s.g)
    def glow_line(s, pts, col, w): s.gd.line([(x / 2, y / 2) for x, y in pts], fill=col, width=max(1, int(w / 2)))

# ---------------- kinetic type ----------------
@functools.lru_cache(maxsize=256)
def text_layer(s, path, size, col):
    f = ImageFont.truetype(path, size)
    bb = f.getbbox(s, anchor="ls"); pad = 6
    lay = Image.new("RGBA", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), col + (0,))
    ImageDraw.Draw(lay).text((pad - bb[0], pad - bb[1]), s, font=f, fill=col + (255,), anchor="ls")
    return lay, bb[0] - pad, bb[1] - pad          # layer + offset of its top-left from the baseline-left anchor

def put_text(fr, xy, s, f, col, a=1.0, scale=1.0, glow=0.0, cache=True):
    """paste text anchored at its left baseline, scaled around its left-middle (so it slams towards the margin)"""
    if a <= 0.003: return
    lay, ox, oy = text_layer(s, f.path, f.size, col) if cache else text_layer.__wrapped__(s, f.path, f.size, col)
    w0, h0 = lay.size
    if abs(scale - 1) > 0.004:
        lay = lay.resize((max(1, int(w0 * scale)), max(1, int(h0 * scale))), Image.BILINEAR)
    cy = xy[1] + oy + h0 / 2                        # vertical middle of the unscaled text
    x0 = int(round(xy[0] + ox)); y0 = int(round(cy - lay.size[1] / 2))
    al = lay.getchannel("A")
    if a < 0.999: al = al.point(lambda v: int(v * a))
    fr.im.paste(lay.convert("RGB"), (x0, y0), al)
    if glow > 0:
        gl = lay.resize((max(1, lay.size[0] // 2), max(1, lay.size[1] // 2)), Image.BILINEAR)
        ga = gl.getchannel("A").point(lambda v: int(v * clamp(glow * a)))
        fr.g.paste(Image.new("RGB", gl.size, col), (x0 // 2, y0 // 2), ga)

def slam(fr, xy, s, f, col, t, t0, t1=None, glow=0.0, big=True, outd=0.3, cache=True):
    """kinetic text: slams in (scale 1.45 -> 1 with a hard ease, quick fade-in, glow flare), holds, fades out with a slight lift"""
    if t < t0: return 0
    u = t - t0
    if big: sc = 1 + 0.45 * (1 - eout5(u / 0.28)); a = clamp(u / 0.09)
    else:   sc = 1 + 0.12 * (1 - eout(u / 0.35)); a = clamp(u / 0.18)
    flare = 1 + 1.6 * decay(t, t0, 0.18) if big else 1
    if t1 is not None:
        o = clamp((t - t1) / outd); a *= 1 - o; sc *= 1 + 0.05 * o
    if a <= 0: return 0
    yy = xy[1] if big else xy[1] + (1 - eout(u / 0.35)) * 18
    put_text(fr, (xy[0], yy), s, f, col, a, sc, glow * flare if glow else (0.35 * (flare - 1) if big else 0), cache)
    return a

def count(t, t0, target, dur=0.9):
    """integer that counts up from 0 and lands exactly on target"""
    return int(round(target * eout((t - t0) / dur)))

# ---------------- finishing: bloom, flash, vignette, grain ----------------
def vignette():
    yy, xx = np.mgrid[0:H, 0:W]; r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    return np.clip(1 - 0.55 * np.clip(r - 0.45, 0, 1) ** 1.5, 0, 1)[..., None].astype(np.float32)
VIG = vignette()
_x = np.linspace(0, 1, W)
LSH = (1 - np.clip(1 - (_x / 0.54) ** 4, 0, 1) * 0.94)[None, :, None].astype(np.float32)   # dark text zone on the left
def left_shade(im, k=1.0):
    m = 1 - (1 - LSH) * k
    return Image.fromarray((np.asarray(im, np.float32) * m).astype(np.uint8))
_gr = np.random.default_rng(7)
GRAIN = [np.asarray(Image.fromarray(_gr.normal(128, 30, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                    np.float32)[..., None] - 128 for _ in range(6)]

def finish(fr, t, map_bloom=None, bloom_k=0.0, flash=0.0):
    g = fr.g.filter(ImageFilter.GaussianBlur(9)); g2 = fr.g.filter(ImageFilter.GaussianBlur(26))
    gg = np.asarray(g, np.float32) * 0.9 + np.asarray(g2, np.float32) * 0.8
    if map_bloom is not None and bloom_k > 0:
        gg = gg + map_bloom * bloom_k
    gg = np.asarray(Image.fromarray(np.clip(gg, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
    a = np.asarray(fr.im, np.float32)
    a = 255 - (255 - a) * (255 - gg) / 255                       # screen
    if flash > 0.002: a = a + (255 - a) * (0.55 * flash) * (0.35 + a / 400)
    a = a * VIG + GRAIN[int(t * FPS) % len(GRAIN)] * 0.11
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def map_bloom_of(im):
    """bright parts of the map, blurred at half resolution (bloom source)"""
    s = np.asarray(im.resize((W // 2, H // 2), Image.BILINEAR), np.float32)
    s = np.clip((s - 90) * 1.5, 0, 255).astype(np.uint8)
    b1 = Image.fromarray(s).filter(ImageFilter.GaussianBlur(6)); b2 = Image.fromarray(s).filter(ImageFilter.GaussianBlur(22))
    return np.asarray(b1, np.float32) * 0.6 + np.asarray(b2, np.float32) * 0.9

