//! Easing helpers and the v10 camera path (`cam_at`), ported 1:1 from render_v10.py / fx_v4.py.
//! `cargo run --release --bin camcheck` compares it against the Python camera for every frame.
use crate::data::{Cam, V10};

pub fn clamp(x: f64) -> f64 {
    x.clamp(0.0, 1.0)
}
pub fn eout(x: f64) -> f64 {
    let x = clamp(x);
    1.0 - (1.0 - x).powi(3)
}
pub fn eout5(x: f64) -> f64 {
    let x = clamp(x);
    1.0 - (1.0 - x).powi(5)
}
pub fn einout(x: f64) -> f64 {
    let x = clamp(x);
    if x < 0.5 { 4.0 * x.powi(3) } else { 1.0 - (-2.0 * x + 2.0).powi(3) / 2.0 }
}
pub fn lerp(a: f64, b: f64, k: f64) -> f64 {
    a + (b - a) * k
}
pub fn decay(t: f64, t0: f64, tau: f64) -> f64 {
    if t >= t0 { (-(t - t0) / tau).exp() } else { 0.0 }
}
/// numpy.interp (xs ascending, clamped at both ends)
pub fn interp(x: f64, xs: &[f64], ys: &[f64]) -> f64 {
    if x <= xs[0] {
        return ys[0];
    }
    let n = xs.len();
    if x >= xs[n - 1] {
        return ys[n - 1];
    }
    let i = xs.partition_point(|v| *v <= x) - 1;
    let k = (x - xs[i]) / (xs[i + 1] - xs[i]);
    ys[i] + (ys[i + 1] - ys[i]) * k
}

pub fn proj(lon: f64, lat: f64, c: &Cam, cos: f64) -> (f64, f64) {
    (c[3] + (lon - c[0]) * c[2] * cos, c[4] - (lat - c[1]) * c[2])
}

fn cam_mix(a: &Cam, b: &Cam, k: f64) -> Cam {
    let z = lerp(a[2].ln(), b[2].ln(), k).exp();
    let kk = if (b[2] / a[2]).ln().abs() < 1.5 {
        k
    } else if b[2] != a[2] {
        (z - a[2]) / (b[2] - a[2])
    } else {
        k
    };
    [lerp(a[0], b[0], kk), lerp(a[1], b[1], kk), z, lerp(a[3], b[3], k), lerp(a[4], b[4], k)]
}

fn cam_fly(a: &Cam, b: &Cam, u: f64, cos: f64) -> Cam {
    let k = einout(u);
    let dist = ((b[0] - a[0]) * cos).hypot(b[1] - a[1]);
    let (la, lb) = (a[2].ln(), b[2].ln());
    let lm = lerp(la, lb, 0.5);
    let zfit = 1000.0 / dist.max(1e-3);
    let dip = (lm - zfit.ln()).max(0.0);
    let lz = lerp(la, lb, k) - dip * 4.0 * k * (1.0 - k);
    [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lz.exp(), lerp(a[3], b[3], k), lerp(a[4], b[4], k)]
}

fn cam_zoomto(a: &Cam, b: &Cam, u: f64, cos: f64) -> Cam {
    let k = einout(u);
    let anc = if b[2] >= a[2] { b } else { a };
    let z = lerp(a[2].ln(), b[2].ln(), k).exp();
    let ox = lerp(a[3], b[3], k);
    let oy = lerp(a[4], b[4], k);
    let pa = proj(anc[0], anc[1], a, cos);
    let pb = proj(anc[0], anc[1], b, cos);
    let px = lerp(pa.0, pb.0, k);
    let py = lerp(pa.1, pb.1, k);
    [anc[0] - (px - ox) / (z * cos), anc[1] + (py - oy) / z, z, ox, oy]
}

pub fn cam_at(d: &V10, t: f64) -> Cam {
    let mut c = d.seg.last().unwrap().3;
    for (t0, t1, a, b, mode) in &d.seg {
        if *t0 <= t && t < *t1 {
            let u = (t - t0) / (t1 - t0);
            c = match mode.as_str() {
                "hold" => *a,
                "fly" => cam_fly(a, b, u, d.cos),
                "zoomto" => cam_zoomto(a, b, u, d.cos),
                _ => cam_mix(a, b, einout(u)),
            };
            break;
        }
    }
    let (mut dx, mut dy) = (0.0, 0.0);
    for s in &d.shakes {
        let e = decay(t, s[0], 0.13);
        if e > 0.01 {
            let u = t - s[0];
            dx += s[1] * e * (u * 83.0).sin();
            dy += s[1] * e * (u * 67.0).cos();
        }
    }
    [c[0], c[1], c[2], c[3] + dx, c[4] + dy]
}
