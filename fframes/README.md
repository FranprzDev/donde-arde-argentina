# «¿Dónde arde Argentina?» — fframes port of v10 (test)

An experimental port of the v10 data video (`render_v10.py`, Python + PIL/OpenCV + ffmpeg) to
[fframes](https://fframes.studio) 1.2.1-rc.30 (Rust, SVG scenes, MIT license), to judge its look and its render speed.
The Python pipeline stays the reference; this directory only reads it, never writes to it.

> **Status:** test port, not the production renderer. 20.8–53.3 s is not ported yet, and the new closing card does not
> pass the reading-time rule (see below). Both are pending Francisco's decision.

> **Path note:** the scripts expect the v10 Python pipeline at `../v10/` (relative to this folder). This repository
> currently ships the pipeline up to `pipeline/v9/`; until v10 is committed, point `V10` in `prep/export_data.py` /
> `prep/time_python.py` at your local v10 folder. `data/v10.json` and `data/cam_check.json` are committed, so
> `cargo build` and `camcheck` work without it; the raster `assets/` still need one export run.

## What is ported

| Time | Beat | Status |
|---|---|---|
| 0–4.6 s | space: stars, sun, globe, rays landing on Argentina, hook «¿DÓNDE ARDE ARGENTINA?» | ported (approximations, see below) |
| 3.95–7.75 s | «EL SOL CALIENTA.» / «EL SOL NO PRENDE FUEGO.», heat wash, hard cut | ported |
| 7.75–12.5 s | the spark, «NOSOTROS SÍ.» + «9 DE CADA 10 CON CAUSA CONOCIDA», 14-year VIIRS timelapse, year + monthly curve | ported |
| 12.5–18.2 s | ash, MODIS scar, «26,6 MILLONES DE HA» / «QUEMADAS: CASI 1 DE CADA 10 DEL PAÍS» | ported |
| 18.2–20.8 s | «= CASI 12 TUCUMANES», 12 real-scale Tucumán outlines | ported (geometry identical) |
| 20.8–53.3 s | ranking, Tucumán / Entre Ríos / Comarca stops, Sentinel-2 zooms | **not ported** (placeholder frame in fframes; the review file splices in the v10 frames, tagged) |
| 53.3–56.8 s | close: whole country lit + every hotspot, «YA NO FALTAN DATOS. / FALTA RESPONSABILIDAD.» | ported |
| 56.8–59.9 s | **new** sources + credits card (Francisco's change of 13-10-2026) | ported, new design |

The camera path (`src/cam.rs`) is a 1:1 port; `cargo run --release --bin camcheck` checks it against the Python camera for
all 1797 frames (worst error 0.000000 px).

## What is (and is not) in the repo

Committed: `src/`, `Cargo.toml`, `Cargo.lock`, `build.rs`, `setup.sh`, `build/*.sh`, `prep/*.py`, `data/*.json` (~0.5 MB,
exported from v10), `vendor/` (fframes MIT licence + the fframes agent skill docs), `qa/TIMINGS.md`.

Not committed (see `.gitignore`), and how to get each:

| Path | What | How to obtain |
|---|---|---|
| `assets/` | ~460 PNG data rasters (~54 MB) + sun texture + grain | `python3 prep/export_data.py` (needs the v10 pipeline and its data, see path note) |
| `media/` | fonts, read by family name at run time | copy `Anton.ttf` → `media/Anton-Regular.ttf`; instance the variable fonts in `../fonts/` with fontTools: `fonttools varLib.instancer ../fonts/Inter.ttf wght=500 -o media/Inter500.ttf` (likewise `wght=600` → `Inter600.ttf`, `JetBrainsMono.ttf wght=700/800` → `JBMono700.ttf` / `JBMono800.ttf`) and set the family name to the file stem (e.g. with fontTools `name` table edits) |
| `target/` | Cargo build output (~1.8 GB) | `cargo build --release` |
| `build/*.mp4`, `*.time`, `*.log`, QA PNG/JPG sheets, `incendios_fframes.mp4` | render outputs | the commands below |
| `.toolchain/` | Rust toolchain + `libx264.so.163` | `source ./setup.sh`; x264 workaround below |
| music | mastered v10 score `music_v10.wav` | produced by the v10 pipeline (`music_v10.py` / `finish_v10.sh`) |

**x264 workaround.** The prebuilt FFmpeg that `ffmpeg-sys-fframes` downloads on aarch64 links against libx264 ABI 163,
while Debian 13 ships ABI 164/165. Download Ubuntu 22.04's arm64 package (`libx264-163_0.163.3060+git5db6aa6-2build1_arm64.deb`
from packages.ubuntu.com / ports.ubuntu.com), extract it with `dpkg-deb -x pkg.deb ex/`, and copy
`ex/usr/lib/aarch64-linux-gnu/libx264.so.163` to `.toolchain/x264/lib/`. `build.rs` adds that folder to the link search path
and an rpath only if the file exists, so on x86_64 or systems with a matching x264 nothing changes. The binary is not
committed (third-party GPL binary, environment-specific).

## How it works

* `prep/export_data.py` imports `render_v10.py` (so every v10 `assert` runs) and exports what the Rust side needs:
  `data/v10.json` (timeline, on-screen strings, numbers, camera segments, rings, rays, stars, embers) and `assets/*.png`
  (georeferenced data rasters: VIIRS hotspots binned per month at the national-map scale, cumulative ember/accumulated
  layers per quarter, MODIS scar layers, plus the procedural sun texture and film grain). Rust never computes a number.
* `src/lib.rs` writes every frame as one SVG document; fframes' built-in CPU backend (tiny-skia via usvgr/resvgr) renders it
  and encodes with libx264 (veryfast, crf 14, same as the v10 chunks).
* Fonts: the same files v10 uses (the repo's `fonts/`), with the variable Inter / JetBrains Mono pinned to
  the weights v10 uses (600 / 700 / 800) and renamed `Inter600`, `JBMono700`, `JBMono800` (fframes resolves by family).
* Audio: not re-synthesised. `build/assemble.sh` muxes the mastered v10 score (`../v10/build/music_v10.wav`, −14 LUFS),
  padded with silence for the 0.13 s the new card adds.

## Commands

```bash
source ./setup.sh                                   # toolchain inside .toolchain/ (sandbox root FS is wiped between sessions)
python3 prep/export_data.py                         # with PYTHONPATH from ../v10/env.sh
cargo build --release
./target/release/camcheck
./target/release/incendios-fframes frame 10s,58.5s -o build/qa/ff
./target/release/incendios-fframes render 0..624 -o /tmp/ff_a.mp4   # render to local disk, then copy (see notes)
bash build/assemble.sh                              # -> incendios_fframes.mp4
python3 prep/sheet.py build/qa/sheet.jpg build/qa/py build/qa/ff 0.3 3 ...   # side-by-side QA
```

## Sandbox notes (what it took)

* Linux aarch64, no GPU: the Skia GPU backend (Vulkan) and the real-time `preview` window are unavailable, so this uses the
  **CPU backend**, which fframes documents as ~10x slower than Skia GPU.
* The prebuilt FFmpeg 9 that `ffmpeg-sys-fframes` downloads links against x264 ABI 163; Debian 13 ships 164/165, so
  `.toolchain/x264/lib/libx264.so.163` (Ubuntu 22.04 arm64 package) is linked via `build.rs` with an rpath.
* The first build needs ~3 GB free on `/` (FFmpeg source fallback); the target dir lives in the workspace.
* A render written straight onto the workspace filesystem once came out without its `moov` atom; render to `/tmp` and copy.

## Closing card (new)

Short source names only, label/value grid, then credits — all names are sources already in `../v10/sources.md`:

```
FUENTES
Focos de calor   NASA FIRMS (VIIRS)
Área quemada     NASA MODIS
Causas           Ministerio de Ambiente
Caña de azúcar   EEAOC
Límites          INDEC · IGN
Imágenes         Copernicus Sentinel-2 (modificado)
Banderas         Wikimedia Commons
CRÉDITOS
Pipeline de Datos, Generación de Video & Producción final:
Harness Engineering with AI
Director & Revisor:
Francisco Perez
```

Reading time: the card holds 3.14 s (56.76 → 59.90 s). With 45 words the v10 rule (0.35 s/word + 1 s) needs 16.8 s; even a
scan rate of 5 words/s needs 10 s. Inside 60 s without retiming the cut that is impossible, so `export_data.py` keeps the
assert behind `STRICT_CARD=1` and otherwise prints the shortfall on every export/run. Options: retime earlier beats to give
the card ~10 s, split sources and credits across two cards, or cut rows (e.g. drop «Caña de azúcar» and «Banderas»).
**Pending Francisco's decision**; the card currently fails the rule.

## Benchmark (13-10-2026)

Conditions: same frames, same x264 settings (veryfast, crf 14), wall clock, Linux aarch64 sandbox, **CPU only** (no GPU),
machine under other load (load average 2–4 during both timings). Raw numbers in `qa/TIMINGS.md`.

| Segment | Python v10 (2 workers, `prep/time_python.py`) | fframes CPU backend (`render`) | Winner |
|---|---|---|---|
| Opening 0–20.8 s (624 frames) | **139.7 s (4.47 fps)** | 325.4 s (1.92 fps); first run 373.6 s | Python, ~2.3x |
| Close 53.3–59.9 s (Python 194 frames / fframes 198) | 44.2 s (4.38 fps) | **29.4 s (6.7 fps)** | fframes, ~1.5x |

Why the opening is slower in fframes: full-resolution bloom/glow blur (see below); v10 blurs at half resolution.
The Skia GPU (Vulkan) backend, which fframes documents as ~10x faster than CPU, is **untested** here (no GPU in the sandbox),
so these numbers are a lower bound for fframes, not a verdict.

Single frames (`frame`, incl. ~1.4 s start-up loading 460 PNG assets): space 3.1 s, rays on map 1.6 s, timelapse peak
5.6 s, scar/Tucumanes 1.7 s, close 1.8 s. The cost is full-resolution `feGaussianBlur` (glow σ 18/52 px and bloom σ 10/36 px
over the whole 1920×1080 frame; v10 blurs at half resolution) and the fire rasters being drawn twice (plain + bloom).
Cheap wins left: blur at half resolution (render the glow group into a scaled-down nested image), precompute the bloom into
the fire PNGs, or a GPU (Skia/Vulkan backend: ~10x per fframes docs; not testable here).

Visual differences seen in `qa/sheet_side_by_side_a.jpg` / `_b.jpg`: text, map edges and outlines are sharper and cleaner
(true vector antialiasing); type, positions, colours, camera and timing match. Weaker/different: the timelapse fire is
binned per month at national scale (less per-point flicker, slightly cooler at the peak), the globe shading and
atmosphere are gradient approximations, ray impact glints are a bit dimmer, the heat-haze shimmer bands are not ported,
grain is approximated with a hard-light overlay. Close and Tucumanes beats are near-identical.

## Validation

* `cargo check --release` (13-10-2026, rustc/cargo 1.99.0, aarch64): passes, 2 dead-code warnings (`F` enum `Clone`
  derive, unused `prov_rings` field).
* `camcheck`: worst camera error 0.000000 px over 1797 frames (run on the original render setup).
