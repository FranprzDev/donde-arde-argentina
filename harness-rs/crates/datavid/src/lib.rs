//! datavid: a harness for short data-story videos rendered with [fframes](https://fframes.studio).
//!
//! The pieces a story needs, all in Rust:
//! * [`story`]: the story config (`story.toml`): video settings, readability rules, named time marks (small arithmetic
//!   expressions resolved in any order), beats with their on-screen texts, sources and credits.
//! * [`facts`]: every number shown on screen lives in a facts map computed by the story's own data code; texts use
//!   `{fact|filter}` placeholders, asserts declared in the config are checked, and a digit typed by hand into a template
//!   fails the build.
//! * [`rules`]: readability rules enforced in code (min text size, words on screen per beat, hold time per text, total
//!   duration).
//! * [`geo`], [`raster`], [`npy`]: data prep helpers (point-in-polygon, polygon rasterisation, geodesic areas, outlines,
//!   Gaussian blur, PNG output, `.npy` / `.npz` input).
//! * [`svg`]: frame building blocks for fframes SVG scenes (text with glow, the "slam" text animation, film finish).
//! * [`audio`]: procedural synthesis primitives, Butterworth filters, FFT reverb, a true-peak limiter and EBU R128
//!   loudness mastering (default −14 LUFS).
//! * [`qa`]: a machine- and human-readable QA report.
//! * [`media`]: ffmpeg/ffprobe helpers (probe, loudness of an encoded file, black frames, contact sheet, frames).
pub mod audio;
pub mod ease;
pub mod expr;
pub mod facts;
pub mod geo;
pub mod media;
pub mod npy;
pub mod qa;
pub mod raster;
pub mod rules;
pub mod story;
pub mod svg;

pub use facts::Facts;
pub use story::Story;
