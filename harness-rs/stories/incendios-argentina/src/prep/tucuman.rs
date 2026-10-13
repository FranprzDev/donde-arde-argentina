//! Tucumán and the sugarcane harvest (zafra). VIIRS points inside Tucumán (INDEC province '90', same assignment as the
//! whole video) → IGN department (point in polygon, nearest for edge points) → cane zone = the 12 departments with more
//! than 5.000 ha of harvestable cane in EEAOC Reporte Agroindustrial 370 (zafra 2026, table 1). Zafra = May–November.
use super::{Geo, viirs};
use anyhow::{Context, Result, ensure};
use datavid::geo::{RegionIndex, geodesic_area_m2, geometry_polys};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

/// lower-case ASCII without spaces or dots (accents folded), with the EEAOC table's one abbreviation expanded
pub fn norm(s: &str) -> String {
    let f: String = s
        .chars()
        .map(|c| match c {
            'á' | 'à' | 'ä' | 'Á' => 'a',
            'é' | 'è' | 'ë' | 'É' => 'e',
            'í' | 'ì' | 'ï' | 'Í' => 'i',
            'ó' | 'ò' | 'ö' | 'Ó' => 'o',
            'ú' | 'ù' | 'ü' | 'Ú' | 'Ü' => 'u',
            'ñ' | 'Ñ' => 'n',
            c => c,
        })
        .filter(|c| *c != '.' && *c != ' ')
        .collect::<String>()
        .to_lowercase();
    if f == "jbalberdi" { "juanbautistaalberdi".into() } else { f }
}

pub struct Deps {
    pub names: Vec<String>,
    pub index: RegionIndex,
}

pub fn load_deps(path: &Path) -> Result<Deps> {
    let v: Value = serde_json::from_str(&std::fs::read_to_string(path).with_context(|| path.display().to_string())?)?;
    let mut regions = vec![];
    for f in v["features"].as_array().context("departamentos: no features")? {
        if f["properties"]["provincia"]["id"].as_str() == Some("90") {
            regions.push((f["properties"]["nombre"].as_str().unwrap_or("").to_string(), geometry_polys(&f["geometry"])?));
        }
    }
    Ok(Deps { names: regions.iter().map(|r| r.0.clone()).collect(), index: RegionIndex::new(regions) })
}

pub fn cane_table(path: &Path) -> Result<BTreeMap<String, i64>> {
    let mut rdr = csv::Reader::from_path(path)?;
    let mut out = BTreeMap::new();
    for r in rdr.deserialize::<BTreeMap<String, String>>() {
        let r = r?;
        out.insert(norm(&r["departamento"]), r["total_ha"].trim().parse::<f64>()? as i64);
    }
    Ok(out)
}

pub fn run(geo: &Geo, out: &Path, deps_path: &Path, eeaoc: &Path) -> Result<Value> {
    let it = geo.idx("90") as u8;
    let pts: Vec<_> = viirs::load(&out.join("points.bin"))?.into_iter().filter(|p| p.prov == it).collect();
    let deps = load_deps(deps_path)?;
    let cane = cane_table(eeaoc)?;
    let cane12: BTreeSet<String> = cane.iter().filter(|(_, v)| **v > 5000).map(|(k, _)| k.clone()).collect();
    ensure!(cane12.len() == 12, "expected 12 cane departments, got {}", cane12.len());
    let dep_norm: BTreeSet<String> = deps.names.iter().map(|n| norm(n)).collect();
    ensure!(cane12.is_subset(&dep_norm), "cane departments not found among IGN departments: {:?}", cane12.difference(&dep_norm).collect::<Vec<_>>());
    let in_cane: Vec<bool> = deps.names.iter().map(|n| cane12.contains(&norm(n))).collect();
    let (mut zafra, mut cane_n, mut cane_zafra) = (0usize, 0usize, 0usize);
    let mut by_dep: BTreeMap<String, usize> = BTreeMap::new();
    let mut by_year_cz: BTreeMap<i32, usize> = BTreeMap::new();
    let mut by_month = [0usize; 12];
    for p in &pts {
        // points are float32 in the cache; the Python reference also tested float32 values widened to float64
        let (d, _) = deps.index.locate_or_nearest(p.lon as f64, p.lat as f64);
        let t = p.t as f64;
        let month = (t % 12.0) as usize + 1;
        let year = 2012 + (t / 12.0).floor() as i32;
        let z = (5..=11).contains(&month);
        zafra += z as usize;
        cane_n += in_cane[d] as usize;
        if z && in_cane[d] {
            cane_zafra += 1;
            *by_year_cz.entry(year).or_default() += 1;
        }
        by_month[month - 1] += 1;
        *by_dep.entry(deps.names[d].clone()).or_default() += 1;
    }
    let area = |sel: &dyn Fn(usize) -> bool| -> f64 { (0..deps.names.len()).filter(|i| sel(*i)).map(|i| deps.index.polys(i).iter().map(geodesic_area_m2).sum::<f64>() / 1e6).sum() };
    let a12 = area(&|i| in_cane[i]);
    let atuc = area(&|_| true);
    let n = pts.len() as f64;
    Ok(json!({
        "total": pts.len(), "zafra": zafra, "cane": cane_n, "cane_zafra": cane_zafra,
        "share_zafra": zafra as f64 / n, "share_cane": cane_n as f64 / n, "share_cane_zafra": cane_zafra as f64 / n,
        "cane_ha_tucuman": cane.values().sum::<i64>(),
        "cane_area_share_12": cane12.iter().map(|k| cane[k]).sum::<i64>() as f64 / cane.values().sum::<i64>() as f64,
        "area_cane12_km2": a12, "area_tuc_km2": atuc,
        "by_month": by_month, "by_year_cane_zafra": by_year_cz, "by_dep": by_dep,
        "cane12": cane12,
    }))
}
