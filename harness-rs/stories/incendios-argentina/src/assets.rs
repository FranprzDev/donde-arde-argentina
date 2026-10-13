//! `incendios assets`: the raster layers the SVG frames draw, all computed in Rust from build/derived:
//! * the 14-year timelapse: VIIRS hotspots binned per month on a lon/lat grid (30 px per degree of latitude = the national
//!   camera), coloured with the fire ramp ("fresh" hot/cool per month, quarterly cumulative ember glow and accumulated fire,
//!   the final ash);
//! * the MODIS burned-area scar (two pyramid levels), the Entre Ríos 2020 event layer and the Comarca 2025/2026 layers;
//! * the procedural sun texture and film grain;
//! * copies of the Sentinel-2 crops.
//! Writes build/assets/*.png|jpg and build/assets.json (bounding boxes and timings).
use crate::prep::{derived, modis, read_json, viirs};
use anyhow::Result;
use datavid::raster::{Img, blur, light_rgba, lut, write_png, write_png_gray};
use datavid::{Facts, Story};
use rand::SeedableRng;
use rand_distr::{Distribution, StandardNormal};
use rand_pcg::Pcg64;
use serde_json::{Value, json};
use std::path::Path;

pub const COS: f64 = crate::timeline::COS;

pub fn fire_lut() -> Vec<[f32; 3]> {
    lut(&[(0.0, [0.0, 0.0, 0.0]), (0.18, [90.0, 12.0, 4.0]), (0.42, [215.0, 56.0, 10.0]), (0.68, [255.0, 150.0, 34.0]), (0.88, [255.0, 214.0, 110.0]), (1.0, [255.0, 250.0, 225.0])])
}
pub fn apply_lut(l: &[[f32; 3]], v: &Img) -> Vec<[f32; 3]> {
    v.px.iter().map(|x| l[(x * 255.0).clamp(0.0, 255.0) as usize]).collect()
}

fn save_light(dir: &Path, name: &str, w: usize, h: usize, rgb: &[[f32; 3]]) -> Result<()> {
    write_png(&dir.join(format!("{name}.png")), w, h, &light_rgba(rgb))
}
fn save_dark(dir: &Path, name: &str, w: usize, h: usize, alpha: &[f32]) -> Result<()> {
    let mut b = Vec::with_capacity(w * h * 4);
    for a in alpha {
        b.extend_from_slice(&[0, 0, 0, (a * 255.0).clamp(0.0, 255.0) as u8]);
    }
    write_png(&dir.join(format!("{name}.png")), w, h, &b)
}

/// smooth value noise: sum of bicubic-upsampled random grids, normalised (the sun's granulation and corona streamers)
fn noise(n: usize, seed: u64, octaves: &[(usize, f32)]) -> Img {
    let mut r = Pcg64::seed_from_u64(seed);
    let mut out = Img::new(n, n);
    for &(cells, amp) in octaves {
        let g: Vec<f32> = (0..cells * cells).map(|_| StandardNormal.sample(&mut r)).collect();
        let cr = |p0: f32, p1: f32, p2: f32, p3: f32, t: f32| 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t * t * t);
        let at = |x: isize, y: isize| g[(y.clamp(0, cells as isize - 1) as usize) * cells + x.clamp(0, cells as isize - 1) as usize];
        for y in 0..n {
            let fy = (y as f32 + 0.5) * cells as f32 / n as f32 - 0.5;
            let (iy, ty) = (fy.floor() as isize, fy - fy.floor());
            for x in 0..n {
                let fx = (x as f32 + 0.5) * cells as f32 / n as f32 - 0.5;
                let (ix, tx) = (fx.floor() as isize, fx - fx.floor());
                let rows: Vec<f32> = (-1..3).map(|dy| cr(at(ix - 1, iy + dy), at(ix, iy + dy), at(ix + 1, iy + dy), at(ix + 2, iy + dy), tx)).collect();
                out.px[y * n + x] += cr(rows[0], rows[1], rows[2], rows[3], ty) * amp;
            }
        }
    }
    let mean = out.px.iter().sum::<f32>() / out.px.len() as f32;
    let sd = (out.px.iter().map(|v| (v - mean).powi(2)).sum::<f32>() / out.px.len() as f32).sqrt();
    out.map(|v| (v - mean) / sd)
}

fn sample_wrap(img: &Img, u: f32, v: f32) -> f32 {
    let (w, h) = (img.w as f32, img.h as f32);
    let (u, v) = (u.rem_euclid(w), v.rem_euclid(h));
    let (x0, y0) = (u.floor() as usize % img.w, v.floor() as usize % img.h);
    let (x1, y1) = ((x0 + 1) % img.w, (y0 + 1) % img.h);
    let (tx, ty) = (u - u.floor(), v - v.floor());
    let a = img.at(x0, y0) * (1.0 - tx) + img.at(x1, y0) * tx;
    let b = img.at(x0, y1) * (1.0 - tx) + img.at(x1, y1) * tx;
    a * (1.0 - ty) + b * ty
}

/// the sun at radius `r` px on black (additive light): limb-darkened disc with granulation, corona with streamers
fn sun_texture(r: f64) -> (usize, Vec<[f32; 3]>) {
    let sun_n = {
        let n = noise(1024, 11, &[(6, 0.5), (24, 0.7), (70, 1.0), (160, 0.8)]);
        let b = blur(&n, 2.2);
        let sd = (b.px.iter().map(|v| v * v).sum::<f32>() / b.px.len() as f32).sqrt();
        b.map(|v| v / sd)
    };
    let cor_n = noise(512, 12, &[(5, 1.0), (12, 0.6)]);
    let slut = lut(&[(0.0, [60.0, 8.0, 0.0]), (0.35, [190.0, 50.0, 6.0]), (0.6, [255.0, 128.0, 20.0]), (0.82, [255.0, 200.0, 90.0]), (1.0, [255.0, 246.0, 214.0])]);
    let e = (r * 2.6 + 30.0) as usize;
    let n = 2 * e;
    let t = 1.0f64;
    let mut out = vec![[0f32; 3]; n * n];
    for y in 0..n {
        for x in 0..n {
            let dx = (x as f64 - e as f64) / r;
            let dy = (y as f64 - e as f64) / r;
            let rr = (dx * dx + dy * dy).sqrt();
            let inside = rr < 1.0;
            let z = (1.0 - rr * rr).clamp(0.0, 1.0).sqrt();
            let mut col = [0f32; 3];
            if inside {
                let u = ((dx.clamp(-1.0, 1.0).asin() / std::f64::consts::PI + 0.5 + 0.004 * t) * 1023.0) as f32;
                let v = ((dy.clamp(-1.0, 1.0).asin() / std::f64::consts::PI + 0.5) * 1023.0) as f32;
                let gran = sample_wrap(&sun_n, u, v) as f64;
                let limb = 1.0 - 0.62 * (1.0 - z) - 0.18 * (1.0 - z).powi(2);
                let detail = (r / 120.0).min(1.0);
                let i = (limb * (0.86 + 0.13 * gran * detail)).clamp(0.0, 1.0);
                col = slut[(i * 255.0) as usize];
            }
            let ang = ((dy.atan2(dx) / (2.0 * std::f64::consts::PI) + 0.5) * 511.0) as f32;
            let st = sample_wrap(&cor_n, ang, (256.0 + 40.0 * t.sin()) as f32) as f64;
            let d = (rr - 1.0).max(0.0);
            let cor = (-d * 3.2).exp() * (0.75 + 0.35 * st) * if rr >= 0.98 { 1.0 } else { 0.0 } + 0.6 * (-d * 9.0).exp();
            let k = if inside { 0.3 } else { 1.0 };
            for (c, base) in [255.0f64, 150.0, 50.0].iter().enumerate() {
                out[y * n + x][c] = col[c] + (cor * base * 0.85 * k) as f32;
            }
        }
    }
    (n, out)
}

pub fn run(story: &Story, _facts: &Facts) -> Result<()> {
    let dir = &story.dir;
    let src = derived(dir);
    let out = story.build_dir().join("assets");
    std::fs::create_dir_all(&out)?;
    let t0 = std::time::Instant::now();
    let l = fire_lut();
    let pts = viirs::load(&src.join("points.bin"))?;
    // ---- the timelapse grid
    let zg = 30.0;
    let (lon0, lon1, lat0, lat1) = (-74.0, -53.0, -55.5, -21.5);
    let (dlon, dlat) = (1.0 / (zg * COS), 1.0 / zg);
    let nx = ((lon1 - lon0) / dlon).ceil() as usize;
    let ny = ((lat1 - lat0) / dlat).ceil() as usize;
    let gbbox = [lon0, lat1 - ny as f64 * dlat, lon0 + nx as f64 * dlon, lat1];
    let cell = |p: &viirs::Pt| -> usize {
        let gx = (((p.lon as f64 - lon0) / dlon) as isize).clamp(0, nx as isize - 1) as usize;
        let gy = (((lat1 - p.lat as f64) / dlat) as isize).clamp(0, ny as isize - 1) as usize;
        gy * nx + gx
    };
    let mut by_month: Vec<Vec<usize>> = vec![vec![]; 168];
    let mut tmon: Vec<Vec<f64>> = vec![vec![]; 168];
    for p in &pts {
        let m = (p.t.floor() as usize).min(167);
        by_month[m].push(cell(p));
        tmon[m].push(p.t as f64);
    }
    let mut fresh = vec![];
    let mut cum = Img::new(nx, ny);
    let mut ember_q = vec![];
    for m in 0..168 {
        if by_month[m].is_empty() {
            fresh.push(Value::Null);
            continue;
        }
        let mut c = Img::new(nx, ny);
        for &i in &by_month[m] {
            c.px[i] += 1.0;
            cum.px[i] += 1.0;
        }
        let (x0, y0, x1, y1) = c.nonzero_bbox(0.0).unwrap();
        let (x0, y0, x1, y1) = (x0.saturating_sub(3), y0.saturating_sub(3), (x1 + 3).min(nx), (y1 + 3).min(ny));
        let cc = c.crop(x0, y0, x1, y1);
        for (tag, k) in [("hot", 1.0f32), ("cool", 0.3)] {
            let v = blur(&cc.map(|x| 1.0 - (-x * 0.55 * k).exp()), 0.7).map(|x| x * 1.25);
            save_light(&out, &format!("fire_{tag}_{m:03}"), cc.w, cc.h, &apply_lut(&l, &v))?;
        }
        let mut tv = tmon[m].clone();
        tv.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let med = if tv.len() % 2 == 1 { tv[tv.len() / 2] } else { (tv[tv.len() / 2 - 1] + tv[tv.len() / 2]) / 2.0 };
        fresh.push(json!({"m": m, "bbox": [gbbox[0] + x0 as f64 * dlon, lat1 - y1 as f64 * dlat, gbbox[0] + x1 as f64 * dlon, lat1 - y0 as f64 * dlat], "median_month": med}));
        if m % 3 == 2 {
            let q = ember_q.len();
            let em = cum.map(|x| (x.ln_1p() / 60f32.ln_1p()).clamp(0.0, 1.0));
            let rgb: Vec<[f32; 3]> = em.px.iter().map(|e| [e * 120.0 * 0.85, e * 30.0 * 0.85, e * 10.0 * 0.85]).collect();
            save_light(&out, &format!("ember_{q:02}"), nx, ny, &rgb)?;
            let v = blur(&cum.map(|x| (x.ln_1p() / 500f32.ln_1p()).clamp(0.0, 1.0).powf(1.1) * 0.92), 0.7).map(|x| x * 1.25);
            save_light(&out, &format!("acc_{q:02}"), nx, ny, &apply_lut(&l, &v))?;
            ember_q.push(m + 1);
        }
    }
    let norm = (500.0f32 * (31.5f32 / 30.0).powf(1.6)).ln_1p();
    let v = blur(&cum.map(|x| (x.ln_1p() / norm).clamp(0.0, 1.0).powf(1.1) * 0.92), 0.7).map(|x| x * 1.25);
    let ash: Vec<[f32; 3]> = v
        .px
        .iter()
        .map(|x| {
            let a = x.clamp(0.0, 1.0).powf(0.8) * 0.75;
            [150.0 * a, 142.0 * a, 134.0 * a]
        })
        .collect();
    save_light(&out, "ash", nx, ny, &ash)?;
    save_light(&out, "acc_full", nx, ny, &apply_lut(&l, &v))?;
    eprintln!("assets: timelapse layers {:.1}s", t0.elapsed().as_secs_f64());

    // ---- MODIS scar: intensity 110 (burned once) .. 255 (8+ times), two pyramid levels
    let g = modis::read_grid(&src)?;
    let cnt = std::fs::read(src.join("scar_count.u8"))?;
    let inten = Img::from(g.w, g.h, cnt.iter().map(|&c| if c > 0 { 110.0 + 145.0 * (((c as f32 - 1.0).ln_1p()) / 7f32.ln_1p()).clamp(0.0, 1.0) } else { 0.0 }).collect());
    let mut lev = inten;
    let mut scar_levels = vec![];
    let save_scar = |name: &str, im: &Img| -> Result<()> {
        let s55: Vec<f32> = im.px.iter().map(|v| (v / 255.0).clamp(0.0, 1.0).powf(0.55)).collect();
        save_dark(&out, &format!("scar_dark_{name}"), im.w, im.h, &s55.iter().map(|s| 0.6 * s).collect::<Vec<_>>())?;
        save_light(&out, &format!("scar_col_{name}"), im.w, im.h, &s55.iter().map(|s| [s * 205.0, s * 190.0, s * 172.0]).collect::<Vec<_>>())?;
        save_light(&out, &format!("scar_warm_{name}"), im.w, im.h, &s55.iter().map(|s| [s * 235.0, s * 110.0, s * 45.0]).collect::<Vec<_>>())
    };
    for k in 1..=3 {
        lev = datavid::raster::shrink(&lev, 2);
        let dk = g.d * (g.w as f64 / lev.w as f64);
        if k == 1 {
            // the fine level only where the camera zooms in (the three stops), to keep the preloaded media small
            for (i, c) in crate::timeline::STOPCAM.iter().enumerate() {
                let (hw, hh) = (1.3 * 1920.0 / (c[2] * COS), 1.3 * 1080.0 / c[2]);
                let (lo0, lo1, la0, la1) = (c[0] - hw, c[0] + hw, c[1] - hh, c[1] + hh);
                let x0 = (((lo0 - g.lon0) / dk).floor().max(0.0)) as usize;
                let x1 = (((lo1 - g.lon0) / dk).ceil() as usize).min(lev.w);
                let y0 = (((g.lat1 - la1) / dk).floor().max(0.0)) as usize;
                let y1 = (((g.lat1 - la0) / dk).ceil() as usize).min(lev.h);
                let crop = lev.crop(x0, y0, x1, y1);
                save_scar(&format!("l1_{i}"), &crop)?;
                scar_levels.push(json!({"level": 1, "stop": i, "bbox": [g.lon0 + x0 as f64 * dk, g.lat1 - y1 as f64 * dk, g.lon0 + x1 as f64 * dk, g.lat1 - y0 as f64 * dk]}));
            }
        }
        if k == 3 {
            save_scar("l3", &lev)?;
            scar_levels.push(json!({"level": 3, "stop": -1, "bbox": [g.lon0, g.lat1 - lev.h as f64 * dk, g.lon0 + lev.w as f64 * dk, g.lat1]}));
        }
    }
    eprintln!("assets: scar {:.1}s", t0.elapsed().as_secs_f64());

    // ---- event layers on crops of the full-resolution MODIS grid
    let crop_box = |m: &[u8], pad: usize| -> (usize, usize, usize, usize) {
        let (mut x0, mut y0, mut x1, mut y1) = (usize::MAX, usize::MAX, 0, 0);
        for y in 0..g.h {
            for x in 0..g.w {
                if m[y * g.w + x] > 0 {
                    x0 = x0.min(x);
                    y0 = y0.min(y);
                    x1 = x1.max(x + 1);
                    y1 = y1.max(y + 1);
                }
            }
        }
        (x0.saturating_sub(pad), y0.saturating_sub(pad), (x1 + pad).min(g.w), (y1 + pad).min(g.h))
    };
    let bbox_of = |x0: usize, y0: usize, x1: usize, y1: usize| -> [f64; 4] { [g.lon0 + x0 as f64 * g.d, g.lat1 - y1 as f64 * g.d, g.lon0 + x1 as f64 * g.d, g.lat1 - y0 as f64 * g.d] };
    let mut events = serde_json::Map::new();
    {
        let m = std::fs::read(src.join("scar_er_2020.u8"))?;
        let (x0, y0, x1, y1) = crop_box(&m, 16);
        let im = Img::from(x1 - x0, y1 - y0, (y0..y1).flat_map(|y| (x0..x1).map(move |x| (y, x))).map(|(y, x)| m[y * g.w + x] as f32).collect());
        let b = blur(&im, 4.0);
        let light: Vec<[f32; 3]> = im
            .px
            .iter()
            .zip(b.px.iter())
            .map(|(e, bl)| {
                let edge = ((e - bl).max(0.0) * 3.0).min(1.0);
                [e * 150.0 + edge * 255.0 * 0.8, e * 46.0 + edge * 140.0 * 0.8, e * 18.0 + edge * 50.0 * 0.8]
            })
            .collect();
        save_light(&out, "er2020_light", im.w, im.h, &light)?;
        save_dark(&out, "er2020_dark", im.w, im.h, &im.px.iter().map(|e| 0.35 * e).collect::<Vec<_>>())?;
        events.insert("er2020".into(), json!(bbox_of(x0, y0, x1, y1)));
    }
    for (name, col) in [("pat_2025", [255.0f32, 176.0, 60.0]), ("pat_2026", [255.0, 64.0, 40.0])] {
        let m = std::fs::read(src.join(format!("scar_{name}.u8")))?;
        let (x0, y0, x1, y1) = crop_box(&m, 4);
        let (w, h) = (x1 - x0, y1 - y0);
        let up = 4;
        let (wu, hu) = (w * up, h * up);
        let at = |x: usize, y: usize| m[(y0 + y / up) * g.w + x0 + x / up] > 0;
        let mut light = vec![[0f32; 3]; wu * hu];
        let mut dark = vec![0f32; wu * hu];
        for y in 0..hu {
            for x in 0..wu {
                if !at(x, y) {
                    continue;
                }
                let edge = x == 0 || y == 0 || x + 1 == wu || y + 1 == hu || !at(x - 1, y) || !at(x + 1, y) || !at(x, y - 1) || !at(x, y + 1);
                let k = 0.28 + if edge { 1.0 } else { 0.0 };
                light[y * wu + x] = [col[0] * k, col[1] * k, col[2] * k];
                dark[y * wu + x] = 0.25;
            }
        }
        save_light(&out, &format!("{name}_light"), wu, hu, &light)?;
        save_dark(&out, &format!("{name}_dark"), wu, hu, &dark)?;
        events.insert(name.into(), json!(bbox_of(x0, y0, x1, y1)));
    }
    eprintln!("assets: events {:.1}s", t0.elapsed().as_secs_f64());

    // ---- sun + grain
    let (n, sun) = sun_texture(400.0);
    save_light(&out, "sun", n, n, &sun)?;
    let mut gr = Pcg64::seed_from_u64(7);
    for i in 0..6 {
        let g8: Vec<u8> = (0..960 * 540)
            .map(|_| {
                let v: f64 = StandardNormal.sample(&mut gr);
                (128.0 + v * 30.0 * 0.44).clamp(0.0, 255.0) as u8
            })
            .collect();
        write_png_gray(&out.join(format!("grain_{i}.png")), 960, 540, &g8)?;
    }
    // ---- Sentinel-2 crops
    let s2 = story.input("s2_dir")?;
    let mut s2m = serde_json::Map::new();
    for name in ["tuc_2025-09-23", "delta_2020-09-23", "comarca_2024", "comarca_2025", "comarca_2026"] {
        std::fs::copy(s2.join(format!("{name}.jpg")), out.join(format!("{name}.jpg")))?;
        let meta = read_json(&s2.join(format!("{name}.json")))?;
        s2m.insert(name.into(), json!(crate::prep::s2_bbox(&meta)));
    }
    // ---- the hotspot replay of each stop, one light raster per video frame
    let geo = read_json(&src.join("geometry.json"))?;
    let codes: Vec<String> = geo["codes"].as_array().unwrap().iter().map(|c| c.as_str().unwrap().to_string()).collect();
    let tl = crate::timeline::Tl::new(story, [crate::prep::s2_bbox(&read_json(&s2.join("tuc_2025-09-23.json"))?), crate::prep::s2_bbox(&read_json(&s2.join("delta_2020-09-23.json"))?)]);
    let ev = crate::timeline::events(&tl, &pts, &codes);
    let mut ev_frames = vec![];
    for i in 0..3 {
        let (s0, s1) = tl.stops[i];
        let c = crate::timeline::STOPCAM[i];
        let mut m = serde_json::Map::new();
        let (f0, f1) = (((s0 - 0.3) * 30.0).ceil() as usize, ((s1 + 0.5) * 30.0).ceil() as usize);
        let rendered: Vec<_> = {
            use rayon::prelude::*;
            (f0..f1).into_par_iter().map(|f| (f, event_raster(&ev, &tl, &l, i, f as f64 / 30.0, &c))).collect()
        };
        for (f, r) in rendered {
            if let Some((rgba, w, h, x0, y0)) = r {
                write_png(&out.join(format!("ev{i}_{f:04}.png")), w, h, &rgba)?;
                // pixel box -> lon/lat under the stop camera
                let lon = |x: f64| c[0] + (x - c[3]) / (c[2] * COS);
                let lat = |y: f64| c[1] - (y - c[4]) / c[2];
                m.insert(f.to_string(), json!([lon(x0), lat(y0 + h as f64), lon(x0 + w as f64), lat(y0)]));
            }
        }
        ev_frames.push(Value::Object(m));
    }
    eprintln!("assets: stop replays {:.1}s", t0.elapsed().as_secs_f64());
    let meta = json!({"ev_frames": ev_frames, "grid_bbox": gbbox, "fresh": fresh, "ember_q": ember_q, "scar_levels": scar_levels, "events": events, "sun": {"r": 400.0, "half": n as f64 / 2.0}, "s2": s2m});
    crate::prep::write_json(&story.build_dir().join("assets.json"), &meta)?;
    eprintln!("assets: done in {:.1}s -> {}", t0.elapsed().as_secs_f64(), out.display());
    Ok(())
}

/// The v10 hotspot replay of stop `i` at time t under camera c: every hotspot that has lit up glows (fresh ones brighter),
/// splatted on screen pixels, blurred by the zoom, coloured with the fire ramp, plus a half-resolution bloom.
/// Returns (RGBA light, w, h, x0, y0) of the cropped raster.
pub fn event_raster(ev: &crate::timeline::Events, tl: &crate::timeline::Tl, l: &[[f32; 3]], i: usize, t: f64, c: &crate::timeline::Cam) -> Option<(Vec<u8>, usize, usize, f64, f64)> {
    use datavid::raster::{resize, shrink};
    let (w_, h_) = (1920.0, 1080.0);
    let (_, s1) = tl.stops[i];
    let fade = 1.0 - ((t - s1 + 0.2) / 0.5).clamp(0.0, 1.0);
    if fade <= 0.0 {
        return None;
    }
    let mut hits: Vec<(f64, f64, f32)> = vec![];
    for (p, tt) in ev.pts[i].iter().zip(ev.times[i].iter()) {
        if *tt <= t {
            let (x, y) = crate::timeline::proj(p.0 as f64, p.1 as f64, c);
            if (-60.0..w_ + 60.0).contains(&x) && (-60.0..h_ + 60.0).contains(&y) {
                hits.push((x, y, ((0.25 + 1.6 * (-(t - tt) / 0.35).exp()) * fade) as f32));
            }
        }
    }
    if hits.is_empty() {
        return None;
    }
    let pad = 90.0;
    let bx0 = (hits.iter().map(|h| h.0).fold(f64::MAX, f64::min) - pad).floor();
    let by0 = (hits.iter().map(|h| h.1).fold(f64::MAX, f64::min) - pad).floor();
    let bx1 = (hits.iter().map(|h| h.0).fold(f64::MIN, f64::max) + pad).ceil();
    let by1 = (hits.iter().map(|h| h.1).fold(f64::MIN, f64::max) + pad).ceil();
    let (w, h) = (((bx1 - bx0) as usize / 2 * 2).max(2), ((by1 - by0) as usize / 2 * 2).max(2));
    let mut img = Img::new(w, h);
    for (x, y, v) in &hits {
        let (xi, yi) = ((x - bx0).round() as isize, (y - by0).round() as isize);
        if xi >= 0 && yi >= 0 && (xi as usize) < w && (yi as usize) < h {
            img.px[yi as usize * w + xi as usize] += v;
        }
    }
    let fire = if i == 2 {
        blur(&img, 2.2).map(|v| v * 9.0)
    } else {
        let k = c[2] / 30.0;
        let base = if k > 1.15 { blur(&img, (0.55 * k.powf(0.8)).min(6.0)).map(|v| v * (k.powf(1.25) * 0.55) as f32) } else { img };
        base.map(|v| v * if i == 0 { 0.5 } else { 0.6 })
    };
    let v = fire.map(|x| 1.0 - (-x * 0.8).exp());
    let f = apply_lut(l, &v);
    let mut bloom: Vec<Img> = Vec::with_capacity(3);
    for ch in 0..3 {
        let plane = Img::from(w, h, f.iter().map(|p| p[ch]).collect());
        bloom.push(resize(&blur(&shrink(&plane, 2), 6.0).map(|x| x * 0.8), w, h));
    }
    let rgb: Vec<[f32; 3]> = (0..w * h).map(|k| [f[k][0] + bloom[0].px[k], f[k][1] + bloom[1].px[k], f[k][2] + bloom[2].px[k]]).collect();
    Some((light_rgba(&rgb), w, h, bx0, by0))
}
