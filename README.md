# ¿Dónde arde Argentina? (Where is Argentina burning?)

Code, data and documentation for the data-visualization video «¿Dónde arde Argentina?» (fire hotspots and burned area in Argentina, 2012–2025). The video itself is in Spanish.

Everything in the video is generated with code from open data: the map, the animation, the numbers and the music. There are no AI-generated images. This repository exists so anyone can verify every figure and reproduce the video.

The current cut (v15) is 59.5 s, 1920×1080, built entirely by the Rust harness in `harness-rs/`.

## What is here

| Folder | Contents |
|---|---|
| `harness-rs/` | **Canonical pipeline.** The all-Rust harness ([fframes](https://fframes.studio)): data prep, fact asserts, readability rules, render, procedural score, loudness mastering, QA, and the final-delivery scripts in `harness-rs/scripts/`. The video is `harness-rs/stories/incendios-argentina/` |
| `docs/` | Timed script (`script.md`), sources and verification of every number (`sources.md`), methodology description (`descripcion-metodologica.md`) |
| `data/` | Small processed data (CSV, JSON, GeoJSON) and the statistics earlier versions read |
| `assets_meta/` | Metadata for each satellite image (product, date, cloud cover, bounding box) and credits from earlier versions |
| `fonts/` | Open fonts (OFL), also used by the thumbnail script |
| `pipeline/` | The original Python pipeline (v2–v9). Kept as a reference: `incendios verify` checks that the Rust prep reproduces its numbers |
| `harness/` | The earlier generic Python harness (`story.yaml` + data → video), reference only |

Heavy raw data (FIRMS archive, MODIS rasters, Sentinel-2) is not in the repo, and neither are the rendered videos or
thumbnails (`*.mp4`, `build/` are git-ignored).

## Data sources

- **Fire hotspots:** NASA FIRMS, VIIRS S-NPP 375 m, Argentina country archive 2012–2025 (type 0, nominal or high confidence).
- **Burned area:** NASA MODIS MCD64A1 Collection 6.1 (500 m, monthly), University of Maryland SFTP server.
- **Fire causes 1993–2019:** Argentina's national Ministry of Environment (Ministerio de Ambiente de la Nación, open data).
- **Boundaries:** INDEC (provinces, 2022 Census radios) and IGN.
- **Sugarcane in Tucumán:** EEAOC (sugarcane-growing departments).
- **Satellite imagery:** Copernicus Sentinel-2 L2A.

Every on-screen figure, how it is computed and how it was verified: `docs/sources.md`. No number is typed by hand:
on-screen numbers come from named facts (`{er_2020|int}`), a literal digit in a text fails the build, and every verbal
rounding («casi» / "almost", «más de» / "more than") has an `[[assert]]` in `story.toml`.

## Make the video (`harness-rs/`)

Requirements: a Rust toolchain, `build-essential clang libclang-dev nasm pkg-config libx264-dev libfontconfig-dev`,
and the `ffmpeg` CLI (plus ImageMagick for the thumbnail). Details: `harness-rs/README.md`.

### 720p drafts

Every render is a 1280×720 draft unless you ask for the final cut. Iterate on drafts until the cut is approved:

```bash
cd harness-rs && source env.sh && cd stories/incendios-argentina
cargo run --release -- build            # prep -> facts -> check -> assets -> music -> render (720p) -> qa
cargo run --release -- check            # readability rules only (text ≥ 48 px, words per beat, hold time, ≤ 60 s)
cargo run --release -- frame 12.5s      # one frame, for quick looks
```

### Final 1080p (chunked)

A full 1080p render decodes ~2 GB of rasters and can be OOM-killed on a machine whose memory is shared. The final is
rendered in small, retried, resumable chunks that each load only the assets they draw; the script then joins the parts,
muxes the score and runs `qa --final`:

```bash
cd harness-rs && source env.sh && cargo build --release
scripts/render_final_chunked.sh -n 1785 --tail-from 1332 --tail-step 6 -o out/final_1080p.mp4
```

(`cargo run --release -- build --final` still works on a machine with enough free memory.)

### QA

`incendios qa <video.mp4> [--final]` writes `build/qa/QA.md` and QA frames: loudness of the MP4 itself (−14 LUFS ±0.5,
true peak ≤ −1.5 dBTP), duration, resolution, minimum text size and the readability rules.

### Upload copy and thumbnail

```bash
scripts/encode_youtube.sh out/final_1080p.mp4                    # libx264 CRF 20, yuv420p, faststart, audio copied
scripts/make_thumbnail.sh out/final_1080p_youtube.mp4 out/thumbnail.jpg --time 15   # 1280×720 from a real frame
```

The re-encode took the master from 95 MB to 38 MB with no visible loss. The thumbnail is cut from the video itself
(map on the right, title in Bebas Neue on the left); title, subtitle, colours, frame time and crop are flags.

### Final-delivery checklist

1. 720p drafts until the cut is approved.
2. Chunked 1080p final (`scripts/render_final_chunked.sh`).
3. QA pass (`qa --final`): read the report and the QA frames.
4. YouTube re-encode (`scripts/encode_youtube.sh`).
5. Thumbnail from a real frame (`scripts/make_thumbnail.sh`).
6. Upload unlisted from a pseudonymous channel (the contest is anonymous): no real name in the channel, handle,
   title, description, credits or metadata. Keep a manual upload as the fallback if an automated upload fails.
7. Fill the submission form.

## Python harness and pipeline (reference)

The Python code below produced v2–v10 and is kept so the numbers can be cross-checked; it is no longer used to render.

### `harness/`

`harness/` is the generic version of this pipeline: a Python package that builds a short video (≤ 60 s) from a
`story.yaml` (the scenes and their text) and a `facts.py` (every number shown on screen, with an `assert` for every
verbal rounding). The readability rules (text ≥ 48 px, words per scene, minimum time on screen, total duration),
the procedural music and the normalization to −14 LUFS live in code: if something does not comply, the build fails.

```bash
cd harness
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt                        # Python 3.10+ and ffmpeg on the PATH

make test                                              # pytest: rules + render of the small example
make check STORY=stories/sismos-argentina/story.yaml   # validate YAML, compute facts, check rules
make video STORY=stories/sismos-argentina/story.yaml PREVIEW=1   # fast half-resolution render
python -m harness new "My story"                       # new story from the template
```

Without `make`: `python -m harness check|qa|render|still <story>`. There is also a `Dockerfile`.

- `harness/stories/sismos-argentina/`: small example (USGS earthquakes, data in the repo, no network, ~1 min).
- `harness/stories/incendios-argentina/`: this video (v9) ported to the harness. The heavy data is not in the repo;
  its `README.md` says which `pipeline/` script generates each file.
- Documentation: `harness/README.md`, `harness/AGENTS.md` (workflow and rules for coding agents), `harness/docs/`.

## Use of AI

An AI assistant helped, under the author's supervision, to write the data-processing code, the animation and the code-synthesized music, and to review the sources. No AI-generated images or videos were used.

## License

Code: MIT. Derived data: follows the license of each original source (see `docs/sources.md`).
