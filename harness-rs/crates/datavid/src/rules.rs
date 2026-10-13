//! Readability rules, enforced in code. `check` fails the build when any of these is broken:
//!
//! 1. every text (prose and labels) is at least `min_font_px` tall (design px at 1080p); the SVG layer also records the
//!    smallest size actually drawn (`svg::min_font_drawn`) so QA can confirm it frame by frame;
//! 2. the prose words on screen at the same moment inside one beat are at most `max_words_per_beat`
//!    (labels such as legends, axis years or image captions with `label = true` are not counted; beats with
//!    `exempt_words = true`, i.e. the sources/credits card, are not word-capped but still have to meet rule 3);
//! 3. every card (texts read together) stays on screen at least `sec_per_word * words + base_hold` seconds, never under
//!    `min_hold`, measured from its first line's entrance to the moment it starts to fade; every line of a card also meets
//!    the rule on its own words from its own entrance;
//! 4. the video is at most `max_duration` seconds long.
//!
//! Words are whitespace-separated tokens with at least one letter or digit ("·", "=", "%", "&" alone do not count;
//! "26,6" is one word).
use crate::story::{Beat, RulesCfg, Story};
use anyhow::{Result, bail};
use serde::Serialize;

pub fn words(s: &str) -> usize {
    s.replace('·', " ").replace('=', " ").split_whitespace().filter(|w| w.chars().any(|c| c.is_alphanumeric())).count()
}

pub fn need(r: &RulesCfg, n: usize) -> f64 {
    r.min_hold.max(r.sec_per_word * n as f64 + r.base_hold)
}

#[derive(Debug, Clone, Serialize)]
pub struct Row {
    pub beat: String,
    pub card: String,
    pub text: String,
    pub words: usize,
    pub t0: f64,
    pub t1: f64,
    pub hold: f64,
    pub need: f64,
    pub ok: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct Report {
    pub rows: Vec<Row>,
    pub words_at_once: Vec<(String, usize, bool)>,
    pub min_size: f64,
    pub total: f64,
    pub max_duration: f64,
    pub problems: Vec<String>,
}

fn max_words_at_once(b: &Beat) -> usize {
    let counted: Vec<_> = b.texts.iter().filter(|t| !t.label).collect();
    counted.iter().map(|t| counted.iter().filter(|o| o.t0 <= t.t0 && t.t0 < o.t1).map(|o| words(&o.s)).sum()).max().unwrap_or(0)
}

/// Evaluate every rule; `Report::problems` lists what is broken (empty = pass).
pub fn evaluate(story: &Story) -> Report {
    let r = &story.file.rules;
    let tol = 0.011;
    let mut rows = vec![];
    let mut probs = vec![];
    let mut wao = vec![];
    let mut min_size = f64::MAX;
    for b in &story.beats {
        for t in &b.texts {
            min_size = min_size.min(t.size);
            if t.size + 1e-9 < r.min_font_px {
                probs.push(format!("beat '{}' text '{}': {} px < min {} px («{}»)", b.id, t.id, t.size, r.min_font_px, t.s));
            }
        }
        let n = max_words_at_once(b);
        let ok_w = b.exempt_words || n <= r.max_words_per_beat;
        wao.push((b.id.clone(), n, ok_w));
        if !ok_w {
            probs.push(format!(
                "beat '{}': {n} words on screen at once > max {}: {:?}. Cut words or split the beat.",
                b.id,
                r.max_words_per_beat,
                b.texts.iter().filter(|t| !t.label).map(|t| t.s.as_str()).collect::<Vec<_>>()
            ));
        }
        // cards
        let mut cards: Vec<String> = vec![];
        for t in b.texts.iter().filter(|t| !t.label) {
            if !cards.contains(&t.card) {
                cards.push(t.card.clone());
            }
        }
        for c in cards {
            let ts: Vec<_> = b.texts.iter().filter(|t| !t.label && t.card == c).collect();
            let nw: usize = ts.iter().map(|t| words(&t.s)).sum();
            let t0 = ts.iter().map(|t| t.t0).fold(f64::MAX, f64::min);
            let t1 = ts.iter().map(|t| t.t1).fold(f64::MIN, f64::max);
            let nd = need(r, nw);
            let ok = t1 - t0 + tol >= nd;
            rows.push(Row { beat: b.id.clone(), card: c.clone(), text: ts.iter().map(|t| t.s.clone()).collect::<Vec<_>>().join(" / "), words: nw, t0, t1, hold: t1 - t0, need: nd, ok });
            if !ok {
                probs.push(format!("beat '{}' card '{c}': {nw} words on screen {:.2} s, need {nd:.2} s ({} s/word + {} s, min {} s). Lengthen the beat or cut words; never speed text up.", b.id, t1 - t0, r.sec_per_word, r.base_hold, r.min_hold));
            }
            if ts.len() > 1 {
                for t in &ts {
                    let nd1 = need(r, words(&t.s));
                    if t.t1 - t.t0 + tol < nd1 {
                        probs.push(format!("beat '{}' text '{}' («{}»): on screen {:.2} s from its own entrance, needs {nd1:.2} s", b.id, t.id, t.s, t.t1 - t.t0));
                    }
                }
            }
        }
    }
    let total = story.duration();
    let maxd = story.file.video.max_duration;
    if total > maxd + 1e-9 {
        probs.push(format!("total {total:.2} s > max {maxd} s"));
    }
    Report { rows, words_at_once: wao, min_size, total, max_duration: maxd, problems: probs }
}

pub fn check(story: &Story) -> Result<Report> {
    let rep = evaluate(story);
    if !rep.problems.is_empty() {
        bail!("readability rules failed:\n  - {}", rep.problems.join("\n  - "));
    }
    Ok(rep)
}

impl Report {
    pub fn table(&self) -> String {
        let mut s = String::from("| beat | card | words | on screen (s) | needs (s) | ok |\n|---|---|---|---|---|---|\n");
        for r in &self.rows {
            s.push_str(&format!("| {} | {} | {} | {:.2} → {:.2} = {:.2} | {:.2} | {} |\n", r.beat, r.text.replace('|', "/"), r.words, r.t0, r.t1, r.hold, r.need, if r.ok { "yes" } else { "**NO**" }));
        }
        s.push_str("\n| beat | most prose words on screen at once | ok |\n|---|---|---|\n");
        for (b, n, ok) in &self.words_at_once {
            s.push_str(&format!("| {b} | {n} | {} |\n", if *ok { "yes" } else { "**NO**" }));
        }
        s.push_str(&format!("\nsmallest declared text: {} px · total {:.2} s (max {} s)\n", self.min_size, self.total, self.max_duration));
        s
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn counts_like_v10() {
        assert_eq!(words("5 PROVINCIAS = 53 %"), 3);
        assert_eq!(words("Director & Revisor: Francisco Perez"), 4);
        assert_eq!(words("Pipeline de Datos, Generación de Video & Producción final: Harness Engineering with AI"), 12);
        assert_eq!(words("ENTRE RÍOS · 2020"), 3);
    }
}
