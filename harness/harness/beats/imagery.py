"""Beats with georeferenced imagery (e.g. Copernicus Sentinel-2 crops from harness.data.sentinel2).

satellite_zoom — the camera dives from the current map view INTO a real satellite image placed at its true bbox,
holds with a label (and optional same-day points / pins), then zooms back out:

    - type: satellite_zoom
      image: s2_city                     # data entry of kind image (jpg + sidecar json with bbox/date)
      labels: ["VALLE X", "{s2_city_date} · Sentinel-2"]
      points: day_points                 # optional points dataset drawn as glowing dots once the image fills the frame
      pins: [{lon: -65.41, lat: -24.79, label: "CIUDAD"}]
      zoom: 1.0                          # seconds of the dive
      zoom_out: 0.45                     # seconds of the way back (to the camera it came from)
      announce: 3.5                      # the image frame appears in place this many seconds before the beat (0 = off)
      fill_px: 900                       # image height on screen once zoomed (design px)

before_after — images of the same bbox replaced by a left-to-right wipe, with optional raster overlays and a
big-number card (same keys as big_number: head, number, count_to, unit, subline, flags):

    - type: before_after
      camera: {center: [-65.4, -24.8], zoom: 760, anchor: [1400, 560]}
      images: [img_before, img_mid, img_after]
      labels: ["ENE 2023", "ENE 2024", "ENE 2025"]        # one per image (labels: not counted as prose, keep short)
      wipes: [0.7, 1.85]                                   # seconds after the card starts
      overlays: [{data: change_a, color: accent2, at: 1.15, label: "■ A"}, {data: change_b, color: red, at: 2.3, label: "■ B"}]
      head: ..., number: ..., unit: ..., subline: ..."""
import cv2
import numpy as np

from ..core.fx import clamp, eout, mixc, outlined_text, put_text, screen
from ..core.geo import GeoImage
from ..rules import TextBlock
from .base import Beat, Card, register
from .cards import MapBeat


@register
class SatelliteZoom(Beat):
    type = "satellite_zoom"
    legend_default = False

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.labels_t = list(cfg.get("labels") or [])
        self.pins = cfg.get("pins") or []
        self.zoom = float(cfg.get("zoom", 1.0)); self.zout = float(cfg.get("zoom_out", 0.45))
        self.announce = float(cfg.get("announce", 3.5))

    def text_templates(self):
        return self.labels_t + [p.get("label", "") for p in self.pins]

    def resolve(self):
        self.labels = [self.story.tpl(x) for x in self.labels_t]
        self.pin_labels = [self.story.tpl(p.get("label", "")) for p in self.pins]

    def plan(self, start, prev):
        self.img = self.story.dataset(self.cfg["image"])
        if not isinstance(self.img, GeoImage):
            raise ValueError(f"beat '{self.id}': image '{self.cfg['image']}' must be a data entry of kind image")
        self.start = start
        self.cam_from = prev.end_camera() if prev is not None else self.world.camera(self.story.cfg["map"]["home_camera"])
        self.cam = self.img.camera(self.world, self.cfg.get("fill_px", 900), tuple(self.cfg.get("anchor", (1390, 540))))
        self.tin = self.zoom
        need = self.need(*self.labels, *[l for l in self.pin_labels if l])
        hold = float(self.cfg.get("hold", need)) if self.cfg.get("hold") not in (None, "auto") else need
        self.z1 = start + self.zoom; self.z2 = self.z1 + hold
        self.end = self.z2 + self.zout; self.dur = self.end - start
        self.text_t0, self.text_t1 = self.z1, self.z2
        self.ui_end = self.end
        self.blocks = [TextBlock(self.labels + [l for l in self.pin_labels if l], self.z1, self.z2, self.id,
                                 sizes=[52, 52] + [48] * len([l for l in self.pin_labels if l]))]
        self.hs = None
        if self.cfg.get("points"):
            p = self.story.dataset(self.cfg["points"]); self.hs = (p.lon, p.lat)

    def end_camera(self):
        return self.cam_from

    def camera_at(self, t):
        if t < self.z1:
            return self.world.cam_zoomto(self.cam_from, self.cam, (t - self.start) / self.zoom)
        if t < self.z2:
            return self.cam
        return self.world.cam_zoomto(self.cam, self.cam_from, (t - self.z2) / max(1e-3, self.zout))

    def vis(self, t):
        a0 = self.start - self.announce if self.announce > 0 else self.start
        return clamp((t - a0) / 0.4) * (1 - clamp((t - self.end - 0.2) / 0.4))

    def _draw_img(self, A, t, cam, R):
        w2 = self.vis(t)
        if w2 <= 0.003:
            return A
        im, m = self.img.layer(R.world, cam, R.W, R.H)
        A = A * (1 - m * w2) + im * m * w2
        if self.hs is not None:
            k = clamp((t - self.z1 - 0.2) / 0.5) * (1 - clamp((t - self.z2) / 0.4))
            if k > 0.003:
                x, y = R.world.proj(self.hs[0], self.hs[1], cam); L = np.zeros((R.H, R.W), np.float32)
                for j, (xx, yy) in enumerate(zip(x, y)):
                    kk = clamp((t - self.z1 - 0.2 - 0.025 * j) / 0.2) * k
                    if kk > 0:
                        cv2.circle(L, (int(xx), int(yy)), max(1, int(7 * R.S)), float(kk), -1, cv2.LINE_AA)
                Lb = cv2.GaussianBlur(L, (0, 0), 6 * R.S) * 1.6
                A = screen(A, L[..., None] * np.array((255, 236, 170), np.float32) + Lb[..., None] * np.array(self.theme.c["accent"], np.float32))
        return A

    def draw_pre(self, A, t, cam, R):
        return self._draw_img(A, t, cam, R) if self.announce > 0 and t >= self.start - self.announce else A

    def draw_post(self, A, t, cam, R):
        return self._draw_img(A, t, cam, R)

    def draw_map(self, A, t, cam, R):
        return self._draw_img(A, t, cam, R)

    def frame_ui(self, fr, t, cam):
        w2 = self.vis(t)
        if w2 <= 0.003:
            return
        th = self.theme; x0, y0, x1, y1 = self.img.corners(self.world, cam); s = fr.S
        before = t < self.z1
        if before:
            fr.d.rectangle((x0 - 3 * s, y0 - 3 * s, x1 + 3 * s, y1 + 3 * s), outline=(8, 6, 6, int(200 * w2)), width=max(1, int(3 * s)))
        fr.d.rectangle((x0, y0, x1, y1), outline=(th.c["hot"] if before else th.c["text"]) + (int(240 * w2),), width=max(1, int((3 if before else 2) * s)))
        if before:
            fr.glow_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], mixc((0, 0, 0), th.c["accent2"], w2), 10)

    def draw_ui(self, fr, t, cam, R):
        self.frame_ui(fr, t, cam)
        la = clamp((t - self.z1 + 0.15) / 0.25) * (1 - clamp((t - self.z2 + 0.05) / 0.25))
        if la <= 0.003:
            return
        th = self.theme
        if self.labels:
            put_text(fr, (110, 470), self.labels[0], th.font("mono", 52, 800), th.c["accent2"], la)
        if len(self.labels) > 1:
            put_text(fr, (110, 550), self.labels[1], th.font("body", 52, 600), th.c["text"], la)
        f = th.font("mono", 48, 800)
        for p, lab in zip(self.pins, self.pin_labels):
            px, py = R.world.proj(p["lon"], p["lat"], cam); r = 10 * fr.S
            fr.d.ellipse((px - r, py - r, px + r, py + r), outline=th.c["text"] + (int(255 * la),), width=max(1, int(3 * fr.S)))
            if lab:
                outlined_text(fr, (px / fr.S + 22, py / fr.S + 16), lab, f, th.c["text"], la)

    def reveals(self):
        return [self.z1]

    def cues(self):
        return [(self.start, "whoosh_down", self.zoom), (self.z1, "impact", self.z2 - self.z1), (self.z2, "whoosh", self.zout)]


@register
class BeforeAfter(MapBeat):
    type = "before_after"
    transition_default = 1.1
    legend_default = False

    def __init__(self, story, cfg, index):
        super().__init__(story, cfg, index)
        self.card = Card(self, cfg)
        self.labels_t = list(cfg.get("labels") or [])
        self.ov_t = [dict(o) for o in (cfg.get("overlays") or [])]

    def text_templates(self):
        return self.card.templates()

    def resolve(self):
        self.card.resolve()
        self.labels = [self.story.tpl(x) for x in self.labels_t]
        self.ovs = [dict(o, label=self.story.tpl(o.get("label", ""))) for o in self.ov_t]

    def text_need(self):
        return self.need(*self.card.lines())

    def plan(self, start, prev):
        self.imgs = [self.story.dataset(n) for n in self.cfg["images"]]
        super().plan(start, prev)
        self.p0 = self.start + self.tin

    def make_blocks(self):
        self.blocks = [TextBlock(self.card.lines(), self.text_t0, self.text_t1, self.id, sizes=self.card.sizes()),
                       TextBlock(self.labels + [o["label"] for o in self.ovs if o.get("label")] + ["Sentinel-2"],
                                 self.start + self.tin, self.end, self.id, count=False, sizes=[48])]

    def w(self, t):
        return clamp((t - self.p0 + 0.3) / 0.5) * (1 - clamp((t - self.end + 0.2) / 0.5))

    def stage(self, t):
        wipes = [self.p0 + float(x) for x in self.cfg.get("wipes", [])]
        i = sum(1 for x in wipes if t >= x + 0.45)
        k = 0.0
        for j, x in enumerate(wipes):
            if x <= t < x + 0.45:
                i = j; k = clamp((t - x) / 0.45)
        return min(i, len(self.imgs) - 1), min(i + 1, len(self.imgs) - 1), k

    def draw_map(self, A, t, cam, R):
        wv = self.w(t)
        if wv > 0.003:
            a, b, k = self.stage(t)
            im0, m = self.imgs[a].layer(R.world, cam, R.W, R.H); im1, _ = self.imgs[b].layer(R.world, cam, R.W, R.H)
            x0, y0, x1, y1 = self.imgs[0].corners(R.world, cam); wipe = x0 + (x1 - x0) * k
            sel = (np.arange(R.W)[None, :, None] < wipe).astype(np.float32)
            img = im1 * sel + im0 * (1 - sel)
            A = A * (1 - m * wv) + img * 0.9 * m * wv
            for o in self.ovs:
                kk = clamp((t - self.p0 - float(o.get("at", 0))) / 0.4) * wv
                if kk > 0:
                    v = self.story.dataset(o["data"]).warp(R.world, cam, R.W, R.H, cv2.INTER_NEAREST)
                    edge = np.clip(v - cv2.erode(v, np.ones((3, 3), np.uint8)), 0, 1); col = np.array(self.c(o.get("color", "accent2")), np.float32)
                    A = A * (1 - 0.25 * v[..., None] * kk) + v[..., None] * col * 0.28 * kk + edge[..., None] * col * kk
        return super().draw_map(A, t, cam, R)

    def draw_ui(self, fr, t, cam, R):
        th = self.theme; s = fr.S
        x0, y0, x1, y1 = self.imgs[0].corners(R.world, cam)
        ao = clamp((t - self.start) / 0.45)
        if t < self.p0 + 0.3 and ao > 0:                         # the frame shows where we are flying to
            k = ao * (1 - clamp((t - self.p0) / 0.3))
            fr.d.rectangle((x0, y0, x1, y1), outline=th.c["accent2"] + (int(230 * k),), width=max(1, int(3 * s)))
            fr.glow_line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], mixc((0, 0, 0), th.c["accent2"], k), 10)
        wv = self.w(t); a = wv * clamp((t - self.p0 - 0.4) / 0.3)
        if a > 0.003:
            fr.d.rectangle((x0, y0, x1, y1), outline=th.c["text"] + (int(200 * a),), width=max(1, int(2 * s)))
            ia, ib, k = self.stage(t)
            lab = self.labels[ib if k >= 0.5 else ia] if self.labels else ""
            X1, Y0, Y1 = x1 / s, y0 / s, y1 / s
            if lab:
                put_text(fr, (X1 + 16, Y0 + 48), lab, th.font("mono", 48, 800), th.c["text"], a)
            src = self.cfg.get("image_credit", "Sentinel-2")
            if src:
                put_text(fr, (X1 + 16, Y0 + 106), src, th.font("body", 48, 600), th.c["muted"], a)
            for j, o in enumerate(reversed(self.ovs)):
                if o.get("label") and t > self.p0 + float(o.get("at", 0)):
                    put_text(fr, (X1 + 16, Y1 - 14 - 62 * j), o["label"], th.font("mono", 48, 800), self.c(o.get("color", "accent2")),
                             a * clamp((t - self.p0 - float(o.get("at", 0))) / 0.3))
        self.card.draw(fr, t, self.text_t0, self.text_t1)

    def cues(self):
        return [(self.start, "whoosh", self.tin), (self.text_t0, "big_hit", 1.0), (self.text_t0 + 0.6, "drums_full", self.text_t1 - 0.1),
                (self.text_t0, "choir", self.text_t1 - self.text_t0)]


@register
class Sources(Beat):
    """sources — the credits card: every dataset, image and licence. Exempt from words/hold rules (meant to be paused),
    not from the minimum text size.

        - type: sources
          title: "FUENTES"
          lines: ["Sismos: USGS ComCat (dominio público).", "Límites: IGN.", "Mapas, animación y música: hechos con código."]
          duration: 3.0"""
    type = "sources"
    exempt_readability = True
    legend_default = False

    def text_templates(self):
        return [self.cfg.get("title", "FUENTES")] + list(self.cfg.get("lines", []))

    def resolve(self):
        self.title = self.story.tpl(self.cfg.get("title", "FUENTES"))
        self.lines = [self.story.tpl(x) for x in self.cfg.get("lines", [])]

    def plan(self, start, prev):
        self.cfg.setdefault("duration", 3.0)
        super().plan(start, prev)
        self.blocks = [TextBlock([self.title] + self.lines, self.start, self.end, self.id, count=False,
                                 sizes=[80] + [self.cfg.get("size", 48)] * len(self.lines))]

    def draw_ui(self, fr, t, cam, R):
        a = clamp((t - self.start) / 0.4)
        th = self.theme
        fr.d.rectangle((0, 0, fr.W, fr.H), fill=(6, 6, 9, int(215 * a)))
        put_text(fr, (110, 170), self.title, th.font("display", 80), th.c["accent"], a)
        size = self.cfg.get("size", 48); step = self.cfg.get("line_step", 92)
        fb = th.font("body", size, 500)
        for i, s in enumerate(self.lines):
            put_text(fr, (110, 272 + i * step), s, fb, th.c["text"], a * clamp((t - self.start - 0.04 * i) / 0.3))

    def cues(self):
        return [(self.start, "outro", 1.0)]

    def reveals(self):
        return []
