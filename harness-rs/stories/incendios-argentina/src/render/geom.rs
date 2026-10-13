//! Render inputs loaded once: geometry (build/derived/geometry.json), asset metadata (build/assets.json) and flags
//! (inline SVG).
use crate::prep::read_json;
use anyhow::{Context, Result};
use datavid::geo::Ring;
use serde_json::Value;
use std::collections::HashMap;
use std::fmt::Write;
use std::path::Path;

pub struct Geom {
    pub codes: Vec<String>,
    pub prov: HashMap<String, Vec<Ring>>,
    pub neigh: Vec<Ring>,
    pub ar_out: Vec<Ring>,
    pub stop_out: [Vec<Ring>; 2],
    pub tuc_zone: Vec<Ring>,
    pub label_pt: HashMap<String, [f64; 2]>,
    pub ar_pts: Vec<[f64; 2]>,
    pub rays: Vec<(f64, i32, f64, f64)>,
    pub embers: Vec<[f64; 3]>,
    pub stars: Vec<[f64; 3]>,
    pub tu_ring: Ring,
    pub tu_c0: [f64; 2],
    pub tu_copies: Vec<[f64; 2]>,
    pub tu_fill12: Vec<Ring>,
    pub land: Vec<Ring>,
}

fn rings(v: &Value) -> Vec<Ring> {
    datavid::geo::rings_json(v).unwrap_or_default()
}
fn p2(v: &Value) -> [f64; 2] {
    [v[0].as_f64().unwrap(), v[1].as_f64().unwrap()]
}

impl Geom {
    pub fn load(path: &Path) -> Result<Self> {
        let g = read_json(path)?;
        let codes: Vec<String> = g["codes"].as_array().context("geometry codes")?.iter().map(|c| c.as_str().unwrap().to_string()).collect();
        let prov = codes.iter().map(|c| (c.clone(), rings(&g["prov"][c]))).collect();
        Ok(Self {
            prov,
            neigh: rings(&g["neigh"]),
            ar_out: rings(&g["ar_out"]),
            stop_out: [rings(&g["stop_out"][0]), rings(&g["stop_out"][1])],
            tuc_zone: rings(&g["tuc_zone"]),
            label_pt: g["label_pt"].as_object().unwrap().iter().map(|(k, v)| (k.clone(), p2(v))).collect(),
            ar_pts: g["ar_pts"].as_array().unwrap().iter().map(p2).collect(),
            rays: g["rays"].as_array().unwrap().iter().map(|r| (r[0].as_f64().unwrap(), r[1].as_f64().unwrap() as i32, r[2].as_f64().unwrap(), r[3].as_f64().unwrap())).collect(),
            embers: g["embers"].as_array().unwrap().iter().map(|e| [e[0].as_f64().unwrap(), e[1].as_f64().unwrap(), e[2].as_f64().unwrap()]).collect(),
            stars: g["stars"].as_array().unwrap().iter().map(|e| [e[0].as_f64().unwrap(), e[1].as_f64().unwrap(), e[2].as_f64().unwrap()]).collect(),
            tu_ring: g["tu_ring"].as_array().context("tu_ring")?.iter().map(p2).collect(),
            tu_c0: p2(&g["tu_c0"]),
            tu_copies: g["tu_copies"].as_array().unwrap().iter().map(p2).collect(),
            tu_fill12: rings(&g["tu_fill12"]),
            land: rings(&g["land"]),
            codes,
        })
    }
}

/// a ring in unit map space (lon·cos, −lat): a camera is then one uniform scale + translate
pub fn ring_unit_d(r: &Ring, cos: f64) -> String {
    let mut d = String::with_capacity(r.len() * 18);
    for (i, p) in r.iter().enumerate() {
        let _ = write!(d, "{}{:.4} {:.4}", if i == 0 { "M" } else { "L" }, p[0] * cos, -p[1]);
    }
    d.push('Z');
    d
}

pub struct Fresh {
    pub m: usize,
    pub bbox: [f64; 4],
    pub median_month: f64,
}

pub struct AssetMeta {
    pub grid_bbox: [f64; 4],
    pub fresh: Vec<Fresh>,
    pub ember_q: Vec<usize>,
    pub scar_levels: Vec<(usize, [f64; 4])>,
    pub events: HashMap<String, [f64; 4]>,
    pub sun_r: f64,
    pub sun_half: f64,
    pub s2: HashMap<String, [f64; 4]>,
    /// per stop: video frame -> lon/lat box of its hotspot-replay raster
    pub ev_frames: [HashMap<usize, [f64; 4]>; 3],
}

fn b4(v: &Value) -> [f64; 4] {
    [0, 1, 2, 3].map(|i| v[i].as_f64().unwrap())
}

impl AssetMeta {
    pub fn load(path: &Path) -> Result<Self> {
        let a = read_json(path).context("build/assets.json (run `incendios assets`)")?;
        Ok(Self {
            grid_bbox: b4(&a["grid_bbox"]),
            fresh: a["fresh"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|f| !f.is_null())
                .map(|f| Fresh { m: f["m"].as_u64().unwrap() as usize, bbox: b4(&f["bbox"]), median_month: f["median_month"].as_f64().unwrap() })
                .collect(),
            ember_q: a["ember_q"].as_array().unwrap().iter().map(|v| v.as_u64().unwrap() as usize).collect(),
            scar_levels: a["scar_levels"].as_array().unwrap().iter().map(|l| (l["level"].as_u64().unwrap() as usize, b4(&l["bbox"]))).collect(),
            events: a["events"].as_object().unwrap().iter().map(|(k, v)| (k.clone(), b4(v))).collect(),
            sun_r: a["sun"]["r"].as_f64().unwrap(),
            sun_half: a["sun"]["half"].as_f64().unwrap(),
            s2: a["s2"].as_object().unwrap().iter().map(|(k, v)| (k.clone(), b4(v))).collect(),
            ev_frames: [0, 1, 2].map(|i| a["ev_frames"][i].as_object().map(|m| m.iter().map(|(k, v)| (k.parse().unwrap(), b4(v))).collect()).unwrap_or_default()),
        })
    }
}

/// A flag SVG ready to be nested in a frame: its viewBox and its content with ids made unique.
pub struct Flag {
    pub vb: [f64; 4],
    pub inner: String,
}

pub fn load_flag(path: &Path, tag: &str) -> Result<Flag> {
    let s = std::fs::read_to_string(path).with_context(|| path.display().to_string())?;
    let i = s.find("<svg").context("no <svg>")?;
    let j = i + s[i..].find('>').context("bad svg")?;
    let head = &s[i..j];
    let attr = |n: &str| -> Option<f64> {
        let k = [' ', '\n', '\t'].iter().find_map(|c| head.find(&format!("{c}{n}=\"")))?;
        let rest = &head[k + n.len() + 3..];
        rest[..rest.find('"')?].trim_end_matches("px").parse().ok()
    };
    let vb = if let Some(k) = head.find("viewBox=\"") {
        let rest = &head[k + 9..];
        let v: Vec<f64> = rest[..rest.find('"').unwrap()].split([' ', ',']).filter(|x| !x.is_empty()).map(|x| x.parse().unwrap()).collect();
        [v[0], v[1], v[2], v[3]]
    } else {
        [0.0, 0.0, attr("width").context("flag without width")?, attr("height").context("flag without height")?]
    };
    let end = s.rfind("</svg>").context("no </svg>")?;
    let mut inner = s[j + 1..end].to_string();
    // strip comments, then make ids unique inside the frame
    while let Some(a) = inner.find("<!--") {
        let b = inner[a..].find("-->").map(|b| a + b + 3).unwrap_or(inner.len());
        inner.replace_range(a..b, "");
    }
    let inner = inner.replace("id=\"", &format!("id=\"{tag}_")).replace("url(#", &format!("url(#{tag}_")).replace("href=\"#", &format!("href=\"#{tag}_"));
    Ok(Flag { vb, inner })
}
