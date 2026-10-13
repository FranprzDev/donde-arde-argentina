//! The story's timeline as numbers (resolved from story.toml marks), the camera path, shakes and reveal flashes, and the
//! per-stop hotspot replays. Shared by the render and the score so picture and sound use the same clock.
use crate::prep::viirs::Pt;
use datavid::Story;
use datavid::ease::{decay, einout, interp, lerp};

/// camera: (lon, lat, zoom in px per degree of latitude, screen x of the centre, screen y of the centre)
pub type Cam = [f64; 5];
pub const COS: f64 = 0.788010753606722; // cos 38°: the map's fixed x-stretch

pub const CAM_IN: Cam = [-64.2, -38.6, 26.5, 1290.0, 560.0];
pub const CAM0: Cam = [-64.2, -38.6, 30.0, 1290.0, 548.0];
pub const CAM_ACC: Cam = [-64.0, -38.4, 31.5, 1290.0, 548.0];
pub const CAM_RK: Cam = [-64.2, -38.6, 30.0, 1430.0, 548.0];
pub const CAM_CL: Cam = [-64.2, -38.6, 28.0, 1500.0, 548.0];
pub const STOPCAM: [Cam; 3] = [[-65.25, -27.05, 230.0, 1440.0, 560.0], [-59.85, -32.75, 150.0, 1380.0, 560.0], [-71.43, -42.18, 760.0, 1400.0, 560.0]];

#[derive(Clone, Copy, PartialEq)]
pub enum Mode {
    Hold,
    Ease,
    Fly,
    ZoomTo,
}

#[derive(Clone)]
pub struct Tl {
    pub space_k: f64,
    pub t_x0: f64,
    pub t_map: f64,
    pub t_hook: (f64, f64),
    pub t_txt1: f64,
    pub t_txt1b: f64,
    pub t_cool: f64,
    pub t_spark: f64,
    pub t_nos: f64,
    pub t_txt2_end: f64,
    pub t_land: f64,
    pub t_a1: f64,
    pub t_ash: f64,
    pub t_scar: f64,
    pub t_d1: f64,
    pub t_tu1: f64,
    pub t_rk: f64,
    pub t_rk2: f64,
    pub t_rk_end: f64,
    pub rk_step: f64,
    pub stops: [(f64, f64); 3],
    pub fly: [f64; 3],
    pub s2z: [(f64, f64, f64); 2],
    pub zout: f64,
    pub t_cl: f64,
    pub cl_dip: f64,
    pub cl_l2: f64,
    pub t_src: f64,
    pub total: f64,
    pub pa_on: (f64, f64),
    pub ka_m: Vec<f64>,
    pub ka_s: Vec<f64>,
    pub seg: Vec<(f64, f64, Cam, Cam, Mode)>,
    pub shakes: Vec<(f64, f64)>,
    pub reveals: Vec<f64>,
    pub s2v_cam: [Cam; 2],
    pub tu_fly: f64,
    pub tu_step: f64,
}

pub fn proj(lon: f64, lat: f64, c: &Cam) -> (f64, f64) {
    (c[3] + (lon - c[0]) * c[2] * COS, c[4] - (lat - c[1]) * c[2])
}

impl Tl {
    /// `s2v_bbox`: the Sentinel-2 crops the camera zooms into (Burruyacú, Delta)
    pub fn new(s: &Story, s2v_bbox: [[f64; 4]; 2]) -> Self {
        let m = |n: &str| s.m(n);
        let t_land = m("T_LAND");
        let (wa, wb, wc) = (m("WARP_A"), m("WARP_B"), m("WARP_C"));
        let ka_m = vec![0.0, 12.0, 156.0, 168.0];
        let ka_s = vec![t_land, t_land + 12.0 * wa, t_land + 12.0 * wa + 144.0 * wb, t_land + 12.0 * wa + 144.0 * wb + 12.0 * wc];
        let stops = [(m("S_TU0"), m("S_TU1")), (m("S_ER0"), m("S_ER1")), (m("S_PA0"), m("S_PA1"))];
        let s2z = [(m("Z_TU0"), m("Z_TU1"), m("Z_TU2")), (m("Z_ER0"), m("Z_ER1"), m("Z_ER2"))];
        let s2v_cam = s2v_bbox.map(|b| [(b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0, 900.0 / (b[3] - b[1]), 1390.0, 540.0]);
        let (t_a1, t_rk, t_rk_end, t_cl, zout) = (m("T_A1"), m("T_RK"), m("T_RK_END"), m("T_CL"), m("ZOUT"));
        use Mode::*;
        let mut seg = vec![
            (0.0, t_land, CAM_IN, CAM_IN, Hold),
            (t_land, t_a1, CAM_IN, CAM0, Ease),
            (t_a1, t_a1 + 0.4, CAM0, CAM_ACC, Ease),
            (t_a1 + 0.4, t_rk - 0.2, CAM_ACC, CAM_ACC, Hold),
            (t_rk - 0.2, t_rk + 0.5, CAM_ACC, CAM_RK, Ease),
            (t_rk + 0.5, t_rk_end - 0.2, CAM_RK, CAM_RK, Hold),
            (t_rk_end - 0.2, stops[0].0 + 0.15, CAM_RK, STOPCAM[0], ZoomTo),
        ];
        for i in 0..2 {
            let (z0, z1, z2) = s2z[i];
            seg.push((stops[i].0 + 0.15, z0, STOPCAM[i], STOPCAM[i], Hold));
            seg.push((z0, z1, STOPCAM[i], s2v_cam[i], ZoomTo));
            seg.push((z1, z2, s2v_cam[i], s2v_cam[i], Hold));
            seg.push((z2, z2 + zout, s2v_cam[i], STOPCAM[i], ZoomTo));
            seg.push((z2 + zout, stops[i + 1].0 + 0.15, STOPCAM[i], STOPCAM[i + 1], Fly));
        }
        seg.push((stops[2].0 + 0.15, stops[2].1 - 0.1, STOPCAM[2], STOPCAM[2], Hold));
        seg.push((stops[2].1 - 0.1, t_cl + 0.3, STOPCAM[2], CAM_CL, ZoomTo));
        seg.push((t_cl + 0.3, 999.0, CAM_CL, CAM_CL, Hold));
        let shakes = vec![(t_land, 7.0), (t_a1, 10.0), (m("T_SCAR"), 5.0), (stops[2].0 + 0.1, 5.0)];
        let reveals = vec![t_land, t_a1, m("T_SCAR"), m("T_RK2") + 0.1, stops[0].0, stops[1].0, stops[2].0, s2z[0].1, s2z[1].1, m("CL_L2")];
        Self {
            space_k: m("SPACE_K"),
            t_x0: m("T_X0"),
            t_map: m("T_MAP"),
            t_hook: (m("T_HOOK0"), m("T_HOOK1")),
            t_txt1: m("T_TXT1"),
            t_txt1b: m("T_TXT1B"),
            t_cool: m("T_COOL"),
            t_spark: m("T_SPARK"),
            t_nos: m("T_NOS"),
            t_txt2_end: m("T_TXT2_END"),
            t_land,
            t_a1,
            t_ash: m("T_ASH"),
            t_scar: m("T_SCAR"),
            t_d1: m("T_D1"),
            t_tu1: m("T_TU1"),
            t_rk,
            t_rk2: m("T_RK2"),
            t_rk_end,
            rk_step: m("RK_STEP"),
            stops,
            fly: [m("FLY_TU"), m("FLY_ER"), m("FLY_PA")],
            s2z,
            zout,
            t_cl,
            cl_dip: m("CL_DIP"),
            cl_l2: m("CL_L2"),
            t_src: m("T_SRC"),
            total: m("TOTAL"),
            pa_on: (1.15, 2.3),
            ka_m,
            ka_s,
            seg,
            shakes,
            reveals,
            s2v_cam,
            tu_fly: 0.5,
            tu_step: 0.07,
        }
    }
    /// month of the 14-year timelapse shown at time t
    pub fn m_now(&self, t: f64) -> f64 {
        if t < self.t_land {
            0.0
        } else if t < self.t_a1 {
            interp(t, &self.ka_s, &self.ka_m)
        } else {
            168.0
        }
    }
    /// the moment a hotspot with month index `m` lights up in the timelapse
    pub fn warp(&self, m: f64) -> f64 {
        interp(m, &self.ka_m, &self.ka_s)
    }
    pub fn rk_t_row(&self, rank: usize) -> f64 {
        self.t_rk + 0.3 + (24 - rank) as f64 * self.rk_step
    }
    pub fn tu_launch(&self, k: usize) -> f64 {
        self.t_d1 + 0.15 + k as f64 * self.tu_step
    }
    pub fn cam_at(&self, t: f64) -> Cam {
        let mut c = self.seg.last().unwrap().3;
        for (t0, t1, a, b, mode) in &self.seg {
            if *t0 <= t && t < *t1 {
                let u = (t - t0) / (t1 - t0);
                c = match mode {
                    Mode::Hold => *a,
                    Mode::Fly => cam_fly(a, b, u),
                    Mode::ZoomTo => cam_zoomto(a, b, u),
                    Mode::Ease => cam_mix(a, b, einout(u)),
                };
                break;
            }
        }
        let (mut dx, mut dy) = (0.0, 0.0);
        for (t0, amp) in &self.shakes {
            let e = decay(t, *t0, 0.13);
            if e > 0.01 {
                let u = t - t0;
                dx += amp * e * (u * 83.0).sin();
                dy += amp * e * (u * 67.0).cos();
            }
        }
        [c[0], c[1], c[2], c[3] + dx, c[4] + dy]
    }
}

fn cam_mix(a: &Cam, b: &Cam, k: f64) -> Cam {
    let z = lerp(a[2].ln(), b[2].ln(), k).exp();
    let kk = if (b[2] / a[2]).ln().abs() < 1.5 { k } else if b[2] != a[2] { (z - a[2]) / (b[2] - a[2]) } else { k };
    [lerp(a[0], b[0], kk), lerp(a[1], b[1], kk), z, lerp(a[3], b[3], k), lerp(a[4], b[4], k)]
}
/// province -> province: pan straight, zoom dips only as much as needed to keep both ends within ~1000 px
fn cam_fly(a: &Cam, b: &Cam, u: f64) -> Cam {
    let k = einout(u);
    let dist = ((b[0] - a[0]) * COS).hypot(b[1] - a[1]);
    let (la, lb) = (a[2].ln(), b[2].ln());
    let lm = lerp(la, lb, 0.5);
    let dip = (lm - (1000.0 / dist.max(1e-3)).ln()).max(0.0);
    let lz = lerp(la, lb, k) - dip * 4.0 * k * (1.0 - k);
    [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lz.exp(), lerp(a[3], b[3], k), lerp(a[4], b[4], k)]
}
/// direct zoom: the zoomed-in end's centre travels on a straight screen line while the zoom is log-interpolated
fn cam_zoomto(a: &Cam, b: &Cam, u: f64) -> Cam {
    let k = einout(u);
    let anc = if b[2] >= a[2] { b } else { a };
    let z = lerp(a[2].ln(), b[2].ln(), k).exp();
    let (ox, oy) = (lerp(a[3], b[3], k), lerp(a[4], b[4], k));
    let pa = proj(anc[0], anc[1], a);
    let pb = proj(anc[0], anc[1], b);
    let (px, py) = (lerp(pa.0, pb.0, k), lerp(pa.1, pb.1, k));
    [anc[0] - (px - ox) / (z * COS), anc[1] + (py - oy) / z, z, ox, oy]
}

/// the hotspots replayed inside each stop, with the moment each one lights up
pub struct Events {
    pub pts: [Vec<(f32, f32)>; 3],
    pub times: [Vec<f64>; 3],
}

pub fn events(tl: &Tl, pts: &[Pt], codes: &[String]) -> Events {
    let idx = |c: &str| codes.iter().position(|x| x == c).unwrap() as u8;
    let (tu, er, ch, rn) = (idx("90"), idx("30"), idx("26"), idx("62"));
    let sel: [Box<dyn Fn(&Pt) -> bool>; 3] = [
        Box::new(move |p: &Pt| p.prov == tu && (p.t as f64 % 12.0) >= 4.0 && (p.t as f64 % 12.0) < 11.0),
        Box::new(move |p: &Pt| p.prov == er && p.t >= 96.0 && p.t < 108.0),
        Box::new(move |p: &Pt| (p.prov == ch || p.prov == rn) && p.lon < -70.9 && p.t >= 156.0 && p.t < 159.0),
    ];
    let durs = [2.4, 2.6, 2.0];
    let mut out = Events { pts: [vec![], vec![], vec![]], times: [vec![], vec![], vec![]] };
    for i in 0..3 {
        let ev: Vec<&Pt> = pts.iter().filter(|p| sel[i](p)).collect();
        let (mn, mx) = ev.iter().fold((f64::MAX, f64::MIN), |a, p| (a.0.min(p.t as f64), a.1.max(p.t as f64)));
        for p in ev {
            let tt = p.t as f64;
            let k = if i == 0 { ((tt % 12.0) - 4.0) / 7.0 * 0.85 } else if mx > mn { (tt - mn) / (mx - mn) } else { 0.0 };
            out.pts[i].push((p.lon, p.lat));
            out.times[i].push(tl.stops[i].0 + 0.3 + k * durs[i]);
        }
    }
    out
}
