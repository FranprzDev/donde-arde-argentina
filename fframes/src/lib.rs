//! «¿Dónde arde Argentina?» v10, ported from Python + ffmpeg (render_v10.py) to fframes.
//!
//! Every frame is one SVG document written as text (fframes' runtime SVG mode) and rasterised by fframes' CPU backend
//! (tiny-skia). All numbers, strings, the timeline and the geometry come from `data/v10.json` (exported from the v10 Python
//! pipeline by `prep/export_data.py`, which runs every v10 assert); georeferenced data rasters come from `assets/`.
//!
//! Ported beats (see README): the opening (space, sun, globe, rays, hook, «EL SOL…», the hard cut, the spark, «NOSOTROS SÍ.»,
//! the 14-year VIIRS timelapse), the MODIS scar + «26,6 MILLONES DE HA», the «= CASI 12 TUCUMANES» beat (0–20.8 s), and the
//! close (53.3 s to the end) with the new sources/credits card. The ranking, the three stops and the Sentinel-2 zooms
//! (20.8–53.3 s) are not ported; `is_ported` tells which frames are.
pub mod cam;
pub mod data;

use cam::*;
use data::{Cam, Ring, V10};
use fframes::{AudioMap, Color, Duration, FFramesContext, FontQuery, Frame, Svgr, Video};
use std::fmt::Write;

pub const WIDTH: usize = 1920;
pub const HEIGHT: usize = 1080;
const W: f64 = WIDTH as f64;
const H: f64 = HEIGHT as f64;

/// First and last second of the part of the timeline that is not ported (rendered as a labelled placeholder).
pub const GAP: (f64, f64) = (20.79, 53.3);
pub fn is_ported(t: f64) -> bool {
    !(GAP.0..GAP.1).contains(&t)
}

type Rgb = [u8; 3];
fn rgb(c: Rgb) -> String {
    format!("rgb({},{},{})", c[0], c[1], c[2])
}
fn mixc(a: Rgb, b: Rgb, k: f64) -> Rgb {
    [0, 1, 2].map(|i| (a[i] as f64 + (b[i] as f64 - a[i] as f64) * k).round().clamp(0.0, 255.0) as u8)
}
fn esc(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")
}
fn op(x: f64) -> f64 {
    (x.clamp(0.0, 1.0) * 1000.0).round() / 1000.0
}

/// Font roles of the v10 renderer (fx_v4.font): Anton display face, Inter 600 body, JetBrains Mono 700/800 labels.
#[derive(Clone, Copy)]
enum F {
    Anton,
    Inter,
    Mono7,
    Mono8,
}
impl F {
    fn family(self) -> &'static str {
        match self {
            F::Anton => "Anton",
            F::Inter => "Inter600",
            F::Mono7 => "JBMono700",
            F::Mono8 => "JBMono800",
        }
    }
    /// cap height / em, used to scale text around its vertical middle like put_text does
    fn cap(self) -> f64 {
        match self {
            F::Anton => 1760.0 / 2048.0,
            F::Inter => 1490.0 / 2048.0,
            _ => 0.73,
        }
    }
}

/// Collects one frame: the main layer and the glow layer (fx_v4.Frame.g), which `finish` blurs and screens on top.
struct Svg {
    s: String,
    glow: String,
}
impl Svg {
    fn new() -> Self {
        Self { s: String::with_capacity(400_000), glow: String::new() }
    }
    fn glow_line(&mut self, pts: &[(f64, f64)], col: Rgb, a: f64, w: f64) {
        if a <= 0.003 || pts.len() < 2 {
            return;
        }
        let _ = write!(self.glow, r#"<path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{w}" stroke-linejoin="round"/>"#,
            pts_d(pts, false), rgb(col), op(a));
    }
    /// put_text: text anchored at its left baseline, scaled around its left-middle; optional glow copy
    #[allow(clippy::too_many_arguments)]
    fn text(&mut self, x: f64, y: f64, s: &str, f: F, size: f64, col: Rgb, a: f64, scale: f64, glow: f64) {
        if a <= 0.003 {
            return;
        }
        let cy = y - size * f.cap() / 2.0;
        let tr = if (scale - 1.0).abs() > 0.004 {
            format!(r#" transform="translate({x:.2} {cy:.2}) scale({scale:.4}) translate({:.2} {:.2})""#, -x, -cy)
        } else {
            String::new()
        };
        let el = format!(r#"<text x="{x:.1}" y="{y:.1}" font-family="{}" font-size="{size}" fill="{}"{tr}"#, f.family(), rgb(col));
        let _ = write!(self.s, r#"{el} opacity="{}">{}</text>"#, op(a), esc(s));
        if glow > 0.0 {
            let _ = write!(self.glow, r#"{el} opacity="{}">{}</text>"#, op(glow * a), esc(s));
        }
    }
}

fn pts_d(pts: &[(f64, f64)], close: bool) -> String {
    let mut d = String::with_capacity(pts.len() * 16);
    for (i, (x, y)) in pts.iter().enumerate() {
        let _ = write!(d, "{}{:.1} {:.1}", if i == 0 { "M" } else { "L" }, x, y);
    }
    if close {
        d.push('Z');
    }
    d
}
/// a ring in "unit" map space (lon*cos, -lat): the camera is then one uniform scale + translate
fn ring_unit_d(r: &Ring, cos: f64) -> String {
    let mut d = String::with_capacity(r.len() * 18);
    for (i, p) in r.iter().enumerate() {
        let _ = write!(d, "{}{:.4} {:.4}", if i == 0 { "M" } else { "L" }, p[0] * cos, -p[1]);
    }
    d.push('Z');
    d
}

/// smoothstep-like Python helpers reused by several beats
fn slam_params(t: f64, t0: f64, t1: Option<f64>, big: bool, outd: f64) -> Option<(f64, f64, f64, f64)> {
    if t < t0 {
        return None;
    }
    let u = t - t0;
    let (mut sc, mut a) = if big { (1.0 + 0.45 * (1.0 - eout5(u / 0.28)), clamp(u / 0.09)) } else { (1.0 + 0.12 * (1.0 - eout(u / 0.35)), clamp(u / 0.18)) };
    let flare = if big { 1.0 + 1.6 * decay(t, t0, 0.18) } else { 1.0 };
    if let Some(t1) = t1 {
        let o = clamp((t - t1) / outd);
        a *= 1.0 - o;
        sc *= 1.0 + 0.05 * o;
    }
    if a <= 0.0 {
        return None;
    }
    let dy = if big { 0.0 } else { (1.0 - eout(u / 0.35)) * 18.0 };
    Some((sc, a, flare, dy))
}

pub struct IncendiosVideo {
    pub d: V10,
    neigh_d: String,
    prov_fill_d: String,
    ar_out_d: String,
    prov_rings: Vec<Ring>,
    globe_land: Vec<Ring>,
}

impl std::fmt::Debug for IncendiosVideo {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("IncendiosVideo").finish()
    }
}

impl IncendiosVideo {
    pub fn new(d: V10) -> Self {
        let cos = d.cos;
        let neigh_d = d.neigh.iter().map(|r| ring_unit_d(r, cos)).collect::<String>();
        let mut keys: Vec<_> = d.prov.keys().cloned().collect();
        keys.sort();
        let prov_rings: Vec<Ring> = keys.iter().flat_map(|k| d.prov[k].iter().cloned()).collect();
        let prov_fill_d = prov_rings.iter().map(|r| ring_unit_d(r, cos)).collect::<String>();
        let ar_out_d = d.ar_out.iter().map(|r| ring_unit_d(r, cos)).collect::<String>();
        let globe_land = d.land.clone();
        Self { d, neigh_d, prov_fill_d, ar_out_d, prov_rings, globe_land }
    }

    fn tm(&self) -> &data::Times {
        &self.d.times
    }

    /// the SVG transform that maps unit map space onto the screen for camera c
    fn geo_tr(&self, c: &Cam) -> String {
        let z = c[2];
        format!("matrix({z:.5} 0 0 {z:.5} {:.3} {:.3})", c[3] - c[0] * self.d.cos * z, c[4] + c[1] * z)
    }
    fn proj(&self, lon: f64, lat: f64, c: &Cam) -> (f64, f64) {
        proj(lon, lat, c, self.d.cos)
    }
    fn ring_px(&self, r: &Ring, c: &Cam) -> Vec<(f64, f64)> {
        r.iter().map(|p| self.proj(p[0], p[1], c)).collect()
    }
    /// a georeferenced raster (bbox = lon0, lat0, lon1, lat1) drawn under camera c
    fn geo_image(&self, href: &str, bbox: [f64; 4], c: &Cam, opacity: f64, blend: &str) -> String {
        if opacity <= 0.003 {
            return String::new();
        }
        let (x0, y0) = self.proj(bbox[0], bbox[3], c);
        let (x1, y1) = self.proj(bbox[2], bbox[1], c);
        let style = if blend.is_empty() { String::new() } else { format!(r#" style="mix-blend-mode:{blend}""#) };
        format!(r#"<image href="{href}" x="{x0:.2}" y="{y0:.2}" width="{:.2}" height="{:.2}" preserveAspectRatio="none" opacity="{}"{style}/>"#,
            x1 - x0, y1 - y0, op(opacity))
    }

    fn m_now(&self, t: f64) -> f64 {
        let tm = self.tm();
        if t < tm.t_land {
            0.0
        } else if t < tm.t_a1 {
            interp(t, &self.d.ka_s, &self.d.ka_m)
        } else {
            168.0
        }
    }

    // ---------------- text beats ----------------
    #[allow(clippy::too_many_arguments)]
    fn slam(&self, o: &mut Svg, x: f64, y: f64, s: &str, f: F, size: f64, col: Rgb, t: f64, t0: f64, t1: Option<f64>, glow: f64, big: bool) {
        if let Some((sc, a, flare, dy)) = slam_params(t, t0, t1, big, 0.3) {
            let g = if glow > 0.0 { glow * flare } else if big { 0.35 * (flare - 1.0) } else { 0.0 };
            o.text(x, y + dy, s, f, size, col, a, sc, g);
        }
    }
    #[allow(clippy::too_many_arguments)]
    fn slam_tight(&self, o: &mut Svg, x: f64, y: f64, s: &str, f: F, size: f64, col: Rgb, t: f64, t0: f64, t1: f64, glow: f64) {
        if t < t0 {
            return;
        }
        let u = t - t0;
        let mut sc = 1.0 + 0.08 * (1.0 - eout5(u / 0.28));
        let mut a = clamp(u / 0.09);
        let flare = 1.0 + 1.6 * decay(t, t0, 0.18);
        let oo = clamp((t - t1) / 0.3);
        a *= 1.0 - oo;
        sc *= 1.0 + 0.03 * oo;
        if a > 0.0 {
            o.text(x, y, s, f, size, col, a, sc, glow * flare);
        }
    }

    fn draw_hook(&self, o: &mut Svg, t: f64) {
        let (h0, h1) = (self.d.t_hook[0], self.d.t_hook[1]);
        if !(h0 <= t && t < h1 + 0.4) {
            return;
        }
        let c = &self.d.colors;
        let (tx, y) = (self.d.tx, self.d.hook_y);
        self.slam(o, tx, y, &self.d.texts.hook1, F::Anton, 132.0, c.wh, t, h0, Some(h1), 0.25, true);
        self.slam(o, tx, y + 142.0, &self.d.texts.hook2, F::Anton, 132.0, c.or, t, h0 + 0.12, Some(h1), 0.6, true);
    }

    fn draw_intro_text(&self, o: &mut Svg, t: f64) {
        let (tm, c, tx, x) = (self.tm(), &self.d.colors, &self.d.texts, self.d.tx);
        if tm.t_txt1 <= t && t < tm.t_spark {
            self.slam(o, x, 420.0, &tx.sol, F::Anton, 100.0, c.wh, t, tm.t_txt1, None, 0.0, false);
            self.slam(o, x, 560.0, &tx.sol2, F::Anton, 100.0, c.wh, t, tm.t_txt1b, None, 0.0, false);
        }
        if tm.t_nos <= t && t < tm.t_txt2_end + 0.4 {
            self.slam_tight(o, x, 560.0, &tx.nos, F::Anton, 150.0, c.or, t, tm.t_nos, tm.t_txt2_end, 0.6);
            self.slam(o, x, 668.0, &tx.causa, F::Anton, 66.0, c.wh, t, tm.t_nos + 0.25, Some(tm.t_txt2_end), 0.0, false);
        }
    }

    // ---------------- opening: sun, globe, rays ----------------
    fn sun_state(&self, t: f64) -> (f64, f64, f64, f64) {
        let tau = t / self.d.space_k;
        let rs = 900.0 * (-2.5 * tau).exp();
        let k = eout(tau / 1.3);
        (lerp(960.0, 330.0, k), lerp(540.0, 250.0, k), rs, 1.0 - clamp((tau - 1.9) / 0.5))
    }
    /// (cx, cy, R, lon0, lat0, flat)
    fn globe_state(&self, t: f64) -> Option<[f64; 6]> {
        let tau = t / self.d.space_k;
        if tau < 0.45 {
            return None;
        }
        let cam_in = self.d.seg[0].2;
        let r_final = cam_in[2] * 180.0 / std::f64::consts::PI;
        let ks = [0.45, 1.5, 2.35, 3.0, 3.7];
        let vs = [3.0f64, 70.0, 420.0, 1050.0, r_final].map(|v| v.ln());
        let re = interp(tau, &ks, &vs).exp();
        let kr = einout((tau - 0.45) / 2.6);
        Some([cam_in[3], cam_in[4], re, lerp(18.0, cam_in[0], kr), lerp(12.0, cam_in[1], kr), clamp((tau - 2.55) / 0.75)])
    }
    /// orthographic projection: (screen x, screen y, x3, y3, z3)
    fn ortho(lon: f64, lat: f64, g: &[f64; 6]) -> (f64, f64, f64, f64, f64) {
        let (p, l, p0) = (lat.to_radians(), (lon - g[3]).to_radians(), g[4].to_radians());
        let x = p.cos() * l.sin();
        let y = p0.cos() * p.sin() - p0.sin() * p.cos() * l.cos();
        let z = p0.sin() * p.sin() + p0.cos() * p.cos() * l.cos();
        (g[0] + g[2] * x, g[1] - g[2] * y, x, y, z)
    }
    fn heat_level(&self, t: f64) -> f64 {
        clamp((t - 2.9) / 1.6) * (1.0 - clamp((t - self.tm().t_cool) / 0.5))
    }

    fn draw_stars(&self, s: &mut String, tau: f64, a: f64) {
        if a <= 0.003 {
            return;
        }
        let zk_t = [0.0, 1.0, 2.0, 3.4];
        let zk_v = [0.6f64, 1.4, 2.6, 4.5].map(|v| v.ln());
        let zoom = interp(tau, &zk_t, &zk_v).exp();
        let vel = (zoom - interp((tau - 0.08).max(0.0), &zk_t, &zk_v).exp()) * 2.5;
        let (cx, cy) = (W / 2.0, H / 2.0);
        // stars are binned by brightness (8 bins) so each bin is one path
        let mut bins: Vec<String> = vec![String::new(); 8];
        for st in &self.d.stars {
            let (sx, sy, b) = (st[0], st[1], st[2]);
            let k = zoom * (0.6 + b);
            let (x, y) = (cx + sx * W * 0.5 * k, cy + sy * W * 0.5 * k);
            if !(-50.0 < x && x < W + 50.0 && -50.0 < y && y < H + 50.0) {
                continue;
            }
            let k2 = k - vel * (0.6 + b);
            let (x2, y2) = (cx + sx * W * 0.5 * k2, cy + sy * W * 0.5 * k2);
            let bi = ((b * 8.0) as usize).min(7);
            let _ = write!(bins[bi], "M{x2:.1} {y2:.1}L{:.1} {:.1}", x + 0.01, y);
        }
        let vf = if vel > 0.01 { 0.5 } else { 1.0 };
        for (i, d) in bins.iter().enumerate() {
            if d.is_empty() {
                continue;
            }
            let v = ((i as f64 + 0.5) / 8.0 * vf * a * 1.4).min(1.0);
            let _ = write!(s, r#"<path d="{d}" stroke="rgb(215,225,255)" stroke-opacity="{}" stroke-width="1.3" stroke-linecap="round" fill="none"/>"#, op(v));
        }
    }

    fn draw_sun(&self, s: &mut String, t: f64) {
        let (sx, sy, rs, sa) = self.sun_state(t);
        if sa <= 0.003 || rs < 0.5 {
            return;
        }
        let k = rs / self.d.sun_tex.r;
        let half = self.d.sun_tex.half * k;
        let _ = write!(s, r#"<image href="sun.png" x="{:.2}" y="{:.2}" width="{:.2}" height="{:.2}" opacity="{}" style="mix-blend-mode:screen"/>"#,
            sx - half, sy - half, 2.0 * half, 2.0 * half, op(sa));
    }

    fn draw_globe(&self, s: &mut String, t: f64, g: &[f64; 6]) {
        let (cx, cy, r, flat) = (g[0], g[1], g[2], g[5]);
        let tau = t / self.d.space_k;
        let a = clamp((tau - 0.45) / 0.15);
        let bg = self.d.bg;
        let ocean = mixc([14, 34, 66], bg, flat);
        let landc = mixc([96, 88, 70], [18, 17, 20], flat);
        let _ = write!(s, r#"<g opacity="{}"><clipPath id="disc"><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}"/></clipPath><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}" fill="{}"/><g clip-path="url(#disc)">"#,
            op(a), rgb(ocean));
        if r > 1.5 {
            let mut d = String::new();
            for ring in &self.globe_land {
                let mut vis = false;
                let mut pts = Vec::with_capacity(ring.len());
                for p in ring {
                    let (x, y, x3, y3, z3) = Self::ortho(p[0], p[1], g);
                    if z3 >= 0.0 {
                        vis = true;
                        pts.push((x, y));
                    } else {
                        // behind the globe: pushed onto the limb
                        let n = x3.hypot(y3).max(1e-9);
                        pts.push((cx + r * x3 / n, cy - r * y3 / n));
                    }
                }
                if vis {
                    d.push_str(&pts_d(&pts, true));
                }
            }
            let _ = write!(s, r#"<path d="{d}" fill="{}"/>"#, rgb(landc));
        }
        // sun-side shading (1 - lit) and the atmosphere, fading out as the globe turns into the flat map
        let l = self.d.light;
        let (lx, ly) = (cx + r * l[0], cy - r * l[1]);
        let _ = write!(s, r#"<radialGradient id="shade" gradientUnits="userSpaceOnUse" cx="{lx:.1}" cy="{ly:.1}" r="{:.1}"><stop offset="0" stop-color="black" stop-opacity="0"/><stop offset="0.35" stop-color="black" stop-opacity="0.18"/><stop offset="0.62" stop-color="black" stop-opacity="0.72"/><stop offset="0.8" stop-color="black" stop-opacity="0.94"/></radialGradient><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}" fill="url(#shade)" opacity="{}"/>"#,
            r * 1.7, op(1.0 - flat));
        let _ = write!(s, r#"<radialGradient id="limb" gradientUnits="userSpaceOnUse" cx="{cx:.1}" cy="{cy:.1}" r="{r:.1}"><stop offset="0.72" stop-color="rgb(70,140,255)" stop-opacity="0"/><stop offset="0.93" stop-color="rgb(70,140,255)" stop-opacity="0.18"/><stop offset="1" stop-color="rgb(70,140,255)" stop-opacity="0.45"/></radialGradient><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}" fill="url(#limb)" opacity="{}" style="mix-blend-mode:screen"/></g></g>"#,
            op(1.0 - flat));
        if flat < 0.999 && r > 4.0 {
            let lw = (r * 0.035).max(6.0);
            let _ = write!(s, r#"<circle cx="{cx:.2}" cy="{cy:.2}" r="{:.2}" fill="none" stroke="rgb(70,140,255)" stroke-width="{lw:.1}" opacity="{}" filter="url(#b{})" style="mix-blend-mode:screen"/>"#,
                r + lw * 0.2, op(0.4 * (1.0 - flat) * a), blur_id(lw * 0.6));
        }
        // Argentina warms on the globe as the rays land
        let hk = self.heat_level(t) * (1.0 - flat * 0.3);
        if hk > 0.01 && r > 200.0 {
            let mut d = String::new();
            for ring in &self.d.ar_out {
                let pts: Vec<_> = ring.iter().map(|p| Self::ortho(p[0], p[1], g)).filter(|q| q.4 > 0.05).map(|q| (q.0, q.1)).collect();
                if pts.len() > 2 {
                    d.push_str(&pts_d(&pts, true));
                }
            }
            let _ = write!(s, r#"<path d="{d}" fill="rgb(120,50,10)" opacity="{}" filter="url(#b{})" style="mix-blend-mode:screen"/>"#,
                op(hk), blur_id((r / 160.0 * 4.0).max(8.0)));
        }
    }

    /// render_v10.ray_layer: sunlight streaks that land on Argentina and glint back. Returns (core, glow) SVG fragments.
    fn ray_layer(&self, t: f64, cmap: Option<&Cam>) -> (String, String) {
        let (mut core, mut glow) = (String::new(), String::new());
        let tm = self.tm();
        if t > tm.t_cool + 0.4 || t < 0.7 {
            return (core, glow);
        }
        let (sx, sy, rs, sa) = self.sun_state(t);
        let g = self.globe_state(t);
        let ray_a = 1.0 - clamp((t - tm.t_cool) / 0.35);
        let light = self.d.light;
        let d_in = self.d.d_in;
        let (travel, refl) = (self.d.ray_travel, self.d.ray_refl);
        let npts = self.d.ar_pts.len();
        let seg = |core: &mut String, glow: &mut String, p: (f64, f64), q: (f64, f64), v: f64| {
            let v = v.min(1.0);
            if v <= 0.004 {
                return;
            }
            let _ = write!(core, r#"<path d="M{:.1} {:.1}L{:.1} {:.1}" stroke-opacity="{}"/>"#, p.0, p.1, q.0, q.1, op(v));
            let _ = write!(glow, r#"<path d="M{:.1} {:.1}L{:.1} {:.1}" stroke-opacity="{}"/>"#, p.0, p.1, q.0, q.1, op(v));
        };
        let norm3 = |v: [f64; 3]| {
            let n = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt();
            [v[0] / n, v[1] / n, v[2] / n]
        };
        let mut hits = String::new();
        for &(te, kind, p1, p2) in &self.d.rays {
            let u = (t - te) / travel;
            if u < 0.0 || u > 1.0 + refl / travel {
                continue;
            }
            let (hit, start, rr, v);
            if kind == 0 {
                let Some(g) = g.as_ref() else { continue };
                if g[2] < 6.0 || sa < 0.05 {
                    continue;
                }
                let (cx, cy) = (g[0], g[1]);
                let pt = self.d.ar_pts[(p1.abs() * (npts - 1) as f64) as usize];
                let (x, y, x3, y3, z3) = Self::ortho(pt[0], pt[1], g);
                if z3 < 0.05 {
                    continue;
                }
                hit = (x, y);
                let dd = (cx - sx).hypot(cy - sy).max(1.0);
                start = (sx + (-(cy - sy)) / dd * p1 * rs * 0.35, sy + (cx - sx) / dd * p1 * rs * 0.35);
                let n3 = norm3([x3 + p1 * 0.4, y3 + 0.3, z3]);
                let dl = (hit.0 - start.0).hypot(hit.1 - start.1).max(1e-3);
                let ddv = ((hit.0 - start.0) / dl, (hit.1 - start.1) / dl);
                let d3 = norm3([ddv.0, -ddv.1, -0.25]);
                let dot = d3[0] * n3[0] + d3[1] * n3[1] + d3[2] * n3[2];
                let r3 = [d3[0] - 2.0 * dot * n3[0], d3[1] - 2.0 * dot * n3[1]];
                let rn = r3[0].hypot(r3[1]).max(1e-3);
                rr = (r3[0] / rn, -r3[1] / rn);
                v = 0.9 * sa * p2 + 0.3;
            } else {
                let pt = self.d.ar_pts[p1 as usize];
                let n3 = match cmap {
                    None => {
                        let Some(g) = g.as_ref() else { continue };
                        let (x, y, x3, y3, z3) = Self::ortho(pt[0], pt[1], g);
                        if z3 < 0.1 {
                            continue;
                        }
                        hit = (x, y);
                        [x3, y3, z3]
                    }
                    Some(c) => {
                        hit = self.proj(pt[0], pt[1], c);
                        [0.0, 0.0, 1.0]
                    }
                };
                let d3 = [-light[0], -light[1], -light[2]];
                let n3 = norm3([n3[0] + p2 * 0.6, n3[1] + 0.35, n3[2]]);
                let dot = d3[0] * n3[0] + d3[1] * n3[1] + d3[2] * n3[2];
                let r3 = [d3[0] - 2.0 * dot * n3[0], d3[1] - 2.0 * dot * n3[1]];
                let rn = r3[0].hypot(r3[1]).max(1e-3);
                rr = (r3[0] / rn, -r3[1] / rn);
                start = (hit.0 - d_in[0] * 1500.0, hit.1 - d_in[1] * 1500.0);
                v = 0.85 * ray_a;
            }
            if v <= 0.01 {
                continue;
            }
            let along = |k: f64| (start.0 + (hit.0 - start.0) * k, start.1 + (hit.1 - start.1) * k);
            if u <= 1.0 {
                seg(&mut core, &mut glow, along((u - 0.28).max(0.0)), along(u), v * (0.55 + 0.45 * u));
            } else {
                let w = (u - 1.0) * travel / refl;
                let tail = along((1.0 - 0.28 + 0.28 * eout(w * 1.6)).min(1.0));
                if (hit.0 - tail.0).hypot(hit.1 - tail.1) > 1.5 {
                    seg(&mut core, &mut glow, tail, hit, v * (1.0 - 0.5 * w));
                }
                let ln = if kind == 1 { 260.0 } else { 420.0 };
                let e = eout(w);
                let head = (hit.0 + rr.0 * ln * e, hit.1 + rr.1 * ln * e);
                let tl = (hit.0 + rr.0 * ln * (e - 0.35).max(0.0), hit.1 + rr.1 * ln * (e - 0.35).max(0.0));
                seg(&mut core, &mut glow, tl, head, v * 0.7 * (1.0 - w));
                let _ = write!(hits, r#"<circle cx="{:.1}" cy="{:.1}" r="{:.1}" fill="none" stroke-width="2" stroke-opacity="{}"/><circle cx="{:.1}" cy="{:.1}" r="3" stroke="none" fill-opacity="{}"/>"#,
                    hit.0, hit.1, 4.0 + 26.0 * e, op(v * (1.0 - w) * 0.9), hit.0, hit.1, op(v * 2.2 * (1.0 - w)));
            }
        }
        core.push_str(&hits);
        glow.push_str(&hits);
        (core, glow)
    }
    fn light_svg(&self, s: &mut String, core: &str, glow: &str) {
        if core.is_empty() {
            return;
        }
        // core streaks (255,236,190)*1.1 and their glow (255,170,70)*2.2 blurred, both additive in v10 -> screen here
        let _ = write!(s, r#"<g style="mix-blend-mode:screen" stroke="rgb(255,255,209)" fill="rgb(255,255,209)" stroke-width="2" stroke-linecap="round" fill-opacity="1">{core}</g><g style="mix-blend-mode:screen" filter="url(#rayglow)" stroke="rgb(255,170,70)" fill="rgb(255,170,70)" stroke-width="3" stroke-linecap="round">{glow}</g>"#);
    }

    fn space_frame(&self, s: &mut String, t: f64) {
        let tau = t / self.d.space_k;
        let _ = write!(s, r#"<rect width="{W}" height="{H}" fill="{}"/>"#, rgb(self.d.bg));
        self.draw_stars(s, tau, 0.9 * (1.0 - clamp((tau - 2.6) / 0.6)));
        self.draw_sun(s, t);
        if let Some(g) = self.globe_state(t) {
            self.draw_globe(s, t, &g);
        }
        let (core, glow) = self.ray_layer(t, None);
        self.light_svg(s, &core, &glow);
    }

    // ---------------- the flat map ----------------
    fn base_map(&self, s: &mut String, c: &Cam) {
        let z = c[2];
        let _ = write!(s, r#"<rect width="{W}" height="{H}" fill="{}"/><g transform="{}"><path d="{}" fill="rgb(13,13,17)" stroke="rgb(34,34,40)" stroke-width="{:.5}"/><path d="{}" fill="rgb(20,19,22)"/><path d="{}" fill="none" stroke="rgb(62,60,64)" stroke-opacity="0.82" stroke-width="{:.5}"/></g>"#,
            rgb(self.d.bg), self.geo_tr(c), self.neigh_d, 1.0 / z, self.prov_fill_d, self.prov_fill_d, 1.0 / z);
    }

    fn heat_wash(&self, s: &mut String, t: f64, c: &Cam) {
        let hk = self.heat_level(t);
        if hk <= 0.01 {
            return;
        }
        // v10 adds (95,38,8) * hk over a blurred Argentina mask (+ heat-haze bands); screen of a slightly hotter colour matches it
        let _ = write!(s, r#"<g filter="url(#b6)" style="mix-blend-mode:screen"><g transform="{}"><path d="{}" fill="rgb(108,43,9)" opacity="{}"/></g></g>"#, self.geo_tr(c), self.ar_out_d, op(hk));
    }

    fn draw_spark(&self, s: &mut String, t: f64, c: &Cam) {
        let tm = self.tm();
        if !(tm.t_spark - 0.05 <= t && t < tm.t_land + 0.6) {
            return;
        }
        let (x, y) = self.proj(self.d.spark_ll[0], self.d.spark_ll[1], c);
        let u = t - tm.t_spark;
        let flick = 0.8 + 0.2 * (u * 37.0).sin() * (u * 23.0 + 1.0).sin();
        let grow = eout(u / 0.25) * (1.0 - clamp((t - tm.t_land - 0.1) / 0.5));
        let burst = decay(t, tm.t_spark, 0.12);
        // the v10 glow is two Gaussians of a 3 px dot (sigma 8 and 44 px at full size, gains 60 and 420): sample that profile
        let (k1, k2) = (16.7 * (0.6 + 1.5 * burst), 3.87 * (0.35 + 0.9 * burst));
        let rmax = 150.0;
        let mut stops = String::new();
        for i in 0..=16 {
            let f = i as f64 / 16.0;
            let r = f * rmax;
            let k = grow * flick * (k1 * (-r * r / 128.0).exp() + k2 * (-r * r / (2.0 * 44.0 * 44.0)).exp());
            let col = [255.0 * k, 150.0 * k, 50.0 * k].map(|v| v.clamp(0.0, 255.0) as u8);
            let _ = write!(stops, r#"<stop offset="{f:.3}" stop-color="{}"/>"#, rgb(col));
        }
        let _ = write!(s, r#"<radialGradient id="spark" gradientUnits="userSpaceOnUse" cx="{x:.1}" cy="{y:.1}" r="{rmax}">{stops}</radialGradient><g style="mix-blend-mode:screen"><circle cx="{x:.1}" cy="{y:.1}" r="{rmax}" fill="url(#spark)"/><circle cx="{x:.1}" cy="{y:.1}" r="6" fill="rgb(255,250,230)" opacity="{}"/>"#,
            op(grow));
        for (k, e) in self.d.embers.iter().enumerate() {
            let uu = t - e[0];
            if (0.0..0.9).contains(&uu) {
                let ex = x + e[1] * uu + 6.0 * (uu * 9.0 + k as f64).sin();
                let ey = y + e[2] * uu;
                let _ = write!(s, r#"<circle cx="{ex:.1}" cy="{ey:.1}" r="2.2" fill="rgb(255,190,90)" opacity="{}"/><circle cx="{ex:.1}" cy="{ey:.1}" r="7" fill="rgb(255,190,90)" opacity="{}" filter="url(#b3)"/>"#,
                    op(1.2 * (1.0 - uu / 0.9) * grow), op(0.9 * (1.0 - uu / 0.9) * grow));
            }
        }
        s.push_str("</g>");
    }

    fn cut_dark(&self, t: f64) -> f64 {
        let tm = self.tm();
        if !(tm.t_spark <= t && t < tm.t_land + 0.3) {
            return 1.0;
        }
        lerp(0.28, 1.0, eout((t - tm.t_spark - 0.08) / (tm.t_land + 0.3 - tm.t_spark - 0.08)))
    }

    /// the 14 fast years of VIIRS hotspots and their burn-out to ash
    fn fire_layers(&self, s: &mut String, t: f64, c: &Cam) {
        let tm = self.tm();
        let gb = self.d.grid.bbox;
        let acc = if t >= tm.t_a1 - 0.3 { (clamp((t - tm.t_a1 + 0.3) / 0.3) * (0.85 + 0.3 * decay(t, tm.t_a1, 0.6))).min(1.0) } else { 0.0 };
        let ash_k = clamp((t - tm.t_ash) / 0.9);
        let gone = clamp((t - tm.t_scar) / 0.6);
        // ember glow of everything that already burned (quarterly cumulative histograms)
        let m = self.m_now(t);
        let q = self.d.ember_q.iter().rposition(|&mq| mq as f64 <= m + 1e-6);
        if let Some(q) = q {
            s.push_str(&self.geo_image(&format!("ember_{q:02}.png"), gb, c, (1.0 - acc) * (1.0 - ash_k), "screen"));
        }
        s.push_str(&self.geo_image("ash.png", gb, c, ash_k * (1.0 - gone), "screen"));
        // fresh fire: the months lit in the last second, each fading with v10's 0.16 s decay
        let mut f = String::new();
        if t < tm.t_a1 + 1.0 {
            for fr in self.d.fresh.iter().flatten() {
                let dt = t - fr.t;
                if !(0.0..1.0).contains(&dt) || t > tm.t_a1 + 1.0 {
                    continue;
                }
                let w = (-dt / 0.16).exp();
                f.push_str(&self.geo_image(&format!("fire_cool_{:03}.png", fr.m), fr.bbox, c, (3.0 * w).min(1.0), "screen"));
                f.push_str(&self.geo_image(&format!("fire_hot_{:03}.png", fr.m), fr.bbox, c, w.powf(1.2), "screen"));
            }
        }
        if acc > 0.0 {
            f.push_str(&self.geo_image("acc_full.png", gb, c, acc, "screen"));
        }
        if !f.is_empty() && ash_k < 1.0 {
            let bloom_k = 0.9 * (1.0 + 0.6 * decay(t, tm.t_a1, 0.9));
            let _ = write!(s, r#"<g opacity="{}" style="mix-blend-mode:screen"><g style="isolation:isolate">{f}</g><g filter="url(#bloom)" opacity="{}" style="mix-blend-mode:screen">{f}</g></g>"#,
                op(1.0 - ash_k), op(bloom_k / 1.5));
        }
    }

    fn scar_layer(&self, s: &mut String, t: f64, c: &Cam) -> f64 {
        let tm = self.tm();
        let sk = clamp((t - tm.t_scar + 0.3) / 0.9);
        if sk <= 0.0 {
            return 0.0;
        }
        let mut dimk = if t < tm.t_d1 { 1.0 } else { 0.5 };
        dimk *= 1.0 - 0.55 * clamp((t - tm.t_rk) / 0.5) * (1.0 - clamp((t - tm.t_rk_end) / 0.6));
        dimk = lerp(dimk, 1.0, clamp((t - tm.t_cl + 0.4) / 1.0));
        dimk *= 1.0 - 0.75 * clamp((c[2] - 900.0) / 1500.0);
        let kw = 0.5 * decay(t, tm.t_scar, 0.8);
        let bb = self.d.scar_bbox;
        s.push_str(&self.geo_image("scar_dark.png", bb, c, sk, ""));
        s.push_str(&self.geo_image("scar_col.png", bb, c, sk * dimk * (1.0 - kw), "screen"));
        s.push_str(&self.geo_image("scar_warm.png", bb, c, sk * dimk * kw, "screen"));
        sk
    }

    /// v8 close: every VIIRS hotspot accumulates over the MODIS scar map
    fn close_embers(&self, s: &mut String, t: f64, c: &Cam) {
        let tm = self.tm();
        if t < tm.t_cl - 0.6 {
            return;
        }
        let hk = clamp((t - tm.t_cl - 0.1) / 1.5);
        let m = 168.0 * eout(hk);
        let Some(q) = self.d.ember_q.iter().rposition(|&mq| mq as f64 <= m + 1e-6) else { return };
        let a = clamp((t - tm.t_cl + 0.6) / 0.6) * (1.0 - 0.35 * clamp((t - tm.t_src) / 0.5));
        let img = self.geo_image(&format!("acc_{q:02}.png"), self.d.grid.bbox, c, a, "screen");
        let bk = 0.7 * (1.0 + 0.5 * decay(t, tm.t_cl + 1.6, 0.8));
        let _ = write!(s, r#"<g style="mix-blend-mode:screen">{img}<g filter="url(#bloom)" opacity="{}" style="mix-blend-mode:screen">{img}</g></g>"#, op(bk / 1.4));
    }

    fn close_w(&self, t: f64) -> f64 {
        let tm = self.tm();
        clamp((t - tm.t_cl - 0.2) / 0.8) * (1.0 - clamp((t - tm.t_src) / 0.5))
    }

    fn draw_country(&self, o: &mut Svg, t: f64, c: &Cam) {
        let k = clamp((t - self.tm().s_tu[0] + 0.75) / 0.6);
        if k <= 0.003 {
            return;
        }
        let cw = self.close_w(t);
        let al = (70.0 + 150.0 * cw) * k / 255.0;
        let am = self.d.colors.am;
        let z = c[2];
        let _ = write!(o.s, r#"<g transform="{}"><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}" stroke-linejoin="round"/></g>"#,
            self.geo_tr(c), self.prov_fill_d, rgb(am), op(al), if cw < 0.5 { 2.0 } else { 3.0 } / z);
        if cw > 0.003 {
            let _ = write!(o.glow, r#"<g transform="{}"><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}"/><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}"/></g>"#,
                self.geo_tr(c), self.prov_fill_d, rgb(am), op(0.55 * cw), 6.0 / z, self.ar_out_d, rgb(self.d.colors.or), op(cw), 12.0 / z);
            let _ = write!(o.s, r#"<g transform="{}"><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}"/></g>"#,
                self.geo_tr(c), self.ar_out_d, rgb(self.d.colors.hot), op(230.0 / 255.0 * cw), 3.0 / z);
        }
    }

    // ---------------- v10: «= CASI 12 TUCUMANES» ----------------
    fn tu_copy(&self, lon: f64, lat: f64) -> Ring {
        let c0 = self.d.tu_c0;
        self.d.tu_ring.iter().map(|p| {
            let k = p[1].to_radians().cos() / (p[1] - c0[1] + lat).to_radians().cos();
            [lon + (p[0] - c0[0]) * k, p[1] - c0[1] + lat]
        }).collect()
    }
    fn draw_tucumanes(&self, o: &mut Svg, t: f64, c: &Cam) {
        let tm = self.tm();
        if !(tm.t_d1 - 0.2 <= t && t < tm.t_tu1 + 0.2) {
            return;
        }
        let col = &self.d.colors;
        let launch = |k: usize| tm.t_d1 + 0.15 + k as f64 * self.d.tu_step;
        let out = 1.0 - clamp((t - tm.t_tu1 + 0.25) / 0.35);
        let src = clamp((t - tm.t_d1 + 0.2) / 0.2) * out * (1.0 - 0.85 * clamp((t - launch(11)) / 0.4));
        let pts = self.ring_px(&self.d.tu_ring, c);
        let mut closed = pts.clone();
        closed.push(pts[0]);
        let _ = write!(o.s, r#"<path d="{}" fill="{}" fill-opacity="{}" stroke="{}" stroke-opacity="{}" stroke-width="3" stroke-linejoin="round"/>"#,
            pts_d(&pts, true), rgb(col.hot), op(110.0 / 255.0 * src), rgb(col.hot), op(src));
        o.glow_line(&closed, col.or, src, 10.0);
        for (k, cp) in self.d.tu_copies.iter().enumerate() {
            let u = (t - launch(k)) / self.d.tu_fly;
            if u <= 0.0 {
                continue;
            }
            let e = einout(u);
            let clo = lerp(self.d.tu_c0[0], cp[0], e);
            let cla = lerp(self.d.tu_c0[1], cp[1], e) + 1.2 * 4.0 * e * (1.0 - e);
            let ring = self.tu_copy(clo, cla);
            let pts = self.ring_px(&ring, c);
            let landed = u >= 1.0;
            let fa = if landed { 0.8 } else { 0.45 } * out;
            if k < 11 || !landed {
                let _ = write!(o.s, r#"<path d="{}" fill="{}" fill-opacity="{}"/>"#, pts_d(&pts, true), rgb(col.or), op(150.0 / 255.0 * fa));
            } else {
                for r12 in &self.d.tu_fill12 {
                    let _ = write!(o.s, r#"<path d="{}" fill="{}" fill-opacity="{}"/>"#, pts_d(&self.ring_px(r12, c), true), rgb(col.or), op(150.0 / 255.0 * fa));
                }
            }
            let _ = write!(o.s, r#"<path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{}" stroke-linejoin="round"/>"#,
                pts_d(&pts, true), rgb(col.hot), op(out), if landed { 3 } else { 2 });
            if landed {
                let mut cl = pts.clone();
                cl.push(pts[0]);
                o.glow_line(&cl, col.or, out * (0.4 + 0.6 * decay(t, launch(k) + self.d.tu_fly, 0.25)), 8.0);
            }
        }
    }

    // ---------------- timeline + year ----------------
    fn draw_timeline(&self, o: &mut Svg, t: f64, a: f64) {
        if a <= 0.003 {
            return;
        }
        let (x0, x1, yb, th) = (110.0, 1010.0, 1018.0, 180.0);
        let mo = &self.d.monthly;
        let mmax = mo.iter().cloned().fold(0.0, f64::max);
        let tl_x = |m: f64| x0 + (x1 - x0) * m / 168.0;
        let tl_y = |v: f64| yb - th * v / mmax;
        let mn = self.m_now(t).clamp(0.0, 168.0);
        let _ = write!(o.s, r#"<path d="M{x0} {yb}L{x1} {yb}" stroke="rgb(120,116,110)" stroke-opacity="{}" stroke-width="2"/>"#, op(150.0 / 255.0 * a));
        for y in 2012..2027 {
            let x = tl_x(((y - 2012) * 12) as f64);
            let _ = write!(o.s, r#"<path d="M{x:.1} {yb}L{x:.1} {}" stroke="rgb(150,146,140)" stroke-opacity="{}" stroke-width="2"/>"#,
                yb + if y % 4 == 0 { 12.0 } else { 6.0 }, op(170.0 / 255.0 * a));
            if [2012, 2016, 2020, 2024].contains(&y) {
                o.text(x + 4.0, yb + 52.0, &y.to_string(), F::Mono7, 48.0, self.d.colors.mu, a, 1.0, 0.0);
            }
        }
        let n = mn as usize;
        let mut pts = vec![(tl_x(0.0), yb)];
        for (i, v) in mo.iter().enumerate().take(n) {
            pts.push((tl_x(i as f64 + 0.5), tl_y(*v)));
        }
        if mn < 168.0 {
            let prev = if n > 0 { mo[n - 1] } else { 0.0 };
            pts.push((tl_x(mn), tl_y(lerp(prev, mo[n], clamp(mn - n as f64)))));
        } else {
            pts.push((tl_x(168.0), tl_y(mo[167])));
        }
        let last = *pts.last().unwrap();
        let mut poly = pts.clone();
        poly.push((last.0, yb));
        let _ = write!(o.s, r#"<path d="{}" fill="rgb(255,120,30)" fill-opacity="{}"/><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="4" stroke-linejoin="round"/>"#,
            pts_d(&poly, true), op(95.0 / 255.0 * a), pts_d(&pts, false), rgb(self.d.colors.am), op(a));
        o.glow_line(&pts, self.d.colors.or, a, 8.0);
        if mn < 168.0 {
            let x = tl_x(mn);
            let _ = write!(o.s, r#"<path d="M{x:.1} {}L{x:.1} {}" stroke="rgb(255,240,220)" stroke-opacity="{}" stroke-width="2"/><circle cx="{x:.1}" cy="{:.1}" r="8" fill="{}" opacity="{}"/>"#,
                yb + 4.0, yb - th - 18.0, op(120.0 / 255.0 * a), last.1, rgb(self.d.colors.hot), op(a));
        }
    }
    fn draw_year(&self, o: &mut Svg, t: f64, a: f64) {
        if a <= 0.003 {
            return;
        }
        let mn = self.m_now(t).clamp(0.0, 167.99);
        let s = if t >= self.tm().t_a1 { "2012–2025".to_string() } else { (2012 + (mn / 12.0) as i32).to_string() };
        o.text(self.d.tx - 6.0, 236.0, &s, F::Anton, 180.0, self.d.colors.wh, a, 1.0, 0.0);
    }

    /// the closing card: short source names in an aligned label/value grid, then the credits (Francisco, 13-10-2026)
    fn sources(&self, o: &mut Svg, t: f64) {
        let tm = self.tm();
        let a = clamp((t - tm.t_src) / 0.4);
        let (c, src, x) = (&self.d.colors, &self.d.sources, self.d.tx);
        let _ = write!(o.s, r#"<rect width="{W}" height="{H}" fill="{}" fill-opacity="{}"/>"#, rgb(self.d.bg), op(215.0 / 255.0 * a));
        let vx = x + 430.0;
        o.text(x, 140.0, &src.title, F::Anton, 64.0, c.or, a, 1.0, 0.0);
        for (i, (l, v)) in src.rows.iter().enumerate() {
            let ai = a * clamp((t - tm.t_src - 0.04 * i as f64) / 0.3);
            let y = 216.0 + i as f64 * 62.0;
            o.text(x, y, l, F::Inter, 48.0, c.mu, ai, 1.0, 0.0);
            o.text(vx, y, v, F::Inter, 48.0, c.wh, ai, 1.0, 0.0);
        }
        let yl = 216.0 + src.rows.len() as f64 * 62.0 - 22.0;
        let _ = write!(o.s, r#"<path d="M{x} {yl}L{} {yl}" stroke="{}" stroke-opacity="{}" stroke-width="2"/>"#, W - x, rgb(c.mu), op(0.35 * a));
        let y0 = yl + 82.0;
        o.text(x, y0, &src.credits_title, F::Anton, 64.0, c.or, a * clamp((t - tm.t_src - 0.3) / 0.3), 1.0, 0.0);
        for (i, (l, v)) in src.credits.iter().enumerate() {
            let ai = a * clamp((t - tm.t_src - 0.35 - 0.06 * i as f64) / 0.3);
            let y = y0 + 74.0 + i as f64 * 130.0;
            o.text(x, y, l, F::Inter, 48.0, c.mu, ai, 1.0, 0.0);
            o.text(x, y + 60.0, v, F::Inter, 48.0, c.wh, ai, 1.0, 0.0);
        }
    }

    fn left_shade(&self, s: &mut String, k: f64) {
        if k <= 0.003 {
            return;
        }
        // fx_v4.LSH: darkness(x) = clip(1 - (x/0.54)^4) * 0.94 (multiplied by k)
        let mut stops = String::new();
        for i in 0..=12 {
            let f = i as f64 / 12.0 * 0.6;
            let dk = (1.0 - (f / 0.54).powi(4)).clamp(0.0, 1.0) * 0.94 * k;
            let _ = write!(stops, r#"<stop offset="{:.3}" stop-color="black" stop-opacity="{}"/>"#, f, op(dk));
        }
        let _ = write!(s, r#"<linearGradient id="lsh" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient><rect width="{W}" height="{H}" fill="url(#lsh)"/>"#);
    }

    fn defs() -> String {
        let mut d = String::from("<defs>");
        // glow: v10 blurs its half-resolution glow layer by 9 and 26 px and weights them 0.9 / 0.8
        d.push_str(r#"<filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="1920" height="1080" color-interpolation-filters="sRGB"><feGaussianBlur in="SourceGraphic" stdDeviation="18" result="a"/><feGaussianBlur in="SourceGraphic" stdDeviation="52" result="b"/><feComposite in="a" in2="b" operator="arithmetic" k1="0" k2="0.9" k3="0.8" k4="0"/></filter>"#);
        d.push_str(r#"<filter id="bloom" filterUnits="userSpaceOnUse" x="0" y="0" width="1920" height="1080" color-interpolation-filters="sRGB"><feGaussianBlur in="SourceGraphic" stdDeviation="10" result="a"/><feGaussianBlur in="SourceGraphic" stdDeviation="36" result="b"/><feComposite in="a" in2="b" operator="arithmetic" k1="0" k2="1" k3="1" k4="0"/></filter>"#);
        d.push_str(r#"<filter id="rayglow" filterUnits="userSpaceOnUse" x="0" y="0" width="1920" height="1080" color-interpolation-filters="sRGB"><feGaussianBlur in="SourceGraphic" stdDeviation="12"/><feComponentTransfer><feFuncA type="linear" slope="2.2"/></feComponentTransfer></filter>"#);
        for b in BLURS {
            let _ = write!(d, r#"<filter id="b{b}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{b}"/></filter>"#);
        }
        // fx_v4.vignette: x (1 - 0.55 * clip(r - 0.45)^1.5), r = elliptical distance (corners ~1.41)
        d.push_str(r#"<radialGradient id="vig" cx="0.5" cy="0.5" r="0.7072">"#);
        for i in 0..=10 {
            let r = i as f64 / 10.0 * 1.4143;
            let dk = 0.55 * (r - 0.45).clamp(0.0, 1.0).powf(1.5);
            let _ = write!(d, r#"<stop offset="{:.3}" stop-color="black" stop-opacity="{:.4}"/>"#, i as f64 / 10.0, dk);
        }
        d.push_str("</radialGradient></defs>");
        d
    }

    fn finish(&self, o: &mut Svg, t: f64, flash: f64) {
        if !o.glow.is_empty() {
            let _ = write!(o.s, r#"<g filter="url(#glow)" style="mix-blend-mode:screen">{}</g>"#, o.glow);
        }
        if flash > 0.002 {
            let _ = write!(o.s, r#"<rect width="{W}" height="{H}" fill="white" opacity="{}" style="mix-blend-mode:screen"/>"#, op(0.55 * flash * 0.45));
        }
        let _ = write!(o.s, r#"<rect width="{W}" height="{H}" fill="url(#vig)"/><image href="grain_{}.png" x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="none" opacity="0.13" style="mix-blend-mode:hard-light"/>"#,
            ((t * 30.0).round() as usize) % 6);
    }

    /// render_v10.render_at, for the ported parts of the timeline
    pub fn render_at<'a>(&'a self, t: f64, frame: &mut Frame, ctx: &FFramesContext<'a, '_>) -> String {
        let tm = self.tm();
        let c = &self.d.colors;
        let mut o = Svg::new();
        o.s.push_str(&Self::defs());
        if !is_ported(t) {
            let _ = write!(o.s, r#"<rect width="{W}" height="{H}" fill="rgb(20,19,22)"/>"#);
            o.text(110.0, 560.0, "(no portado a fframes: ranking, paradas, Sentinel-2)", F::Inter, 48.0, c.mu, 1.0, 1.0, 0.0);
            return o.s;
        }
        if t < tm.t_x0 {
            self.space_frame(&mut o.s, t);
            self.draw_hook(&mut o, t);
            self.draw_intro_text(&mut o, t);
            self.finish(&mut o, t, 0.0);
            return o.s;
        }
        let cm = cam_at(&self.d, t);
        // the map layers are collected separately so the space frame can cross-fade under them
        let mut m = String::new();
        self.base_map(&mut m, &cm);
        if t < tm.t_land + 0.7 {
            self.heat_wash(&mut m, t, &cm);
            let (core, glow) = self.ray_layer(t, Some(&cm));
            self.light_svg(&mut m, &core, &glow);
            let cd = self.cut_dark(t);
            if cd < 0.999 {
                let _ = write!(m, r#"<rect width="{W}" height="{H}" fill="black" opacity="{}"/>"#, op(1.0 - cd));
            }
            self.draw_spark(&mut m, t, &cm);
        }
        if tm.t_land <= t && t < tm.t_scar + 0.6 {
            self.fire_layers(&mut m, t, &cm);
        }
        let sk = self.scar_layer(&mut m, t, &cm);
        self.close_embers(&mut m, t, &cm);
        if t < tm.t_map {
            let kx = einout((t - tm.t_x0) / (tm.t_map - tm.t_x0));
            self.space_frame(&mut o.s, t);
            let _ = write!(o.s, r#"<g opacity="{}">{m}</g>"#, op(kx));
        } else {
            o.s.push_str(&m);
        }
        self.left_shade(&mut o.s, 0.92 * clamp((t - tm.t_x0 - 0.2) / 0.5));
        self.draw_country(&mut o, t, &cm);
        self.draw_tucumanes(&mut o, t, &cm);
        let ui = clamp((t - tm.t_land) / 0.4) * (1.0 - clamp((t - tm.t_ash + 0.2) / 0.5));
        self.draw_year(&mut o, t, ui);
        self.draw_timeline(&mut o, t, ui);
        // legend (bottom-right)
        let la = clamp((t - tm.t_land - 0.3) / 0.4) * (1.0 - clamp((t - tm.t_cl + 0.3) / 0.4)) * (1.0 - clamp((t - tm.t_rk) / 0.3) * (1.0 - clamp((t - tm.t_rk_end) / 0.4)));
        if la > 0.003 {
            let tx = &self.d.texts;
            let _ = write!(o.s, r#"<text x="{}" y="{}" font-family="Inter600" font-size="48" fill="{}" text-anchor="end" opacity="{}">{}</text>"#, W - 80.0, H - 60.0, rgb(c.mu), op(la), esc(&tx.leg1));
            if sk > 0.0 {
                let _ = write!(o.s, r#"<text x="{}" y="{}" font-family="Inter600" font-size="48" fill="{}" text-anchor="end" opacity="{}">{}</text>"#, W - 80.0, H - 122.0, rgb(c.ash), op(la * sk), esc(&tx.leg2));
            }
        }
        self.draw_hook(&mut o, t);
        self.draw_intro_text(&mut o, t);
        let (x, tx) = (self.d.tx, &self.d.texts);
        if tm.t_scar - 0.05 <= t && t < tm.t_tu1 {
            // number_line: «26,6 MILLONES» slams on the scar boom, «DE HA» follows next to it
            let t1 = tm.t_tu1 - 0.3;
            self.slam(&mut o, x, 600.0, &tx.uniq, F::Anton, 150.0, c.wh, t, tm.t_scar, Some(t1), 0.4, true);
            let fq = FontQuery { family: "Anton", size: 150, weight: 400, ..Default::default() };
            let nw = frame.text_width(ctx, fq, self.uniq_static()).unwrap_or(780) as f64;
            self.slam(&mut o, x + nw + 26.0, 600.0, &tx.uniq_unit, F::Anton, 80.0, c.wh, t, tm.t_scar + 0.3, Some(t1), 0.0, false);
            self.slam(&mut o, x, 700.0, &tx.area, F::Anton, 66.0, c.or, t, tm.t_scar + 0.35, Some(tm.t_d1 - 0.3), 0.3, true);
            if t >= tm.t_d1 {
                self.slam(&mut o, x, 730.0, &tx.tucs, F::Anton, 90.0, c.or, t, tm.t_d1, Some(t1), 0.4, true);
            }
        }
        if tm.cl_l2 - 0.05 <= t && t < tm.t_src {
            let e = tm.t_src - 0.3;
            self.slam_tight(&mut o, x, 560.0, &tx.close1, F::Anton, 124.0, c.wh, t, tm.cl_l2, e, 0.35);
            self.slam_tight(&mut o, x, 704.0, &tx.close2, F::Anton, 124.0, c.or, t, tm.cl_l2 + 0.25, e, 0.6);
        }
        if t >= tm.t_src {
            self.sources(&mut o, t);
        }
        let flash = self.d.reveals.iter().map(|r| 0.3 * decay(t, *r, 0.11)).sum::<f64>().min(1.0);
        self.finish(&mut o, t, flash);
        o.s
    }

    fn uniq_static(&self) -> &str {
        &self.d.texts.uniq
    }
}

/// blur radii used by `filter="url(#bN)"` (rounded to these ids)
const BLURS: [u32; 8] = [3, 4, 6, 8, 12, 16, 24, 32];
fn blur_id(sigma: f64) -> u32 {
    *BLURS.iter().min_by(|a, b| ((**a as f64) - sigma).abs().partial_cmp(&((**b as f64) - sigma).abs()).unwrap()).unwrap()
}

impl Video for IncendiosVideo {
    const FPS: usize = 30;
    const WIDTH: usize = WIDTH;
    const HEIGHT: usize = HEIGHT;
    const BACKGROUND_COLOR: Color = Color::BLACK;

    fn duration(&self) -> Duration<'_> {
        Duration::Frames((self.d.total_new * 30.0).round() as usize)
    }

    fn audio(&self) -> AudioMap<'_> {
        // the mastered v10 score is muxed afterwards with ffmpeg (stream copy), so the loudness stays exactly −14 LUFS
        AudioMap::none()
    }

    fn render_frame<'a>(&'a self, mut frame: Frame, ctx: &FFramesContext<'a, '_>) -> Svgr<'a> {
        let t = frame.global_index as f64 / 30.0;
        let body = self.render_at(t, &mut frame, ctx);
        Svgr::from(format!(r#"<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">{body}</svg>"#))
    }
}
