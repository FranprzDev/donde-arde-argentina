//! The map and overlay layers of each beat (ported from render_v10.py).
use super::*;
use datavid::svg::blur_id;

const LIGHT: [f64; 3] = [-0.5631544, 0.2867004, 0.8088421]; // normalised (-0.55, 0.28, 0.79): the sun's direction

fn norm3(v: [f64; 3]) -> [f64; 3] {
    let n = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt();
    [v[0] / n, v[1] / n, v[2] / n]
}

fn seg(core: &mut String, p: (f64, f64), q: (f64, f64), v: f64) {
    let v = v.min(1.0);
    if v > 0.004 {
        let _ = write!(core, r#"<path d="M{:.1} {:.1}L{:.1} {:.1}" stroke-opacity="{}"/>"#, p.0, p.1, q.0, q.1, op(v));
    }
}

impl Incendios {
    // ---------------- opening: sun, globe, rays ----------------
    fn sun_state(&self, t: f64) -> (f64, f64, f64, f64) {
        let tau = t / self.tl.space_k;
        let rs = 900.0 * (-2.5 * tau).exp();
        let k = eout(tau / 1.3);
        (lerp(960.0, 330.0, k), lerp(540.0, 250.0, k), rs, 1.0 - clamp((tau - 1.9) / 0.5))
    }
    /// (cx, cy, R, lon0, lat0, flat)
    fn globe_state(&self, t: f64) -> Option<[f64; 6]> {
        let tau = t / self.tl.space_k;
        if tau < 0.45 {
            return None;
        }
        let ci = crate::timeline::CAM_IN;
        let r_final = ci[2] * 180.0 / std::f64::consts::PI;
        let ks = [0.45, 1.5, 2.35, 3.0, 3.7];
        let vs = [3.0f64, 70.0, 420.0, 1050.0, r_final].map(|v| v.ln());
        let re = interp(tau, &ks, &vs).exp();
        let kr = einout((tau - 0.45) / 2.6);
        Some([ci[3], ci[4], re, lerp(18.0, ci[0], kr), lerp(12.0, ci[1], kr), clamp((tau - 2.55) / 0.75)])
    }
    fn ortho(lon: f64, lat: f64, g: &[f64; 6]) -> (f64, f64, f64, f64, f64) {
        let (p, l, p0) = (lat.to_radians(), (lon - g[3]).to_radians(), g[4].to_radians());
        let x = p.cos() * l.sin();
        let y = p0.cos() * p.sin() - p0.sin() * p.cos() * l.cos();
        let z = p0.sin() * p.sin() + p0.cos() * p.cos() * l.cos();
        (g[0] + g[2] * x, g[1] - g[2] * y, x, y, z)
    }
    fn heat_level(&self, t: f64) -> f64 {
        clamp((t - 2.9) / 1.6) * (1.0 - clamp((t - self.tl.t_cool) / 0.5))
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
        let mut bins: Vec<String> = vec![String::new(); 8];
        for st in &self.g.stars {
            let (sx, sy, b) = (st[0], st[1], st[2]);
            let k = zoom * (0.6 + b);
            let (x, y) = (cx + sx * W * 0.5 * k, cy + sy * W * 0.5 * k);
            if !(-50.0 < x && x < W + 50.0 && -50.0 < y && y < H + 50.0) {
                continue;
            }
            let k2 = k - vel * (0.6 + b);
            let (x2, y2) = (cx + sx * W * 0.5 * k2, cy + sy * W * 0.5 * k2);
            let _ = write!(bins[((b * 8.0) as usize).min(7)], "M{x2:.1} {y2:.1}L{:.1} {:.1}", x + 0.01, y);
        }
        let vf = if vel > 0.01 { 0.5 } else { 1.0 };
        for (i, d) in bins.iter().enumerate() {
            if !d.is_empty() {
                let v = ((i as f64 + 0.5) / 8.0 * vf * a * 1.4).min(1.0);
                let _ = write!(s, r#"<path d="{d}" stroke="rgb(215,225,255)" stroke-opacity="{}" stroke-width="1.3" stroke-linecap="round" fill="none"/>"#, op(v));
            }
        }
    }

    fn draw_sun(&self, s: &mut String, t: f64) {
        let (sx, sy, rs, sa) = self.sun_state(t);
        if sa <= 0.003 || rs < 0.5 {
            return;
        }
        let half = self.a.sun_half * rs / self.a.sun_r;
        let _ = write!(s, r#"<image href="sun.png" x="{:.2}" y="{:.2}" width="{:.2}" height="{:.2}" opacity="{}" style="mix-blend-mode:screen"/>"#, sx - half, sy - half, 2.0 * half, 2.0 * half, op(sa));
    }

    fn draw_globe(&self, s: &mut String, t: f64, g: &[f64; 6]) {
        let (cx, cy, r, flat) = (g[0], g[1], g[2], g[5]);
        let a = clamp((t / self.tl.space_k - 0.45) / 0.15);
        let ocean = mixc([14, 34, 66], BG, flat);
        let landc = mixc([96, 88, 70], [18, 17, 20], flat);
        let _ = write!(s, r#"<g opacity="{}"><clipPath id="disc"><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}"/></clipPath><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}" fill="{}"/><g clip-path="url(#disc)">"#, op(a), rgb(ocean));
        if r > 1.5 {
            let mut d = String::new();
            for ring in &self.g.land {
                let mut vis = false;
                let mut pts = Vec::with_capacity(ring.len());
                for p in ring {
                    let (x, y, x3, y3, z3) = Self::ortho(p[0], p[1], g);
                    if z3 >= 0.0 {
                        vis = true;
                        pts.push((x, y));
                    } else {
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
        let (lx, ly) = (cx + r * LIGHT[0], cy - r * LIGHT[1]);
        let _ = write!(s, r#"<radialGradient id="shade" gradientUnits="userSpaceOnUse" cx="{lx:.1}" cy="{ly:.1}" r="{:.1}"><stop offset="0" stop-color="black" stop-opacity="0"/><stop offset="0.35" stop-color="black" stop-opacity="0.18"/><stop offset="0.62" stop-color="black" stop-opacity="0.72"/><stop offset="0.8" stop-color="black" stop-opacity="0.94"/></radialGradient><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}" fill="url(#shade)" opacity="{}"/>"#, r * 1.7, op(1.0 - flat));
        let _ = write!(s, r#"<radialGradient id="limb" gradientUnits="userSpaceOnUse" cx="{cx:.1}" cy="{cy:.1}" r="{r:.1}"><stop offset="0.72" stop-color="rgb(70,140,255)" stop-opacity="0"/><stop offset="0.93" stop-color="rgb(70,140,255)" stop-opacity="0.18"/><stop offset="1" stop-color="rgb(70,140,255)" stop-opacity="0.45"/></radialGradient><circle cx="{cx:.2}" cy="{cy:.2}" r="{r:.2}" fill="url(#limb)" opacity="{}" style="mix-blend-mode:screen"/></g></g>"#, op(1.0 - flat));
        if flat < 0.999 && r > 4.0 {
            let lw = (r * 0.035).max(6.0);
            let _ = write!(s, r#"<circle cx="{cx:.2}" cy="{cy:.2}" r="{:.2}" fill="none" stroke="rgb(70,140,255)" stroke-width="{lw:.1}" opacity="{}" filter="url(#b{})" style="mix-blend-mode:screen"/>"#, r + lw * 0.2, op(0.4 * (1.0 - flat) * a), blur_id(lw * 0.6));
        }
        let hk = self.heat_level(t) * (1.0 - flat * 0.3);
        if hk > 0.01 && r > 200.0 {
            let mut d = String::new();
            for ring in &self.g.ar_out {
                let pts: Vec<_> = ring.iter().map(|p| Self::ortho(p[0], p[1], g)).filter(|q| q.4 > 0.05).map(|q| (q.0, q.1)).collect();
                if pts.len() > 2 {
                    d.push_str(&pts_d(&pts, true));
                }
            }
            let _ = write!(s, r#"<path d="{d}" fill="rgb(120,50,10)" opacity="{}" filter="url(#b{})" style="mix-blend-mode:screen"/>"#, op(hk), blur_id((r / 160.0 * 4.0).max(8.0)));
        }
    }

    /// sunlight streaks that land on Argentina and glint back (one SVG fragment, drawn as core + glow)
    pub(super) fn ray_layer(&self, t: f64, cmap: Option<&Cam>) -> (String, String) {
        let mut core = String::new();
        let tl = &self.tl;
        if t > tl.t_cool + 0.4 || t < 0.7 {
            return (core, String::new());
        }
        let (sx, sy, rs, sa) = self.sun_state(t);
        let g = self.globe_state(t);
        let ray_a = 1.0 - clamp((t - tl.t_cool) / 0.35);
        let (travel, refl) = (0.32, 0.45);
        let d_in = {
            let (x, y) = (-LIGHT[0], LIGHT[1]);
            let n = x.hypot(y);
            (x / n, y / n)
        };
        let npts = self.g.ar_pts.len();
        let mut hits = String::new();
        for &(te, kind, p1, p2) in &self.g.rays {
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
                let pt = self.g.ar_pts[(p1.abs() * (npts - 1) as f64) as usize];
                let (x, y, x3, y3, z3) = Self::ortho(pt[0], pt[1], g);
                if z3 < 0.05 {
                    continue;
                }
                hit = (x, y);
                let dd = (g[0] - sx).hypot(g[1] - sy).max(1.0);
                start = (sx + (-(g[1] - sy)) / dd * p1 * rs * 0.35, sy + (g[0] - sx) / dd * p1 * rs * 0.35);
                let n3 = norm3([x3 + p1 * 0.4, y3 + 0.3, z3]);
                let dl = (hit.0 - start.0).hypot(hit.1 - start.1).max(1e-3);
                let d3 = norm3([(hit.0 - start.0) / dl, -(hit.1 - start.1) / dl, -0.25]);
                let dot = d3[0] * n3[0] + d3[1] * n3[1] + d3[2] * n3[2];
                let r3 = [d3[0] - 2.0 * dot * n3[0], d3[1] - 2.0 * dot * n3[1]];
                let rn = r3[0].hypot(r3[1]).max(1e-3);
                rr = (r3[0] / rn, -r3[1] / rn);
                v = 0.9 * sa * p2 + 0.3;
            } else {
                let pt = self.g.ar_pts[(p1 as usize).min(npts - 1)];
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
                        hit = proj(pt[0], pt[1], c);
                        [0.0, 0.0, 1.0]
                    }
                };
                let d3 = [-LIGHT[0], -LIGHT[1], -LIGHT[2]];
                let n3 = norm3([n3[0] + p2 * 0.6, n3[1] + 0.35, n3[2]]);
                let dot = d3[0] * n3[0] + d3[1] * n3[1] + d3[2] * n3[2];
                let r3 = [d3[0] - 2.0 * dot * n3[0], d3[1] - 2.0 * dot * n3[1]];
                let rn = r3[0].hypot(r3[1]).max(1e-3);
                rr = (r3[0] / rn, -r3[1] / rn);
                start = (hit.0 - d_in.0 * 1500.0, hit.1 - d_in.1 * 1500.0);
                v = 0.85 * ray_a;
            }
            if v <= 0.01 {
                continue;
            }
            let along = |k: f64| (start.0 + (hit.0 - start.0) * k, start.1 + (hit.1 - start.1) * k);
            if u <= 1.0 {
                seg(&mut core, along((u - 0.28).max(0.0)), along(u), v * (0.55 + 0.45 * u));
            } else {
                let w = (u - 1.0) * travel / refl;
                let tail = along((1.0 - 0.28 + 0.28 * eout(w * 1.6)).min(1.0));
                if (hit.0 - tail.0).hypot(hit.1 - tail.1) > 1.5 {
                    seg(&mut core, tail, hit, v * (1.0 - 0.5 * w));
                }
                let ln = if kind == 1 { 260.0 } else { 420.0 };
                let e = eout(w);
                let head = (hit.0 + rr.0 * ln * e, hit.1 + rr.1 * ln * e);
                let tl_ = (hit.0 + rr.0 * ln * (e - 0.35).max(0.0), hit.1 + rr.1 * ln * (e - 0.35).max(0.0));
                seg(&mut core, tl_, head, v * 0.7 * (1.0 - w));
                let _ = write!(hits, r#"<circle cx="{:.1}" cy="{:.1}" r="{:.1}" fill="none" stroke-width="2" stroke-opacity="{}"/><circle cx="{:.1}" cy="{:.1}" r="3" stroke="none" fill-opacity="{}"/>"#, hit.0, hit.1, 4.0 + 26.0 * e, op(v * (1.0 - w) * 0.9), hit.0, hit.1, op(v * 2.2 * (1.0 - w)));
            }
        }
        core.push_str(&hits);
        let glow = core.clone();
        (core, glow)
    }
    pub(super) fn light_svg(&self, s: &mut String, core: &str, glow: &str) {
        if !core.is_empty() {
            let _ = write!(s, r#"<g style="mix-blend-mode:screen" stroke="rgb(255,255,209)" fill="rgb(255,255,209)" stroke-width="2" stroke-linecap="round">{core}</g><g style="mix-blend-mode:screen" filter="url(#rayglow)" stroke="rgb(255,170,70)" fill="rgb(255,170,70)" stroke-width="3" stroke-linecap="round">{glow}</g>"#);
        }
    }

    pub(super) fn space_frame(&self, s: &mut String, t: f64) {
        let tau = t / self.tl.space_k;
        let _ = write!(s, r#"<rect width="{W}" height="{H}" fill="{}"/>"#, rgb(BG));
        self.draw_stars(s, tau, 0.9 * (1.0 - clamp((tau - 2.6) / 0.6)));
        self.draw_sun(s, t);
        if let Some(g) = self.globe_state(t) {
            self.draw_globe(s, t, &g);
        }
        let (core, glow) = self.ray_layer(t, None);
        self.light_svg(s, &core, &glow);
    }

    // ---------------- the flat map ----------------
    pub(super) fn base_map(&self, s: &mut String, c: &Cam) {
        let z = c[2];
        let _ = write!(s, r#"<rect width="{W}" height="{H}" fill="{}"/><g transform="{}"><path d="{}" fill="rgb(13,13,17)" stroke="rgb(34,34,40)" stroke-width="{:.5}"/><path d="{}" fill="rgb(20,19,22)"/><path d="{}" fill="none" stroke="rgb(62,60,64)" stroke-opacity="0.82" stroke-width="{:.5}"/></g>"#, rgb(BG), self.geo_tr(c), self.neigh_d, 1.0 / z, self.prov_all_d, self.prov_all_d, 1.0 / z);
    }
    pub(super) fn heat_wash(&self, s: &mut String, t: f64, c: &Cam) {
        let hk = self.heat_level(t);
        if hk > 0.01 {
            let _ = write!(s, r#"<g filter="url(#b6)" style="mix-blend-mode:screen"><g transform="{}"><path d="{}" fill="rgb(108,43,9)" opacity="{}"/></g></g>"#, self.geo_tr(c), self.ar_out_d, op(hk));
        }
    }
    pub(super) fn cut_dark(&self, t: f64) -> f64 {
        let tl = &self.tl;
        if !(tl.t_spark <= t && t < tl.t_land + 0.3) {
            return 1.0;
        }
        lerp(0.28, 1.0, eout((t - tl.t_spark - 0.08) / (tl.t_land + 0.3 - tl.t_spark - 0.08)))
    }
    pub(super) fn draw_spark(&self, s: &mut String, t: f64, c: &Cam) {
        let tl = &self.tl;
        if !(tl.t_spark - 0.05 <= t && t < tl.t_land + 0.6) {
            return;
        }
        let sp = self.ev_first;
        let (x, y) = proj(sp[0], sp[1], c);
        let u = t - tl.t_spark;
        let flick = 0.8 + 0.2 * (u * 37.0).sin() * (u * 23.0 + 1.0).sin();
        let grow = eout(u / 0.25) * (1.0 - clamp((t - tl.t_land - 0.1) / 0.5));
        let burst = decay(t, tl.t_spark, 0.12);
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
        let _ = write!(s, r#"<radialGradient id="spark" gradientUnits="userSpaceOnUse" cx="{x:.1}" cy="{y:.1}" r="{rmax}">{stops}</radialGradient><g style="mix-blend-mode:screen"><circle cx="{x:.1}" cy="{y:.1}" r="{rmax}" fill="url(#spark)"/><circle cx="{x:.1}" cy="{y:.1}" r="6" fill="rgb(255,250,230)" opacity="{}"/>"#, op(grow));
        for (k, e) in self.g.embers.iter().enumerate() {
            let uu = t - (tl.t_spark + e[0]);
            if (0.0..0.9).contains(&uu) {
                let ex = x + e[1] * uu + 6.0 * (uu * 9.0 + k as f64).sin();
                let ey = y + e[2] * uu;
                let _ = write!(s, r#"<circle cx="{ex:.1}" cy="{ey:.1}" r="2.2" fill="rgb(255,190,90)" opacity="{}"/><circle cx="{ex:.1}" cy="{ey:.1}" r="7" fill="rgb(255,190,90)" opacity="{}" filter="url(#b3)"/>"#, op(1.2 * (1.0 - uu / 0.9) * grow), op(0.9 * (1.0 - uu / 0.9) * grow));
            }
        }
        s.push_str("</g>");
    }

    /// the 14 fast years of VIIRS hotspots and their burn-out to ash
    pub(super) fn fire_layers(&self, s: &mut String, t: f64, c: &Cam) {
        let tl = &self.tl;
        let gb = self.a.grid_bbox;
        let acc = if t >= tl.t_a1 - 0.3 { (clamp((t - tl.t_a1 + 0.3) / 0.3) * (0.85 + 0.3 * decay(t, tl.t_a1, 0.6))).min(1.0) } else { 0.0 };
        let ash_k = clamp((t - tl.t_ash) / 0.9);
        let gone = clamp((t - tl.t_scar) / 0.6);
        let m = tl.m_now(t);
        if let Some(q) = self.a.ember_q.iter().rposition(|&mq| mq as f64 <= m + 1e-6) {
            s.push_str(&self.geo_image(&format!("ember_{q:02}.png"), gb, c, (1.0 - acc) * (1.0 - ash_k), "screen", false));
        }
        s.push_str(&self.geo_image("ash.png", gb, c, ash_k * (1.0 - gone), "screen", false));
        let mut f = String::new();
        if t < tl.t_a1 + 1.0 {
            for fr in &self.a.fresh {
                let dt = t - tl.warp(fr.median_month);
                if !(0.0..1.0).contains(&dt) {
                    continue;
                }
                let w = (-dt / 0.16).exp();
                f.push_str(&self.geo_image(&format!("fire_cool_{:03}.png", fr.m), fr.bbox, c, (3.0 * w).min(1.0), "screen", false));
                f.push_str(&self.geo_image(&format!("fire_hot_{:03}.png", fr.m), fr.bbox, c, w.powf(1.2), "screen", false));
            }
        }
        if acc > 0.0 {
            f.push_str(&self.geo_image("acc_full.png", gb, c, acc, "screen", false));
        }
        if !f.is_empty() && ash_k < 1.0 {
            let bloom_k = 0.9 * (1.0 + 0.6 * decay(t, tl.t_a1, 0.9));
            let _ = write!(s, r#"<g opacity="{}" style="mix-blend-mode:screen"><g style="isolation:isolate">{f}</g><g filter="url(#bloom)" opacity="{}" style="mix-blend-mode:screen">{f}</g></g>"#, op(1.0 - ash_k), op(bloom_k / 1.5));
        }
    }

    /// MODIS burned area (+ the Entre Ríos 2020 event at its stop); returns its visibility
    pub(super) fn scar_layer(&self, s: &mut String, t: f64, c: &Cam) -> f64 {
        let tl = &self.tl;
        let sk = clamp((t - tl.t_scar + 0.3) / 0.9);
        if sk <= 0.0 {
            return 0.0;
        }
        let mut dimk = if t < tl.t_d1 + 0.4 { 1.0 } else { 0.5 };
        dimk *= 1.0 - 0.55 * clamp((t - tl.t_rk) / 0.5) * (1.0 - clamp((t - tl.t_rk_end) / 0.6));
        dimk = lerp(dimk, 1.0, clamp((t - tl.t_cl + 0.4) / 1.0));
        dimk *= 1.0 - 0.75 * clamp((c[2] - 900.0) / 1500.0);
        let kw = 0.5 * decay(t, tl.t_scar, 0.8);
        // pyramid level: ~1 texel per screen pixel
        let texel = (1.0 / (c[2] * COS)) / crate::prep::modis::D;
        let lv = if texel < 4.0 { 1 } else { 3 };
        let bb = self.a.scar_levels.iter().find(|l| l.0 == lv).unwrap().1;
        s.push_str(&self.geo_image(&format!("scar_dark_l{lv}.png"), bb, c, sk, "", false));
        s.push_str(&self.geo_image(&format!("scar_col_l{lv}.png"), bb, c, sk * dimk * (1.0 - kw), "screen", false));
        s.push_str(&self.geo_image(&format!("scar_warm_l{lv}.png"), bb, c, sk * dimk * kw, "screen", false));
        let w = self.stop_w(t, 1);
        if w > 0.003 {
            let eb = self.a.events["er2020"];
            s.push_str(&self.geo_image("er2020_dark.png", eb, c, w, "", false));
            s.push_str(&self.geo_image("er2020_light.png", eb, c, w, "screen", false));
        }
        sk
    }

    /// choropleth: each province lights up when its row lands; in the top-5 phase the others dim
    pub(super) fn ranking_fill(&self, s: &mut String, t: f64, c: &Cam) {
        let tl = &self.tl;
        if !(tl.t_rk <= t && t < tl.t_rk_end + 0.8) {
            return;
        }
        let out = 1.0 - clamp((t - tl.t_rk_end + 0.1) / 0.6);
        let k2 = clamp((t - tl.t_rk2) / 0.5);
        let _ = write!(s, r#"<g transform="{}">"#, self.geo_tr(c));
        for r in &self.rows {
            let a = clamp((t - tl.rk_t_row(r.rank)) / 0.15);
            if a <= 0.0 {
                continue;
            }
            let al = if r.rank <= 5 { 0.78 } else { lerp(0.78, 0.22, k2) } * a * out;
            let col = if r.ha > 0.0 { self.rk_col(r.ha) } else { [40, 38, 40] };
            let _ = write!(s, r#"<path d="{}" fill="{}" fill-opacity="{}"/>"#, self.prov_d[&r.code], rgb(col), op(al));
        }
        s.push_str("</g>");
    }

    /// Comarca Andina: Sentinel-2 Dec 2024 → Apr 2025 → Apr 2026 wiped in place, then the MODIS 2025 / 2026 scars
    pub(super) fn comarca_layers(&self, s: &mut String, t: f64, c: &Cam, wpa: f64) {
        let p0 = self.tl.stops[2].0;
        let (from, to, k) = if t < p0 + 1.75 { ("comarca_2024", "comarca_2025", clamp((t - p0 - 0.7) / 0.45)) } else { ("comarca_2025", "comarca_2026", clamp((t - p0 - 1.85) / 0.45)) };
        let (x0, y0, x1, y1) = self.box_px(self.s2_box, c);
        let wipe = x0 + (x1 - x0) * k;
        let img = |n: &str| format!(r#"<image href="{n}.jpg" x="{x0:.2}" y="{y0:.2}" width="{:.2}" height="{:.2}" preserveAspectRatio="none"/>"#, x1 - x0, y1 - y0);
        let _ = write!(
            s,
            r#"<g opacity="{}"><clipPath id="wl"><rect x="{x0:.2}" y="{y0:.2}" width="{:.2}" height="{:.2}"/></clipPath><clipPath id="wr"><rect x="{wipe:.2}" y="{y0:.2}" width="{:.2}" height="{:.2}"/></clipPath><g clip-path="url(#wl)">{}</g><g clip-path="url(#wr)">{}</g><rect x="{x0:.2}" y="{y0:.2}" width="{:.2}" height="{:.2}" fill="black" opacity="0.1"/></g>"#,
            op(wpa),
            (wipe - x0).max(0.0),
            y1 - y0,
            (x1 - wipe).max(0.0),
            y1 - y0,
            img(to),
            img(from),
            x1 - x0,
            y1 - y0
        );
        for (name, on) in [("pat_2025", self.tl.pa_on.0), ("pat_2026", self.tl.pa_on.1)] {
            let kk = clamp((t - p0 - on) / 0.4) * wpa;
            if kk > 0.0 {
                let eb = self.a.events[name];
                s.push_str(&self.geo_image(&format!("{name}_dark.png"), eb, c, kk, "", true));
                s.push_str(&self.geo_image(&format!("{name}_light.png"), eb, c, kk, "screen", true));
            }
        }
    }
    pub(super) fn comarca_frame(&self, o: &mut Svg, t: f64, c: &Cam, wpa: f64) {
        let p0 = self.tl.stops[2].0;
        let (x0, y0, x1, y1) = self.box_px(self.s2_box, c);
        let a = wpa * clamp((t - p0 - 0.4) / 0.3);
        let _ = write!(o.s, r#"<rect x="{x0:.1}" y="{y0:.1}" width="{:.1}" height="{:.1}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="2"/>"#, x1 - x0, y1 - y0, rgb(WH), op(200.0 / 255.0 * a));
        let lab = if t < p0 + 0.92 { "comarca.date0" } else if t < p0 + 2.07 { "comarca.date1" } else { "comarca.date2" };
        let l = self.text(lab);
        o.text(x1 + 16.0, y0 + 48.0, &l.s, MONO8, l.size, WH, a, 1.0, 0.0);
        let sat = self.text("comarca.sat");
        o.text(x1 + 16.0, y0 + 106.0, &sat.s, INTER6, sat.size, MU, a, 1.0, 0.0);
        let (k25, k26) = (self.text("comarca.k25"), self.text("comarca.k26"));
        if t > p0 + self.tl.pa_on.0 {
            o.text(x1 + 16.0, y1 - 76.0, &k25.s, MONO8, k25.size, AM, a * clamp((t - p0 - self.tl.pa_on.0) / 0.3), 1.0, 0.0);
        }
        if t > p0 + self.tl.pa_on.1 {
            o.text(x1 + 16.0, y1 - 14.0, &k26.s, MONO8, k26.size, RD, a * clamp((t - p0 - self.tl.pa_on.1) / 0.3), 1.0, 0.0);
        }
    }

    // ---------------- Sentinel-2 views of Tucumán and the Delta, in place on the same map ----------------
    fn s2v_w(&self, t: f64, i: usize) -> f64 {
        let (_, _, z2) = self.tl.s2z[i];
        clamp((t - self.tl.stops[i].0 - 1.2) / 0.4) * (1.0 - clamp((t - z2 - self.tl.zout - 0.2) / 0.4))
    }
    fn s2v_label_a(&self, t: f64, i: usize) -> f64 {
        let (_, z1, z2) = self.tl.s2z[i];
        clamp((t - z1 + 0.15) / 0.25) * (1.0 - clamp((t - z2 + 0.05) / 0.25))
    }
    pub(super) fn s2v_layer(&self, s: &mut String, t: f64, c: &Cam, i: usize) {
        let w2 = self.s2v_w(t, i);
        if w2 <= 0.003 {
            return;
        }
        let name = ["tuc_2025-09-23", "delta_2020-09-23"][i];
        s.push_str(&self.geo_image(&format!("{name}.jpg"), self.s2v_bbox[i], c, w2, "", false));
        // that afternoon's VIIRS detections on top (same law as every other point in the video)
        let (_, z1, z2) = self.tl.s2z[i];
        let k = clamp((t - z1 - 0.2) / 0.5) * (1.0 - clamp((t - z2) / 0.4));
        if k <= 0.003 {
            return;
        }
        let (lon, lat) = &self.day[i];
        let (mut core, mut glow) = (String::new(), String::new());
        for (j, (x, y)) in lon.iter().zip(lat.iter()).enumerate() {
            let kk = clamp((t - z1 - 0.2 - 0.025 * j as f64) / 0.2) * k;
            if kk > 0.0 {
                let (px, py) = proj(*x, *y, c);
                let _ = write!(core, r#"<circle cx="{px:.1}" cy="{py:.1}" r="7" opacity="{}"/>"#, op(kk));
                let _ = write!(glow, r#"<circle cx="{px:.1}" cy="{py:.1}" r="16" opacity="{}"/>"#, op(kk));
            }
        }
        let _ = write!(s, r#"<g style="mix-blend-mode:screen"><g fill="rgb(255,110,30)" filter="url(#b8)">{glow}{glow}</g><g fill="rgb(255,236,170)">{core}</g></g>"#);
    }
    pub(super) fn s2v_frame(&self, o: &mut Svg, t: f64, c: &Cam, i: usize) {
        let w2 = self.s2v_w(t, i);
        let (_, z1, _) = self.tl.s2z[i];
        if w2 > 0.003 {
            let (x0, y0, x1, y1) = self.box_px(self.s2v_bbox[i], c);
            if t < z1 {
                let _ = write!(o.s, r#"<rect x="{:.1}" y="{:.1}" width="{:.1}" height="{:.1}" fill="none" stroke="rgb(8,6,6)" stroke-opacity="{}" stroke-width="3"/>"#, x0 - 3.0, y0 - 3.0, x1 - x0 + 6.0, y1 - y0 + 6.0, op(200.0 / 255.0 * w2));
                let _ = write!(o.s, r#"<rect x="{x0:.1}" y="{y0:.1}" width="{:.1}" height="{:.1}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="3"/>"#, x1 - x0, y1 - y0, rgb(HOT), op(240.0 / 255.0 * w2));
                o.glow_line(&[(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], AM, w2, 10.0);
            } else {
                let _ = write!(o.s, r#"<rect x="{x0:.1}" y="{y0:.1}" width="{:.1}" height="{:.1}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="2"/>"#, x1 - x0, y1 - y0, rgb(WH), op(240.0 / 255.0 * w2));
            }
        }
        let la2 = self.s2v_label_a(t, i);
        if la2 > 0.003 {
            let b = ["burruyacu", "delta"][i];
            let (l1, l2) = (self.text(&format!("{b}.l1")), self.text(&format!("{b}.l2")));
            o.text(TX, 470.0, &l1.s, MONO8, l1.size, AM, la2, 1.0, 0.0);
            o.text(TX, 550.0, &l2.s, INTER6, l2.size, WH, la2, 1.0, 0.0);
            if i == 1 {
                let (px, py) = proj(-60.68, -32.95, c); // Rosario
                let _ = write!(o.s, r#"<circle cx="{px:.1}" cy="{py:.1}" r="10" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="3"/>"#, rgb(WH), op(la2));
                let pin = self.text("delta.pin");
                o.text_halo(px + 22.0, py + 16.0, &pin.s, MONO8, pin.size, WH, [10, 8, 8], 2.0, la2);
            }
        }
    }

    /// the hotspots replayed inside each stop: one precomputed light raster per frame (`incendios assets`), placed in
    /// lon/lat so the camera's own small moves (shake, the zoom-out into the satellite crop) still apply
    pub(super) fn event_layer(&self, s: &mut String, t: f64, c: &Cam, i: usize) {
        let f = (t * 30.0).round() as usize;
        if let Some(bb) = self.a.ev_frames[i].get(&f) {
            s.push_str(&self.geo_image(&format!("ev{i}_{f:04}.png"), *bb, c, 1.0, "screen", false));
        }
    }

    /// the close: every VIIRS hotspot accumulates over the MODIS scar map
    pub(super) fn close_embers(&self, s: &mut String, t: f64, c: &Cam) {
        let tl = &self.tl;
        if t < tl.t_cl - 0.6 {
            return;
        }
        let hk = clamp((t - tl.t_cl - 0.1) / 1.5);
        let m = 168.0 * eout(hk);
        let Some(q) = self.a.ember_q.iter().rposition(|&mq| mq as f64 <= m + 1e-6) else { return };
        let a = clamp((t - tl.t_cl + 0.6) / 0.6) * (1.0 - 0.35 * clamp((t - tl.t_src) / 0.5));
        let img = self.geo_image(&format!("acc_{q:02}.png"), self.a.grid_bbox, c, a, "screen", false);
        let bk = 0.7 * (1.0 + 0.5 * decay(t, tl.t_cl + 1.6, 0.8));
        let _ = write!(s, r#"<g style="mix-blend-mode:screen">{img}<g filter="url(#bloom)" opacity="{}" style="mix-blend-mode:screen">{img}</g></g>"#, op(bk / 1.4));
    }

    /// the rest of the country dims around the stop province (Tucumán, Entre Ríos)
    pub(super) fn spotlight(&self, s: &mut String, t: f64, c: &Cam) {
        for i in 0..2 {
            let w = self.stop_w(t, i);
            if w <= 0.003 {
                continue;
            }
            let mut d = format!("M-20 -20H{}V{}H-20Z", W + 20.0, H + 20.0);
            for r in &self.g.stop_out[i] {
                d.push_str(&pts_d(&self.ring_px(r, c), true));
            }
            let _ = write!(s, r#"<path d="{d}" fill="rgb(0,0,8)" fill-rule="evenodd" opacity="{}" filter="url(#b8)"/>"#, op(0.25 * w));
        }
    }

    /// the whole of Argentina marked: every jurisdiction outlined from the first stop on, brightest in the close
    pub(super) fn draw_country(&self, o: &mut Svg, t: f64, c: &Cam) {
        let k = clamp((t - self.tl.stops[0].0 + self.tl.fly[0]) / 0.6);
        if k <= 0.003 {
            return;
        }
        let cw = self.close_w(t);
        let al = (70.0 + 150.0 * cw) * k / 255.0;
        let z = c[2];
        let _ = write!(o.s, r#"<g transform="{}"><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}" stroke-linejoin="round"/></g>"#, self.geo_tr(c), self.prov_all_d, rgb(AM), op(al), if cw < 0.5 { 2.0 } else { 3.0 } / z);
        if cw > 0.003 {
            let _ = write!(o.glow, r#"<g transform="{}"><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}"/><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}"/></g>"#, self.geo_tr(c), self.prov_all_d, rgb(AM), op(0.55 * cw), 6.0 / z, self.ar_out_d, rgb(OR), op(cw), 12.0 / z);
            let _ = write!(o.s, r#"<g transform="{}"><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{:.5}"/></g>"#, self.geo_tr(c), self.ar_out_d, rgb(HOT), op(230.0 / 255.0 * cw), 3.0 / z);
        }
    }

    fn draw_flags(&self, o: &mut Svg, names: &[&str], x: f64, y_mid: f64, a: f64, sc: f64) -> f64 {
        if a <= 0.003 {
            return x;
        }
        let mut x = x;
        let fh = 54.0 * sc;
        for n in names {
            let f = &self.flags[n];
            let fw = fh * f.vb[2] / f.vb[3];
            let y = y_mid - fh / 2.0;
            let _ = write!(
                o.s,
                r#"<g opacity="{}"><rect x="{:.1}" y="{:.1}" width="{fw:.1}" height="{fh:.1}" fill="black" opacity="0.66" filter="url(#b4)"/><svg x="{x:.1}" y="{y:.1}" width="{fw:.1}" height="{fh:.1}" viewBox="{} {} {} {}" preserveAspectRatio="none" overflow="hidden">{}</svg><rect x="{:.1}" y="{:.1}" width="{:.1}" height="{:.1}" fill="none" stroke="rgb(235,230,222)" stroke-opacity="0.78" stroke-width="2"/></g>"#,
                op(a),
                x + 3.0,
                y + 5.0,
                f.vb[0],
                f.vb[1],
                f.vb[2],
                f.vb[3],
                f.inner,
                x - 1.0,
                y - 1.0,
                fw + 1.0,
                fh + 1.0
            );
            x += fw + 14.0;
        }
        x
    }

    pub(super) fn draw_stop<'a>(&'a self, o: &mut Svg, t: f64, i: usize, c: &Cam, frame: &mut Frame, ctx: &FFramesContext<'a, '_>) {
        let (t0, t1) = self.tl.stops[i];
        let fly = self.tl.fly[i];
        let ao = clamp((t - t0 + fly) / 0.45) * (1.0 - clamp((t - t1 + 0.1) / 0.35));
        if ao > 0.0 && t0 - fly <= t && t < t1 + 0.4 {
            if i != 2 {
                for r in &self.g.stop_out[i] {
                    let mut pts = self.ring_px(r, c);
                    pts.push(pts[0]);
                    let _ = write!(o.s, r#"<path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="3" stroke-linejoin="round"/>"#, pts_d(&pts, false), rgb(AM), op(220.0 / 255.0 * ao));
                    o.glow_line(&pts, AM, ao, 10.0);
                }
            } else if t < t0 + 0.3 {
                let (x0, y0, x1, y1) = self.box_px(self.s2_box, c);
                let k = ao * (1.0 - clamp((t - t0) / 0.3));
                let _ = write!(o.s, r#"<rect x="{x0:.1}" y="{y0:.1}" width="{:.1}" height="{:.1}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="3"/>"#, x1 - x0, y1 - y0, rgb(AM), op(230.0 / 255.0 * k));
                o.glow_line(&[(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], AM, k, 10.0);
            }
        }
        if !(t0 - 0.2 <= t && t < t1 + 0.4) {
            return;
        }
        let a = clamp((t - t0 + 0.1) / 0.35) * (1.0 - clamp((t - t1 + 0.1) / 0.35));
        if i == 0 && a > 0.0 {
            for r in &self.g.tuc_zone {
                let mut pts = self.ring_px(r, c);
                pts.push(pts[0]);
                let _ = write!(o.s, r#"<path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="4" stroke-linejoin="round"/>"#, pts_d(&pts, false), rgb(HOT), op(a));
            }
        }
        let b = ["tucuman", "entre_rios", "comarca"][i];
        let head = self.text(&format!("{b}.head"));
        let (cb, ce) = (head.t0, head.t1);
        let u = t - cb;
        let fa = clamp(u / 0.2) * (1.0 - clamp((t - ce) / 0.3));
        let fsc = 1.0 + 0.12 * (1.0 - eout(u / 0.35));
        let names: &[&str] = match i {
            0 => &["tucuman"],
            1 => &["entre_rios"],
            _ => &["chubut", "rio_negro"],
        };
        let xe = if t >= cb { self.draw_flags(o, names, TX, 430.0 - 17.0 + (1.0 - eout(u / 0.35)) * 18.0, fa, fsc) } else { TX };
        o.slam(xe + 10.0, 430.0, &head.s, MONO8, head.size, AM, t, cb, Some(ce), 0.0, false);
        // the big number (counts up for Entre Ríos and the Comarca), its unit, the line
        let num = self.text(&format!("{b}.num"));
        let shown = if i == 0 {
            num.s.clone()
        } else {
            let target = if i == 1 { self.f.num("er_2020") } else { self.f.num("pa26") };
            datavid::facts::es_int((target * eout((t - num.t0) / 1.0)).round())
        };
        o.slam(TX, 600.0, &shown, ANTON, num.size, HOT, t, num.t0, Some(num.t1), 0.55, true);
        let nw = self.text_w(frame, ctx, ANTON, num.size, &num.s);
        self.slam_t(o, &format!("{b}.unit"), TX + nw + 26.0, 600.0, WH, t, 0.0, false);
        self.slam_t(o, &format!("{b}.line"), TX, 700.0, AM, t, 0.3, true);
    }

    pub(super) fn draw_ranking(&self, o: &mut Svg, t: f64, c: &Cam) {
        let tl = &self.tl;
        if !(tl.t_rk <= t && t < tl.t_rk_end + 0.4) {
            return;
        }
        let out = 1.0 - clamp((t - tl.t_rk_end + 0.3) / 0.35);
        let k2 = clamp((t - tl.t_rk2) / 0.45);
        for r in &self.rows {
            let tr = tl.rk_t_row(r.rank);
            let e = if t >= tr { decay(t, tr, 0.25) } else { 0.0 };
            let top = r.rank <= 5;
            let w = e.max(if top { k2 } else { 0.0 }) * out;
            if w > 0.02 {
                for ring in &self.g.prov[&r.code] {
                    let mut pts = self.ring_px(ring, c);
                    pts.push(pts[0]);
                    let _ = write!(o.s, r#"<path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{}" stroke-linejoin="round"/>"#, pts_d(&pts, false), rgb(if e > 0.5 { HOT } else { AM }), op(230.0 / 255.0 * w), if top { 3 } else { 2 });
                    o.glow_line(&pts, AM, w, 8.0);
                }
            }
        }
        if k2 <= 0.003 {
            return;
        }
        self.slam_t(o, "ranking.hdr", TX, 250.0, OR, t, 0.4, true);
        for j in 0..5 {
            let id = format!("ranking.r{}", j + 1);
            let tx = self.text(&id);
            if t < tx.t0 {
                continue;
            }
            let y = 400.0 + j as f64 * 112.0;
            let u = t - tx.t0;
            let a = clamp(u / 0.15) * out;
            o.slam(TX, y, &(j + 1).to_string(), ANTON, tx.size, OR, t, tx.t0, Some(tx.t1), 0.0, false);
            o.slam(TX + 70.0, y, &tx.s, ANTON, tx.size, WH, t, tx.t0, Some(tx.t1), 0.0, false);
            let frac = self.f.num(&format!("rk{}_frac", j + 1));
            let bw = (960.0 - TX - 70.0) * frac * eout(u / 0.4);
            let ba = a * (1.0 - clamp((t - tl.t_rk_end + 0.3) / 0.3));
            let _ = write!(o.s, r#"<rect x="{}" y="{}" width="{bw:.1}" height="10" fill="{}" opacity="{}"/>"#, TX + 70.0, y + 18.0, rgb(self.rk_col(self.rows[j].ha)), op(ba));
        }
        // rank numbers on the map
        let lab = self.text("ranking.ranks");
        for (j, r) in self.rows.iter().take(5).enumerate() {
            let lp = self.g.label_pt[&r.code];
            let (lx, ly) = proj(lp[0], lp[1], c);
            let aa = k2 * out * clamp((t - tl.t_rk2 - 0.25 - j as f64 * 0.09) / 0.2);
            if aa > 0.003 {
                let s = (j + 1).to_string();
                let _ = write!(o.s, r#"<text x="{lx:.1}" y="{:.1}" font-family="Anton" font-size="{}" fill="{}" stroke="rgb(12,10,10)" stroke-width="6" stroke-linejoin="round" paint-order="stroke" text-anchor="middle" opacity="{}">{s}</text>"#, ly + 20.0, lab.size, rgb(WH), op(aa));
            }
        }
    }

    pub(super) fn draw_tucumanes(&self, o: &mut Svg, t: f64, c: &Cam) {
        let tl = &self.tl;
        if !(tl.t_d1 - 0.2 <= t && t < tl.t_tu1 + 0.2) {
            return;
        }
        let out = 1.0 - clamp((t - tl.t_tu1 + 0.25) / 0.35);
        let src = clamp((t - tl.t_d1 + 0.2) / 0.2) * out * (1.0 - 0.85 * clamp((t - tl.tu_launch(11)) / 0.4));
        let pts = self.ring_px(&self.g.tu_ring, c);
        let mut closed = pts.clone();
        closed.push(pts[0]);
        let _ = write!(o.s, r#"<path d="{}" fill="{}" fill-opacity="{}" stroke="{}" stroke-opacity="{}" stroke-width="3" stroke-linejoin="round"/>"#, pts_d(&pts, true), rgb(HOT), op(110.0 / 255.0 * src), rgb(HOT), op(src));
        o.glow_line(&closed, OR, src, 10.0);
        let c0 = self.g.tu_c0;
        for (k, cp) in self.g.tu_copies.iter().enumerate() {
            let u = (t - tl.tu_launch(k)) / tl.tu_fly;
            if u <= 0.0 {
                continue;
            }
            let e = einout(u);
            let (clo, cla) = (lerp(c0[0], cp[0], e), lerp(c0[1], cp[1], e) + 1.2 * 4.0 * e * (1.0 - e));
            let ring = crate::prep::tucumanes::copy_at(&self.g.tu_ring, c0, clo, cla);
            let pts = self.ring_px(&ring, c);
            let landed = u >= 1.0;
            let fa = if landed { 0.8 } else { 0.45 } * out;
            if k < 11 || !landed {
                let _ = write!(o.s, r#"<path d="{}" fill="{}" fill-opacity="{}"/>"#, pts_d(&pts, true), rgb(OR), op(150.0 / 255.0 * fa));
            } else {
                for r12 in &self.g.tu_fill12 {
                    let _ = write!(o.s, r#"<path d="{}" fill="{}" fill-opacity="{}"/>"#, pts_d(&self.ring_px(r12, c), true), rgb(OR), op(150.0 / 255.0 * fa));
                }
            }
            let _ = write!(o.s, r#"<path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="{}" stroke-linejoin="round"/>"#, pts_d(&pts, true), rgb(HOT), op(out), if landed { 3 } else { 2 });
            if landed {
                let mut cl = pts.clone();
                cl.push(pts[0]);
                o.glow_line(&cl, OR, out * (0.4 + 0.6 * decay(t, tl.tu_launch(k) + tl.tu_fly, 0.25)), 8.0);
            }
        }
    }
}
