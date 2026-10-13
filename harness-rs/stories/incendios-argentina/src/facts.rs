//! Every number on screen, computed from build/derived (the Rust data prep), saved as build/facts.json. The asserts that
//! guard each wording («casi 7», «9 de cada 10», «casi 12 Tucumanes», …) live in story.toml [[assert]] and run on every build.
use crate::prep::{derived, read_json, s2_date, viirs};
use anyhow::Result;
use datavid::Facts;
use datavid::story::{StoryFile, input_path};
use std::path::Path;

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 { v[n / 2] } else { (v[n / 2 - 1] + v[n / 2]) / 2.0 }
}

pub fn compute(file: &StoryFile, dir: &Path) -> Result<Facts> {
    let out = derived(dir);
    let d = |n: &str| read_json(&out.join(n));
    let mut f = Facts::new();
    let v = d("viirs.json")?;
    f.set("total_focos", v["total_used"].clone(), "FIRMS VIIRS S-NPP 2012-2025, type 0, confidence n/h (viirs.json)");
    let years: Vec<i64> = v["by_year"].as_object().unwrap().keys().map(|k| k.parse().unwrap()).collect();
    f.set("y0", *years.iter().min().unwrap(), "first year of the VIIRS series");
    f.set("y1", *years.iter().max().unwrap(), "last year of the VIIRS series");

    let c = d("causas.json")?;
    let h = c["all_1993_2019"]["humana_sobre_conocida"].as_f64().unwrap();
    f.set("hum_share_known", h, "Min. Ambiente causes 1993-2019: (negligencia + intencional) / known cause");
    f.set("hum_10", (h * 10.0).round(), "round(human share of known-cause fires x 10)");

    let rk = d("ranking.json")?;
    let uniq = rk["total_ha_unique"].as_f64().unwrap();
    f.set("uniq_ha", uniq, "MODIS MCD64A1 distinct area burned at least once 2012-2025 (ranking.json)");
    f.set("uniq_mha_txt", datavid::facts::es_dec(uniq / 1e6, 1), "uniq_ha in millions, 1 decimal");
    f.set("share_country", rk["share_country_burned"].clone(), "distinct burned area / area of the 24 jurisdictions");
    f.set("top_n", 5, "rows shown in the ranking");
    f.set("top5_share", rk["top5_share"].clone(), "share of the distinct burned area in the top-5 provinces");
    let rows = rk["rows"].as_array().unwrap();
    let vmax = rows[0]["ha_unique"].as_f64().unwrap();
    for (i, r) in rows.iter().take(5).enumerate() {
        f.set(&format!("rk{}_name", i + 1), r["name"].as_str().unwrap().to_uppercase(), "province name (IGN), ranked by distinct burned ha");
        f.set(&format!("rk{}_code", i + 1), r["code"].clone(), "INDEC province code");
        f.set(&format!("rk{}_frac", i + 1), r["ha_unique"].as_f64().unwrap() / vmax, "bar length: ha / ha of the first");
    }
    f.set("top5_names", serde_json::json!(rows.iter().take(5).map(|r| r["name"].as_str().unwrap().to_uppercase()).collect::<Vec<_>>()), "top-5 names");

    let q = d("tucumanes.json")?;
    let ratio = q["ratio"].as_f64().unwrap();
    f.set("tucumanes", ratio, "distinct burned ha / Tucumán area (geodesic, INDEC/IGN boundary)");
    f.set("tucumanes_indec", q["ratio_indec"].clone(), "same with INDEC's official 22.524 km²");
    f.set("tucumanes_n", ratio.ceil(), "«casi N»: the next whole number");

    let t = d("tucuman.json")?;
    f.set("tuc_share_cane_zafra", t["share_cane_zafra"].clone(), "Tucumán focos in the 12 EEAOC cane departments during May-Nov / all Tucumán focos");
    f.set("tuc_pct", (t["share_cane_zafra"].as_f64().unwrap() * 100.0).round(), "rounded percentage");
    f.set("tuc_cane_zafra", t["cane_zafra"].clone(), "count");
    f.set("tuc_zone_pct", (100.0 * t["area_cane12_km2"].as_f64().unwrap() / t["area_tuc_km2"].as_f64().unwrap()).round(), "cane departments / Tucumán area (geodesic)");

    // Entre Ríos 2020 vs its median of the other 13 years
    let pts = viirs::load(&out.join("points.bin"))?;
    let geo = crate::prep::Geo::load(&input_path(file, dir, "natgeo")?, &input_path(file, dir, "provincias")?)?;
    let ier = geo.idx("30") as u8;
    let mut ery = [0f64; 14];
    for p in pts.iter().filter(|p| p.prov == ier && p.t < 168.0) {
        ery[(p.t as f64 / 12.0).floor() as usize] += 1.0;
    }
    let er2020 = ery[8];
    let med = median(ery.iter().enumerate().filter(|(i, _)| *i != 8).map(|(_, v)| *v).collect());
    f.set("er_year", 2020, "year of the Entre Ríos stop (the record year of its VIIRS series)");
    f.set("er_2020", er2020, "VIIRS focos in Entre Ríos in 2020");
    f.set("er_median_other13", med, "median of Entre Ríos focos in the other 13 years 2012-2025");
    f.set("er_ratio", er2020 / med, "2020 / median of the other years");
    f.set("er_x", (er2020 / med).round(), "«casi N veces»");
    f.set("er_is_record", (ery.iter().cloned().fold(0.0, f64::max) == er2020) as i64, "2020 is the maximum of the series");

    let b = d("burn.json")?;
    let (c25, c26) = (b["comarca_2025_q1_ha"].as_f64().unwrap(), b["comarca_2026_q1_ha"].as_f64().unwrap());
    f.set("pa25", (c25 / 1000.0).floor() * 1000.0, "Comarca Andina box, MODIS Jan-Mar 2025, floored to thousands");
    f.set("pa26", (c26 / 1000.0).floor() * 1000.0, "Comarca Andina box, MODIS Jan-Mar 2026, floored to thousands");
    f.set("pa_ratio", c26 / c25, "2026 / 2025");
    f.set("pa_x", (c26 / c25).floor(), "«N veces más»: whole part");
    f.set("pa_year", 2026, "Comarca season shown");
    f.set("pa_prev", 2025, "previous season");

    let s2 = |n: &str| -> Result<String> { s2_date(&read_json(&input_path(file, dir, "s2_dir")?.join(format!("{n}.json")))?) };
    f.set("tuc_s2_date", s2("tuc_2025-09-23")?, "Sentinel-2 L2A acquisition (product id)");
    f.set("er_s2_date", s2("delta_2020-09-23")?, "Sentinel-2 L2A acquisition (product id)");
    for y in ["2024", "2025", "2026"] {
        f.set(&format!("c{}_date", &y[2..]), s2(&format!("comarca_{y}"))?, "Sentinel-2 L2A acquisition (product id)");
    }
    Ok(f)
}
