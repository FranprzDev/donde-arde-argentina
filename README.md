# ¿Dónde arde Argentina? (Where is Argentina burning?)

Code, data and documentation for the data-visualization video «¿Dónde arde Argentina?» (fire hotspots and burned area in Argentina, 2012–2025). The video itself is in Spanish.

Everything in the video is generated with code from open data: the map, the animation, the numbers and the music. There are no AI-generated images. This repository exists so anyone can verify every figure and reproduce the video.

## What is here

| Folder | Contents |
|---|---|
| `pipeline/` | Scripts for download, processing, frame rendering, music and final assembly |
| `data/` | Small processed data (CSV, JSON, GeoJSON) and the statistics the renderer reads |
| `docs/` | Timed script (`script.md`), sources and verification of every number (`sources.md`), methodology description (`descripcion-metodologica.md`) |
| `assets_meta/` | Metadata for each satellite image (product, date, cloud cover, bounding box) and credits from earlier versions |
| `fonts/` | Open fonts (OFL) |
| `harness/` | Generic harness for data-story videos (`story.yaml` + data → video), with the `sismos-argentina` example and this video ported to `stories/incendios-argentina/` |
| `harness-rs/` | **Canonical render path.** The all-Rust harness ([fframes](https://fframes.studio)): data prep, fact asserts, readability rules, render, score and QA. The current video is `harness-rs/stories/incendios-argentina/` |

Heavy raw data (FIRMS archive, MODIS rasters, Sentinel-2) is not in the repo: the scripts download it.

## Data sources

- **Fire hotspots:** NASA FIRMS, VIIRS S-NPP 375 m, Argentina country archive 2012–2025 (type 0, nominal or high confidence).
- **Burned area:** NASA MODIS MCD64A1 Collection 6.1 (500 m, monthly), University of Maryland SFTP server.
- **Fire causes 1993–2019:** Argentina's national Ministry of Environment (Ministerio de Ambiente de la Nación, open data).
- **Boundaries:** INDEC (provinces, 2022 Census radios) and IGN.
- **Sugarcane in Tucumán:** EEAOC (sugarcane-growing departments).
- **Satellite imagery:** Copernicus Sentinel-2.
- v9 uses no photos or press headlines: everything happens on a single map, with zooms into Sentinel-2 images. Specific figures: see `docs/sources.md` and `assets_meta/v9/`.

## How it is generated

```
pipeline/prep_data.py        # FIRMS VIIRS -> data/raw/points.npz + stats
pipeline/burn/fetch_umd.py   # download MCD64A1 (UMD)
pipeline/prep_burn.py        # burned area per province, burn scars
pipeline/causas.py           # fire causes (Ministry of Environment)
pipeline/prep_tucuman.py     # hotspots in the sugarcane zone during the harvest (zafra)
pipeline/prep_v2.py, prep_v4.py, prep_v7.py   # statistics and provincial ranking
pipeline/v9/render_v9.py --nums   # (v9, current version) prints every number shown on screen
pipeline/v9/s2_date.py            # Copernicus Sentinel-2 crops for one date (Burruyacú 2025-09-23, Delta 2020-09-23)
pipeline/v9/build_v9.sh           # parallel frame render + music + assembly
```

Requirements: Python 3.10+, numpy, scipy, Pillow, OpenCV, rasterio, pyproj, ffmpeg.

No number is typed by hand in the renderer: all of them are read from the JSON files in `data/`, and `render_v9.py` has an `assert` for every verbal rounding («casi» / "almost", «más de» / "more than") and for every ranking value.

## Rust harness (`harness-rs/`, canonical)

The video is built with `harness-rs/`: everything (prep, facts, render, music, QA) is Rust. See `harness-rs/README.md`.

```bash
cd harness-rs && source env.sh && cd stories/incendios-argentina
cargo run --release -- build            # prep -> facts -> check -> assets -> music -> render -> qa
```

An earlier experimental port lived in `fframes/`; it only covered part of the video and was removed once `harness-rs/`
rendered the whole video and passed QA.

## Python harness (`harness/`, reference)

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
