//! NASA FIRMS VIIRS S-NPP 375 m country archive (Argentina, one CSV per year, 2012–2025) → hotspot points + counts.
//!
//! Filter (same as the whole project since v1): `type == 0` («presumed vegetation fire») and confidence nominal or high
//! (`n`/`h`; low-confidence detections are dropped). Each point gets a fractional month index
//! `t = (year-2012)*12 + (month-1) + (day-1)/days_in_month + (acq_time div 100)/24/30` and a province: point-in-polygon
//! against the INDEC (Censo 2022) province polygons, or the nearest province for the few points that fall in no polygon
//! because of coastline/border simplification.
use super::Geo;
use anyhow::{Context, Result};
use rayon::prelude::*;
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Copy)]
pub struct Pt {
    pub lon: f32,
    pub lat: f32,
    pub t: f32,
    pub prov: u8,
}

#[derive(Debug, Clone, Serialize)]
pub struct DayPts {
    pub date: String,
    pub bbox: [f64; 4],
    pub acq_time_utc: Vec<u32>,
    pub lon: Vec<f64>,
    pub lat: Vec<f64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct ViirsStats {
    pub rows_all_types: usize,
    pub type0_all_conf: usize,
    pub type0_low_conf_dropped: usize,
    pub total_used: usize,
    pub unmatched_to_nearest: usize,
    pub by_year: std::collections::BTreeMap<i32, usize>,
}

fn days_in_month(y: i32, m: u32) -> u32 {
    match m {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        _ => {
            if (y % 4 == 0 && y % 100 != 0) || y % 400 == 0 {
                29
            } else {
                28
            }
        }
    }
}

struct Row {
    lon: f64,
    lat: f64,
    t: f64,
    year: i32,
    date: String,
    acq: u32,
    day: bool,
}

/// Read every `viirs_<year>.csv` in `dir` for 2012..=2025. `days` = (date, bbox) windows whose daytime detections are kept
/// apart (the hotspots of the same afternoon as a Sentinel-2 image).
pub fn read(dir: &Path, geo: &Geo, days: &[(String, [f64; 4])]) -> Result<(Vec<Pt>, ViirsStats, Vec<DayPts>)> {
    let years: Vec<i32> = (2012..=2025).collect();
    let per_year: Vec<Result<(Vec<Row>, usize, usize, usize)>> = years
        .par_iter()
        .map(|y| {
            let p = dir.join(format!("viirs_{y}.csv"));
            let mut rdr = csv::Reader::from_path(&p).with_context(|| format!("reading {}", p.display()))?;
            let h = rdr.headers()?.clone();
            let col = |n: &str| h.iter().position(|c| c == n).with_context(|| format!("{}: no column {n}", p.display()));
            let (ila, ilo, idt, itm, icf, ity, idn) = (col("latitude")?, col("longitude")?, col("acq_date")?, col("acq_time")?, col("confidence")?, col("type")?, col("daynight")?);
            let (mut all, mut t0, mut t0low) = (0, 0, 0);
            let mut out = vec![];
            let mut rec = csv::ByteRecord::new();
            while rdr.read_byte_record(&mut rec)? {
                all += 1;
                if &rec[ity] != b"0" {
                    continue;
                }
                t0 += 1;
                if &rec[icf] == b"l" {
                    t0low += 1;
                    continue;
                }
                let date = std::str::from_utf8(&rec[idt])?;
                let yy: i32 = date[0..4].parse()?;
                let mm: u32 = date[5..7].parse()?;
                let dd: u32 = date[8..10].parse()?;
                let acq: u32 = std::str::from_utf8(&rec[itm])?.trim().parse()?;
                let t = (yy - 2012) as f64 * 12.0 + (mm - 1) as f64 + (dd - 1) as f64 / days_in_month(yy, mm) as f64 + (acq / 100) as f64 / 24.0 / 30.0;
                out.push(Row {
                    lon: std::str::from_utf8(&rec[ilo])?.parse()?,
                    lat: std::str::from_utf8(&rec[ila])?.parse()?,
                    t,
                    year: yy,
                    date: date.to_string(),
                    acq,
                    day: &rec[idn] == b"D",
                });
            }
            Ok((out, all, t0, t0low))
        })
        .collect();
    let mut rows = vec![];
    let mut st = ViirsStats { rows_all_types: 0, type0_all_conf: 0, type0_low_conf_dropped: 0, total_used: 0, unmatched_to_nearest: 0, by_year: Default::default() };
    for r in per_year {
        let (v, a, t0, tl) = r?;
        st.rows_all_types += a;
        st.type0_all_conf += t0;
        st.type0_low_conf_dropped += tl;
        rows.extend(v);
    }
    st.total_used = rows.len();
    let provs: Vec<(u8, bool)> = rows
        .par_iter()
        .map(|r| {
            let (i, inside) = geo.prov_index.locate_or_nearest(r.lon, r.lat);
            (i as u8, inside)
        })
        .collect();
    st.unmatched_to_nearest = provs.iter().filter(|p| !p.1).count();
    let mut pts: Vec<Pt> = rows.iter().zip(provs.iter()).map(|(r, p)| Pt { lon: r.lon as f32, lat: r.lat as f32, t: r.t as f32, prov: p.0 }).collect();
    for r in &rows {
        *st.by_year.entry(r.year).or_default() += 1;
    }
    let mut dp = vec![];
    for (date, bb) in days {
        let mut d = DayPts { date: date.clone(), bbox: *bb, acq_time_utc: vec![], lon: vec![], lat: vec![] };
        for r in rows.iter().filter(|r| &r.date == date && r.day && r.lon >= bb[0] && r.lon <= bb[2] && r.lat >= bb[1] && r.lat <= bb[3]) {
            if !d.acq_time_utc.contains(&r.acq) {
                d.acq_time_utc.push(r.acq);
            }
            d.lon.push(r.lon);
            d.lat.push(r.lat);
        }
        dp.push(d);
    }
    // stable sort by time (the order the renderer replays them)
    pts.sort_by(|a, b| a.t.partial_cmp(&b.t).unwrap());
    Ok((pts, st, dp))
}

/// points file: little-endian records of (lon f32, lat f32, t f32, prov u8)
pub fn save(path: &Path, pts: &[Pt]) -> Result<()> {
    let mut b = Vec::with_capacity(pts.len() * 13);
    for p in pts {
        b.extend_from_slice(&p.lon.to_le_bytes());
        b.extend_from_slice(&p.lat.to_le_bytes());
        b.extend_from_slice(&p.t.to_le_bytes());
        b.push(p.prov);
    }
    std::fs::write(path, b)?;
    Ok(())
}

pub fn load(path: &Path) -> Result<Vec<Pt>> {
    let b = std::fs::read(path).with_context(|| format!("{} (run `incendios prep`)", path.display()))?;
    Ok(b.chunks_exact(13)
        .map(|c| Pt {
            lon: f32::from_le_bytes(c[0..4].try_into().unwrap()),
            lat: f32::from_le_bytes(c[4..8].try_into().unwrap()),
            t: f32::from_le_bytes(c[8..12].try_into().unwrap()),
            prov: c[12],
        })
        .collect())
}
