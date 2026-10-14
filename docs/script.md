# Current cut — harness-rs (2026-10-13, 1280×720 draft)

The current video is rendered by `harness-rs/stories/incendios-argentina` (all Rust); its `story.toml` is the source of
truth for every on-screen text and time. The sections below this one describe v9, the last Python version.

**New opening (Francisco, 2026-10-13):**

| Time (s) | Picture | On-screen text (words → time on screen) | Sound |
|---|---|---|---|
| 0.45–3.30 | Sun → rays → Earth → Argentina | «¿DÓNDE ARDE / ARGENTINA?» (3 → 2.85 s) | solar roar |
| 3.40–6.85 | Flat map: rays land, Argentina heats up and cools (heat fades from 6.25) | «EL SOL QUEMA,» (3.40) / «PERO NO PROVOCA» / «INCENDIOS.» (3.95, three lines so the text stays left of the map) — 7 words → 3.45 s, 100 px | warm pad until the cut |
| 6.85 | **Hard cut**: text out, map near black, the spark (the first VIIRS hotspot, Jan 2012) | — | the music drops; procedural match strike |
| 6.91–11.41 | The spark; at 7.35 it ignites the 14-year VIIRS timelapse (no pause): big year + monthly curve | «EL HUMANO, SÍ.» (150 px) + «9 DE CADA 10 CON CAUSA CONOCIDA» (66 px) — 10 words → 4.50 s | taiko on «EL HUMANO», riser, hit at 7.35 |

The rest follows the v10 order (scar + «QUEMADAS = CASI 12 TUCUMANES», top 5, Tucumán + Burruyacú Sentinel-2, Entre Ríos
2020 + Delta Sentinel-2, Comarca Andina, close, sources/credits card), every later mark shifted 0.40 s earlier. Total 59.49 s.
«9 DE CADA 10» keeps its assert (`hum_10 == 9`: 90.2 % human among fires with a known cause, Min. Ambiente 1993–2019).

---

# v9 — «¿Dónde arde Argentina?» (Visual story, 59.77 s, 1080p30)

The video is in Spanish: every on-screen string below is quoted **verbatim in Spanish** («…»), exactly as it appears on screen.

**v9 = v8 + the author's notes (2026-10-13), all mandatory:**
1. **Rays that hit Argentina:** on the globe and on the flat map, every ray from the Sun lands on a point inside the country and its streak ends there (flash + glint); before, the first rays fell anywhere on the globe.
2. **Tucumán with an image of Tucumán:** the Queensland photo is gone. The stop ends with a zoom, within the same map, into a Copernicus Sentinel-2 image of **Burruyacú (a sugarcane department), 2025-09-23, at the height of the harvest (zafra)**: two smoke columns from active burns, with that afternoon's VIIRS hotspots over the source of the smoke. There is no verified open photo of a sugarcane burn in Tucumán (Commons checked again).
3. **A single visualization:** the other two cuts to photos (grassland, forest) and the 4 headlines are gone. Entre Ríos ends with a zoom into Sentinel-2 of **the Delta islands opposite Rosario, 2020-09-23**; the Comarca keeps its Sentinel-2 before/after in place. Everything happens on one continuous map.
4. **No Corrientes:** the highlighted Corrientes 2022 burn scar (it looked misplaced) and the La Nación headline are gone. Corrientes only appears as a name in the ranking (4th place, real data).
5. **Less text, bigger, longer:** ≤ ~12 words per moment; body text ≥ 48 px (figures 150 px, phrases 66–124 px); each text ≥ 0.35 s per word + 1 s (min. 2.5 s), verified by `assert` in `render_v9.py`. To fit in 60 s, beats were removed rather than sped up: the «2.550.467 FOCOS» card, the second title, the grey source line for the causes, the 24 ranking rows and the top-5 hectares, the grey Tucumán note and the closing header.

Kept: the outline of the whole country lit up, the ranking (now only the top 5 with names), the final map with everything that burned 2012–2025 under «YA NO FALTAN DATOS. / FALTA RESPONSABILIDAD.», figures only from the pipeline JSON files with `assert`s, −14 LUFS, no author name.

| Time (s) | Image / camera | On-screen text, Spanish verbatim (words → time on screen) | Music |
|---|---|---|---|
| 0.0–4.6 | Sun → rays → Earth → Argentina: every ray lands in the country | «¿DÓNDE ARDE / ARGENTINA?» (0.45–3.85; 3 → 3.4 s) | solar roar, flash per ray |
| 4.0–5.45 | Flat map: rays keep falling on Argentina, which heats up | «EL SOL CALIENTA.» (4.45–7.05; 3 → 2.6 s) | warm pad |
| 5.55–10.6 | The heat fades; a spark (first VIIRS hotspot, Jan 2012) | **«LA CHISPA ES HUMANA.»** + «9 DE CADA 10, CON CAUSA CONOCIDA» (5.65–10.6; 11 → 4.95 s) | match strike, riser |
| 8.3–12.2 | The spark ignites 14 years of VIIRS hotspots; big year label + monthly curve (2012 · 2016 · 2020 · 2024) | (the spark text stays until 10.6) · legend «1 punto = 1 foco de calor (satélite)» | hit, drums, tick each January |
| 12.2–13.5 | Everything lit → ash → MODIS burn scar | — · legend «gris = área quemada» | braam, whoosh |
| 13.5–18.7 | National burn scar | **«26,6 MILLONES DE HA»** / «QUEMADAS: CASI 1 DE CADA 10 DEL PAÍS» (12 → 5.25 s) | boom |
| 18.7–20.4 | The 24 jurisdictions light up on the map (choropleth), no text | — | one tick per province |
| 20.4–25.8 | Top 5 on the map (numbers) | «5 PROVINCIAS = 53 % DE LO QUEMADO» / 1 FORMOSA · 2 LA PAMPA · 3 SANTA FE · 4 CORRIENTES · 5 SANTIAGO DEL ESTERO (5.4 s) | hit, drums |
| 25.8–26.8 | Direct zoom to Tucumán | — | whoosh |
| 26.8–31.9 | **Tucumán**: sugarcane zone outlined, harvest hotspots; the zoom frame appears | [flag] «TUCUMÁN» / **«89 %»** «DE SUS FOCOS» / «EN ZONA CAÑERA, EN PLENA ZAFRA» (11 → 4.9 s) | hit, drums |
| 31.8–32.8 | Zoom within the map into the frame | — | descending whoosh |
| 32.8–35.4 | **Sentinel-2, Burruyacú 2025-09-23**: smoke columns; that afternoon's VIIRS hotspots | «BURRUYACÚ, TUCUMÁN» / «23/09/2025 · Sentinel-2» (4 → 2.6 s) | impact + fire roar |
| 35.4–36.8 | Zoom out and fly to Entre Ríos | — | whoosh |
| 36.8–41.5 | **Entre Ríos 2020**: the year's hotspots, MODIS 2020 burn scar highlighted | [flag] «ENTRE RÍOS · 2020» / **«37.506»** (counts up) «FOCOS» / «CASI 7 VECES LO HABITUAL» (10 → 4.7 s) | hit, drums |
| 41.4–42.4 | Zoom to the Delta | — | whoosh |
| 42.4–45.5 | **Sentinel-2, islands opposite Rosario 2020-09-23**: smoke over the islands, Rosario on the left; that afternoon's VIIRS hotspots | «ISLAS DEL DELTA» / «23/09/2020 · Sentinel-2» + label «ROSARIO» (6 → 3.1 s) | impact + roar |
| 45.5–47.1 | Zoom out and fly to the Andes | — | whoosh, swell |
| 47.1–52.2 | **Comarca Andina**: Sentinel-2 Dec 2024 → Apr 2025 → Apr 2026, burn scars 2025 (amber) / 2026 (red) | [flags] «COMARCA ANDINA · 2026» / **«42.000»** (counts up) «HA» / «7 VECES MÁS QUE EN 2025» (11 → 5.1 s) · labels «DIC 2024 / ABR 2025 / ABR 2026 · Sentinel-2 · ■ 2025 · ■ 2026» | drop, choir |
| 52.2–52.9 | Zoom out to the country | — | drum roll |
| 52.9–56.8 | **Closing**: 24 jurisdictions lit; all 2012–2025 hotspots accumulate over the MODIS burn scar | 53.67 **«YA NO FALTAN DATOS.»** / 53.92 **«FALTA RESPONSABILIDAD.»** (5 → 3.1 s) | silence 53.4–53.67; boom, taiko, bell |
| 56.8–59.77 | SOURCES card (FUENTES, 8 lines, 48 px) | see sources.md | decrescendo |

Sizes: minimum text 48 px (legends, labels, sources, curve years); mono headers 52 px; phrases 66 px; figures 150 px; closing 124 px.
