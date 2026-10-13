//! Human scale: «CASI 12 TUCUMANES». Tucumán's geodesic area (INDEC/IGN boundary, cross-checked against INDEC's official
//! 22.524 km²) → ratio = distinct burned area 2012–2025 / Tucumán. Then 12 real-scale copies of the Tucumán outline are
//! placed on the national burned-area map: greedy, each copy where the burned share under its footprint is highest, no
//! overlaps, ≥ 92 % inside Argentina, never on Tucumán itself. A copy moved from latitude φ0 to φ keeps its ground size on
//! this map (fixed cos 38° x-stretch) by widening its longitude extent by cos φ0 / cos φ per vertex; each copy's geodesic
//! area is asserted within 1 % of the original. The 12th copy is filled only up to the fractional part (bottom-up).
use super::{Geo, modis, read_json};
use anyhow::{Context, Result, ensure};
use datavid::geo::{Grid, Poly, Ring, centroid, geodesic_area_m2, geometry_polys, rasterize};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::path::Path;

pub const INDEC_KM2: f64 = 22524.0;

pub fn copy_at(ring: &Ring, c0: [f64; 2], lon: f64, lat: f64) -> Ring {
    ring.iter()
        .map(|p| {
            let k = p[1].to_radians().cos() / (p[1] - c0[1] + lat).to_radians().cos();
            [lon + (p[0] - c0[0]) * k, p[1] - c0[1] + lat]
        })
        .collect()
}

/// the part of a ring south of latitude `y` (Sutherland–Hodgman against one half-plane)
pub fn clip_below(r: &Ring, y: f64) -> Ring {
    let mut out = vec![];
    let n = r.len();
    for i in 0..n {
        let (a, b) = (r[i], r[(i + 1) % n]);
        let (ia, ib) = (a[1] <= y, b[1] <= y);
        if ia {
            out.push(a);
        }
        if ia != ib {
            let k = (y - a[1]) / (b[1] - a[1]);
            out.push([a[0] + k * (b[0] - a[0]), y]);
        }
    }
    out
}

fn km2(r: &Ring) -> f64 {
    geodesic_area_m2(&Poly { ext: r.clone(), holes: vec![] }) / 1e6
}

pub fn run(geo: &Geo, out: &Path, provincias: &Path) -> Result<Value> {
    let pv: Value = serde_json::from_str(&std::fs::read_to_string(provincias)?)?;
    let f = pv["features"].as_array().unwrap().iter().find(|f| f["properties"]["id"] == "90").context("no Tucumán (90) in provincias")?;
    let tuc_km2: f64 = geometry_polys(&f["geometry"])?.iter().map(geodesic_area_m2).sum::<f64>() / 1e6;
    ensure!((tuc_km2 / INDEC_KM2 - 1.0).abs() < 0.01, "Tucumán boundary {tuc_km2} km² is not within 1 % of INDEC's {INDEC_KM2}");
    let burn_ha = read_json(&out.join("ranking.json"))?["total_ha_unique"].as_f64().unwrap();
    let ratio = burn_ha / (tuc_km2 * 100.0);
    let ratio_indec = burn_ha / (INDEC_KM2 * 100.0);
    ensure!((11.5..12.0).contains(&ratio) && (11.5..12.0).contains(&ratio_indec), "«CASI 12» needs a ratio in [11.5, 12): {ratio}");
    let ring: Ring = geo.prov_rings[geo.idx("90")].iter().max_by_key(|r| r.len()).unwrap().clone();
    let c0 = centroid(&ring);
    // burned fraction on a grid 8x coarser than MODIS (0.035°)
    let g = modis::read_grid(out)?;
    let cnt = std::fs::read(out.join("scar_count.u8"))?;
    let fct = 8;
    let (h, w) = (g.h / fct, g.w / fct);
    let mut fr = vec![0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let mut s = 0;
            for yy in 0..fct {
                for xx in 0..fct {
                    s += (cnt[(y * fct + yy) * g.w + x * fct + xx] > 0) as u32;
                }
            }
            fr[y * w + x] = s as f32 / (fct * fct) as f32;
        }
    }
    let gc = Grid { lon0: g.lon0, lat1: g.lat1, d: g.d * fct as f64, w, h };
    let all: Vec<(&Ring, u8)> = geo.prov_rings.iter().flat_map(|rs| rs.iter().map(|r| (r, 1u8))).collect();
    let arm = rasterize(&all, &gc);
    let mut occ = rasterize(&[(&ring, 1)], &gc);
    let mut cands = vec![];
    let mut la = -22.5;
    while la > -52.0 + 1e-9 {
        let mut lo = -72.5;
        while lo < -54.0 - 1e-9 {
            cands.push((lo, la));
            lo += 0.25;
        }
        la -= 0.25;
    }
    let mut placed = vec![];
    for k in 0..12 {
        let scores: Vec<(f64, usize)> = cands
            .par_iter()
            .enumerate()
            .map(|(ci, &(lo, la))| {
                let r = copy_at(&ring, c0, lo, la);
                let m = rasterize(&[(&r, 1)], &gc);
                let (mut n, mut inside, mut s, mut hit) = (0usize, 0usize, 0f64, false);
                for i in 0..m.len() {
                    if m[i] == 1 {
                        n += 1;
                        inside += arm[i] as usize;
                        s += fr[i] as f64;
                        hit |= occ[i] == 1;
                    }
                }
                if n == 0 || hit || (inside as f64) < 0.92 * n as f64 { (-1.0, ci) } else { (s / n as f64, ci) }
            })
            .collect();
        // first best in candidate order (strictly greater wins, like the reference loop)
        let mut best = (-1.0, usize::MAX);
        for s in &scores {
            if s.0 > best.0 {
                best = *s;
            }
        }
        ensure!(best.0 > 0.0, "copy {k}: no valid place");
        let (lo, la) = cands[best.1];
        let r = copy_at(&ring, c0, lo, la);
        let m = rasterize(&[(&r, 1)], &gc);
        for i in 0..m.len() {
            occ[i] |= m[i];
        }
        let a = km2(&r);
        ensure!((a / tuc_km2 - 1.0).abs() < 0.01, "copy {k} area {a} km² vs {tuc_km2}");
        placed.push(json!({"lon": (lo * 1000.0f64).round() / 1000.0, "lat": (la * 1000.0f64).round() / 1000.0, "burned_share": (best.0 * 1000.0).round() / 1000.0, "area_km2": (a * 10.0).round() / 10.0}));
    }
    // the 12th copy, filled to the fractional part: bisection on the latitude of the cut
    let frac = ratio - 11.0;
    let r12 = copy_at(&ring, c0, placed[11]["lon"].as_f64().unwrap(), placed[11]["lat"].as_f64().unwrap());
    let a12 = km2(&r12);
    let (mut lo_, mut hi_) = (r12.iter().map(|p| p[1]).fold(f64::MAX, f64::min), r12.iter().map(|p| p[1]).fold(f64::MIN, f64::max));
    let mut mid = 0.0;
    for _ in 0..40 {
        mid = (lo_ + hi_) / 2.0;
        if km2(&clip_below(&r12, mid)) / a12 < frac {
            lo_ = mid;
        } else {
            hi_ = mid;
        }
    }
    Ok(json!({
        "tuc_km2": tuc_km2, "indec_km2": INDEC_KM2, "burn_ha": burn_ha, "ratio": ratio, "ratio_indec": ratio_indec, "frac12": frac,
        "cut_lat12": mid, "src_centroid": c0, "copies": placed,
        "ring_src": "INDEC province 90 (render ring)", "area_src": "provincias.geojson id 90 (IGN/INDEC)",
    }))
}
