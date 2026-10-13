"""globe_intro — Sun -> rays -> Earth -> region, then the flat map .

    - type: globe_intro
      target: all                 # region codes the sun rays land on ('all' = every region of map.regions)
      camera: home                # where the globe lands (default: map.home_camera)
      speed: 1.25                 # slow factor of the space travel
      title: ["SISMOS EN LA", "ARGENTINA"]     # hook, 1-2 lines (2nd line in accent), shown in the first second
      title_size: 132
      flat_text: "EL SOL SALE PARA TODOS."     # optional, while the rays keep landing on the flat map (heat wash)
      spark:                                   # optional turn: a single spark on the map + statement
        at: {first_point: events}              # or [lon, lat]
        lines:
          - {text: "TODO EMPIEZA ACÁ.", size: 116, color: accent}
          - {text: "{first_year}: EL PRIMER REGISTRO", size: 66}
        landing: 2.75                          # seconds from the spark to the end of the beat (next beat lands)
Rays: every streak from the Sun ends on a random point inside `target`."""
import math

import cv2
import numpy as np
from PIL import Image

from ..core import space as SP
from ..core.fx import Canvas, clamp, decay, einout, eout, lerp, put_text, screen, slam, slam_tight
from ..rules import TextBlock
from .base import Beat, register


@register
class GlobeIntro(Beat):
    type = "globe_intro"
    legend_default = False
    text_delay_default = 0.0

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.K = float(cfg.get("speed", 1.25))
        t = cfg.get("title") or []
        self.title_t = [t] if isinstance(t, str) else list(t)
        self.title_size = cfg.get("title_size", 132)
        self.flat_t = cfg.get("flat_text")
        self.flat_size = cfg.get("flat_size", 100)
        sp = cfg.get("spark") or None
        self.spark_cfg = sp
        self.spark_lines_t = [dict(l) for l in (sp.get("lines") or [])] if sp else []
        self.target = cfg.get("target", "all")
        self.n_rays = cfg.get("rays", {"globe": 70, "flat": 150})

    def text_templates(self):
        return self.title_t + ([self.flat_t] if self.flat_t else []) + [l["text"] for l in self.spark_lines_t]

    def resolve(self):
        T = self.story.tpl
        self.title = [T(x) for x in self.title_t]
        self.flat = T(self.flat_t) if self.flat_t else None
        self.spark_lines = [dict(l, text=T(l["text"])) for l in self.spark_lines_t]

    def plan(self, start, prev):
        K = self.K
        self.start = start
        spec = self.cfg.get("camera", "home")
        self.cam = self.world.camera(self.story.cfg["map"]["home_camera"] if spec in ("home", None) else spec)
        self.cam_from = None; self.tin = 0
        s = start
        self.T_X0 = s + 3.2 * K; self.T_MAP = s + 3.7 * K
        self.T_COOL = self.T_MAP + float(self.cfg.get("flat", 0.825))
        self.T_TXT1 = self.T_MAP - 0.175
        self.T_TXT1_END = self.T_TXT1 + max(self.need(self.flat) + 0.55, 0) if self.flat else self.T_TXT1
        self.hook = (s + 0.45, self.T_X0 - 0.15)
        self.blocks = []
        if self.title:
            self.blocks.append(TextBlock(self.title, *self.hook, self.id, sizes=[self.title_size] * len(self.title)))
        if self.flat:
            self.blocks.append(TextBlock([self.flat], self.T_TXT1, self.T_TXT1_END, self.id, sizes=[self.flat_size]))
        if self.spark_cfg:
            self.T_SPARK = self.T_COOL + 0.1
            lines = [l["text"] for l in self.spark_lines]
            self.T_TXT2_END = self.T_SPARK + 0.1 + self.need(*lines)
            self.end = self.T_SPARK + float(self.spark_cfg.get("landing", 2.75))
            if lines:
                self.blocks.append(TextBlock(lines, self.T_SPARK + 0.1, self.T_TXT2_END, self.id, sizes=[l.get("size", 66) for l in self.spark_lines]))
            self.ui_end = max(self.end, self.T_TXT2_END + 0.4)
        else:
            self.T_SPARK = None
            self.end = self.T_COOL + 0.5
            self.ui_end = max(self.end, self.T_TXT1_END + 0.4)
        if self.cfg.get("duration") not in (None, "auto"):
            self.end = start + float(self.cfg["duration"])
        self.dur = self.end - start
        self.text_t0 = self.hook[0]; self.text_t1 = self.hook[1]
        # rays
        codes = None if self.target in ("all", "*", None) else ([self.target] if isinstance(self.target, str) else list(self.target))
        self.pts = self.world.random_points_in(codes, 400, 3)
        self.outline = self.world.outline(codes)
        rr = np.random.default_rng(41)
        self.rays = []
        for k in range(self.n_rays.get("globe", 70)):
            self.rays.append((0.75 + k * 0.026 + rr.uniform(0, 0.02), 0, rr.uniform(-1, 1), rr.uniform(0.15, 0.95)))
        for k in range(self.n_rays.get("flat", 150)):
            self.rays.append((2.55 + k * 0.0185 + rr.uniform(0, 0.015), 1, int(rr.integers(0, len(self.pts))), rr.uniform(-0.45, 0.45)))
        L = np.array((-0.55, 0.28, 0.79)); self.LIGHT = tuple(L / np.linalg.norm(L))
        d = np.array((-self.LIGHT[0], self.LIGHT[1]), np.float32); self.D_IN = d / np.linalg.norm(d)
        self.R_FINAL = self.cam[2] * 180 / math.pi
        sp = self.spark_cfg
        if sp:
            at = sp.get("at")
            if isinstance(at, dict) and "first_point" in at:
                p = self.story.dataset(at["first_point"]); self.spark_ll = (float(p.lon[0]), float(p.lat[0]))
            else:
                self.spark_ll = (float(at[0]), float(at[1]))

    def camera_at(self, t):
        return self.cam

    def end_camera(self):
        return self.cam

    # ---------------- space ----------------
    def sun_state(self, t):
        S = self.story.H / 1080
        tau = (t - self.start) / self.K
        Rs = 900 * math.exp(-2.5 * tau); k = eout(tau / 1.3)
        return lerp(960, 330, k) * S, lerp(540, 250, k) * S, Rs * S, 1 - clamp((tau - 1.9) / 0.5)

    def globe_state(self, t):
        S = self.story.H / 1080
        tau = (t - self.start) / self.K
        if tau < 0.45:
            return None
        keys = [(0.45, 3), (1.5, 70), (2.35, 420), (3.0, 1050), (3.7, self.R_FINAL)]
        ts, vs = zip(*keys); Re = math.exp(float(np.interp(tau, ts, np.log(vs))))
        kr = einout((tau - 0.45) / 2.6)
        return self.cam[3] * S, self.cam[4] * S, Re * S, lerp(18.0, self.cam[0], kr), lerp(12.0, self.cam[1], kr), clamp((tau - 2.55) / 0.75)

    def heat_level(self, t):
        cool = self.T_COOL - self.start
        u = t - self.start
        return clamp((u - 2.9) / 1.6) * (1 - clamp((u - cool) / 0.5))

    def ray_layer(self, t, cam=None):
        R = self.story; W, H = R.W, R.H; S = H / 1080
        L = np.zeros((H, W), np.float32); Hh = np.zeros((H, W), np.float32)
        u0 = t - self.start
        if t > self.T_COOL + 0.4 or u0 < 0.7:
            return L, Hh
        sx, sy, Rs, sa = self.sun_state(t); g = self.globe_state(t)
        ray_a = 1 - clamp((t - self.T_COOL) / 0.35)
        TRAV, REFL = 0.32, 0.45
        lw = max(1, int(round(2 * S)))

        def seg(p, q, v):
            cv2.line(L, (int(p[0] * 4), int(p[1] * 4)), (int(q[0] * 4), int(q[1] * 4)), float(v), lw, cv2.LINE_AA, shift=2)
        for te, kind, p1, p2 in self.rays:
            u = (u0 - te) / TRAV
            if u < 0 or u > 1 + REFL / TRAV:
                continue
            if kind == 0:
                if g is None or g[2] < 6 * S or sa < 0.05:
                    continue
                cx, cy = g[0], g[1]
                lon, lat = self.pts[int(abs(p1) * (len(self.pts) - 1))]
                X, Y, x3, y3, z3 = SP.ortho(lon, lat, *g[:5])
                if z3 < 0.05:
                    continue
                hit = np.array((float(X), float(Y)))
                start = np.array((sx, sy)) + np.array((-(cy - sy), cx - sx)) / max(1.0, math.hypot(cx - sx, cy - sy)) * p1 * Rs * 0.35
                n3 = np.array((float(x3), float(y3), float(z3))) + np.array((p1 * 0.4, 0.3, 0.0)); n3 /= np.linalg.norm(n3)
                dd = hit - start; dd = dd / max(1e-3, np.linalg.norm(dd))
                d3 = np.array((dd[0], -dd[1], -0.25)); d3 /= np.linalg.norm(d3)
                r3 = d3 - 2 * np.dot(d3, n3) * n3; rr = np.array((r3[0], -r3[1])); rr /= max(1e-3, np.linalg.norm(rr))
                v = 0.9 * sa * p2 + 0.3
            else:
                if cam is None:
                    if g is None:
                        continue
                    lon, lat = self.pts[p1]; X, Y, x3, y3, z3 = SP.ortho(lon, lat, *g[:5])
                    if z3 < 0.1:
                        continue
                    hit = np.array((float(X), float(Y))); n3 = np.array((float(x3), float(y3), float(z3)))
                else:
                    lon, lat = self.pts[p1]; X, Y = self.world.proj(lon, lat, cam); hit = np.array((float(X), float(Y))); n3 = np.array((0.0, 0.0, 1.0))
                d3 = -np.array(self.LIGHT)
                n3 = n3 + np.array((p2 * 0.6, 0.35, 0.0)); n3 /= np.linalg.norm(n3)
                r3 = d3 - 2 * np.dot(d3, n3) * n3; rr = np.array((r3[0], -r3[1])); rr = rr / max(np.linalg.norm(rr), 1e-3)
                start = hit - self.D_IN * 1500 * S
                v = 0.85 * ray_a
            if v <= 0.01:
                continue
            if u <= 1:
                head = start + (hit - start) * u; tail = start + (hit - start) * max(0.0, u - 0.28)
                seg(tail, head, v * (0.55 + 0.45 * u))
            else:
                w = (u - 1) * TRAV / REFL
                tail = start + (hit - start) * min(1.0, 1 - 0.28 + 0.28 * eout(w * 1.6))
                if np.linalg.norm(hit - tail) > 1.5:
                    seg(tail, hit, v * (1 - 0.5 * w))
                ln = (260 if kind == 1 else 420) * S
                head = hit + rr * ln * eout(w); tail = hit + rr * ln * max(0.0, eout(w) - 0.35)
                seg(tail, head, v * 0.7 * (1 - w))
                cv2.circle(Hh, (int(hit[0]), int(hit[1])), int((4 + 26 * eout(w)) * S), float(v * (1 - w) * 0.9), lw, cv2.LINE_AA)
                cv2.circle(Hh, (int(hit[0]), int(hit[1])), max(1, int(3 * S)), float(v * 2.2 * (1 - w)), -1, cv2.LINE_AA)
        return L, Hh

    def light_rgb(self, L, Hh):
        H, W = L.shape; S = H / 1080
        core = L + Hh
        gl = cv2.resize(cv2.GaussianBlur(cv2.resize(core, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), 6 * S), (W, H))
        return core[..., None] * np.array((255, 236, 190), np.float32) * 1.1 + gl[..., None] * np.array((255, 170, 70), np.float32) * 2.2

    def space_frame(self, t):
        st = self.story; W, H = st.W, st.H; th = self.theme
        tau = (t - self.start) / self.K
        A = np.zeros((H, W, 3), np.float32) + np.array(th.c["bg"], np.float32)
        zk = [(0, 0.6), (1.0, 1.4), (2.0, 2.6), (3.4, 4.5)]
        ts, vs = zip(*zk)
        zf = lambda x: math.exp(float(np.interp(x, ts, np.log(vs))))
        zoom = zf(tau); vel = zoom - zf(max(0, tau - 0.08))
        SP.draw_stars(A, zoom, vel * 2.5, 0.9 * (1 - clamp((tau - 2.6) / 0.6)))
        sx, sy, Rs, sa = self.sun_state(t)
        SP.draw_sun(A, sx, sy, Rs, tau, sa)
        g = self.globe_state(t)
        if g is not None:
            SP.draw_globe(A, g[0], g[1], g[2], g[3], g[4], self.LIGHT, g[5], clamp((tau - 0.45) / 0.15), th.c["bg"], th.c["land"])
            hk = self.heat_level(t) * (1 - g[5] * 0.3)
            if hk > 0.01 and g[2] > 200 * st.H / 1080:
                X, Y, _, _, z3 = SP.ortho(self.pts[:, 0], self.pts[:, 1], *g[:5])
                Hm = np.zeros((H // 4, W // 4), np.float32); ok = z3 > 0.05
                for xx, yy in zip(X[ok] / 4, Y[ok] / 4):
                    if 0 <= xx < W // 4 and 0 <= yy < H // 4:
                        Hm[int(yy), int(xx)] += 1
                Hm = cv2.resize(cv2.GaussianBlur(Hm, (0, 0), max(2.0, g[2] / 160)), (W, H)); Hm /= max(1e-6, Hm.max())
                A = A + Hm[..., None] * np.array((120, 50, 10), np.float32) * hk
        L, Hh = self.ray_layer(t, None)
        return A + self.light_rgb(L, Hh)

    def full_frame(self, t, R):
        if t < self.T_X0:
            fr = Canvas(R.W, R.H, self.theme, Image.fromarray(np.clip(self.space_frame(t), 0, 255).astype(np.uint8)))
            self.draw_hook(fr, t)
            return fr
        return None

    # ---------------- flat map phase ----------------
    def heat_wash(self, A, t, cam):
        hk = self.heat_level(t)
        if hk <= 0.01:
            return A
        H, W = A.shape[:2]
        m = self.world.mask(self.outline, cam, W, H, blur=3)
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        shimmer = 0.85 + 0.15 * np.sin(yy * 60 + t * 9)
        return A + (m * shimmer)[..., None] * np.array((95, 38, 8), np.float32) * hk

    def draw_spark(self, A, t, cam):
        if self.T_SPARK is None or not (self.T_SPARK - 0.05 <= t < self.end + 0.6):
            return A
        H, W = A.shape[:2]; S = H / 1080
        x, y = self.world.proj(*self.spark_ll, cam); u = t - self.T_SPARK
        flick = 0.8 + 0.2 * math.sin(u * 37) * math.sin(u * 23 + 1)
        grow = eout(u / 0.25) * (1 - clamp((t - self.end - 0.1) / 0.5))
        burst = decay(t, self.T_SPARK, 0.12)
        L = np.zeros((H // 2, W // 2), np.float32)
        cv2.circle(L, (int(x / 2), int(y / 2)), max(1, int(3 * S)), 1.0, -1, cv2.LINE_AA)
        g1 = cv2.GaussianBlur(L, (0, 0), 4 * S) * 60; g2 = cv2.GaussianBlur(L, (0, 0), 22 * S) * 420
        G = cv2.resize(g1 * (0.6 + 1.5 * burst) + g2 * (0.35 + 0.9 * burst), (W, H)) * grow * flick
        rg = np.random.default_rng(9); E = np.zeros((H, W), np.float32)
        for k in range(30):
            t0 = self.T_SPARK + rg.uniform(0, 2.7); vx, vy = rg.uniform(-30, 30) * S, rg.uniform(-110, -50) * S
            uu = t - t0
            if 0 <= uu < 0.9:
                cv2.circle(E, (int(x + vx * uu + 6 * S * math.sin(uu * 9 + k)), int(y + vy * uu)), max(1, int(2 * S)), float(1.2 * (1 - uu / 0.9)), -1, cv2.LINE_AA)
        E = E + cv2.GaussianBlur(E, (0, 0), 3 * S) * 2.5
        col = G[..., None] * np.array((255, 150, 50), np.float32) + E[..., None] * np.array((255, 190, 90), np.float32) * grow
        core = np.zeros((H, W), np.float32); cv2.circle(core, (int(x), int(y)), max(1, int(6 * S)), 1.0, -1, cv2.LINE_AA)
        col = col + core[..., None] * np.array((255, 250, 230), np.float32) * grow
        return screen(A, col)

    def draw_map(self, A, t, cam, R):
        A = self.heat_wash(A, t, cam)
        L, Hh = self.ray_layer(t, cam)
        A = A + self.light_rgb(L, Hh)
        A = self.draw_spark(A, t, cam)
        if t < self.T_MAP:
            kx = einout((t - self.T_X0) / (self.T_MAP - self.T_X0))
            A = self.space_frame(t) * (1 - kx) + A * kx
        return A

    def shade(self, t):
        return 0.92 * clamp((t - self.T_X0 - 0.2) / 0.5)

    def draw_hook(self, fr, t):
        h0, h1 = self.hook
        if not self.title or not (h0 <= t < h1 + 0.4):
            return
        f = self.theme.font("display", self.title_size)
        y = self.cfg.get("title_y", 820)
        cols = [self.theme.c["text"], self.theme.c["accent"]]
        for i, line in enumerate(self.title):
            slam(fr, (110, y + i * (self.title_size + 10)), line, f, cols[min(i, 1)] if len(self.title) > 1 else cols[1], t, h0 + 0.12 * i, h1, glow=0.25 if i == 0 else 0.6)

    def draw_ui(self, fr, t, cam, R):
        if t >= self.T_X0:
            self.draw_hook(fr, t)
        th = self.theme
        if self.flat and self.T_TXT1 <= t < self.T_TXT1_END + 0.4:
            slam(fr, (110, self.cfg.get("flat_y", 420)), self.flat, th.font("display", self.flat_size), th.c["text"], t, self.T_TXT1, self.T_TXT1_END, big=False)
        if self.T_SPARK is not None and self.T_SPARK <= t < self.T_TXT2_END + 0.4:
            y = self.cfg.get("spark_y", 590)
            for i, l in enumerate(self.spark_lines):
                size = l.get("size", 66); col = self.c(l.get("color", "text"))
                t0 = self.T_SPARK + 0.1 + float(l.get("delay", 0.4 * i))
                if i == 0:
                    slam_tight(fr, (110, y), l["text"], th.font("display", size), col, t, t0, self.T_TXT2_END, glow=0.55)
                else:
                    slam(fr, (110, y + 100 * i), l["text"], th.font("display", size), col, t, t0, self.T_TXT2_END, big=False)

    def reveals(self):
        return [self.T_SPARK] if self.T_SPARK else []

    def cues(self):
        c = [(self.start, "space", 1.0), (self.hook[0], "hook", 0.6), (self.T_MAP, "land_map", 0.5), (self.T_COOL, "cool", 0.5)]
        for te, kind, p1, p2 in self.rays:
            x = self.start + te + 0.32
            if x <= self.T_COOL + 0.2:
                c.append((x, "glint", 0.1 if kind else 0.16))
        if self.T_SPARK:
            c += [(self.T_SPARK, "spark", 1.0), (self.end, "landing", 1.0)]
        return c

    def activity(self, t):
        return 0.15 if self.T_SPARK and self.T_SPARK <= t < self.end else 0.0
