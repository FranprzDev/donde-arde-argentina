//! `incendios verify`: compare the Rust data prep against the outputs of the original Python pipeline (kept only as a
//! reference, never run by the harness). Writes build/derived/VERIFY.md and fails if a number that reaches the screen differs.
use crate::prep::{read_json, viirs};
use anyhow::{Result, bail};
use datavid::npy;
use datavid::story::{StoryFile, input_path};
use serde_json::Value;
use std::path::Path;

struct T {
    rows: Vec<String>,
    bad: Vec<String>,
}
impl T {
    fn num(&mut self, what: &str, rust: f64, py: f64, rel: f64, on_screen: bool) {
        let d = if py != 0.0 { (rust - py).abs() / py.abs() } else { (rust - py).abs() };
        let ok = d <= rel;
        self.rows.push(format!("| {what} | {rust} | {py} | {:.2e} | {} |", d, if ok { "yes" } else if on_screen { "**NO**" } else { "differs (off screen)" }));
        if !ok && on_screen {
            self.bad.push(what.to_string());
        }
    }
    fn note(&mut self, what: &str, rust: &str, py: &str, ok: bool) {
        self.rows.push(format!("| {what} | {rust} | {py} | | {} |", if ok { "yes" } else { "differs (see note)" }));
    }
}

pub fn run(file: &StoryFile, dir: &Path) -> Result<()> {
    let refd = input_path(file, dir, "reference_dir")?;
    let out = crate::prep::derived(dir);
    let r = |n: &str| read_json(&refd.join(n));
    let d = |n: &str| read_json(&out.join(n));
    let mut t = T { rows: vec!["| quantity | Rust | Python reference | rel. diff | match |".into(), "|---|---|---|---|---|".into()], bad: vec![] };

    let v = d("viirs.json")?;
    let s_old = read_json(&input_path(file, dir, "reference_viirs_stats")?)?;
    t.num("VIIRS points used (type 0, conf n/h)", v["total_used"].as_f64().unwrap(), s_old["total_used"].as_f64().unwrap(), 0.0, true);
    for y in 2012..=2025 {
        t.num(&format!("VIIRS points {y}"), v["by_year"][y.to_string()].as_f64().unwrap(), s_old["by_year"][y.to_string()].as_f64().unwrap(), 0.0, false);
    }
    // per-point province assignment against points.npz
    let pts = viirs::load(&out.join("points.bin"))?;
    let z = npy::read_npz(&input_path(file, dir, "reference_points")?)?;
    let (pt, pp) = (z["t"].to_f64(), z["prov"].to_f64());
    let mut order: Vec<usize> = (0..pt.len()).collect();
    order.sort_by(|a, b| pt[*a].partial_cmp(&pt[*b]).unwrap());
    let same = order.iter().zip(pts.iter()).filter(|(i, p)| pp[**i] as u8 == p.prov && (pt[**i] as f32) == p.t).count();
    t.num("points with identical (t, province) after the stable time sort", same as f64, pts.len() as f64, 1e-5, true);

    let c = d("causas.json")?;
    let cr = r("causas_stats.json")?;
    t.num("causes: human share of known-cause fires 1993–2019", c["all_1993_2019"]["humana_sobre_conocida"].as_f64().unwrap(), cr["all_1993_2019"]["humana_sobre_conocida"].as_f64().unwrap(), 1e-12, true);
    t.num("causes: unknown share of all fires", c["all_1993_2019"]["desconocida_sobre_total"].as_f64().unwrap(), cr["all_1993_2019"]["desconocida_sobre_total"].as_f64().unwrap(), 1e-12, false);

    let b = d("burn.json")?;
    let br = r("burn_stats.json")?;
    for (k, kr, scr) in [("total_ha_2012_2025", "total_ha_2012_2025", false), ("unique_ha_2012_2025", "unique_ha_2012_2025", true), ("er_2020_ha", "er_2020_ha", false), ("comarca_2025_q1_ha", "comarca_2025_q1_ha", true), ("comarca_2026_q1_ha", "comarca_2026_q1_ha", true), ("pitch_every_s", "pitch_every_s", false)] {
        t.num(&format!("MODIS {k}"), b[k].as_f64().unwrap(), br[kr].as_f64().unwrap(), 1e-6, scr);
    }
    let cnt = std::fs::read(out.join("scar_count.u8"))?;
    let cref = npy::read_npy(&refd.join("scar_count.npy"))?;
    let cv = cref.to_f64();
    let eq = cnt.iter().zip(cv.iter()).filter(|(a, b)| **a as f64 == **b).count();
    t.num("MODIS burn-count raster: identical pixels", eq as f64, cv.len() as f64, 0.0, true);

    let k = d("ranking.json")?;
    let kr = r("ranking_v7.json")?;
    t.num("ranking: distinct burned ha (country)", k["total_ha_unique"].as_f64().unwrap(), kr["total_ha_unique"].as_f64().unwrap(), 1e-9, true);
    t.num("ranking: share of the country burned", k["share_country_burned"].as_f64().unwrap(), kr["share_country_burned"].as_f64().unwrap(), 1e-9, true);
    t.num("ranking: top-5 share", k["top5_share"].as_f64().unwrap(), kr["top5_share"].as_f64().unwrap(), 1e-9, true);
    let names = |v: &Value| v["rows"].as_array().unwrap().iter().map(|r| r["code"].as_str().unwrap().to_string()).collect::<Vec<_>>();
    t.note("ranking order (24 codes)", &names(&k).join(","), &names(&kr).join(","), names(&k) == names(&kr));
    if names(&k) != names(&kr) {
        t.bad.push("ranking order".into());
    }
    for (a, bb) in k["rows"].as_array().unwrap().iter().zip(kr["rows"].as_array().unwrap()) {
        t.num(&format!("focos {}", a["name"].as_str().unwrap()), a["focos"].as_f64().unwrap(), bb["focos"].as_f64().unwrap(), 0.0, false);
    }

    let tu = d("tucuman.json")?;
    let tr = r("tucuman_stats.json")?;
    for (key, scr) in [("total", false), ("cane_zafra", true), ("share_cane_zafra", true), ("area_cane12_km2", true), ("area_tuc_km2", true)] {
        t.num(&format!("Tucumán {key}"), tu[key].as_f64().unwrap(), tr[key].as_f64().unwrap(), 1e-6, scr);
    }
    let q = d("tucumanes.json")?;
    let qr = r("tucumanes_v10.json")?;
    t.num("Tucumán area (geodesic km²)", q["tuc_km2"].as_f64().unwrap(), qr["tuc_km2"].as_f64().unwrap(), 1e-6, true);
    t.num("burned area / Tucumán", q["ratio"].as_f64().unwrap(), qr["ratio"].as_f64().unwrap(), 1e-6, true);
    let cp = |v: &Value| v["copies"].as_array().unwrap().iter().map(|c| format!("({},{})", c["lon"], c["lat"])).collect::<Vec<_>>().join(" ");
    t.note("12 Tucumán copy positions", &cp(&q), &cp(&qr), cp(&q) == cp(&qr));

    let s = d("s2_day.json")?;
    let sr = r("s2_day_hotspots.json")?;
    for kk in ["tuc", "er"] {
        t.num(&format!("Sentinel-2 day hotspots {kk}"), s[kk]["lon"].as_array().unwrap().len() as f64, sr[kk]["lon"].as_array().unwrap().len() as f64, 0.0, false);
    }
    let md = format!(
        "# Rust data prep vs the Python reference\n\nReference = outputs of the original Python pipeline (v10), used only for this comparison.\n\
         \"off screen\" rows do not reach the video.\n\n{}\n\nOn-screen mismatches: {}\n",
        t.rows.join("\n"),
        if t.bad.is_empty() { "none".to_string() } else { t.bad.join(", ") }
    );
    std::fs::write(out.join("VERIFY.md"), &md)?;
    println!("{md}");
    if !t.bad.is_empty() {
        bail!("Rust prep differs from the Python reference on: {}", t.bad.join(", "));
    }
    Ok(())
}
