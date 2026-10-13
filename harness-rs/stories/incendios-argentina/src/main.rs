//! `incendios`: the fires story built with the datavid harness. See README.md for the full command list.
mod prep;
mod verify;

use anyhow::Result;
use datavid::story::StoryFile;
use std::path::PathBuf;

fn story_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("story.toml")
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let sp = story_path();
    let dir = sp.parent().unwrap().to_path_buf();
    match args.get(1).map(|s| s.as_str()) {
        Some("prep") => prep::run(&StoryFile::load(&sp)?, &dir, &args[2..]),
        Some("verify") => verify::run(&StoryFile::load(&sp)?, &dir),
        _ => {
            eprintln!("usage: incendios prep [step..] | verify");
            Ok(())
        }
    }
}
