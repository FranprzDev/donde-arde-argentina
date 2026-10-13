//! Data prep, all in Rust: raw open data → `build/derived/*` (points, statistics, rasters, geometry).
//!
//! | step | input (story.toml [inputs]) | output |
//! |---|---|---|
//! | viirs | FIRMS VIIRS S-NPP CSVs 2012–2025 | points.bin, viirs.json, s2_day.json |
//! | causas | Min. Ambiente causes CSV 1993–2019 | causas.json |
//! | modis | MCD64A1 C6.1 monthly windows (UMD) | burn.json, scar_count.u8, scar_*.u8 |
//! | ranking | burn rasters + provinces + points | ranking.json |
//! | tucuman | points + IGN departments + EEAOC cane table | tucuman.json |
//! | tucumanes | INDEC province boundary + burn raster | tucumanes.json |
//! | geometry | provinces, neighbours, departments, Natural Earth | geometry.json |
pub mod causas;
pub mod geometry;
pub mod modis;
pub mod ranking;
pub mod tucuman;
pub mod tucumanes;
pub mod viirs;

use anyhow::{Context, Result};
use datavid::geo::{Poly, RegionIndex, Ring};
use datavid::story::{StoryFile, input_path};
use serde_json::Value;
use std::path::{Path, PathBuf};
use std::time::Instant;

/// Province geometry shared by every step: INDEC Censo 2022 provinces (dissolved census radios), codes sorted.
pub struct Geo {
    pub codes: Vec<String>,
    pub prov_rings: Vec<Vec<Ring>>,
    pub prov_index: RegionIndex,
    pub names: std::collections::HashMap<String, String>,
}

impl Geo {
    pub fn load(natgeo: &Path, provincias: &Path) -> Result<Self> {
        let v: Value = serde_json::from_str(&std::fs::read_to_string(natgeo).with_context(|| natgeo.display().to_string())?)?;
        let prov = v["prov"].as_object().context("natgeo: no 'prov'")?;
        let mut codes: Vec<String> = prov.keys().cloned().collect();
        codes.sort();
        let prov_rings: Vec<Vec<Ring>> = codes.iter().map(|c| datavid::geo::rings_json(&prov[c])).collect::<Result<_>>()?;
        let prov_index = RegionIndex::new(codes.iter().zip(prov_rings.iter()).map(|(c, rs)| (c.clone(), rs.iter().map(|r| Poly { ext: r.clone(), holes: vec![] }).collect())).collect());
        let pv: Value = serde_json::from_str(&std::fs::read_to_string(provincias)?)?;
        let mut names = std::collections::HashMap::new();
        for f in pv["features"].as_array().context("provincias: no features")? {
            names.insert(f["properties"]["id"].as_str().unwrap_or("").to_string(), f["properties"]["nombre"].as_str().unwrap_or("").to_string());
        }
        names.insert("94".into(), "Tierra del Fuego".into());
        names.insert("02".into(), "CABA".into());
        Ok(Self { codes, prov_rings, prov_index, names })
    }
    pub fn idx(&self, code: &str) -> usize {
        self.codes.iter().position(|c| c == code).unwrap_or_else(|| panic!("unknown province code {code}"))
    }
    pub fn polys(&self, code: &str) -> Vec<Poly> {
        self.prov_rings[self.idx(code)].iter().map(|r| Poly { ext: r.clone(), holes: vec![] }).collect()
    }
}

pub fn derived(dir: &Path) -> PathBuf {
    dir.join("build").join("derived")
}

pub fn write_json(path: &Path, v: &impl serde::Serialize) -> Result<()> {
    if let Some(p) = path.parent() {
        std::fs::create_dir_all(p)?;
    }
    std::fs::write(path, serde_json::to_string_pretty(v)?)?;
    Ok(())
}
pub fn read_json(path: &Path) -> Result<Value> {
    Ok(serde_json::from_str(&std::fs::read_to_string(path).with_context(|| format!("{} (run `incendios prep`)", path.display()))?)?)
}

/// the acquisition date (YYYY-MM-DD, UTC) of a Sentinel-2 crop, read from its first product id (…_YYYYMMDDTHHMMSS_…)
pub fn s2_date(meta: &Value) -> Result<String> {
    let id = meta["ids"][0].as_str().or_else(|| meta["id"].as_str()).context("s2 meta without ids")?;
    let f = id.split('_').nth(2).context("unexpected Sentinel-2 id")?;
    Ok(format!("{}-{}-{}", &f[0..4], &f[4..6], &f[6..8]))
}
pub fn s2_bbox(meta: &Value) -> [f64; 4] {
    let b = &meta["bbox"];
    [0, 1, 2, 3].map(|i| b[i].as_f64().unwrap())
}

/// Run every prep step (or the ones named in `only`).
pub fn run(file: &StoryFile, dir: &Path, only: &[String]) -> Result<()> {
    let want = |s: &str| only.is_empty() || only.iter().any(|o| o == s);
    let out = derived(dir);
    std::fs::create_dir_all(&out)?;
    let inp = |n: &str| input_path(file, dir, n);
    let geo = Geo::load(&inp("natgeo")?, &inp("provincias")?)?;
    let t0 = Instant::now();
    let s2 = |name: &str| -> Result<Value> { read_json(&inp("s2_dir")?.join(format!("{name}.json"))) };
    if want("viirs") {
        let tuc = s2("tuc_2025-09-23")?;
        let er = s2("delta_2020-09-23")?;
        let days = vec![(s2_date(&tuc)?, s2_bbox(&tuc)), (s2_date(&er)?, s2_bbox(&er))];
        let (pts, st, dp) = viirs::read(&inp("viirs_dir")?, &geo, &days)?;
        viirs::save(&out.join("points.bin"), &pts)?;
        write_json(&out.join("viirs.json"), &st)?;
        write_json(&out.join("s2_day.json"), &serde_json::json!({"tuc": dp[0], "er": dp[1]}))?;
        eprintln!("prep viirs: {} points ({} to nearest province) in {:.1}s", st.total_used, st.unmatched_to_nearest, t0.elapsed().as_secs_f64());
    }
    if want("causas") {
        let c = causas::run(&inp("causas_csv")?)?;
        write_json(&out.join("causas.json"), &c)?;
        eprintln!("prep causas: done");
    }
    if want("modis") {
        let t = Instant::now();
        modis::run(&inp("modis_dir")?, &geo, &out)?;
        eprintln!("prep modis: done in {:.1}s", t.elapsed().as_secs_f64());
    }
    if want("ranking") {
        let r = ranking::run(&geo, &out)?;
        write_json(&out.join("ranking.json"), &r)?;
        eprintln!("prep ranking: done");
    }
    if want("tucuman") {
        let r = tucuman::run(&geo, &out, &inp("departamentos")?, &inp("eeaoc_csv")?)?;
        write_json(&out.join("tucuman.json"), &r)?;
        eprintln!("prep tucuman: done");
    }
    if want("tucumanes") {
        let t = Instant::now();
        let r = tucumanes::run(&geo, &out, &inp("provincias")?)?;
        write_json(&out.join("tucumanes.json"), &r)?;
        eprintln!("prep tucumanes: done in {:.1}s", t.elapsed().as_secs_f64());
    }
    if want("geometry") {
        let g = geometry::run(file, dir, &geo, &out)?;
        write_json(&out.join("geometry.json"), &g)?;
        eprintln!("prep geometry: done");
    }
    eprintln!("prep: total {:.1}s", t0.elapsed().as_secs_f64());
    Ok(())
}
