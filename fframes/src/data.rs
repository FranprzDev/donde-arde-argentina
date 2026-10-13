//! Data exported by `prep/export_data.py` from the v10 Python pipeline (numbers, texts, timeline, geometry).
//! The Rust side never recomputes a number: it only reads these values and draws them.
use serde::Deserialize;
use std::collections::HashMap;

pub type Ring = Vec<[f64; 2]>;
/// Camera: (lon, lat, zoom in px per degree of latitude, screen x of the centre, screen y of the centre).
pub type Cam = [f64; 5];

#[derive(Debug, Deserialize)]
pub struct Colors {
    #[serde(rename = "WH")]
    pub wh: [u8; 3],
    #[serde(rename = "MU")]
    pub mu: [u8; 3],
    #[serde(rename = "AM")]
    pub am: [u8; 3],
    #[serde(rename = "OR")]
    pub or: [u8; 3],
    #[serde(rename = "RD")]
    pub rd: [u8; 3],
    #[serde(rename = "HOT")]
    pub hot: [u8; 3],
    #[serde(rename = "ASH")]
    pub ash: [u8; 3],
}

#[derive(Debug, Deserialize)]
pub struct Times {
    #[serde(rename = "T_X0")]
    pub t_x0: f64,
    #[serde(rename = "T_MAP")]
    pub t_map: f64,
    #[serde(rename = "T_TXT1")]
    pub t_txt1: f64,
    #[serde(rename = "T_TXT1B")]
    pub t_txt1b: f64,
    #[serde(rename = "T_NOS")]
    pub t_nos: f64,
    #[serde(rename = "T_TXT2_END")]
    pub t_txt2_end: f64,
    #[serde(rename = "T_TU1")]
    pub t_tu1: f64,
    #[serde(rename = "T_COOL")]
    pub t_cool: f64,
    #[serde(rename = "T_SPARK")]
    pub t_spark: f64,
    #[serde(rename = "T_LAND")]
    pub t_land: f64,
    #[serde(rename = "T_A1")]
    pub t_a1: f64,
    #[serde(rename = "T_ASH")]
    pub t_ash: f64,
    #[serde(rename = "T_SCAR")]
    pub t_scar: f64,
    #[serde(rename = "T_D1")]
    pub t_d1: f64,
    #[serde(rename = "T_RK")]
    pub t_rk: f64,
    #[serde(rename = "T_RK_END")]
    pub t_rk_end: f64,
    #[serde(rename = "S_TU")]
    pub s_tu: [f64; 2],
    #[serde(rename = "T_CL")]
    pub t_cl: f64,
    #[serde(rename = "CL_L2")]
    pub cl_l2: f64,
    #[serde(rename = "T_SRC")]
    pub t_src: f64,
    #[serde(rename = "TOTAL")]
    pub total: f64,
}

#[derive(Debug, Deserialize)]
pub struct Texts {
    pub sol: String,
    pub sol2: String,
    pub nos: String,
    pub causa: String,
    pub area: String,
    pub tucs: String,
    pub uniq: String,
    pub uniq_unit: String,
    pub leg1: String,
    pub leg2: String,
    pub hook1: String,
    pub hook2: String,
    pub close1: String,
    pub close2: String,
}

#[derive(Debug, Deserialize)]
pub struct Sources {
    pub title: String,
    pub rows: Vec<(String, String)>,
    pub credits_title: String,
    pub credits: Vec<(String, String)>,
    pub hold: f64,
    pub strict_need: f64,
    pub scan_need: f64,
    pub reading_ok: bool,
    pub words: usize,
}

#[derive(Debug, Deserialize)]
pub struct Fresh {
    pub m: usize,
    pub bbox: [f64; 4],
    pub t: f64,
}

#[derive(Debug, Deserialize)]
pub struct Grid {
    pub bbox: [f64; 4],
}

#[derive(Debug, Deserialize)]
pub struct SunTex {
    pub r: f64,
    pub half: f64,
}

#[derive(Debug, Deserialize)]
pub struct V10 {
    #[serde(rename = "COS")]
    pub cos: f64,
    #[serde(rename = "BG")]
    pub bg: [u8; 3],
    #[serde(rename = "TX")]
    pub tx: f64,
    pub colors: Colors,
    pub times: Times,
    pub total_new: f64,
    pub space_k: f64,
    pub t_hook: [f64; 2],
    pub hook_y: f64,
    pub seg: Vec<(f64, f64, Cam, Cam, String)>,
    pub shakes: Vec<[f64; 2]>,
    pub reveals: Vec<f64>,
    pub texts: Texts,
    pub sources: Sources,
    pub monthly: Vec<f64>,
    pub ka_m: Vec<f64>,
    pub ka_s: Vec<f64>,
    pub neigh: Vec<Ring>,
    pub prov: HashMap<String, Vec<Ring>>,
    pub ar_out: Vec<Ring>,
    pub ar_pts: Vec<[f64; 2]>,
    pub light: [f64; 3],
    pub d_in: [f64; 2],
    pub spark_ll: [f64; 2],
    pub rays: Vec<(f64, i32, f64, f64)>,
    pub ray_travel: f64,
    pub ray_refl: f64,
    pub stars: Vec<[f64; 3]>,
    pub tu_ring: Ring,
    pub tu_c0: [f64; 2],
    pub tu_copies: Vec<[f64; 2]>,
    pub tu_fill12: Vec<Ring>,
    pub tu_fly: f64,
    pub tu_step: f64,
    pub embers: Vec<[f64; 3]>,
    pub land: Vec<Ring>,
    pub grid: Grid,
    pub fresh: Vec<Option<Fresh>>,
    pub ember_q: Vec<usize>,
    pub scar_bbox: [f64; 4],
    pub sun_tex: SunTex,
}

impl V10 {
    pub fn load(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        Ok(serde_json::from_str(&std::fs::read_to_string(path)?)?)
    }
}
