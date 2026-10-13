//! Province ranking by DISTINCT burned area 2012–2025 (each 500 m pixel counted once if it burned at least once), with
//! province areas on the same grid, repeat-burn totals and VIIRS hotspot counts per province.
use super::{Geo, modis, read_json, viirs};
use anyhow::{Result, ensure};
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct Row {
    pub code: String,
    pub name: String,
    pub ha_total: f64,
    pub ha_unique: f64,
    pub area_ha: f64,
    pub focos: usize,
    pub share_unique: f64,
    pub rank: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct Ranking {
    pub metric: String,
    pub rows: Vec<Row>,
    pub total_ha_unique: f64,
    pub total_ha_repeat: f64,
    pub country_area_ha: f64,
    pub share_country_burned: f64,
    pub top5_share: f64,
}

pub fn run(geo: &Geo, out: &Path) -> Result<Ranking> {
    let burn = read_json(&out.join("burn.json"))?;
    let g = modis::read_grid(out)?;
    let prov = modis::prov_raster(geo, &g);
    let pixha = modis::pix_ha(&g);
    let cnt = std::fs::read(out.join("scar_count.u8"))?;
    let n = geo.codes.len();
    let (mut uniq, mut area) = (vec![0.0; n + 1], vec![0.0; n + 1]);
    for r in 0..g.h {
        for c in 0..g.w {
            let i = r * g.w + c;
            area[prov[i] as usize] += pixha[r];
            if cnt[i] > 0 {
                uniq[prov[i] as usize] += pixha[r];
            }
        }
    }
    let pts = viirs::load(&out.join("points.bin"))?;
    let mut foc = vec![0usize; n];
    for p in pts.iter().filter(|p| p.t < 168.0) {
        foc[p.prov as usize] += 1;
    }
    let mut rows: Vec<Row> = geo
        .codes
        .iter()
        .enumerate()
        .map(|(i, c)| Row {
            code: c.clone(),
            name: geo.names.get(c).cloned().unwrap_or_default(),
            ha_total: burn["by_prov_total_ha_2012_2025"][c].as_f64().unwrap_or(0.0),
            ha_unique: uniq[i + 1],
            area_ha: area[i + 1],
            focos: foc[i],
            share_unique: if area[i + 1] > 0.0 { uniq[i + 1] / area[i + 1] } else { 0.0 },
            rank: 0,
        })
        .collect();
    let tot: f64 = rows.iter().map(|r| r.ha_total).sum();
    let btot = burn["total_ha_2012_2025"].as_f64().unwrap();
    ensure!((tot - btot).abs() / tot < 1e-6, "province totals {tot} != national {btot}");
    rows.sort_by(|a, b| b.ha_unique.partial_cmp(&a.ha_unique).unwrap());
    for (j, r) in rows.iter_mut().enumerate() {
        r.rank = j + 1;
    }
    let tot_u: f64 = rows.iter().map(|r| r.ha_unique).sum();
    let tot_area: f64 = rows.iter().map(|r| r.area_ha).sum();
    let burned_any: f64 = (0..g.h).map(|r| cnt[r * g.w..(r + 1) * g.w].iter().filter(|v| **v > 0).count() as f64 * pixha[r]).sum();
    ensure!((tot_u - burned_any).abs() / tot_u < 1e-3, "burned pixels outside provinces: {tot_u} vs {burned_any}");
    let top5: f64 = rows[..5].iter().map(|r| r.ha_unique).sum();
    Ok(Ranking {
        metric: "MODIS MCD64A1 C6.1, distinct area burned at least once 2012-2025 (500 m pixels, spherical pixel area), ha".into(),
        total_ha_unique: tot_u,
        total_ha_repeat: tot,
        country_area_ha: tot_area,
        share_country_burned: tot_u / tot_area,
        top5_share: top5 / tot_u,
        rows,
    })
}
