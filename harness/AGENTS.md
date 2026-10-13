# AGENTS.md — how to work in this harness (Codex, Claude Code, Cursor, humans)

This directory (`harness/`, inside the `donde-arde-argentina` repo) generates short data-story videos from a `story.yaml`.
Read all of this before touching anything. Commands assume you are in `harness/`.

## Workflow for a new story

1. **Question and data.** One question, one visual answer. Find **open data** (official portals, NASA,
   Copernicus, USGS, INDEC, etc.). Record in `stories/<slug>/SOURCES.md`: publisher, URL, download date,
   license, filters. If there is no open data for something, **it does not go on screen**.
2. **Scaffold.** `python -m harness new "Name"` → `stories/<slug>/` (starts out renderable with real example data).
3. **Data.** Small files in `stories/<slug>/data/`. Heavy raw files in `data/raw/` (ignored by git) + a
   `prepare.py` that downloads them with the adapters (`python -m harness.data.firms|modis|sentinel2 ...`).
4. **Facts.** In `facts.py`, `compute(ctx)` returns a dict with **every number** that will appear (and lists for rankings).
   `ctx.data("name")`, `ctx.json("data/x.json")`, `ctx.table("data/x.csv")`, `ctx.world`.
5. **Beats.** Write the script in `story.yaml` (reference: `docs/beats.md`). Text uses `{fact|filter}`.
   Every verbal rounding → an `assert` in `facts.asserts`. Every number you type by hand (dates, «1 de cada 10» /
   "1 in 10", «Sentinel-2») → an entry in `facts.literals` with its `assert`.
6. **Quick check.** `python -m harness check stories/<slug>` (seconds). If it fails, the message says which rule and how to
   fix it. **Never loosen a rule to make it pass**: shorten the text, lengthen the scene or remove a scene.
7. **Visual QA.** `python -m harness qa stories/<slug> --preview` → look at `build/qa/contact_sheet.png` and
   `phone_sheet.png` (clipped or overlapping text, low contrast, anything unreadable on a phone).
8. **Render.** `make video STORY=stories/<slug>/story.yaml` (or `python -m harness render ... --workers N`).
   Resumes chunks if interrupted. Afterwards `python -m harness qa stories/<slug>` reports the mp4's duration and loudness.
9. **Delivery.** Show the mp4 + `build/qa/timing.md` + a summary of changes. Version stories under iteration as
   `stories/<slug>/` + git; do not overwrite delivered versions without saying so.

## Rules (non-negotiable)

- **Open data only**, cited in `SOURCES.md` and in the `sources` beat, with its license.
- **No invented numbers.** No "illustrative" figures, no eyeballed averages, no projections without a citable
  model. Every number on screen comes from `facts.py` and has an `assert`. The build rejects hand-typed digits.
- **Association ≠ causation.** If the data shows correlation, the text does not say "because of".
- **No AI-generated images, video, voices or music** when the story is for a contest or a publication that
  forbids it (default: do not use them). AI may help with code and analysis, and that is disclosed.
- **Credits and licenses.** Photos/images only PD, CC0, CC BY (CC BY-SA if there is no alternative) or open data
  (Copernicus: "Contains modified Copernicus Sentinel data YEAR"; on Spanish-language screens: "Contiene datos
  Copernicus Sentinel modificados AÑO"). Flags/coats of arms: verify the license.
- **Readability**: ≥ 48 px at 1080p, ≤ 12 words on screen at once per scene, 0.35 s/word + 1 s (min. 2.5 s), total ≤ the
  limit. If it does not fit: remove scenes or words, **never speed up** the text.
- **Audio**: −14 LUFS integrated, true peak ≤ −1.5 dBTP (verified by the render).
- **Do not commit** mp4, wav, raw rasters, `build/`, `data/raw/` (already in `.gitignore`).
- **Privacy**: no personal data, tokens, clients or private URLs in the repo. This repo is private; if
  the harness is published separately, private stories (such as `stories/incendios-argentina/`) do not go with it.

## Code map

| File | What it does |
|---|---|
| `harness/story.py` | Loads the YAML, runs facts, builds and schedules the beats, checks rules |
| `harness/facts.py` | `facts.json`, `{x\|filter}` placeholders, asserts, the hand-typed-number rule |
| `harness/rules.py` | Readability rules (`ReadabilityError` with actionable messages) |
| `harness/render.py` | Frame compositor, parallel chunked render, final mux |
| `harness/layers.py` | Persistent map layers: points, rasters, images, choropleths |
| `harness/core/fx.py` | Kinetic typography (slam), glow, vignette, grain; minimum font size |
| `harness/core/geo.py` | Projection, cameras (fly / zoomto / ease), rasters, georeferenced images |
| `harness/core/space.py` | Sun, Earth and stars drawn in code |
| `harness/beats/*.py` | One file per scene family (`@register`) |
| `harness/audio/` | Cue-driven procedural music + −14 LUFS normalization |
| `harness/data/` | Loaders + FIRMS / MODIS / Sentinel-2 adapters |
| `harness/qa.py` | Stills, contact sheet, phone sheet, timing report |

## Adding a beat type

See `docs/adding-a-beat.md`. Summary: subclass `Beat` in `harness/beats/`, `@register`, `type = "name"`,
implement `text_templates/resolve/text_need/make_blocks/draw_map/draw_ui/cues`, import it in
`harness/beats/__init__.py`, document it in `docs/beats.md` and add a case to the example or to `tests/`.

## Verification commands before a PR

```bash
python -m harness check stories/sismos-argentina
pytest -q
```
