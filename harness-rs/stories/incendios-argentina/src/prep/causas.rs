//! Fire causes from the open dataset «Causas y cantidad de incendios por provincia» (Ministerio de Ambiente y Desarrollo
//! Sostenible, Programa Nacional de Estadística Forestal, 1993–2019; Latin-1, `;`-separated). Human = negligencia +
//! intencional; shares over all fires and over fires with a known cause.
use anyhow::{Context, Result};
use serde::Serialize;
use std::collections::BTreeMap;
use std::path::Path;

#[derive(Debug, Clone, Default, Serialize)]
pub struct Share {
    pub total: i64,
    pub negligencia: i64,
    pub intencional: i64,
    pub natural: i64,
    pub desconocida: i64,
    pub conocida: i64,
    pub humana_sobre_total: f64,
    pub desconocida_sobre_total: f64,
    pub humana_sobre_conocida: f64,
    pub natural_sobre_conocida: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct Causas {
    pub rows: usize,
    pub years: [i64; 2],
    pub all_1993_2019: Share,
    pub by_prov: BTreeMap<String, Share>,
}

fn share(rows: &[[i64; 5]]) -> Share {
    let mut s = Share::default();
    for r in rows {
        s.total += r[0];
        s.negligencia += r[1];
        s.intencional += r[2];
        s.natural += r[3];
        s.desconocida += r[4];
    }
    s.conocida = s.negligencia + s.intencional + s.natural;
    let t = s.total.max(1) as f64;
    let k = s.conocida.max(1) as f64;
    s.humana_sobre_total = (s.negligencia + s.intencional) as f64 / t;
    s.desconocida_sobre_total = s.desconocida as f64 / t;
    s.humana_sobre_conocida = (s.negligencia + s.intencional) as f64 / k;
    s.natural_sobre_conocida = s.natural as f64 / k;
    s
}

pub fn run(csv_path: &Path) -> Result<Causas> {
    let raw = std::fs::read(csv_path).with_context(|| csv_path.display().to_string())?;
    let txt: String = raw.iter().map(|&b| b as char).collect(); // Latin-1 → Unicode is a 1:1 byte map
    let mut rdr = csv::ReaderBuilder::new().delimiter(b';').from_reader(txt.as_bytes());
    let h = rdr.headers()?.clone();
    let col = |n: &str| h.iter().position(|c| c == n).with_context(|| format!("causes CSV: no column {n}"));
    let (iy, ip) = (col("incendio_anio")?, col("incendio_provincia")?);
    let ic = [col("incendio_total_numero")?, col("incendio_negligencia_numero")?, col("incendio_intencional_numero")?, col("incendio_natural_numero")?, col("incendio_desconocida_numero")?];
    let mut all = vec![];
    let mut byp: BTreeMap<String, Vec<[i64; 5]>> = BTreeMap::new();
    let (mut y0, mut y1) = (i64::MAX, i64::MIN);
    for rec in rdr.records() {
        let rec = rec?;
        let y: i64 = rec[iy].trim().parse().unwrap_or(0);
        y0 = y0.min(y);
        y1 = y1.max(y);
        // pandas.to_numeric(errors="coerce").fillna(0)
        let v = ic.map(|i| rec[i].trim().parse::<f64>().map(|f| f as i64).unwrap_or(0));
        all.push(v);
        byp.entry(rec[ip].to_string()).or_default().push(v);
    }
    Ok(Causas { rows: all.len(), years: [y0, y1], all_1993_2019: share(&all), by_prov: byp.iter().map(|(k, v)| (k.clone(), share(v))).collect() })
}
