# AGENTS.md — working in harness-rs (Codex, Claude Code, Cursor, humans)

The Rust harness: `crates/datavid` (shared library), `crates/promo` (short-form promo template, binary `promo`),
`stories/` (data stories). The Python harness in `../harness/` has its own AGENTS.md. Read `README.md` and, for
promos, `docs/PROMO_VIDEOS.md` first.

## Rules

- **Reuse before writing.** ffmpeg/ffprobe calls go through `datavid::media`; easing, SVG defs and blur presets
  through `datavid::ease` / `datavid::svg`; synth voices, mastering and loudness through `datavid::audio`; QA reports
  through `datavid::qa::Report`. Extend these instead of adding a parallel helper.
- **No content in code.** Texts, clips, positions, timings, claims and brand names live in configs
  (`examples/`, `templates/`, a story's `story.toml`). The promo code must stay generic.
- **Finite domains are enums** (aspect, resolution, crop mode, cue kind, music kind, stage, exit code), never strings.
- **Drafts first.** 360p `--preview` to check a cut, 720p draft (default) for review, `--final` 1080p only after the
  author approves the draft.
- **Burned-in captions stay off by default** in the promo template (the author adds subtitles downstream from the SRT).
- **Never invent claims.** On-screen and voice-over text comes from the author or the brand's own material.
- **Never commit media:** clips, motion graphics, renders, SRTs, `build/`, `out/`, `examples/*/media/` are ignored.
  Fonts only with a license that allows redistribution (OFL), with the license file next to them in `../fonts/`.
- English for code, comments, commits and docs; branches `feat/` `fix/` `chore/` (agents: `agent/`), never push to
  `main`, PRs with What / Why / Impact / Validation.

## Lessons (sandbox: 2 CPUs, no GPU, ~7 GB RAM shared)

- A release build takes ~4 minutes and outlives a 120 s tool call: run it detached
  (`setsid nohup cargo build --release -p promo > /tmp/build.log 2>&1 &`) and poll the log.
- **Do not render while cargo links.** The final link of a fframes binary needs ~2 GB; a render running at the same
  time got the linker OOM-killed (`ld terminated with signal 9`). Build, then render.
- Write MP4s to local disk (`/tmp`) and copy them: `+faststart` fails with "Error writing trailer" on JuiceFS.
  `promo mux` already does this.
- One fframes process keeps both cores busy: render chunks sequentially, not in parallel.
- fframes decodes every raster in its media folder; give each chunk only the rasters it draws (hard links).
- Drive files over 100 MB need ranged downloads: `scripts/drive_download.sh`.
- After a sandbox restart reinstall `build-essential clang libclang-dev nasm pkg-config libx264-dev libfontconfig-dev`.
- Config-only edits need no rebuild; `promo check` validates a config in milliseconds.
