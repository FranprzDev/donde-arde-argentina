# datavid — a Rust harness for data videos

Everything runs in Rust: data prep, fact asserts, readability rules, rendering
([fframes](https://fframes.studio) 1.2.1-rc.30, CPU backend), the procedural score, loudness mastering and QA.
The Python in `harness/` and `src/` is kept only as a reference: `incendios verify` checks that the Rust prep
reproduces its numbers.

```
harness-rs/
  crates/datavid/              the reusable library
    story.rs  expr.rs          story.toml loader, time-mark expressions
    facts.rs                   facts store, {fact|format} templates, [[assert]] checks
    rules.rs                   readability rules (size, words per beat, hold time, total length)
    geo.rs raster.rs npy.rs    geometry (point in polygon, geodesic area, rasterize), blur/resize/PNG, .npy/.npz reader
    svg.rs                     SVG frame helpers (text slams, glow, grain, vignette)
    audio/                     synth voices, scipy-compatible Butterworth filters, reverb, limiter, EBU R128
    qa.rs                      QA report
  stories/incendios-argentina/ «¿Dónde arde Argentina?» (the first story)
    story.toml                 beats, texts, data bindings, asserts, sources, credits
    src/prep/                  FIRMS VIIRS, MODIS MCD64A1, causes, Tucumán, geometry
    src/render/                the frames
    src/music.rs               the score
```

## Make a video

```bash
source env.sh                                   # Rust toolchain (see "Sandbox notes")
cd stories/incendios-argentina
cargo run --release -- build                    # prep -> facts -> check -> assets -> music -> render -> qa
```

Or step by step: `prep`, `verify`, `facts`, `check`, `assets`, `music`, `render -o out.mp4`, `qa out.mp4`.

### Resolution: drafts first

Every render is a **1280×720 draft** unless you ask for the final cut:

```bash
cargo run --release -- build              # 1280×720 draft (default)
cargo run --release -- build --final      # 1920×1080, only once the cut is approved
cargo run --release -- render -o out.mp4 --final
DATAVID_FINAL=1 cargo run --release -- build
```

The story is always laid out on the design canvas (`[video] width/height`, 1920×1080): positions, font sizes and the
readability rules (≥ 48 px) are in design pixels; only the output is scaled (`[video] draft_height`, default 720).
`qa` checks the file against the resolution you asked for (pass the same `--final` to `qa`). A draft render also links
each chunk to PNG copies pre-scaled to the draft size (`build/assets_draft/`, rebuilt when a source raster is newer),
so a chunk decodes ~44 % of the pixels.
Every fframes command works too: `frame 12.5s`, `strip all -n 12`, `svg 30s`, `audio analyze`.
Outputs land in `build/` (`facts.json`, `asserts.txt`, `readability.md`, `assets/`, `qa/QA.md` and QA frames).

## Make a new video with the harness

1. Copy `stories/incendios-argentina` to `stories/<slug>` and add it to the workspace `Cargo.toml`.
2. Edit `story.toml`:
   - `[inputs]`: the raw files (paths may use `${ENV:-default}`).
   - `[params]` and `[marks]`: the timeline. Marks are expressions (`"S_TU0 + MAP_TU"`, `max(..)`) and may use facts.
   - `[[beat]]` with `[[beat.text]]`: every on-screen text with its `t0`/`t1`, size and font. Numbers come only from
     facts: `{er_2020|int}`, `{top5_share|pct}`, `{tuc_s2_date|ddmmyyyy}`. A literal digit in a template fails the
     build unless the text says why in `allow_digits`. `label = true` marks map labels and axes (not counted as prose).
   - `[[assert]]`: one per verbal rounding on screen (`«casi 7»` → `gt = 6.5, lt = 7.0`).
   - `[[source]]` / `[[credit]]`: the closing card (label/value rows).
3. Write `src/prep/` (raw data → `build/derived`) and `src/facts.rs` (derived → named facts).
4. Write the render (`src/render/`): one SVG per frame from the story texts, the facts and the assets.
5. `cargo run --release -- check` until every rule passes, then `build`.

### Rules (checked in code, the build stops on a failure)

- text ≥ 48 px; ≤ 12 prose words on screen at once per beat;
- every card held ≥ 0.35 s per word + 1 s (min 2.5 s), measured from its first text's entrance to the fade;
- total ≤ 60 s; audio at −14 LUFS ±0.5, true peak ≤ −1.5 dBTP (measured on the MP4 itself).

The sources/credits card is exempt from the word cap but not from the hold rule or the size rule.

## The fires story: what changed from v10

- **New opening (2026-10-13).** «EL SOL QUEMA, / PERO NO PROVOCA INCENDIOS.» (7 words, 3.45 s) → hard cut with the
  match → the spark and «EL HUMANO, SÍ.» + «9 DE CADA 10 CON CAUSA CONOCIDA» (10 words, 4.50 s). The 14-year timelapse
  ignites from that spark 0.5 s later, while the line is still on screen, so the video runs on from it without a pause.
  Every later mark moves 0.40 s earlier (total 59.49 s).
- **Closing card tradeoff.** v10 gave the sources 3.14 s for 45 words. The new card has short source names in a
  label/value grid plus the two credits verbatim: 24 words → 9.4 s. To fit inside 60 s: the first sun line enters
  0.55 s earlier; the scar and the «CASI 12 TUCUMANES» beats became one card (the line «QUEMADAS: CASI 1 DE CADA 10
  DEL PAÍS» is cut); every card is held exactly what the rule asks; flights, zooms and the ash pause are 15–20 %
  shorter. Long source names (IGN, Wikimedia flags, EEAOC RA 370, product ids) are in `story.toml` comments and the
  repo docs instead of on screen.
- The 12 Tucumán copies are placed by the same greedy rule, but the rasterizer differs from OpenCV's `fillPoly`,
  so 6 of the 12 positions differ slightly from v10 (`incendios verify` lists them). The ratio (11,78) is identical.
- Inputs kept pre-extracted: MODIS MCD64A1 monthly windows (`*.npz`, cut from the UMD GeoTIFFs) and the Sentinel-2
  JPEG crops were produced offline by the original pipeline. The harness reads `.npz` natively; it does not yet fetch
  or reproject GeoTIFF/JP2 rasters.

### Memory: chunked renders

fframes decodes the whole media folder the first time a frame draws an image: ~1.9 GB of RGBA for `build/assets`
(~3.5 GB RSS), which the OOM killer stopped in a 7 GB sandbox shared with other builds. A full `render -o out.mp4`
(no range) therefore runs in chunks (`INCENDIOS_CHUNKS`, default 6), each in its own process: a probe pass records the
`<image href>` of every frame without drawing, then the chunk renders with only those rasters (~1.5–1.8 GB RSS). The
parts are joined without re-encoding and the score is muxed once with the `ffmpeg` CLI. A range (`render 10s..20s`)
renders in one process as before (at the draft size unless `--final` or an explicit `--scale`).

Chunks run one after the other on purpose: fframes already keeps both cores of the sandbox busy inside one process, so
parallel chunks would only double the memory.

### Where the time goes

The 14-year timelapse (≈ 8–12 s) is the expensive part: up to ~50 monthly fire rasters screened together plus a
full-frame bloom, about 2 s per 1080p frame on 2 cores; the rest of the video costs ~0.15 s per frame. The fire layer
and the closing embers draw their rasters once and add the bloom in the same filter (`datavid::svg::bloom_screen`);
before, each group was drawn twice (sharp copy + blurred copy).

## Sandbox notes

`env.sh` points `RUSTUP_HOME`/`CARGO_HOME` at a persistent folder and `CARGO_TARGET_DIR` at a shared target. System
packages needed: `build-essential clang libclang-dev nasm pkg-config libx264-dev libfontconfig-dev`, and the `ffmpeg`
CLI for `qa` (decoding the MP4 audio; the loudness itself is measured in Rust).
