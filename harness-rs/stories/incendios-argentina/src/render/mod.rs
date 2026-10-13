//! The picture: every frame is one SVG document built from the story (texts and marks), the facts, the derived data and
//! the asset rasters, rasterised by fframes (CPU backend: tiny-skia) and encoded with libx264. The look follows the v10
//! Python renderer beat by beat (space opening, the spark, the 14-year timelapse, the scar and the 12 Tucumanes, the
//! ranking, the three stops with their Sentinel-2 zooms, the close) plus the new sources/credits card.
mod geom;
mod layers;

use crate::prep::{read_json, viirs};
use crate::timeline::{Cam, Events, Tl, proj};
use anyhow::{Context, Result};
use datavid::ease::*;
use datavid::svg::{self, Font, Rgb, Svg, mixc, op, pts_d, rgb};
use datavid::{Facts, Story};
use fframes::{AudioMap, Color, Duration, FFramesContext, FontQuery, Frame, Svgr, Video};
use geom::{AssetMeta, Flag, Geom, ring_unit_d};
use std::collections::HashMap;
use std::fmt::Write;
use std::process::ExitCode;

pub const W: f64 = 1920.0;
pub const H: f64 = 1080.0;
pub const TX: f64 = 110.0;
pub const BG: Rgb = [6, 6, 9];
pub const WH: Rgb = [242, 240, 236];
pub const MU: Rgb = [190, 182, 172];
pub const AM: Rgb = [255, 176, 60];
pub const OR: Rgb = [255, 110, 30];
pub const RD: Rgb = [255, 64, 40];
pub const HOT: Rgb = [255, 226, 160];
pub const ASH: Rgb = [150, 142, 134];
const COS: f64 = crate::timeline::COS;

pub const ANTON: Font = Font { family: "Anton", weight: 400, cap: 1760.0 / 2048.0 };
pub const INTER6: Font = Font { family: "Inter", weight: 600, cap: 1490.0 / 2048.0 };
pub const INTER5: Font = Font { family: "Inter", weight: 500, cap: 1490.0 / 2048.0 };
pub const MONO7: Font = Font { family: "JetBrains Mono", weight: 700, cap: 0.73 };
pub const MONO8: Font = Font { family: "JetBrains Mono", weight: 800, cap: 0.73 };

pub struct RankRow {
    pub code: String,
    pub rank: usize,
    pub ha: f64,
}

pub struct Incendios {
    pub st: Story,
    pub f: Facts,
    pub tl: Tl,
    pub g: Geom,
    pub a: AssetMeta,
    pub ev: Events,
    pub day: [(Vec<f64>, Vec<f64>); 2],
    pub s2v_bbox: [[f64; 4]; 2],
    pub s2_box: [f64; 4],
    pub flags: HashMap<&'static str, Flag>,
    pub rows: Vec<RankRow>,
    pub lut: Vec<[f32; 3]>,
    pub neigh_d: String,
    pub prov_all_d: String,
    pub prov_d: HashMap<String, String>,
    pub ar_out_d: String,
    pub legend_gap: Option<(f64, f64)>,
    /// VIIRS hotspots per month (the timeline chart and the score's crackle)
    pub monthly: Vec<f64>,
    /// the first VIIRS hotspot of the series (Jan 2012): where the spark lands
    pub ev_first: [f64; 2],
}

impl std::fmt::Debug for Incendios {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Incendios").finish()
    }
}

pub fn font_of(name: &str) -> Font {
    match name {
        "anton" => ANTON,
        "inter500" => INTER5,
        "mono700" => MONO7,
        "mono800" => MONO8,
        _ => INTER6,
    }
}

impl Incendios {
    pub fn new(st: Story, f: Facts) -> Result<Self> {
        let b = st.build_dir();
        let d = crate::prep::derived(&st.dir);
        let a = AssetMeta::load(&b.join("assets.json"))?;
        let s2v_bbox = [a.s2["tuc_2025-09-23"], a.s2["delta_2020-09-23"]];
        let s2_box = a.s2["comarca_2024"];
        let tl = Tl::new(&st, s2v_bbox);
        let g = Geom::load(&d.join("geometry.json"))?;
        let pts = viirs::load(&d.join("points.bin"))?;
        let ev = crate::timeline::events(&tl, &pts, &g.codes);
        let mut monthly = vec![0.0; 168];
        for p in &pts {
            monthly[(p.t.floor() as usize).min(167)] += 1.0;
        }
        let ev_first = [pts[0].lon as f64, pts[0].lat as f64];
        drop(pts);
        let sd = read_json(&d.join("s2_day.json"))?;
        let arr = |v: &serde_json::Value| v.as_array().unwrap().iter().map(|x| x.as_f64().unwrap()).collect::<Vec<_>>();
        let day = [(arr(&sd["tuc"]["lon"]), arr(&sd["tuc"]["lat"])), (arr(&sd["er"]["lon"]), arr(&sd["er"]["lat"]))];
        let fd = st.input("flags_dir")?;
        let mut flags = HashMap::new();
        for n in ["tucuman", "entre_rios", "chubut", "rio_negro"] {
            flags.insert(n, geom::load_flag(&fd.join(format!("{n}.svg")), &format!("fl_{n}"))?);
        }
        let rk = read_json(&d.join("ranking.json"))?;
        let rows = rk["rows"].as_array().unwrap().iter().map(|r| RankRow { code: r["code"].as_str().unwrap().to_string(), rank: r["rank"].as_u64().unwrap() as usize, ha: r["ha_unique"].as_f64().unwrap() }).collect();
        let neigh_d = g.neigh.iter().map(|r| ring_unit_d(r, COS)).collect();
        let prov_d: HashMap<String, String> = g.codes.iter().map(|c| (c.clone(), g.prov[c].iter().map(|r| ring_unit_d(r, COS)).collect())).collect();
        let prov_all_d = g.codes.iter().map(|c| prov_d[c].clone()).collect();
        let ar_out_d = g.ar_out.iter().map(|r| ring_unit_d(r, COS)).collect();
        let mut me = Self { st, f, tl, g, a, ev, day, s2v_bbox, s2_box, flags, rows, lut: crate::assets::fire_lut(), neigh_d, prov_all_d, prov_d, ar_out_d, legend_gap: None, monthly, ev_first };
        me.legend_gap = me.compute_legend_gap();
        Ok(me)
    }

    /// frames where the Comarca Sentinel-2 frame would cover the legend (bottom right): the legend steps aside
    fn compute_legend_gap(&self) -> Option<(f64, f64)> {
        let s0 = self.tl.stops[2].0;
        let (a, b) = (((s0 - self.tl.fly[2] - 0.2) * 30.0) as i64, ((s0 + 1.0) * 30.0) as i64);
        let ov: Vec<f64> = (a..b)
            .map(|f| f as f64 / 30.0)
            .filter(|&t| {
                let (x0, y0, x1, y1) = self.box_px(self.s2_box, &self.tl.cam_at(t));
                x1 > W - 960.0 && x0 < W - 60.0 && y1 > H - 170.0 && y0 < H - 30.0
            })
            .collect();
        if ov.is_empty() { None } else { Some((ov[0], *ov.last().unwrap())) }
    }

    pub fn text(&self, id: &str) -> &datavid::story::Text {
        self.st.text(id)
    }
    /// draw a story text with the slam entrance at its own t0/t1
    #[allow(clippy::too_many_arguments)]
    fn slam_t(&self, o: &mut Svg, id: &str, x: f64, y: f64, col: Rgb, t: f64, glow: f64, big: bool) {
        let tx = self.text(id);
        o.slam(x, y, &tx.s, font_of(&tx.font), tx.size, col, t, tx.t0, Some(tx.t1), glow, big);
    }

    fn geo_tr(&self, c: &Cam) -> String {
        let z = c[2];
        format!("matrix({z:.5} 0 0 {z:.5} {:.3} {:.3})", c[3] - c[0] * COS * z, c[4] + c[1] * z)
    }
    fn ring_px(&self, r: &[[f64; 2]], c: &Cam) -> Vec<(f64, f64)> {
        r.iter().map(|p| proj(p[0], p[1], c)).collect()
    }
    fn box_px(&self, b: [f64; 4], c: &Cam) -> (f64, f64, f64, f64) {
        let (x0, y0) = proj(b[0], b[3], c);
        let (x1, y1) = proj(b[2], b[1], c);
        (x0, y0, x1, y1)
    }
    /// a georeferenced raster drawn under camera c
    fn geo_image(&self, href: &str, bbox: [f64; 4], c: &Cam, opacity: f64, blend: &str, nearest: bool) -> String {
        if opacity <= 0.003 {
            return String::new();
        }
        let (x0, y0, x1, y1) = self.box_px(bbox, c);
        if x1 < -50.0 || y1 < -50.0 || x0 > W + 50.0 || y0 > H + 50.0 {
            return String::new();
        }
        let style = if blend.is_empty() { String::new() } else { format!(r#" style="mix-blend-mode:{blend}""#) };
        let ir = if nearest { r#" image-rendering="optimizeSpeed""# } else { "" };
        format!(r#"<image href="{href}" x="{x0:.2}" y="{y0:.2}" width="{:.2}" height="{:.2}" preserveAspectRatio="none" opacity="{}"{style}{ir}/>"#, x1 - x0, y1 - y0, op(opacity))
    }
    fn stop_w(&self, t: f64, i: usize) -> f64 {
        let (t0, t1) = self.tl.stops[i];
        clamp((t - t0 + 0.3) / 0.5) * (1.0 - clamp((t - t1 + 0.2) / 0.5))
    }
    fn close_w(&self, t: f64) -> f64 {
        clamp((t - self.tl.t_cl - 0.2) / 0.8) * (1.0 - clamp((t - self.tl.t_src) / 0.5))
    }
    fn rk_col(&self, v: f64) -> Rgb {
        let vmax = self.rows[0].ha;
        let c = self.lut[(70.0 + 140.0 * (v / vmax).powf(0.55)) as usize];
        [c[0] as u8, c[1] as u8, c[2] as u8]
    }
    fn text_w(&self, frame: &mut Frame, ctx: &FFramesContext, f: Font, size: f64, s: &str) -> f64 {
        let fq = FontQuery { family: f.family, size: size as _, weight: f.weight as _, ..Default::default() };
        frame.text_width(ctx, fq, s).map(|w| w as f64).unwrap_or(size * 0.5 * s.chars().count() as f64)
    }

    /// render_v10.render_at, ported
    pub fn render_at(&self, t: f64, frame: &mut Frame, ctx: &FFramesContext) -> String {
        let tl = &self.tl;
        let mut o = Svg::new();
        o.s.push_str(&svg::defs(W, H));
        let fi = frame.global_index;
        if t < tl.t_x0 {
            self.space_frame(&mut o.s, t);
            self.draw_hook(&mut o, t);
            self.draw_intro_text(&mut o, t);
            o.finish(W, H, fi, 0.0, true);
            return o.s;
        }
        let cm = tl.cam_at(t);
        let mut m = String::new();
        self.base_map(&mut m, &cm);
        if t < tl.t_land + 0.7 {
            self.heat_wash(&mut m, t, &cm);
            let (core, glow) = self.ray_layer(t, Some(&cm));
            self.light_svg(&mut m, &core, &glow);
            let cd = self.cut_dark(t);
            if cd < 0.999 {
                let _ = write!(m, r#"<rect width="{W}" height="{H}" fill="black" opacity="{}"/>"#, op(1.0 - cd));
            }
            self.draw_spark(&mut m, t, &cm);
        }
        if tl.t_land <= t && t < tl.t_scar + 0.6 {
            self.fire_layers(&mut m, t, &cm);
        }
        let sk = self.scar_layer(&mut m, t, &cm);
        self.ranking_fill(&mut m, t, &cm);
        let wpa = self.stop_w(t, 2);
        if wpa > 0.003 {
            self.comarca_layers(&mut m, t, &cm, wpa);
        }
        for i in 0..2 {
            self.s2v_layer(&mut m, t, &cm, i);
        }
        for i in 0..3 {
            self.event_layer(&mut m, t, &cm, i);
        }
        self.close_embers(&mut m, t, &cm);
        self.spotlight(&mut m, t, &cm);
        if t < tl.t_map {
            let kx = einout((t - tl.t_x0) / (tl.t_map - tl.t_x0));
            self.space_frame(&mut o.s, t);
            let _ = write!(o.s, r#"<g opacity="{}">{m}</g>"#, op(kx));
        } else {
            o.s.push_str(&m);
        }
        svg::left_shade(&mut o.s, W, H, 0.92 * clamp((t - tl.t_x0 - 0.2) / 0.5));
        if wpa > 0.003 {
            self.comarca_frame(&mut o, t, &cm, wpa);
        }
        for i in 0..2 {
            self.s2v_frame(&mut o, t, &cm, i);
        }
        self.draw_country(&mut o, t, &cm);
        for i in 0..3 {
            self.draw_stop(&mut o, t, i, &cm, frame, ctx);
        }
        self.draw_ranking(&mut o, t, &cm);
        self.draw_tucumanes(&mut o, t, &cm);
        let ui = clamp((t - tl.t_land) / 0.4) * (1.0 - clamp((t - tl.t_ash + 0.2) / 0.5));
        self.draw_year(&mut o, t, ui);
        self.draw_timeline(&mut o, t, ui);
        self.draw_legend(&mut o, t, sk);
        self.draw_hook(&mut o, t);
        self.draw_intro_text(&mut o, t);
        if tl.t_scar - 0.05 <= t && t < tl.t_tu1 {
            self.slam_t(&mut o, "scar.uniq", TX, 600.0, WH, t, 0.4, true);
            let num = self.text("scar.uniq");
            let nw = self.text_w(frame, ctx, ANTON, num.size, &num.s);
            self.slam_t(&mut o, "scar.unit", TX + nw + 26.0, 600.0, WH, t, 0.0, false);
            self.slam_t(&mut o, "scar.tucs", TX, 728.0, OR, t, 0.4, true);
        }
        if tl.cl_l2 - 0.05 <= t && t < tl.t_src {
            let (l1, l2) = (self.text("cierre.l1"), self.text("cierre.l2"));
            o.slam_tight(TX, 560.0, &l1.s, ANTON, l1.size, WH, t, l1.t0, l1.t1, 0.35);
            o.slam_tight(TX, 704.0, &l2.s, ANTON, l2.size, OR, t, l2.t0, l2.t1, 0.6);
        }
        if t >= tl.t_src {
            self.sources(&mut o, t);
        }
        let flash = tl.reveals.iter().map(|r| 0.3 * decay(t, *r, 0.11)).sum::<f64>().min(1.0);
        o.finish(W, H, fi, flash, true);
        o.s
    }

    fn draw_hook(&self, o: &mut Svg, t: f64) {
        let (h0, h1) = self.tl.t_hook;
        if !(h0 <= t && t < h1 + 0.4) {
            return;
        }
        self.slam_t(o, "intro.hook1", TX, 820.0, WH, t, 0.25, true);
        self.slam_t(o, "intro.hook2", TX, 962.0, OR, t, 0.6, true);
    }

    fn draw_intro_text(&self, o: &mut Svg, t: f64) {
        let tl = &self.tl;
        if tl.t_txt1 <= t && t < tl.t_spark {
            // no fade: both lines vanish on the frame of the hard cut
            let (a, b) = (self.text("intro.sol"), self.text("intro.sol2"));
            o.slam(TX, 420.0, &a.s, ANTON, a.size, WH, t, a.t0, None, 0.0, false);
            o.slam(TX, 560.0, &b.s, ANTON, b.size, WH, t, b.t0, None, 0.0, false);
        }
        if tl.t_nos <= t && t < tl.t_txt2_end + 0.4 {
            let n = self.text("spark.nos");
            o.slam_tight(TX, 560.0, &n.s, ANTON, n.size, OR, t, n.t0, n.t1, 0.6);
            self.slam_t(o, "spark.causa", TX, 668.0, WH, t, 0.0, false);
        }
    }

    fn draw_legend(&self, o: &mut Svg, t: f64, sk: f64) {
        let tl = &self.tl;
        let mut la = clamp((t - tl.t_land - 0.3) / 0.4) * (1.0 - clamp((t - tl.t_cl + 0.3) / 0.4)) * (1.0 - clamp((t - tl.t_rk) / 0.3) * (1.0 - clamp((t - tl.t_rk_end) / 0.4)));
        if let Some((g0, g1)) = self.legend_gap {
            la *= clamp((g0 - 0.05 - t) / 0.25).max(clamp((t - g1 - 0.05) / 0.3));
        }
        for (z0, _, z2) in tl.s2z {
            la *= 1.0 - clamp((t - z0 + 0.3) / 0.3) * (1.0 - clamp((t - z2 - tl.zout) / 0.3));
        }
        if la > 0.003 {
            let l1 = self.text("spark.legend1");
            o.text_a(W - 80.0, H - 60.0, &l1.s, INTER6, l1.size, MU, la, 1.0, 0.0, "end");
            if sk > 0.0 {
                let l2 = self.text("scar.legend2");
                o.text_a(W - 80.0, H - 122.0, &l2.s, INTER6, l2.size, ASH, la * sk, 1.0, 0.0, "end");
            }
        }
    }

    fn draw_year(&self, o: &mut Svg, t: f64, a: f64) {
        if a <= 0.003 {
            return;
        }
        let mn = self.tl.m_now(t).clamp(0.0, 167.99);
        let y0 = self.f.num("y0") as i64;
        let s = if t >= self.tl.t_a1 { self.text("spark.years").s.clone() } else { (y0 + (mn / 12.0) as i64).to_string() };
        o.text(TX - 6.0, 236.0, &s, ANTON, 180.0, WH, a, 1.0, 0.0);
    }

    fn draw_timeline(&self, o: &mut Svg, t: f64, a: f64) {
        if a <= 0.003 {
            return;
        }
        let (x0, x1, yb, th) = (110.0, 1010.0, 1018.0, 180.0);
        let mo = &self.monthly;
        let mmax = mo.iter().cloned().fold(0.0, f64::max);
        let tl_x = |m: f64| x0 + (x1 - x0) * m / 168.0;
        let tl_y = |v: f64| yb - th * v / mmax;
        let mn = self.tl.m_now(t).clamp(0.0, 168.0);
        let y0 = self.f.num("y0") as i64;
        let _ = write!(o.s, r#"<path d="M{x0} {yb}L{x1} {yb}" stroke="rgb(120,116,110)" stroke-opacity="{}" stroke-width="2"/>"#, op(150.0 / 255.0 * a));
        for k in 0..15 {
            let y = y0 + k;
            let x = tl_x((k * 12) as f64);
            let _ = write!(o.s, r#"<path d="M{x:.1} {yb}L{x:.1} {}" stroke="rgb(150,146,140)" stroke-opacity="{}" stroke-width="2"/>"#, yb + if y % 4 == 0 { 12.0 } else { 6.0 }, op(170.0 / 255.0 * a));
            if k % 4 == 0 {
                o.text(x + 4.0, yb + 52.0, &y.to_string(), MONO7, 48.0, MU, a, 1.0, 0.0);
            }
        }
        let n = mn as usize;
        let mut pts = vec![(tl_x(0.0), yb)];
        for (i, v) in mo.iter().enumerate().take(n) {
            pts.push((tl_x(i as f64 + 0.5), tl_y(*v)));
        }
        if mn < 168.0 {
            let prev = if n > 0 { mo[n - 1] } else { 0.0 };
            pts.push((tl_x(mn), tl_y(lerp(prev, mo[n.min(167)], clamp(mn - n as f64)))));
        } else {
            pts.push((tl_x(168.0), tl_y(mo[167])));
        }
        let last = *pts.last().unwrap();
        let mut poly = pts.clone();
        poly.push((last.0, yb));
        let _ = write!(o.s, r#"<path d="{}" fill="rgb(255,120,30)" fill-opacity="{}"/><path d="{}" fill="none" stroke="{}" stroke-opacity="{}" stroke-width="4" stroke-linejoin="round"/>"#, pts_d(&poly, true), op(95.0 / 255.0 * a), pts_d(&pts, false), rgb(AM), op(a));
        o.glow_line(&pts, OR, a, 8.0);
        if mn < 168.0 {
            let x = tl_x(mn);
            let _ = write!(o.s, r#"<path d="M{x:.1} {}L{x:.1} {}" stroke="rgb(255,240,220)" stroke-opacity="{}" stroke-width="2"/><circle cx="{x:.1}" cy="{:.1}" r="8" fill="{}" opacity="{}"/>"#, yb + 4.0, yb - th - 18.0, op(120.0 / 255.0 * a), last.1, rgb(HOT), op(a));
        }
    }

    /// the closing card: short source names in an aligned label/value grid, a rule, then the credits (label over value)
    fn sources(&self, o: &mut Svg, t: f64) {
        let tl = &self.tl;
        let a = clamp((t - tl.t_src) / 0.4);
        let _ = write!(o.s, r#"<rect width="{W}" height="{H}" fill="{}" fill-opacity="{}"/>"#, rgb(BG), op(225.0 / 255.0 * a));
        let size = self.st.texts.iter().find(|x| x.beat == "fuentes").map(|x| x.size).unwrap_or(52.0);
        let vx = TX + 330.0;
        let mut y = 300.0;
        for (i, lv) in self.st.file.sources.iter().enumerate() {
            let ai = a * clamp((t - tl.t_src - 0.05 * i as f64) / 0.3);
            o.text(TX, y, &lv.label, INTER6, size, MU, ai, 1.0, 0.0);
            o.text(vx, y, &lv.value, INTER6, size, WH, ai, 1.0, 0.0);
            y += 84.0;
        }
        let yl = y - 30.0;
        let _ = write!(o.s, r#"<path d="M{TX} {yl}L{} {yl}" stroke="{}" stroke-opacity="{}" stroke-width="2"/>"#, W - TX, rgb(MU), op(0.4 * a));
        y = yl + 100.0;
        for (i, lv) in self.st.file.credits.iter().enumerate() {
            let ai = a * clamp((t - tl.t_src - 0.2 - 0.08 * i as f64) / 0.3);
            o.text(TX, y, &lv.label, INTER6, size, MU, ai, 1.0, 0.0);
            o.text(TX, y + 70.0, &lv.value, INTER6, size, WH, ai, 1.0, 0.0);
            y += 180.0;
        }
    }
}

impl Video for Incendios {
    const FPS: usize = 30;
    const WIDTH: usize = 1920;
    const HEIGHT: usize = 1080;
    const BACKGROUND_COLOR: Color = Color::BLACK;

    fn duration(&self) -> Duration<'_> {
        Duration::Frames(self.st.frames())
    }

    fn audio(&self) -> AudioMap<'_> {
        // the score is synthesised and mastered by `incendios music` (build/assets/score.wav, −14 LUFS) and muxed as is
        if self.st.build_dir().join("assets/score.wav").exists() {
            use fframes::{AudioTimestamp::*, AudioTrack};
            AudioMap::from([AudioTrack::new("score.wav", Second(0.0)..Eof)])
        } else {
            AudioMap::none()
        }
    }

    fn render_frame<'a>(&'a self, mut frame: Frame, ctx: &FFramesContext<'a, '_>) -> Svgr<'a> {
        let t = frame.global_index as f64 / 30.0;
        let body = self.render_at(t, &mut frame, ctx);
        Svgr::from(format!(r#"<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1920" height="1080" viewBox="0 0 1920 1080">{body}</svg>"#))
    }
}

/// Run the fframes CLI on this story (render, frame, strip, timeline, audio, ...). With `args`, run it as a child process.
pub fn render_cli(story: &Story, facts: &Facts, args: Option<Vec<String>>) -> Result<ExitCode> {
    if let Some(a) = args {
        let exe = std::env::current_exe()?;
        let st = std::process::Command::new(exe).args(&a[1..]).status()?;
        anyhow::ensure!(st.success(), "render failed");
        return Ok(ExitCode::SUCCESS);
    }
    let video = Incendios::new(story.clone(), facts.clone())?;
    let fonts = fframes::MediaDirectory::read_folder(story.dir.join("media")).context("media/ (fonts)")?;
    let assets = fframes::MediaDirectory::read_folder(story.build_dir().join("assets")).context("build/assets (run `incendios assets`)")?;
    let fonts_p = fonts.process_media_source().map_err(|e| anyhow::anyhow!("{e:?}"))?;
    let assets_p = assets.process_media_source().map_err(|e| anyhow::anyhow!("{e:?}"))?;
    let media = fframes::CombinedMediaProvider::from([&fonts_p as &dyn fframes::MediaProvider, &assets_p as &dyn fframes::MediaProvider]);
    Ok(fframes::cli::new(
        &video,
        fframes::RenderOptions {
            media: Some(&media),
            video_encoder_options: fframes::EncoderOptions { preferred_encoder: Some("libx264"), codec_params: Some(&[("crf", "18"), ("preset", "veryfast")]), ..Default::default() },
            ..Default::default()
        },
    )
    .run())
}
