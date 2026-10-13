//! Burned area: MODIS MCD64A1 Collection 6.1 (500 m, monthly), the University of Maryland "Win06" + "Win07" GeoTIFF windows
//! (geographic lat/lon grid of 0.00439453125°, value = burn day of year, 0 unburned, <0 unmapped/water), cut to the
//! Argentina box, one cache file per month (`YYYY-MM.npz` holding `a6/t6/a7/t7`: the int16 window and its affine transform).
//!
//! A pixel counts as burned in a month when burndate > 0 and it lies inside an INDEC province (pixel centre in polygon).
//! Pixel area = (R·d)² · cos(lat), R = 6 371 007.181 m (the MODIS sphere).
//! Outputs: burn.json (every area number), scar_count.u8 (months burned per pixel, 2012–2025), and event masks
//! scar_er_2020.u8 (Entre Ríos 2020), scar_pat_2025.u8 / scar_pat_2026.u8 (Comarca Andina box, Jan–Mar).
use super::Geo;
use anyhow::{Context, Result};
use datavid::geo::{Grid, rasterize};
use datavid::npy;
use rayon::prelude::*;
use serde_json::json;
use std::collections::BTreeMap;
use std::path::Path;

pub const D: f64 = 0.00439453125;
pub const R_MODIS: f64 = 6371007.181;
pub const COMARCA: [f64; 4] = [-71.80, -42.62, -71.05, -41.75];

pub fn pix_ha(g: &Grid) -> Vec<f64> {
    (0..g.h).map(|r| {
        let lat = g.lat1 - (r as f64 + 0.5) * g.d;
        (R_MODIS * g.d.to_radians()).powi(2) * lat.to_radians().cos() / 1e4
    }).collect()
}

pub fn prov_raster(geo: &Geo, g: &Grid) -> Vec<u8> {
    let shapes: Vec<(&datavid::geo::Ring, u8)> = geo.prov_rings.iter().enumerate().flat_map(|(i, rs)| rs.iter().map(move |r| (r, (i + 1) as u8))).collect();
    rasterize(&shapes, g)
}

pub fn read_grid(dir: &Path) -> Result<Grid> {
    let v = super::read_json(&dir.join("scar_grid.json"))?;
    Ok(Grid { lon0: v["LON0"].as_f64().unwrap(), lat1: v["LAT1"].as_f64().unwrap(), d: v["D"].as_f64().unwrap(), w: v["W"].as_u64().unwrap() as usize, h: v["H"].as_u64().unwrap() as usize })
}

pub fn run(src: &Path, geo: &Geo, out: &Path) -> Result<()> {
    let mut files: Vec<_> = std::fs::read_dir(src).with_context(|| src.display().to_string())?.filter_map(|e| e.ok()).map(|e| e.path()).filter(|p| p.file_name().and_then(|n| n.to_str()).is_some_and(|n| n.starts_with("20") && n.ends_with(".npz"))).collect();
    files.sort();
    let months: Vec<String> = files.iter().map(|p| p.file_name().unwrap().to_str().unwrap()[..7].to_string()).collect();
    let z0 = npy::read_npz(&files[0])?;
    let t6 = z0["t6"].to_f64();
    let t7 = z0["t7"].to_f64();
    let lon0 = t6[2].min(t7[2]);
    let lat1 = t6[5];
    let place = |t: &[f64]| (((lat1 - t[5]) / D).round() as usize, ((t[2] - lon0) / D).round() as usize);
    let (r6, c6) = place(&t6);
    let (r7, c7) = place(&t7);
    let (s6, s7) = (&z0["a6"].shape, &z0["a7"].shape);
    let h = (r6 + s6[0]).max(r7 + s7[0]);
    let w = (c6 + s6[1]).max(c7 + s7[1]);
    let g = Grid { lon0, lat1, d: D, w, h };
    let pixha = pix_ha(&g);
    let prov = prov_raster(geo, &g);
    let ncodes = geo.codes.len();
    let i_er = geo.idx("30") as u8 + 1;
    let cb = (((lat1 - COMARCA[3]) / D) as usize, ((lat1 - COMARCA[1]) / D) as usize, ((COMARCA[0] - lon0) / D) as usize, ((COMARCA[2] - lon0) / D) as usize);
    let mut count = vec![0u8; w * h];
    let mut ev_er = vec![0u8; w * h];
    let mut ev_p25 = vec![0u8; w * h];
    let mut ev_p26 = vec![0u8; w * h];
    let mut monthly_ha: BTreeMap<String, f64> = BTreeMap::new();
    let mut prov_month: BTreeMap<String, Vec<f64>> = BTreeMap::new();
    // months are independent: decode + mask in parallel batches, accumulate in order
    for chunk in files.chunks(4).zip(months.chunks(4)) {
        let masks: Vec<Result<Vec<u8>>> = chunk
            .0
            .par_iter()
            .map(|f| {
                let z = npy::read_npz(f)?;
                let (a6, a7) = (z["a6"].as_i16()?, z["a7"].as_i16()?);
                let (s6, s7) = (&z["a6"].shape, &z["a7"].shape);
                let mut gv = vec![0i16; w * h];
                for r in 0..s6[0] {
                    gv[(r6 + r) * w + c6..(r6 + r) * w + c6 + s6[1]].copy_from_slice(&a6[r * s6[1]..(r + 1) * s6[1]]);
                }
                for r in 0..s7[0] {
                    for c in 0..s7[1] {
                        let v = a7[r * s7[1] + c];
                        if v != 0 {
                            gv[(r7 + r) * w + c7 + c] = v;
                        }
                    }
                }
                Ok(gv.iter().zip(prov.iter()).map(|(v, p)| (*v > 0 && *p > 0) as u8).collect())
            })
            .collect();
        for (m, ym) in masks.into_iter().zip(chunk.1.iter()) {
            let b = m?;
            let y: i32 = ym[..4].parse()?;
            let mo: u32 = ym[5..].parse()?;
            let mut pm = vec![0.0; ncodes + 1];
            let mut tot = 0.0;
            for r in 0..h {
                let ph = pixha[r];
                let row = &b[r * w..(r + 1) * w];
                for c in 0..w {
                    if row[c] == 1 {
                        let i = r * w + c;
                        tot += ph;
                        pm[prov[i] as usize] += ph;
                        if y <= 2025 {
                            count[i] = count[i].saturating_add(1);
                        }
                        if y == 2020 && prov[i] == i_er {
                            ev_er[i] = 1;
                        }
                        let inbox = r >= cb.0 && r < cb.1 && c >= cb.2 && c < cb.3;
                        if inbox && mo <= 3 && y == 2025 {
                            ev_p25[i] = 1;
                        }
                        if inbox && mo <= 3 && y == 2026 {
                            ev_p26[i] = 1;
                        }
                    }
                }
            }
            monthly_ha.insert(ym.clone(), tot);
            prov_month.insert(ym.clone(), pm);
        }
    }
    let ha = |m: &[u8]| -> f64 { (0..h).map(|r| m[r * w..(r + 1) * w].iter().filter(|v| **v > 0).count() as f64 * pixha[r]).sum() };
    let total_2012_2025: f64 = monthly_ha.iter().filter(|(k, _)| k[..4].parse::<i32>().unwrap() <= 2025).map(|(_, v)| v).sum();
    let mut by_year = BTreeMap::new();
    for (k, v) in &monthly_ha {
        *by_year.entry(k[..4].to_string()).or_insert(0.0) += v;
    }
    let mut by_prov_total = BTreeMap::new();
    let mut prov_area = BTreeMap::new();
    let mut area = vec![0.0; ncodes + 1];
    for r in 0..h {
        for c in 0..w {
            area[prov[r * w + c] as usize] += pixha[r];
        }
    }
    for (i, c) in geo.codes.iter().enumerate() {
        by_prov_total.insert(c.clone(), prov_month.iter().filter(|(k, _)| k[..4].parse::<i32>().unwrap() <= 2025).map(|(_, v)| v[i + 1]).sum::<f64>());
        prov_area.insert(c.clone(), area[i + 1]);
    }
    let er_2020: f64 = prov_month.iter().filter(|(k, _)| k.starts_with("2020")).map(|(_, v)| v[i_er as usize]).sum();
    let pitch_ha = 105.0 * 68.0 / 1e4;
    let seconds = 14.0 * 365.25 * 86400.0 - 0.25 * 86400.0 * 2.0 + 0.5 * 86400.0 * 2.0; // computed exactly below
    let _ = seconds;
    // 2012-01-01 .. 2026-01-01: 14 years with 4 leap days (2012, 2016, 2020, 2024)
    let secs_14y = (14.0 * 365.0 + 4.0) * 86400.0;
    let burn = json!({
        "source": "MODIS MCD64A1 C6.1 (UMD Win06+Win07 windows), pixels inside INDEC provinces",
        "months": months, "grid": {"LON0": lon0, "LAT1": lat1, "D": D, "W": w, "H": h},
        "total_ha_2012_2025": total_2012_2025,
        "unique_ha_2012_2025": ha(&count),
        "by_year_ha": by_year,
        "by_prov_total_ha_2012_2025": by_prov_total,
        "prov_area_ha": prov_area,
        "er_2020_ha": er_2020,
        "er_unique_2020_ha": ha(&ev_er),
        "comarca_box": COMARCA,
        "comarca_2025_q1_ha": ha(&ev_p25),
        "comarca_2026_q1_ha": ha(&ev_p26),
        "pitch_ha": pitch_ha,
        "seconds_2012_2025": secs_14y,
        "pitch_every_s": secs_14y / (total_2012_2025 / pitch_ha),
    });
    super::write_json(&out.join("burn.json"), &burn)?;
    super::write_json(&out.join("scar_grid.json"), &json!({"H": h, "W": w, "D": D, "LON0": lon0, "LAT1": lat1}))?;
    std::fs::write(out.join("scar_count.u8"), &count)?;
    std::fs::write(out.join("scar_er_2020.u8"), &ev_er)?;
    std::fs::write(out.join("scar_pat_2025.u8"), &ev_p25)?;
    std::fs::write(out.join("scar_pat_2026.u8"), &ev_p26)?;
    Ok(())
}
