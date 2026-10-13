//! `incendios`: «¿Dónde arde Argentina?», the first story built with the datavid harness. Everything is Rust:
//!
//! ```text
//! incendios prep [step..]   raw open data -> build/derived (FIRMS, MODIS, causes, Tucumán, geometry)
//! incendios verify          compare build/derived with the Python v10 outputs (reference only)
//! incendios facts           build/facts.json + every [[assert]] of story.toml
//! incendios check           readability rules (fails the build when broken) -> build/readability.md
//! incendios assets          render rasters (fire layers, MODIS scars, sun, grain) -> build/assets
//! incendios music           procedural score mastered to the story's LUFS -> build/assets/score.wav
//! incendios build           all of the above, then render -> build/<slug>.mp4, then qa
//! incendios qa [video.mp4]  QA frames + report (loudness of the MP4, duration, rules, min text size drawn)
//! incendios render -o out.mp4  full render in chunks (INCENDIOS_CHUNKS, default 6), parts joined, score muxed
//! incendios render|frame|strip|timeline|audio ...   the fframes CLI (see `incendios help`)
//! ```
mod assets;
mod facts;
mod music;
mod prep;
mod qa;
mod render;
mod timeline;
mod verify;

use anyhow::{Context, Result};
use datavid::story::StoryFile;
use datavid::{Facts, Story};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

pub fn story_path() -> PathBuf {
    std::env::var("STORY").map(PathBuf::from).unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("story.toml"))
}

/// facts.json (computed if missing) + the resolved story
pub fn load_story(sp: &Path) -> Result<(Story, Facts)> {
    let dir = sp.parent().unwrap();
    let fp = dir.join("build/facts.json");
    let facts = if fp.exists() { Facts::load(&fp)? } else { cmd_facts(sp)? };
    let story = Story::load(sp, &facts)?;
    Ok((story, facts))
}

fn cmd_facts(sp: &Path) -> Result<Facts> {
    let file = StoryFile::load(sp)?;
    let dir = sp.parent().unwrap();
    let f = facts::compute(&file, dir)?;
    let lines = f.check(&file.asserts)?;
    f.save(&dir.join("build/facts.json"))?;
    std::fs::write(dir.join("build/asserts.txt"), lines.join("\n") + "\n")?;
    for l in &lines {
        println!("{l}");
    }
    Ok(f)
}

fn cmd_check(sp: &Path) -> Result<datavid::rules::Report> {
    let (story, _) = load_story(sp)?;
    let rep = datavid::rules::evaluate(&story);
    let md = format!(
        "# Readability — {}\n\n{}\n{}\n",
        story.file.story.title,
        rep.table(),
        if rep.problems.is_empty() { "All rules pass.".to_string() } else { format!("**Problems:**\n\n- {}", rep.problems.join("\n- ")) }
    );
    std::fs::write(story.build_dir().join("readability.md"), &md)?;
    println!("{md}");
    datavid::rules::check(&story)?;
    Ok(rep)
}

fn main() -> ExitCode {
    match run() {
        Ok(c) => c,
        Err(e) => {
            eprintln!("error: {e:#}");
            ExitCode::FAILURE
        }
    }
}

fn run() -> Result<ExitCode> {
    let args: Vec<String> = std::env::args().collect();
    let sp = story_path();
    let dir = sp.parent().unwrap().to_path_buf();
    std::fs::create_dir_all(dir.join("build"))?;
    let ok = ExitCode::SUCCESS;
    match args.get(1).map(|s| s.as_str()) {
        Some("prep") => prep::run(&StoryFile::load(&sp)?, &dir, &args[2..]).map(|_| ok),
        Some("verify") => verify::run(&StoryFile::load(&sp)?, &dir).map(|_| ok),
        Some("facts") => cmd_facts(&sp).map(|_| ok),
        Some("check") => cmd_check(&sp).map(|_| ok),
        Some("assets") => {
            let (story, facts) = load_story(&sp)?;
            assets::run(&story, &facts).map(|_| ok)
        }
        Some("music") => {
            let (story, facts) = load_story(&sp)?;
            music::run(&story, &facts).map(|_| ok)
        }
        Some("qa") => {
            let (story, facts) = load_story(&sp)?;
            let video = args.get(2).map(PathBuf::from).unwrap_or_else(|| story.build_dir().join(format!("{}.mp4", story.file.story.slug)));
            qa::run(&story, &facts, &video).map(|_| ok)
        }
        Some("build") => {
            prep::run(&StoryFile::load(&sp)?, &dir, &[])?;
            cmd_facts(&sp)?;
            cmd_check(&sp)?;
            let (story, facts) = load_story(&sp)?;
            assets::run(&story, &facts)?;
            music::run(&story, &facts)?;
            let out = story.build_dir().join(format!("{}.mp4", story.file.story.slug));
            render::render_chunked(&story, &out, 6)?;
            qa::run(&story, &facts, &out).map(|_| ok)
        }
        Some("render") if !args[2..].iter().any(|a| !a.starts_with('-') && !args[2..].windows(2).any(|w| w[0] == "-o" && &w[1] == a)) && std::env::var_os("INCENDIOS_ASSETS").is_none() => {
            // a full render (no range): chunked, so only the rasters each part uses are in memory
            let (story, _) = load_story(&sp)?;
            let out = args.windows(2).find(|w| w[0] == "-o" || w[0] == "--output").map(|w| PathBuf::from(&w[1])).unwrap_or_else(|| PathBuf::from("out.mp4"));
            let n = std::env::var("INCENDIOS_CHUNKS").ok().and_then(|v| v.parse().ok()).unwrap_or(6);
            render::render_chunked(&story, &out, n).map(|_| ok)
        }
        _ => {
            // everything else goes to the fframes CLI (render, frame, strip, timeline, audio, inspect, ...)
            let (story, facts) = load_story(&sp).context("loading the story (run `incendios prep` and `incendios facts` first)")?;
            render::render_cli(&story, &facts, None)
        }
    }
}
