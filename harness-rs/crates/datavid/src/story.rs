//! The story config (`story.toml`) and its resolution into numbers and strings.
//!
//! ```toml
//! [story]   title, slug, locale
//! [video]   width, height, fps, max_duration
//! [rules]   min_font_px, max_words_per_beat, sec_per_word, base_hold, min_hold      (see rules.rs)
//! [audio]   lufs, true_peak, lufs_tolerance, seed
//! [inputs]  name = "path"            ${VAR:-default} is expanded; relative paths are relative to the story folder
//! [params]  name = number            plain numbers usable in marks
//! [marks]   name = "expression"      time marks: arithmetic over params, other marks and facts (see expr.rs)
//! [[assert]] fact = "...", eq | gt | ge | lt | le = ..., why = "..."
//! [[beat]]  id, kind, start, end (mark expressions), enabled (default true), exempt_words (sources cards)
//!   [[beat.text]] id, template ("{fact|filter}" placeholders), size (px), font, t0, t1 (mark expressions; t1 = the
//!                 moment the text starts to fade out), card (texts read together), label (not prose: no word count),
//!                 allow_digits ("why a literal digit is fine")
//! [[source]] label, value             the closing card's sources (short names)
//! [[credit]] label, value             the closing card's credits (verbatim)
//! ```
use crate::{expr, facts::Facts};
use anyhow::{Context, Result, anyhow, bail};
use indexmap::IndexMap;
use serde::Deserialize;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Deserialize)]
pub struct Meta {
    pub title: String,
    pub slug: String,
    #[serde(default = "es")]
    pub locale: String,
}
fn es() -> String {
    "es".into()
}

#[derive(Debug, Clone, Deserialize)]
pub struct VideoCfg {
    /// design canvas (every coordinate and font size in the story is in these pixels); the final render uses it as is
    pub width: usize,
    pub height: usize,
    pub fps: usize,
    pub max_duration: f64,
    /// output height of draft renders (the default until the author signs off on the final cut); 720 → 1280×720
    #[serde(default = "d720")]
    pub draft_height: usize,
}

fn d720() -> usize {
    720
}

/// Output resolution of a render. Drafts are the default; the full design resolution needs an explicit `--final`
/// (or `DATAVID_FINAL=1`), so nobody waits for a 1080p render before the cut is approved.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Resolution {
    Draft,
    Final,
}

impl Resolution {
    /// `--final` among the CLI args or `DATAVID_FINAL=1` in the environment selects [`Resolution::Final`]
    pub fn from_args(args: &[String]) -> Self {
        let env_final = std::env::var("DATAVID_FINAL").is_ok_and(|v| v == "1");
        if env_final || args.iter().any(|a| a == "--final") { Self::Final } else { Self::Draft }
    }
    /// factor applied to the design canvas (fframes `--scale`)
    pub fn scale(self, video: &VideoCfg) -> f64 {
        match self {
            Self::Final => 1.0,
            Self::Draft => video.draft_height as f64 / video.height as f64,
        }
    }
    /// output size in pixels, rounded to even numbers like fframes does (yuv420 needs even dimensions)
    pub fn size(self, video: &VideoCfg) -> (usize, usize) {
        let k = self.scale(video);
        let even = |v: usize| ((v as f64 * k / 2.0).round() as usize * 2).max(2);
        (even(video.width), even(video.height))
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct RulesCfg {
    #[serde(default = "d48")]
    pub min_font_px: f64,
    #[serde(default = "d12")]
    pub max_words_per_beat: usize,
    #[serde(default = "d035")]
    pub sec_per_word: f64,
    #[serde(default = "d1")]
    pub base_hold: f64,
    #[serde(default = "d25")]
    pub min_hold: f64,
}
fn d48() -> f64 {
    48.0
}
fn d12() -> usize {
    12
}
fn d035() -> f64 {
    0.35
}
fn d1() -> f64 {
    1.0
}
fn d25() -> f64 {
    2.5
}
impl Default for RulesCfg {
    fn default() -> Self {
        Self { min_font_px: 48.0, max_words_per_beat: 12, sec_per_word: 0.35, base_hold: 1.0, min_hold: 2.5 }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct AudioCfg {
    #[serde(default = "dlufs")]
    pub lufs: f64,
    #[serde(default = "dtp")]
    pub true_peak: f64,
    #[serde(default = "dtol")]
    pub lufs_tolerance: f64,
    #[serde(default)]
    pub seed: u64,
}
fn dlufs() -> f64 {
    -14.0
}
fn dtp() -> f64 {
    -1.5
}
fn dtol() -> f64 {
    0.5
}

#[derive(Debug, Clone, Deserialize)]
pub struct AssertCfg {
    pub fact: String,
    pub eq: Option<toml::Value>,
    pub gt: Option<f64>,
    pub ge: Option<f64>,
    pub lt: Option<f64>,
    pub le: Option<f64>,
    #[serde(default)]
    pub why: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TextCfg {
    pub id: String,
    pub template: String,
    pub size: f64,
    #[serde(default)]
    pub font: String,
    pub t0: toml::Value,
    pub t1: toml::Value,
    pub card: Option<String>,
    #[serde(default)]
    pub label: bool,
    pub allow_digits: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BeatCfg {
    pub id: String,
    #[serde(default)]
    pub kind: String,
    pub start: toml::Value,
    pub end: toml::Value,
    #[serde(default = "yes")]
    pub enabled: bool,
    #[serde(default)]
    pub exempt_words: bool,
    #[serde(default)]
    pub note: String,
    #[serde(default)]
    pub text: Vec<TextCfg>,
    /// kind = "sources": size of the rows generated from [[source]] and [[credit]]
    pub card_size: Option<f64>,
}
fn yes() -> bool {
    true
}

#[derive(Debug, Clone, Deserialize)]
pub struct LabelValue {
    pub label: String,
    pub value: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct StoryFile {
    pub story: Meta,
    pub video: VideoCfg,
    #[serde(default)]
    pub rules: RulesCfg,
    pub audio: AudioCfg,
    #[serde(default)]
    pub inputs: IndexMap<String, String>,
    #[serde(default)]
    pub params: IndexMap<String, f64>,
    #[serde(default)]
    pub marks: IndexMap<String, toml::Value>,
    #[serde(default, rename = "assert")]
    pub asserts: Vec<AssertCfg>,
    #[serde(default, rename = "beat")]
    pub beats: Vec<BeatCfg>,
    #[serde(default, rename = "source")]
    pub sources: Vec<LabelValue>,
    #[serde(default, rename = "credit")]
    pub credits: Vec<LabelValue>,
}

/// A text with its placeholders filled and its times resolved.
#[derive(Debug, Clone)]
pub struct Text {
    pub id: String,
    pub beat: String,
    pub s: String,
    pub size: f64,
    pub font: String,
    pub t0: f64,
    pub t1: f64,
    pub card: String,
    pub label: bool,
}

#[derive(Debug, Clone)]
pub struct Beat {
    pub id: String,
    pub kind: String,
    pub start: f64,
    pub end: f64,
    pub exempt_words: bool,
    pub texts: Vec<Text>,
}

/// The resolved story: numbers for every mark, strings for every text.
#[derive(Debug, Clone)]
pub struct Story {
    pub dir: PathBuf,
    pub file: StoryFile,
    pub marks: IndexMap<String, f64>,
    pub beats: Vec<Beat>,
    pub sources: Vec<(String, String)>,
    pub credits: Vec<(String, String)>,
}

fn expand_env(s: &str) -> String {
    // ${VAR:-default} and ${VAR}
    let mut out = String::new();
    let mut rest = s;
    while let Some(i) = rest.find("${") {
        out.push_str(&rest[..i]);
        let Some(j) = rest[i..].find('}') else {
            out.push_str(&rest[i..]);
            return out;
        };
        let inner = &rest[i + 2..i + j];
        let (var, def) = inner.split_once(":-").unwrap_or((inner, ""));
        out.push_str(&std::env::var(var).unwrap_or_else(|_| def.to_string()));
        rest = &rest[i + j + 1..];
    }
    out.push_str(rest);
    out
}

fn val_expr(v: &toml::Value) -> Result<String> {
    Ok(match v {
        toml::Value::String(s) => s.clone(),
        toml::Value::Float(f) => format!("{f}"),
        toml::Value::Integer(i) => format!("{i}"),
        other => bail!("expected a number or an expression, got {other}"),
    })
}

impl StoryFile {
    pub fn load(path: &Path) -> Result<Self> {
        let txt = std::fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
        toml::from_str(&txt).with_context(|| format!("parsing {}", path.display()))
    }
}

impl Story {
    /// Load `story.toml`, resolve marks (params + numeric facts may be used in them) and fill every text from `facts`.
    pub fn load(path: &Path, facts: &Facts) -> Result<Self> {
        let file = StoryFile::load(path)?;
        let dir = path.parent().unwrap_or(Path::new(".")).to_path_buf();
        let mut known: IndexMap<String, f64> = file.params.clone();
        for (k, v) in facts.numbers() {
            known.entry(k).or_insert(v);
        }
        let defs: IndexMap<String, String> = file.marks.iter().map(|(k, v)| Ok((k.clone(), val_expr(v)?))).collect::<Result<_>>()?;
        let marks = expr::resolve(&defs, &known)?;
        let look = |n: &str| marks.get(n).copied();
        let mut beats = vec![];
        for b in file.beats.iter().filter(|b| b.enabled) {
            let start = expr::eval(&val_expr(&b.start)?, &look).with_context(|| format!("beat '{}' start", b.id))?;
            let end = expr::eval(&val_expr(&b.end)?, &look).with_context(|| format!("beat '{}' end", b.id))?;
            let mut texts = vec![];
            for t in &b.text {
                let lit = Facts::literal_part(&t.template);
                if lit.chars().any(|c| c.is_ascii_digit()) && t.allow_digits.is_none() {
                    bail!(
                        "beat '{}' text '{}': the template «{}» has a number typed by hand. Put it in the facts and use a \
                         placeholder, or add allow_digits = \"why\" if it is not data.",
                        b.id, t.id, t.template
                    );
                }
                let s = facts.render(&t.template).with_context(|| format!("beat '{}' text '{}'", b.id, t.id))?;
                texts.push(Text {
                    id: t.id.clone(),
                    beat: b.id.clone(),
                    s,
                    size: t.size,
                    font: t.font.clone(),
                    t0: expr::eval(&val_expr(&t.t0)?, &look).with_context(|| format!("text '{}' t0", t.id))?,
                    t1: expr::eval(&val_expr(&t.t1)?, &look).with_context(|| format!("text '{}' t1", t.id))?,
                    card: t.card.clone().unwrap_or_else(|| t.id.clone()),
                    label: t.label,
                });
            }
            if b.kind == "sources" && b.text.is_empty() {
                // the closing card reads exactly the [[source]] and [[credit]] rows
                for (i, lv) in file.sources.iter().chain(file.credits.iter()).enumerate() {
                    texts.push(Text {
                        id: format!("row{i}"),
                        beat: b.id.clone(),
                        s: format!("{} {}", lv.label, lv.value),
                        size: b.card_size.unwrap_or(file.rules.min_font_px),
                        font: String::new(),
                        t0: start,
                        t1: end,
                        card: "card".into(),
                        label: false,
                    });
                }
            }
            beats.push(Beat { id: b.id.clone(), kind: b.kind.clone(), start, end, exempt_words: b.exempt_words, texts });
        }
        let sources = file.sources.iter().map(|lv| (lv.label.clone(), lv.value.clone())).collect();
        let credits = file.credits.iter().map(|lv| (lv.label.clone(), lv.value.clone())).collect();
        Ok(Self { dir, file, marks, beats, sources, credits })
    }

    /// a resolved time mark (panics with a clear message when it does not exist: marks are part of the story contract)
    pub fn m(&self, name: &str) -> f64 {
        *self.marks.get(name).unwrap_or_else(|| panic!("story.toml has no mark or param named '{name}'"))
    }
    pub fn has_mark(&self, name: &str) -> bool {
        self.marks.contains_key(name)
    }
    pub fn beat(&self, id: &str) -> Option<&Beat> {
        self.beats.iter().find(|b| b.id == id)
    }
    pub fn enabled(&self, beat: &str) -> bool {
        self.beat(beat).is_some()
    }
    /// a text by "beat.text" id
    pub fn text(&self, id: &str) -> &Text {
        let (b, t) = id.split_once('.').unwrap_or_else(|| panic!("text id '{id}' must be 'beat.text'"));
        self.beat(b)
            .and_then(|bb| bb.texts.iter().find(|x| x.id == t))
            .unwrap_or_else(|| panic!("story.toml has no text '{id}' (or its beat is disabled)"))
    }
    pub fn try_text(&self, id: &str) -> Option<&Text> {
        let (b, t) = id.split_once('.')?;
        self.beat(b)?.texts.iter().find(|x| x.id == t)
    }
    pub fn duration(&self) -> f64 {
        self.m("TOTAL")
    }
    pub fn frames(&self) -> usize {
        (self.duration() * self.file.video.fps as f64).round() as usize
    }
    /// an input path from [inputs] (env-expanded, relative to the story folder)
    pub fn input(&self, name: &str) -> Result<PathBuf> {
        let raw = self.file.inputs.get(name).ok_or_else(|| anyhow!("story.toml [inputs] has no '{name}'"))?;
        let p = PathBuf::from(expand_env(raw));
        Ok(if p.is_absolute() { p } else { self.dir.join(p) })
    }
    pub fn build_dir(&self) -> PathBuf {
        self.dir.join("build")
    }
}

/// Inputs can be read before facts exist (data prep runs first).
pub fn input_path(file: &StoryFile, dir: &Path, name: &str) -> Result<PathBuf> {
    let raw = file.inputs.get(name).ok_or_else(|| anyhow!("story.toml [inputs] has no '{name}'"))?;
    let p = PathBuf::from(expand_env(raw));
    Ok(if p.is_absolute() { p } else { dir.join(p) })
}
