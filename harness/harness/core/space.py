"""Sun, Earth and stars drawn with code only (numpy / PIL / OpenCV). No photos, no AI imagery.

Sun: limb-darkened disc + granulation noise + corona. Earth:
orthographic globe sampled from an equirectangular land mask rasterised from Natural Earth 1:50m land (public domain,
bundled in harness/assets). All functions draw into a float image A of shape (H, W, 3) in REAL pixels."""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .fx import ASSETS

NE = os.path.join(ASSETS, "ne_50m_land.geojson")
TEXW, TEXH = 8192, 4096
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "data-video-harness")
_LAND = None


def land_tex():
    global _LAND
    if _LAND is not None:
        return _LAND
    p = os.path.join(CACHE, "land_tex_8192.png")
    if os.path.exists(p):
        _LAND = cv2.imread(p, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
        return _LAND
    g = json.load(open(NE)); im = Image.new("L", (TEXW, TEXH), 0); d = ImageDraw.Draw(im)

    def px(r):
        return [((x + 180) / 360 * TEXW, (90 - y) / 180 * TEXH) for x, y in r]
    for f in g["features"]:
        geo = f["geometry"]; polys = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
        for poly in polys:
            d.polygon(px(poly[0]), fill=255)
            for hole in poly[1:]:
                d.polygon(px(hole), fill=0)
    os.makedirs(CACHE, exist_ok=True); im.save(p)
    _LAND = np.asarray(im, np.float32) / 255
    return _LAND


def _noise(n, seed, octaves):
    r = np.random.default_rng(seed); out = np.zeros((n, n), np.float32)
    for cells, amp in octaves:
        g = r.standard_normal((cells, cells)).astype(np.float32)
        out += cv2.resize(g, (n, n), interpolation=cv2.INTER_CUBIC) * amp
    out -= out.mean(); return out / out.std()


SUN_N = cv2.GaussianBlur(_noise(1024, 11, ((6, 0.5), (24, 0.7), (70, 1.0), (160, 0.8))), (0, 0), 2.2); SUN_N /= SUN_N.std()
COR_N = _noise(512, 12, ((5, 1.0), (12, 0.6)))


def _sunlut():
    st = [(0.0, (60, 8, 0)), (0.35, (190, 50, 6)), (0.6, (255, 128, 20)), (0.82, (255, 200, 90)), (1.0, (255, 246, 214))]
    x = np.linspace(0, 1, 256); o = np.zeros((256, 3), np.float32)
    for c in range(3):
        o[:, c] = np.interp(x, [s[0] for s in st], [s[1][c] for s in st])
    return o


SLUT = _sunlut()


def draw_sun(A, cx, cy, R, t, a=1.0):
    """additive sun on float image A"""
    H, W = A.shape[:2]
    if a <= 0.003 or R < 0.5:
        return
    ext = R * 2.6 + 30
    x0, x1 = int(max(0, cx - ext)), int(min(W, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(H, cy + ext))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    dx, dy = (xx - cx) / R, (yy - cy) / R; r = np.sqrt(dx * dx + dy * dy)
    inside = r < 1
    z = np.sqrt(np.clip(1 - r * r, 0, 1))
    u = (np.arcsin(np.clip(dx, -1, 1)) / math.pi + 0.5 + 0.004 * t) * 1023
    v = (np.arcsin(np.clip(dy, -1, 1)) / math.pi + 0.5) * 1023
    gran = cv2.remap(SUN_N, u.astype(np.float32), v.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    limb = 1 - 0.62 * (1 - z) - 0.18 * (1 - z) ** 2
    detail = min(1.0, R / 120)
    I = np.clip(limb * (0.86 + 0.13 * gran * detail), 0, 1)
    col = SLUT[np.clip(I * 255, 0, 255).astype(np.uint8)] * inside[..., None]
    ang = (np.arctan2(dy, dx) / (2 * math.pi) + 0.5) * 511
    st = cv2.remap(COR_N, ang.astype(np.float32), np.full_like(ang, 256 + 40 * math.sin(t)), cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    d = np.clip(r - 1, 0, None)
    cor = np.exp(-d * 3.2) * (0.75 + 0.35 * st) * (r >= 0.98) + 0.6 * np.exp(-d * 9)
    cor = cor[..., None] * np.array((255, 150, 50), np.float32) * 0.85
    A[y0:y1, x0:x1] += a * (col + cor * (1 - inside[..., None] * 0.7))


def draw_globe(A, cx, cy, R, lon0, lat0, light, flat=0.0, a=1.0, bg=(6, 6, 9), land_flat=(18, 17, 20)):
    """orthographic Earth composited onto A. light: camera-space unit vector. flat in [0,1] converges the colours to
    the flat data map (ocean = background, dark land, uniform light) so the globe can crossfade into the map."""
    H, W = A.shape[:2]
    LAND = land_tex()
    ext = R * 1.12 + 6
    x0, x1 = int(max(0, cx - ext)), int(min(W, cx + ext)); y0, y1 = int(max(0, cy - ext)), int(min(H, cy + ext))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    x, y = (xx - cx) / R, -(yy - cy) / R; rho2 = x * x + y * y; r = np.sqrt(rho2)
    inside = rho2 < 1; z = np.sqrt(np.clip(1 - rho2, 0, 1))
    p0 = math.radians(lat0)
    lat = np.degrees(np.arcsin(np.clip(z * math.sin(p0) + y * math.cos(p0), -1, 1)))
    lon = lon0 + np.degrees(np.arctan2(x, z * math.cos(p0) - y * math.sin(p0)))
    lon = (lon + 180) % 360 - 180
    mu = ((lon + 180) / 360 * TEXW).astype(np.float32); mv = ((90 - lat) / 180 * TEXH).astype(np.float32)
    land = cv2.remap(LAND, mu, mv, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    lx, ly, lz = light
    diff = np.clip(x * lx + y * ly + z * lz, 0, 1)
    lit = (0.06 + 0.94 * diff ** 0.8) * (1 - flat) + flat * 1.0
    spec = np.clip(x * lx + y * ly + z * lz, 0, 1) ** 90 * (1 - land) * 0.18 * (1 - flat)
    ocean = np.array((14, 34, 66), np.float32) * (1 - flat) + np.array(bg, np.float32) * flat
    landc = np.array((96, 88, 70), np.float32) * (1 - flat) + np.array(land_flat, np.float32) * flat
    col = (ocean + (landc - ocean) * land[..., None]) * lit[..., None] + spec[..., None] * np.array((200, 220, 255), np.float32)
    sd = np.clip((x * lx + y * ly) / np.maximum(r, 1e-3) * 0.5 + 0.6, 0.15, 1.1)
    rim_in = (r ** 6) * inside * sd
    rim_out = np.exp(-np.clip(r - 1, 0, None) * R / max(6.0, R * 0.035)) * (~inside) * sd
    atm = (rim_in * 0.8 + rim_out * 0.9)[..., None] * np.array((70, 140, 255), np.float32) * (1 - flat)
    aa = np.clip((1 - r) * R + 0.5, 0, 1)[..., None] * a
    sub = A[y0:y1, x0:x1]
    sub[:] = sub * (1 - aa) + col * aa + atm * a


_sr = np.random.default_rng(5)
STARS = np.c_[_sr.uniform(-1.2, 1.2, 1400), _sr.uniform(-1.2, 1.2, 1400), _sr.uniform(0.15, 1.0, 1400) ** 2.2]


def draw_stars(A, zoom, vel, a=1.0):
    """stars spread from the centre as `zoom` grows (camera travelling forward); vel -> streak length"""
    H, W = A.shape[:2]
    if a <= 0.003:
        return
    S = np.zeros((H, W), np.float32)
    cx, cy = W / 2, H / 2
    for sx, sy, b in STARS:
        k = zoom * (0.6 + b)
        x, y = cx + sx * W * 0.5 * k, cy + sy * W * 0.5 * k
        if not (-50 < x < W + 50 and -50 < y < H + 50):
            continue
        x2, y2 = cx + sx * W * 0.5 * (k - vel * (0.6 + b)), cy + sy * W * 0.5 * (k - vel * (0.6 + b))
        cv2.line(S, (int(x2), int(y2)), (int(x), int(y)), float(b) * (0.5 if vel > 0.01 else 1.0), 1, cv2.LINE_AA)
    S = S + cv2.GaussianBlur(S, (0, 0), 1.2) * 0.8
    A += (S[..., None] * np.array((215, 225, 255), np.float32) * a)


def ortho(lon, lat, cx, cy, R, lon0, lat0):
    p, l = np.radians(lat), np.radians(np.asarray(lon) - lon0); p0 = math.radians(lat0)
    x = np.cos(p) * np.sin(l); y = math.cos(p0) * np.sin(p) - math.sin(p0) * np.cos(p) * np.cos(l)
    z = math.sin(p0) * np.sin(p) + math.cos(p0) * np.cos(p) * np.cos(l)
    return cx + R * x, cy - R * y, x, y, z
