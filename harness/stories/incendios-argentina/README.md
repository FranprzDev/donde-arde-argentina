# incendios-argentina — the v9 video, ported to the harness

Port of `pipeline/v9/render_v9.py` to the harness's generic structure: the same script and the same numbers, written
as `story.yaml` (beats) + `facts.py` (every number shown on screen, with its `assert`s). The on-screen text is in Spanish.

## What is included and what is not

In the repo: `story.yaml`, `facts.py`, flags (`assets/flags/`) and the small data it reads (`data/*.json`, `*.geojson`,
`*.csv`, metadata for each Sentinel-2 crop in `data/s2/*.json`).

Not in the repo (heavy, see `.gitignore`); regenerate it with the root pipeline before rendering:

| File | Where it comes from |
|---|---|
| `data/raw/points.npz` | `pipeline/prep_data.py` (NASA FIRMS VIIRS 2012–2025) |
| `data/raw/scar_all.npz`, `scar_er_2020.npz`, `scar_pat_2025.npz`, `scar_pat_2026.npz` | `pipeline/burn/fetch_umd.py` + `pipeline/v9/prep_burn.py` + `pipeline/v9/prep_assets.py` (MODIS MCD64A1) |
| `data/s2/tuc_2025-09-23.jpg`, `delta_2020-09-23.jpg` | `pipeline/v9/s2_date.py` |
| `data/s2/comarca_2024.jpg`, `comarca_2025.jpg`, `comarca_2026.jpg` | `pipeline/v9/s2_comarca.py` |

Copy those files into this folder's `data/raw/` and `data/s2/` (the `.json` files in `data/s2/` give the date, product and bounding box
of each crop).

## Running

```bash
cd harness
pip install -r requirements.txt
python -m harness check stories/incendios-argentina            # timing table + rules (seconds)
python -m harness qa stories/incendios-argentina --preview     # stills + contact sheet
python -m harness render stories/incendios-argentina --workers 2   # 1080p, ~5–6 min with 2 vCPU
```

## Differences from v9

- Ranking headline shortened to «5 PROVINCIAS = 53 %» ("5 PROVINCES = 53 %"): with the v9 one, the 0.35 s/word + 1 s rule pushed the video past 60 s.
- The harness's generic procedural music (same instruments and cue logic, not bit-for-bit identical).
- The legend shows only the current scene's layers.
- Total duration 59.63 s (v9: 59.77 s).
