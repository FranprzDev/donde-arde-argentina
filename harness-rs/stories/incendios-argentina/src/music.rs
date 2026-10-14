//! `incendios music`: the procedural score (no samples, no AI), cut to the story's timeline and mastered to the story's
//! loudness target (−14 LUFS, true peak under −1.5 dBTP after AAC). A port of the v10 score: solar roar and ray glints,
//! the hard cut with a synthesised match strike, the landing hit and the frantic 14-year drums, braams on the total and
//! the scar, a tick per province in the ranking, hits and drums per stop, impacts on each Sentinel-2 zoom, the closing
//! dip, hits, choir and bell. A data-driven layer: fire crackle follows the hotspots glowing on screen.
use crate::render::Incendios;
use crate::timeline::Tl;
use anyhow::Result;
use datavid::audio::{Score, dsp, dsp::Kind, master, synth::*};
use datavid::ease::interp;
use datavid::{Facts, Story};

const SR: usize = 48000;

fn drums(sc: &mut Score, t0: f64, t1: f64, g: f64, full: bool, bar: f64) {
    let pat = [(0, 1.0), (3, 0.55), (6, 0.7), (8, 0.95), (10, 0.5), (11, 0.6), (12, 0.8), (14, 0.6)];
    let st = bar / 16.0;
    let mut bx = t0;
    while bx < t1 - 0.01 {
        for (step, a) in pat {
            let x = bx + step as f64 * st;
            if x < t1 - 0.01 {
                let s = taiko_d(sc, a * g);
                sc.add(x, &s, 1.0, if step % 2 == 1 { 0.35 } else { -0.35 }, 0.35);
            }
        }
        if full {
            for s_ in [4, 12] {
                if bx + s_ as f64 * st < t1 {
                    let s = snare(sc, 0.55 * g);
                    sc.add(bx + s_ as f64 * st, &s, 1.0, 0.1, 0.4);
                }
            }
            let step = if bar < 2.0 { 1 } else { 2 };
            for s_ in (0..16).step_by(step) {
                if bx + s_ as f64 * st < t1 {
                    let s = hat(sc);
                    sc.add(bx + s_ as f64 * st, &s, 0.18 * g, 0.5, 0.1);
                }
            }
        }
        bx += bar;
    }
}

fn hit(sc: &mut Score, x: f64, g: f64, root: f64, big: bool) {
    let b = boom(sc, if big { 2.6 } else { 2.0 }, 140.0, 28.0, 1.2, 2.2);
    sc.add(x, &b, if big { 1.1 } else { 0.8 } * g, 0.0, 0.6);
    let tk = taiko_d(sc, g);
    sc.add(x, &tk, 1.0, 0.0, 0.5);
    if big {
        let br = braam(sc, root, 4.0);
        sc.add(x, &br, 1.1 * g, 0.0, 0.6);
    }
}

fn chord_seq(sc: &mut Score, t0: f64, t1: f64, chords: &[Vec<f64>], step: f64, g: f64, bright: f64) {
    let (mut i, mut x) = (0usize, t0);
    while x < t1 - 0.05 {
        let d = step.min(t1 - x);
        let p = pad_voice(sc, &chords[i % chords.len()], d, bright, if step < 2.0 { 0.3 } else { 0.5 }, 1.0);
        sc.add(x, &p, g, if i % 2 == 1 { -0.3 } else { 0.3 }, 0.6);
        i += 1;
        x += step;
    }
}

fn match_strike(sc: &mut Score) -> Vec<f64> {
    let n = (1.6 * sc.sr) as usize;
    let tt: Vec<f64> = (0..n).map(|i| i as f64 / sc.sr).collect();
    let nz = sc.noise(n);
    let grain: Vec<f64> = (0..n).map(|_| if sc.random() < 0.35 { sc.uniform(0.4, 1.0) } else { 0.0 }).collect();
    let g: Vec<f64> = nz.iter().zip(grain.iter()).map(|(a, b)| a * b).collect();
    let scratch = dsp::filt(&g, 2, Kind::Band(1800.0, 9000.0), sc.sr);
    let n2 = sc.noise(n);
    let catch = dsp::filt(&n2, 2, Kind::Band(2500.0, 12000.0), sc.sr);
    let n3 = sc.noise(n);
    let fw = dsp::filt(&n3, 2, Kind::Low(700.0), sc.sr);
    let n4 = sc.noise(n);
    let siz = dsp::filt(&n4, 2, Kind::High(5000.0), sc.sr);
    tt.iter()
        .enumerate()
        .map(|(i, &t)| {
            let s = scratch[i] * (t / 0.008).clamp(0.0, 1.0) * (-(t - 0.05).max(0.0) * 60.0).exp() * if t < 0.11 { 1.0 } else { 0.0 };
            let c = catch[i] * (-(t - 0.07).max(0.0) * 28.0).exp() * if t >= 0.07 { 0.8 } else { 0.0 };
            let f = fw[i] * ((t - 0.08) / 0.12).clamp(0.0, 1.0) * (-(t - 0.2).max(0.0) * 2.6).exp() * 2.4;
            let z = siz[i] * ((t - 0.1) / 0.1).clamp(0.0, 1.0) * (-(t - 0.2).max(0.0) * 3.5).exp() * 0.25;
            s * 1.6 + c + f + z
        })
        .collect()
}

/// fire on screen per video frame (same glow law as the picture), normalised to 0..1
fn activity(v: &Incendios, tl: &Tl) -> Vec<f64> {
    let nf = (tl.total * 30.0) as usize;
    let mut ps: Vec<f64> = v.monthly.iter().enumerate().flat_map(|(m, n)| {
        // spread each month's hotspots evenly through the month: the timelapse lights them in that order
        let n = *n as usize;
        (0..n).map(move |k| m as f64 + (k as f64 + 0.5) / n.max(1) as f64)
    }).map(|m| tl.warp(m)).collect();
    ps.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let mut act = vec![0.0; nf];
    for (f, a) in act.iter_mut().enumerate() {
        let t = f as f64 / 30.0;
        if t < tl.t_spark {
            continue;
        }
        if tl.t_land <= t && t < tl.t_ash {
            let i0 = ps.partition_point(|x| *x < t - 1.0);
            let i1 = ps.partition_point(|x| *x <= t);
            *a = ps[i0..i1].iter().map(|x| (-(t - x) / 0.16).exp()).sum();
            continue;
        }
        let mut done = false;
        for i in 0..3 {
            let (s0, s1) = tl.stops[i];
            if s0 - 0.2 <= t && t < s1 {
                let s: f64 = v.ev.times[i].iter().filter(|tt| **tt <= t && **tt > t - 2.0).map(|tt| (-(t - tt) / 0.4).exp()).sum();
                *a = s * [3.0, 0.15, 60.0][i];
                done = true;
                break;
            }
        }
        if !done && tl.t_spark <= t && t < tl.t_land {
            *a = 0.15;
        }
    }
    let mut nz: Vec<f64> = act.iter().cloned().filter(|x| *x > 0.0).collect();
    nz.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let p99 = if nz.is_empty() { 1.0 } else { nz[((nz.len() as f64 * 0.99) as usize).min(nz.len() - 1)] };
    let mx = act.iter().map(|x| x.min(p99)).fold(1e-9, f64::max);
    act.iter().map(|x| x.min(p99) / mx).collect()
}

pub fn run(story: &Story, facts: &Facts) -> Result<master::Loudness> {
    let v = Incendios::new(story.clone(), facts.clone())?;
    let tl = &v.tl;
    let total = tl.total;
    let mut sc = Score::new(SR, total, story.file.audio.seed);
    let n = sc.n;
    let k = tl.space_k;
    let (tsp, tl_, ta1, tash, tscar, td1) = (tl.t_spark, tl.t_land, tl.t_a1, tl.t_ash, tl.t_scar, tl.t_d1);
    let (stu, ser, spa) = (tl.stops[0], tl.stops[1], tl.stops[2]);
    let (trk, trk2, trke, tcl, tsrc) = (tl.t_rk, tl.t_rk2, tl.t_rk_end, tl.t_cl, tl.t_src);
    // ---- 1. drone
    let dr = sc.env(&[(0.0, 0.0), (0.4 * k, 0.55), (tl.t_cool, 0.8), (tsp, 0.35), (tl_ - 0.01, 0.7), (tl_, 1.0), (ta1, 1.0), (tash, 0.6), (tscar, 0.3), (td1, 0.5), (trk2, 0.8), (trke, 0.75), (stu.0, 0.85), (stu.1, 0.8), (ser.0, 0.85), (ser.1, 0.8), (spa.0, 1.0), (spa.1, 0.9), (tcl, 1.0), (tsrc, 0.7), (total - 1.2, 0.6), (total, 0.0)]);
    let nz = sc.noise(n);
    let rumble = dsp::filt(&nz, 4, Kind::Low(90.0), sc.sr);
    for i in 0..n {
        let t = i as f64 / sc.sr;
        let d = ((2.0 * std::f64::consts::PI * datavid::audio::hz(38.0) * t).sin() + 0.5 * (2.0 * std::f64::consts::PI * datavid::audio::hz(50.0) * t + 1.0).sin() + 0.25 * (2.0 * std::f64::consts::PI * datavid::audio::hz(45.0) * t + 2.0).sin()) * dr[i];
        for ch in 0..2 {
            sc.dry[ch][i] += 0.42 * d + 0.25 * rumble[i] * 3.0 * dr[i];
            sc.wet[ch][i] += 0.1 * d;
        }
    }
    // ---- 2. space: solar roar, shimmer, ray glints, heat
    let nz = sc.noise(n);
    let roar_env = sc.env(&[(0.0, 0.9), (0.8 * k, 0.7), (1.8 * k, 0.15), (2.4 * k, 0.0)]);
    let roar: Vec<f64> = dsp::filt(&nz, 2, Kind::Band(60.0, 900.0), sc.sr).iter().zip(roar_env.iter()).map(|(a, b)| a * b * 1.4).collect();
    let nz = sc.noise(n);
    let sh_env = sc.env(&[(0.0, 0.0), (0.6 * k, 0.12), (2.6 * k, 0.25), (tl.t_cool, 0.18), (tl.t_cool + 0.3, 0.0)]);
    let shimmer: Vec<f64> = dsp::filt(&nz, 2, Kind::High(6000.0), sc.sr).iter().zip(sh_env.iter()).map(|(a, b)| a * b).collect();
    for ch in 0..2 {
        for i in 0..n {
            let r = roar[(i + n - ch * 61) % n];
            let s = shimmer[(i + n - ch * 23) % n];
            sc.dry[ch][i] += 0.5 * r + 0.3 * s;
            sc.wet[ch][i] += 0.3 * roar[i] + 0.4 * shimmer[i];
        }
    }
    let b = boom(&mut sc, 3.0, 70.0, 28.0, 0.8, 1.2);
    sc.add(0.0, &b, 0.55, 0.0, 0.7);
    let c = choir(&mut sc, &[62.0, 69.0, 74.0], 3.0 * k, 0.5, 1.2);
    sc.add(0.0, &c, 0.45, 0.0, 0.9);
    let w = whoosh(&mut sc, 1.0 * k, 2500.0, 300.0, true);
    sc.add(0.2, &w, 0.45, -0.4, 0.5);
    let w = whoosh(&mut sc, 1.6 * k, 200.0, 3000.0, false);
    sc.add(0.9 * k, &w, 0.35, 0.3, 0.4);
    let w = whoosh(&mut sc, tl.t_map - 2.1 * k, 300.0, 9000.0, false);
    sc.add(2.1 * k, &w, 0.6, 0.0, 0.4);
    for (j, (te, kind, _, _)) in v.g.rays.iter().enumerate() {
        let x = te + 0.32;
        if x > tl.t_cool + 0.2 {
            continue;
        }
        let p = ping(&sc, 86.0 + ((j * 7) % 12) as f64, 0.18, 28.0, 0.5);
        sc.add(x, &p, if *kind == 1 { 0.10 } else { 0.16 }, if j % 2 == 1 { 0.6 } else { -0.6 }, 0.6);
    }
    let nz = sc.noise(n);
    let he = sc.env(&[(0.0, 0.0), (2.9, 0.0), (4.4, 0.5), (tl.t_cool, 0.6), (tl.t_cool + 0.4, 0.0)]);
    let heat: Vec<f64> = dsp::filt(&nz, 2, Kind::Low(500.0), sc.sr).iter().zip(he.iter()).map(|(a, b)| a * b).collect();
    sc.add_bed(&heat, 0.5, 0.2, 0);
    let w = whoosh(&mut sc, 0.6, 4000.0, 300.0, true);
    sc.add(tl.t_cool - 0.1, &w, 0.35, 0.0, 0.6);
    // ---- 3. pads
    let dm = vec![50.0, 57.0, 62.0, 65.0];
    let bb = vec![46.0, 58.0, 62.0, 65.0];
    let gm = vec![43.0, 58.0, 62.0, 67.0];
    let aa = vec![45.0, 57.0, 61.0, 64.0];
    chord_seq(&mut sc, 0.6, tsp, &[vec![50.0, 57.0, 62.0]], tsp - 0.6, 0.45, 0.4);
    let p = pad_voice(&mut sc, &[38.0, 45.0, 50.0], tl_ - tsp, 0.5, 0.6, 0.6);
    sc.add(tsp, &p, 0.6, 0.0, 0.8);
    chord_seq(&mut sc, tl_, ta1, &[dm.clone(), bb.clone(), gm.clone(), aa.clone()], 0.6, 0.75, 1.3);
    let p = pad_voice(&mut sc, &[38.0, 50.0, 57.0, 62.0, 65.0], tash - ta1 + 0.5, 1.2, 0.05, 1.5);
    sc.add(ta1, &p, 1.1, 0.0, 0.7);
    let p = pad_voice(&mut sc, &[38.0, 45.0, 50.0, 53.0], td1 - tash + 1.0, 0.6, 1.0, 2.0);
    sc.add(tash, &p, 1.0, 0.0, 0.8);
    chord_seq(&mut sc, td1, tcl, &[dm.clone(), bb.clone(), gm, aa], 2.4, 0.9, 1.0);
    // the close pad and choir now sustain under the whole credits card and ring out with the master fade (v12 let
    // them die ~2 s into the card, which left the last seconds near-silent)
    let p = pad_voice(&mut sc, &[38.0, 50.0, 57.0, 62.0, 65.0, 69.0], total - tcl - 1.0, 1.4, 0.6, 3.0);
    sc.add(tcl, &p, 1.4, 0.0, 0.7);
    let c = choir(&mut sc, &[57.0, 62.0, 65.0, 69.0], total - tcl - 1.0, 1.0, 3.0);
    sc.add(tcl, &c, 0.9, 0.0, 0.9);
    // a slow Dm-Bb bed under the credits so the music carries to the last frame
    chord_seq(&mut sc, tsrc, total, &[dm, bb], 3.2, 0.55, 0.8);
    let c = choir(&mut sc, &[50.0, 57.0, 62.0, 65.0], spa.1 - spa.0, 1.5, 2.0);
    sc.add(spa.0, &c, 0.55, 0.0, 0.9);
    // ---- 4. fire crackle following the hotspots on screen
    let act = activity(&v, tl);
    let fx: Vec<f64> = (0..act.len()).map(|f| f as f64 / 30.0).collect();
    let actv: Vec<f64> = (0..n).map(|i| interp(i as f64 / sc.sr, &fx, &act)).collect();
    let mut cr = vec![0.0; n];
    for i in 0..n {
        let dens = 40.0 + 1100.0 * actv[i].powf(0.7);
        if sc.random() < dens / sc.sr {
            cr[i] = sc.uniform(0.3, 1.0) * if sc.random() < 0.5 { -1.0 } else { 1.0 };
        }
    }
    let crb = dsp::filt(&cr, 2, Kind::Band(1500.0, 9000.0), sc.sr);
    let nz = sc.noise(n);
    let low = dsp::filt(&nz, 2, Kind::Low(400.0), sc.sr);
    let crk: Vec<f64> = (0..n).map(|i| {
        let t = i as f64 / sc.sr;
        (crb[i] * 1.6 + low[i] * 0.1 * actv[i]) * (0.25 + 0.75 * actv[i]) * ((t - tsp) / 0.3).clamp(0.0, 1.0) * (1.0 - ((t - tsrc) / 1.0).clamp(0.0, 1.0) * 0.8)
    }).collect();
    for ch in 0..2 {
        for i in 0..n {
            sc.dry[ch][i] += 0.22 * crk[(i + n - ch * 37) % n];
            sc.wet[ch][i] += 0.05 * crk[i];
        }
    }
    // ---- 5. the hard cut + match strike (mixed after the dip), riser into the landing
    let mut post = Score::new(SR, total, story.file.audio.seed + 1);
    let ms = match_strike(&mut post);
    post.add(tsp - 0.03, &ms, 2.0, 0.12, 0.35);
    let b = boom(&mut post, 1.4, 85.0, 38.0, 2.6, 1.3);
    post.add(tsp + 0.1, &b, 0.5, 0.0, 0.5);
    let p = pad_voice(&mut sc, &[38.0, 45.0, 50.0], tl_ - tsp + 0.4, 0.5, 0.25, 0.6);
    sc.add(tsp + 0.05, &p, 0.6, 0.0, 0.8);
    let tk = taiko(&mut sc, 0.6, 120.0, 50.0);
    sc.add(tl.t_nos, &tk, 1.0, 0.0, 0.5);
    let rs = rev_swell(&mut sc, tl_ - tsp - 0.05);
    sc.add(tsp + 0.05, &rs, 0.85, 0.0, 0.5);
    let w = whoosh(&mut sc, 0.45, 300.0, 8000.0, false);
    sc.add(tl_ - 0.45, &w, 0.5, 0.0, 0.4);
    for kk in 0..8 {
        let s = snare(&mut sc, 0.15 + 0.06 * kk as f64);
        sc.add(tl_ - 0.4 + kk as f64 * 0.05, &s, 1.0, 0.0, 0.3);
    }
    // the 12 Tucumanes: a soft hit, then a wooden tok as each copy lands
    let b = boom(&mut sc, 1.8, 120.0, 36.0, 2.0, 1.6);
    sc.add(td1, &b, 0.55, 0.0, 0.6);
    let tk = taiko_d(&mut sc, 0.6);
    sc.add(td1, &tk, 1.0, 0.0, 0.5);
    for kk in 0..12 {
        let x = tl.tu_launch(kk) + tl.tu_fly;
        let tt: Vec<f64> = (0..(0.12 * sc.sr) as usize).map(|i| i as f64 / sc.sr).collect();
        let nz = sc.noise(tt.len());
        let bp = dsp::filt(&nz, 2, Kind::Band(800.0, 3000.0), sc.sr);
        let f = datavid::audio::hz(64.0 + ((kk % 4) * 2) as f64);
        let tok: Vec<f64> = tt.iter().enumerate().map(|(i, t)| ((2.0 * std::f64::consts::PI * f * t).sin() * 0.7 + bp[i] * 0.4) * (-t * 45.0).exp()).collect();
        sc.add(x, &tok, if kk < 11 { 0.35 } else { 0.22 }, if kk % 2 == 1 { 0.3 } else { -0.3 }, 0.3);
    }
    // the hook slams
    let tk = taiko(&mut sc, 0.55, 130.0, 55.0);
    sc.add(tl.t_hook.0, &tk, 1.0, 0.0, 0.5);
    let b = boom(&mut sc, 1.6, 110.0, 36.0, 2.4, 1.4);
    sc.add(tl.t_hook.0, &b, 0.45, 0.0, 0.6);
    // ---- 6. landing + the frantic 14 years
    hit(&mut sc, tl_, 1.0, 38.0, true);
    let tk = taiko_d(&mut sc, 0.7);
    sc.add(tl_ + 0.15, &tk, 1.0, 0.2, 0.4);
    drums(&mut sc, tl_ + 0.3, ta1 - 0.05, 0.9, true, 1.2);
    for y in 0..14 {
        let x = tl.warp((y * 12) as f64);
        let p = ping(&sc, 74.0 + y as f64, 0.12, 30.0, 0.5);
        sc.add(x, &p, 0.45, if y % 2 == 1 { 0.3 } else { -0.3 }, 0.2);
        let tk = tick(&mut sc, true);
        sc.add(x, &tk, 0.45, if y % 2 == 1 { 0.3 } else { -0.3 }, 0.2);
    }
    let arp = [62.0, 65.0, 69.0, 74.0];
    let (mut x, mut kk) = (tl_ + 0.3, 0usize);
    while x < ta1 - 0.05 {
        let up = (12.0 * (x - tl_) / (ta1 - tl_)).floor();
        let f = datavid::audio::hz(arp[kk % 4] + up);
        let s: Vec<f64> = (0..(0.07 * sc.sr) as usize).map(|i| {
            let t = i as f64 / sc.sr;
            (2.0 * ((f * t) % 1.0) - 1.0) * (-t * 40.0).exp() * 0.35
        }).collect();
        sc.add(x, &s, 0.5, if kk % 2 == 1 { 0.4 } else { -0.4 }, 0.25);
        x += 0.075;
        kk += 1;
    }
    {
        let m = (2.5 * sc.sr) as usize;
        let nz = sc.noise(m);
        let hpn = dsp::filt(&nz, 2, Kind::High(3000.0), sc.sr);
        let mut acc = 0.0;
        let s: Vec<f64> = (0..m).map(|i| {
            let t = i as f64 / sc.sr;
            let e = (t / 2.5).powi(2);
            acc += datavid::audio::hz(50.0) * (1.0 + e);
            (2.0 * std::f64::consts::PI * acc / sc.sr).sin() * e * 0.35 + hpn[i] * e * 0.3
        }).collect();
        sc.add(ta1 - 2.5, &s, 1.0, 0.0, 0.5);
    }
    // ---- 7. the total, the ash, the scars
    let br = braam(&mut sc, 36.0, 4.4);
    sc.add(ta1, &br, 1.25, 0.0, 0.6);
    let b = boom(&mut sc, 3.2, 150.0, 26.0, 0.9, 2.6);
    sc.add(ta1, &b, 1.2, 0.0, 0.6);
    let tk = taiko_d(&mut sc, 1.0);
    sc.add(ta1, &tk, 1.0, 0.0, 0.5);
    let w = whoosh(&mut sc, 1.2, 5000.0, 200.0, false);
    sc.add(tash - 0.1, &w, 0.55, 0.0, 0.6);
    let b = boom(&mut sc, 4.0, 80.0, 24.0, 0.7, 1.6);
    sc.add(tscar, &b, 1.0, 0.0, 0.8);
    let br = braam(&mut sc, 33.0, 4.0);
    sc.add(tscar, &br, 0.8, 0.0, 0.7);
    // ---- 8. the ranking: a rising tick per province, then the top-5 hit
    for r in v.rows.iter() {
        let x = tl.rk_t_row(r.rank);
        let g = 0.4 + 0.3 * (24 - r.rank) as f64 / 23.0;
        let p = ping(&sc, 69.0 + ((24 - r.rank) / 2) as f64, 0.09, 40.0, 0.5);
        sc.add(x, &p, g, 0.0, 0.25);
        let tk: Vec<f64> = tick(&mut sc, false).iter().map(|v| v * 0.5).collect();
        sc.add(x, &tk, g, if r.rank % 2 == 1 { 0.3 } else { -0.3 }, 0.25);
    }
    let rs = rev_swell(&mut sc, trk2 - trk - 0.4);
    sc.add(trk + 0.4, &rs, 0.35, 0.0, 0.5);
    hit(&mut sc, trk2 + 0.1, 1.0, 38.0, true);
    drums(&mut sc, trk2 + 0.7, trke - 0.2, 0.6, true, 2.4);
    // ---- 9. the stops
    let w = whoosh(&mut sc, 1.0, 300.0, 6000.0, false);
    sc.add(stu.0 - 1.0, &w, 0.5, -0.2, 0.4);
    hit(&mut sc, stu.0, 0.9, 38.0, false);
    drums(&mut sc, stu.0 + 0.6, stu.1 - 0.1, 0.55, false, 2.4);
    let w = whoosh(&mut sc, 1.2, 300.0, 6000.0, false);
    sc.add(ser.0 - 1.2, &w, 0.5, 0.2, 0.4);
    hit(&mut sc, ser.0, 0.9, 41.0, false);
    drums(&mut sc, ser.0 + 0.6, ser.1 - 0.1, 0.55, false, 2.4);
    let w = whoosh(&mut sc, 1.4, 200.0, 7000.0, false);
    sc.add(spa.0 - 1.4, &w, 0.55, 0.2, 0.4);
    let rs = rev_swell(&mut sc, 1.0);
    sc.add(spa.0 - 1.0, &rs, 0.7, 0.0, 0.6);
    hit(&mut sc, spa.0, 1.0, 36.0, true);
    drums(&mut sc, spa.0 + 0.6, spa.1 - 0.1, 0.75, true, 2.4);
    for (j, (z0, z1, z2)) in tl.s2z.iter().enumerate() {
        let w = whoosh(&mut sc, z1 - z0, 6000.0, 250.0, false);
        sc.add(*z0, &w, 0.45, 0.0, 0.4);
        let rs = rev_swell(&mut sc, 0.45);
        sc.add(z1 - 0.45, &rs, 0.55, 0.0, 0.5);
        let b = boom(&mut sc, 2.2, 150.0, 30.0, 1.6, 2.2);
        sc.add(*z1, &b, 0.95, 0.0, 0.6);
        let tk = taiko_d(&mut sc, 1.0);
        sc.add(*z1, &tk, 1.0, 0.0, 0.5);
        let m = ((z2 - z1 + 0.3) * sc.sr) as usize;
        let n1 = sc.noise(m);
        let n2 = sc.noise(m);
        let l1 = dsp::filt(&n1, 2, Kind::Low(700.0), sc.sr);
        let b2 = dsp::filt(&n2, 2, Kind::Band(1500.0, 6000.0), sc.sr);
        let roar: Vec<f64> = (0..m).map(|i| {
            let t = i as f64 / sc.sr;
            (l1[i] * 2.2 + b2[i] * 0.35) * (t / 0.03).min(1.0) * (-t * 1.2).exp()
        }).collect();
        sc.add(*z1, &roar, 0.35, if j % 2 == 1 { 0.2 } else { -0.2 }, 0.4);
    }
    // ---- 10. into the close
    let w = whoosh(&mut sc, 1.0, 6000.0, 300.0, true);
    sc.add(spa.1 - 0.3, &w, 0.4, 0.0, 0.6);
    let roll: Vec<f64> = {
        let mut v = vec![];
        let mut x = spa.1 - 0.2;
        while x < tcl - 0.02 {
            v.push(x);
            x += 0.075;
        }
        v
    };
    for (j, x) in roll.iter().enumerate() {
        let s = snare(&mut sc, 0.1 + 0.45 * j as f64 / roll.len().max(1) as f64);
        sc.add(*x, &s, 1.0, 0.0, 0.4);
    }
    let rs = rev_swell(&mut sc, 0.9);
    sc.add(tcl - 0.9, &rs, 0.6, 0.0, 0.6);
    let b = boom(&mut sc, 4.0, 130.0, 27.0, 0.8, 2.2);
    sc.add(tcl, &b, 1.2, 0.0, 0.8);
    let tk = taiko_d(&mut sc, 1.0);
    sc.add(tcl, &tk, 1.0, 0.0, 0.6);
    let (l2, dip) = (tl.cl_l2, tl.cl_dip);
    let rs = rev_swell(&mut sc, (dip - tcl - 0.2).max(0.1));
    sc.add(tcl + 0.2, &rs, 0.45, 0.0, 0.7);
    let b = boom(&mut sc, 3.2, 140.0, 27.0, 0.9, 2.4);
    sc.add(l2, &b, 1.2, 0.0, 0.8);
    let tk = taiko_d(&mut sc, 1.0);
    sc.add(l2, &tk, 1.0, 0.0, 0.6);
    let tk = taiko_d(&mut sc, 0.85);
    sc.add(l2 + 0.25, &tk, 1.0, 0.0, 0.6);
    let br = braam(&mut sc, 38.0, 3.0);
    sc.add(l2, &br, 0.7, 0.0, 0.7);
    let bell: Vec<f64> = (0..(3.5 * sc.sr) as usize).map(|i| {
        let t = i as f64 / sc.sr;
        [74.0, 77.0, 81.0, 86.0].iter().map(|m| (2.0 * std::f64::consts::PI * datavid::audio::hz(*m) * t).sin()).sum::<f64>() / 4.0 * (-t * 1.2).exp()
    }).collect();
    sc.add(l2 + 0.25, &bell, 0.22, 0.0, 0.8);
    let tk = taiko(&mut sc, 0.45, 120.0, 50.0);
    sc.add(tsrc, &tk, 1.0, 0.0, 0.6);
    // ---- reverb, mix, dips
    let ir = sc.impulse(2.6);
    let mut mix = sc.mixdown(&ir);
    let postmix = post.mixdown(&ir);
    let fade: Vec<f64> = (0..n).map(|i| {
        let t = i as f64 / sc.sr;
        (t / 0.3).min((total - t) / 1.6).clamp(0.0, 1.0)
    }).collect();
    let dipe = sc.env(&[(0.0, 1.0), (dip, 1.0), (dip + 0.2, 0.063), (l2 - 0.02, 0.063), (l2, 1.0), (total, 1.0)]);
    let cut = sc.env(&[(0.0, 1.0), (tsp - 0.06, 1.0), (tsp - 0.01, 0.08), (tsp + 0.35, 0.08), (tl_ - 0.05, 0.85), (tl_, 1.0), (total, 1.0)]);
    for ch in 0..2 {
        for i in 0..n {
            mix[ch][i] = mix[ch][i] * fade[i] * dipe[i] * cut[i] + postmix[ch][i] * fade[i];
        }
    }
    let target = master::Target {
        lufs: story.file.audio.lufs,
        ceiling_db: -2.8,
        // the landing hit + snare roll overshoots in the AAC encode: a lower local ceiling there
        ceiling_env: vec![(0.0, 0.0), (tl_ - 0.4, 0.0), (tl_ - 0.2, -2.2), (tl_ + 0.8, -2.2), (tl_ + 1.0, 0.0), (total, 0.0)],
    };
    let (y, l) = master::master(&mix, SR, &target)?;
    let out = story.build_dir().join("assets/score.wav");
    datavid::audio::write_wav(&out, SR, &y)?;
    crate::prep::write_json(&story.build_dir().join("score_loudness.json"), &l)?;
    eprintln!("music: {:.2} s, {:.2} LUFS, true peak {:.2} dBTP, LRA {:.1} LU -> {}", l.seconds, l.integrated_lufs, l.true_peak_dbtp, l.lra, out.display());
    Ok(l)
}
