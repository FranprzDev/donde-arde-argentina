//! `incendios qa [video.mp4]`: checks the encoded MP4 and writes build/qa/QA.md + qa.json + QA frames.
//! * container: duration ≤ max, 1920×1080, 30 fps, one AAC audio stream (ffprobe);
//! * loudness of the MP4's own audio (decoded by the ffmpeg CLI, measured in Rust with EBU R128): integrated LUFS within
//!   tolerance of the target and true peak ≤ the ceiling;
//! * readability rules (datavid::rules) and fact asserts (build/asserts.txt);
//! * smallest font size actually drawn, read from the final SVG of a frame every second (`incendios svg <t>`);
//! * QA frames at the key beats (`incendios frame`).
use anyhow::{Context, Result, bail};
use datavid::qa::Report;
use datavid::{Facts, Story};
use serde_json::{Value, json};
use std::path::Path;
use std::process::Command;

fn self_cmd(args: &[&str]) -> Result<std::process::Output> {
    let exe = std::env::current_exe()?;
    Ok(Command::new(exe).args(args).output()?)
}

pub fn run(story: &Story, _facts: &Facts, video: &Path) -> Result<()> {
    let qa_dir = story.build_dir().join("qa");
    std::fs::create_dir_all(&qa_dir)?;
    let mut r = Report::new(&story.file.story.title);
    // ---- container
    let pr = Command::new("ffprobe").args(["-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels", "-of", "json"]).arg(video).output().context("ffprobe")?;
    let pj: Value = serde_json::from_slice(&pr.stdout).context("ffprobe output")?;
    let dur: f64 = pj["format"]["duration"].as_str().unwrap_or("0").parse()?;
    let streams = pj["streams"].as_array().cloned().unwrap_or_default();
    let v = streams.iter().find(|s| s["codec_type"] == "video").cloned().unwrap_or(Value::Null);
    let a = streams.iter().find(|s| s["codec_type"] == "audio").cloned().unwrap_or(Value::Null);
    let maxd = story.file.video.max_duration;
    r.section("Video file", &format!("`{}`", video.display()));
    r.check("duration", dur <= maxd + 1e-3, &format!("{dur:.3} s (max {maxd} s)"));
    r.check("size", v["width"] == story.file.video.width && v["height"] == story.file.video.height, &format!("{}×{}", v["width"], v["height"]));
    r.check("fps", v["r_frame_rate"] == format!("{}/1", story.file.video.fps), &format!("{}", v["r_frame_rate"]));
    r.check("audio stream", !a.is_null(), &format!("{} {} Hz, {} ch", a["codec_name"], a["sample_rate"].as_str().unwrap_or("?"), a["channels"]));
    r.put("container", json!({"duration_s": dur, "video": v, "audio": a}));
    // ---- loudness of the encoded audio
    let wav = qa_dir.join("decoded_audio.wav");
    let st = Command::new("ffmpeg").args(["-v", "error", "-y", "-i"]).arg(video).args(["-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le"]).arg(&wav).status().context("ffmpeg decode")?;
    if !st.success() {
        bail!("ffmpeg could not decode the audio of {}", video.display());
    }
    let (sr, x) = datavid::audio::read_wav(&wav)?;
    let l = datavid::audio::master::measure(&x, sr)?;
    let _ = std::fs::remove_file(&wav);
    let au = &story.file.audio;
    r.md.push('\n');
    r.section("Loudness (MP4 audio, EBU R128, measured in Rust)", "");
    r.check("integrated loudness", (l.integrated_lufs - au.lufs).abs() <= au.lufs_tolerance, &format!("{:.2} LUFS (target {} ± {})", l.integrated_lufs, au.lufs, au.lufs_tolerance));
    r.check("true peak", l.true_peak_dbtp <= au.true_peak, &format!("{:.2} dBTP (max {})", l.true_peak_dbtp, au.true_peak));
    r.md.push_str(&format!("- loudness range: {:.1} LU\n", l.lra));
    r.put("loudness_mp4", serde_json::to_value(&l)?);
    if let Ok(s) = std::fs::read_to_string(story.build_dir().join("score_loudness.json")) {
        r.put("loudness_master_wav", serde_json::from_str(&s)?);
    }
    // ---- readability + facts
    let rep = datavid::rules::evaluate(story);
    r.md.push('\n');
    r.section("Readability", &rep.table());
    r.check("readability rules", rep.problems.is_empty(), &if rep.problems.is_empty() { "all pass".to_string() } else { rep.problems.join("; ") });
    let asserts = std::fs::read_to_string(story.build_dir().join("asserts.txt")).unwrap_or_default();
    r.section("Fact asserts", &format!("```\n{asserts}```"));
    r.check("fact asserts", !asserts.is_empty() && !asserts.contains("FAIL"), &format!("{} asserts", asserts.lines().count()));
    // ---- QA frames + the final SVG of a frame every 2 s (one fframes process: loading the assets is the slow part)
    let m = |n: &str| story.m(n);
    let shots = [
        ("01_hook_globe", 1.6),
        ("02_timelapse", m("T_A1") - 1.0),
        ("03_scar_tucumanes", m("T_SCAR") + 3.2),
        ("04_ranking", m("T_RK2") + 3.0),
        ("05_tucuman", m("S_TU0") + 3.0),
        ("06_burruyacu_s2", m("Z_TU1") + 1.2),
        ("07_entre_rios", m("S_ER0") + 3.0),
        ("08_delta_s2", m("Z_ER1") + 1.5),
        ("09_comarca", m("S_PA0") + 3.5),
        ("10_close", m("CL_L2") + 1.5),
        ("11_sources_credits", m("T_SRC") + 3.0),
    ];
    let tok = |t: f64| format!("{t:.2}s");
    let mut times: Vec<String> = shots.iter().map(|s| tok(s.1)).collect();
    let mut tt = 0.5;
    while tt < story.duration() {
        times.push(tok(tt));
        tt += 2.0;
    }
    let tmp = qa_dir.join("raw");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp)?;
    let out = self_cmd(&["frame", &times.join(","), "-o", &tmp.display().to_string(), "--svg"])?;
    if !out.status.success() {
        bail!("fframes frame failed: {}", String::from_utf8_lossy(&out.stderr));
    }
    let (mut min_font, mut at) = (f64::MAX, String::new());
    for e in std::fs::read_dir(&tmp)?.filter_map(|e| e.ok()) {
        let p = e.path();
        if p.extension().is_some_and(|x| x == "svg") {
            let s = std::fs::read_to_string(&p)?;
            for part in s.split("font-size=\"").skip(1) {
                if let Some(v) = part.split('"').next().and_then(|v| v.trim_end_matches("px").parse::<f64>().ok()) {
                    if v < min_font {
                        min_font = v;
                        at = p.file_stem().unwrap().to_string_lossy().to_string();
                    }
                }
            }
        }
    }
    let minf = story.file.rules.min_font_px;
    r.check("smallest text drawn", min_font >= minf, &format!("{min_font} px at {at} (min {minf} px; final SVG of {} frames)", times.len()));
    let mut list = String::new();
    for (name, t) in shots.iter() {
        let src = tmp.join(format!("{}.png", tok(*t)));
        if src.exists() {
            std::fs::rename(&src, qa_dir.join(format!("{name}.png")))?;
            list.push_str(&format!("- `{name}.png` — {t:.2} s\n"));
        }
    }
    let _ = std::fs::remove_dir_all(&tmp);
    r.md.push('\n');
    r.section("QA frames", &list);
    std::fs::write(qa_dir.join("QA.md"), &r.md)?;
    std::fs::write(qa_dir.join("qa.json"), serde_json::to_string_pretty(&Value::Object(r.json.clone()))?)?;
    println!("{}", r.md);
    if !r.failures.is_empty() {
        bail!("QA failed: {}", r.failures.join(" | "));
    }
    Ok(())
}
