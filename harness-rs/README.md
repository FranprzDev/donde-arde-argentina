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
    media.rs                   ffmpeg/ffprobe helpers: probe, loudness of an MP4, black frames, contact sheet
  crates/promo/                short-form promo / vertical ad template (binary `promo`), see docs/PROMO_VIDEOS.md
  examples/spookmc-ad4/        the SpookMC ad #4 as a template config (promo.toml explicit, brief.toml texts-in)
  templates/promo/             starter brief + timed voice-over script for a new ad
  build-support/x264_rpath.rs  shared build script (libx264 ABI 163 rpath) for crates that link fframes
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

The sources/credits card is exempt from the word cap but not from the size rule. A beat can carry
`[beat.hold_exception]` (`hold`, `approved_by`, `why`): its cards then meet that hold instead of the reading rule, and
`check`/`qa` print the rule's own figure next to the approved one with who approved it. It is for an editorial call a
person signed off, never to make a failing check pass (today: the credits card, see below).

## Promo videos (vertical ads)

`crates/promo` turns texts + clips into a short-form promo (9:16, 16:9 or 1:1): clips with push-ins, alpha motion
graphics with their own sound effects, cut flashes, an end card, procedural or external music, an optional voice-over,
−14 LUFS mastering and QA (loudness, true peak, black frames, contact sheet). Burned-in captions are off by default;
the texts set the timing and are written as an SRT sidecar.

```bash
source env.sh && cargo build --release -p promo          # ~4 min; config edits need no rebuild
P=$CARGO_TARGET_DIR/release/promo
cp -r templates/promo my-ad                                # write one [[beat]] per idea in my-ad/brief.toml
$P check my-ad/brief.toml                                  # timeline + missing files, no rendering
$P build my-ad/brief.toml --preview                        # 360p smoke check
$P build my-ad/brief.toml                                  # 720p draft (default)
$P build my-ad/brief.toml --final                          # 1080p after approval
$P batch ads.txt --json                                    # several configs; NDJSON progress, exit codes 0-4
```

Step-by-step guide, config reference, app integration (JSON in, NDJSON progress, exit codes), sandbox lessons and the
roadmap: [docs/PROMO_VIDEOS.md](docs/PROMO_VIDEOS.md). The SpookMC ad #4 is the reference example:
`examples/spookmc-ad4/promo.toml` (explicit cut list) and `brief.toml` (the same ad as beats).

## The fires story: what changed from v10

- **Credits use the contest pseudonym (v15, 2026-10-13).** The contest is anonymous and does not accept AI
  authorship (AI assistance for code under human direction is allowed), so the two credit rows are now
  «Autor: FranMC23» and «Código: AI Assistance, bajo supervisión humana»; no real name is drawn on screen. The card
  drops from 24 to 16 words (the rule would ask 6.6 s); it keeps the approved 6.40 s hold and every other beat, total
  59.49 s.
- **Burned-area legend is a map key (v14, 2026-10-13).** «gris = área quemada» named a colour the scars do not show:
  they are a warm sand/ash tint (`SCAR` = 205,190,172, screened over the dark map), and the label itself was drawn in
  a dimmer grey than the legend under it, so it read as a caption rather than a key. It now draws a swatch in the
  scar tint (the same `SCAR` constant the `scar_col_*` rasters use) next to «área quemada {y0}–{y1} (MODIS)», in the
  same tone and size as «1 punto = 1 foco de calor (satélite)». The swatch also tells the scars apart from the
  hotspot dots, whose legend is still on screen during the scar beat. Same timing (T_SCAR → T_RK), same 48 px.
- **Longer timelapse, shorter credits (v13, 2026-10-13).** In v12 the credits card sat still for 9.4 s (50.1–59.5 s)
  while the score had already faded to near silence from ~54 s: it read as dead air. the author approved cutting that
  card to 6.4 s (a `hold_exception`; the rule would ask 9.4 s for its 24 words) and giving the 3.0 s to the 14-year
  timelapse: every month plays 1.7716× slower (`WARP_A/B/C` 0.036/0.0215/0.030 → 0.06378/0.03809/0.05315 s per month),
  so the timelapse runs 7.35–14.24 s instead of 7.35–11.24 s. Same data, same months, same year labels; every later
  mark moves 3.0 s later and the total stays 59.49 s. The close pad and choir now sustain under the whole credits card
  and a slow Dm–Bb bed carries the music to the last frame.
- **New opening (2026-10-13).** «EL SOL QUEMA, / PERO NO PROVOCA INCENDIOS.» (7 words, 3.45 s) → hard cut with the
  match → the spark and «EL HUMANO, SÍ.» + «9 DE CADA 10 CON CAUSA CONOCIDA» (10 words, 4.50 s). The 14-year timelapse
  ignites from that spark 0.5 s later, while the line is still on screen, so the video runs on from it without a pause.
  Every later mark moves 0.40 s earlier (total 59.49 s).
- **Closing card tradeoff.** v10 gave the sources 3.14 s for 45 words. The new card has short source names in a
  label/value grid plus the two credits verbatim: 24 words → 9.4 s (6.4 s since v13, approved exception). To fit inside 60 s: the first sun line enters
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

The 14-year timelapse (≈ 7–14 s since v13) is the expensive part: up to ~50 monthly fire rasters screened together plus a
full-frame bloom, about 2 s per 1080p frame on 2 cores; the rest of the video costs ~0.15 s per frame. The fire layer
and the closing embers draw their rasters once and add the bloom in the same filter (`datavid::svg::bloom_screen`);
before, each group was drawn twice (sharp copy + blurred copy).

## Final delivery

Scripts in `scripts/` (bash; need `ffmpeg`, and ImageMagick for the thumbnail; `--help` lists every option):

| Script | What it does |
|---|---|
| `scripts/render_final_chunked.sh` | 1080p final in small frame ranges: a probe pass (`INCENDIOS_PROBE`) lists the rasters each range draws, only those are hard-linked into a per-chunk asset folder, each chunk is retried (default 8 attempts) and finished chunks are skipped on a rerun; the parts are joined without re-encoding, the score is muxed once and `qa --final` runs on the result. Story, binary, frame count, chunk size, retries and paths are flags or env vars. |
| `scripts/encode_youtube.sh` | Upload copy of the master: libx264 CRF 20, `yuv420p`, `+faststart`, audio copied (the fires master went from 95 MB to 38 MB with no visible loss). |
| `scripts/make_thumbnail.sh` | 1280×720 JPG from a real frame: map crop on the right with a vignette, title lines in Bebas Neue (`fonts/`) on the left; text, colours, frame time and crop are flags. |

Why chunks of a few dozen frames instead of the built-in `render -o` (6 chunks): on a machine whose RAM is shared with
other jobs even a sixth of the 1080p video can be OOM-killed, and a killed chunk would restart the whole render. Small
retried chunks lose at most one chunk's work, and the heaviest stretch (the timelapse) can use smaller chunks
(`--tail-from`/`--tail-step`).

```bash
source env.sh && cargo build --release
B=$CARGO_TARGET_DIR/release/incendios
(cd stories/incendios-argentina && $B assets && $B music)        # if build/assets is not current
scripts/render_final_chunked.sh -n 1785 --tail-from 1332 --tail-step 6 -o out/final_1080p.mp4
scripts/encode_youtube.sh out/final_1080p.mp4                      # -> out/final_1080p_youtube.mp4
scripts/make_thumbnail.sh out/final_1080p_youtube.mp4 out/thumbnail.jpg --time 15
```

### Checklist

1. **720p drafts until the cut is approved** (`build`, `render -o`, `qa` without `--final`). Iterate on drafts only.
2. **Chunked 1080p final** with `scripts/render_final_chunked.sh` once the cut is signed off.
3. **QA pass**: the script runs `qa --final`; read `build/qa/QA.md` and look at the QA frames (loudness, duration,
   resolution, minimum text size, rules).
4. **Re-encode for upload** with `scripts/encode_youtube.sh`; keep the master.
5. **Thumbnail** from a real frame with `scripts/make_thumbnail.sh`; open it and check text and crop.
6. **Upload unlisted from a pseudonymous channel** when the contest is anonymous: channel name and handle both
   pseudonymous, no real name in the title, description, tags, credits or file metadata, and no link to anything that
   reveals the author. If a browser-automated upload fails, upload the file by hand.
7. **Fill the submission form** with the unlisted link and the methodology/sources text from `docs/`.

Never commit renders, thumbnails or other large binaries: `*.mp4` and `build/` are ignored on purpose.

## Sandbox notes

`env.sh` points `RUSTUP_HOME`/`CARGO_HOME` at a persistent folder and `CARGO_TARGET_DIR` at a shared target. System
packages needed: `build-essential clang libclang-dev nasm pkg-config libx264-dev libfontconfig-dev`, and the `ffmpeg`
CLI for `qa` (decoding the MP4 audio; the loudness itself is measured in Rust).
