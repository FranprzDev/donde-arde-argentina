# Current cut — harness-rs (2026-10-13)

Numbers are computed by `harness-rs` (`incendios prep` + `incendios facts`) and guarded by the 15 `[[assert]]` in
`story.toml`; `incendios verify` compares them with the Python v10 outputs. An independent re-computation from the raw
files (FIRMS CSVs, UMD MCD64A1 windows, IGN/INDEC boundaries, causes CSV, EEAOC table) on 2026-10-13 matched every
on-screen figure. Two facts a reader needs to reproduce the hotspot counts:

* **Province of a hotspot:** INDEC Census 2022 province polygons (`data/natgeo_v7.json`); a hotspot that falls outside
  every polygon (rivers, Delta islands, coast) goes to the **nearest** province. Entre Ríos gets 477 such hotspots over
  2012–2025, which is why «37.506» needs this rule (37.382 without it; 37.580 with the IGN outline). «CASI 7 VECES»
  holds with every variant (6.96–7.00).
* **Boundaries:** hotspots and MODIS use INDEC polygons; Tucumán's area and its departments use IGN (Georef). The sources
  card says «INDEC»; the form's sources field lists both.

The opening line changed to «EL SOL QUEMA, / PERO NO PROVOCA INCENDIOS.» → «EL HUMANO, SÍ.»; the figure under it is the
same «9 DE CADA 10 CON CAUSA CONOCIDA» (105.576 / 117.034 = 90.2 %, 47.9 % without a determined cause).

---

# Sources and verification of every on-screen number — v9 «¿Dónde arde Argentina?»

The video is in Spanish: on-screen strings are quoted **verbatim in Spanish** («…»).

Data chain: `prep_*.py` → `data/*.json` → `render_v9.py`, with an `assert` for every figure, rounding and word that depends on data (`python3 render_v9.py --nums` prints them). v9 adds no new figures; it adds two Sentinel-2 images and the VIIRS hotspots from those same afternoons. Queries: 2026-10-12/13.

## What is new in v9 (2026-10-13)

1. **Intro:** every ray from the Sun (on the globe and on the flat map) lands inside Argentina and the streak visibly ends there (in v8 the first rays went to random points on the sunlit side and seemed to miss the country).
2. **A single visualization:** the 3 cuts to photos and the 4 press headlines are gone. Tucumán and Entre Ríos end with a **zoom within the same map** into a real Copernicus Sentinel-2 satellite image, georeferenced in place, with the VIIRS hotspots from that same afternoon on top. Comarca Andina keeps its Sentinel-2 before/after in place.
3. **The Corrientes 2022 visualization is gone** (highlighted burn scar under the La Nación headline), and so is that headline.
4. **Much less text:** ≤ ~12 words per moment, body text ≥ 48 px, each text on screen ≥ 0.35 s per word + 1 s (minimum 2.5 s; verified with an `assert` in the script). Removed: the «2.550.467 FOCOS» card, the second title, the grey source line for the causes, the 24 ranking rows and their hectares, the grey Tucumán baseline line, the closing header.

## On-screen figures (all with `assert`)

| v9 screen (Spanish, verbatim) | Exact value | Computation / source |
|---|---|---|
| «9 DE CADA 10, CON CAUSA CONOCIDA» (under «LA CHISPA ES HUMANA.») — "9 in 10, with a known cause" | 90.2 % | 105,576 human-caused fires (negligence + intentional) / 117,034 with a known cause, 1993–2019 (5). For 47.9 % the cause was not determined (not shown on screen; stated in the methodology description). |
| «26,6 MILLONES DE HA» / «QUEMADAS: CASI 1 DE CADA 10 DEL PAÍS» — "26.6 million ha burned: almost 1 in 10 of the country" | 26,642,264 ha; 9.53 % | MODIS pixels that burned at least once 2012–2025 (each pixel counted once) / 279,462,711 ha of the 24 jurisdictions on the same grid (2)+(3) |
| «5 PROVINCIAS = 53 % DE LO QUEMADO» + 1 Formosa · 2 La Pampa · 3 Santa Fe · 4 Corrientes · 5 Santiago del Estero | 53.3 % (14,205,536 / 26,642,264 ha) | `data/ranking_v7.json`: Formosa 3,182,339 · La Pampa 3,041,100 · Santa Fe 2,837,162 · Corrientes 2,685,422 · Santiago del Estero 2,459,513 ha. Corrientes appears only as a name in this ranking. |
| «TUCUMÁN» / «89 % DE SUS FOCOS» / «EN ZONA CAÑERA, EN PLENA ZAFRA» — "89 % of its hotspots, in the sugarcane zone, at the height of the harvest" | 89.17 % (53,625 of 60,136) | Tucumán hotspots 2012–2025 in the 12 EEAOC sugarcane departments and in May–November (1)+(3)+(4). Baseline (off screen in v9): those departments are 69.5 % of the province; an even spread over area and over the year would give ≈ 40 %. Caveat: departments, not plots. |
| «ENTRE RÍOS · 2020» / «37.506 FOCOS» | 37,506 | VIIRS hotspots in 2020 inside Entre Ríos (INDEC); the renderer verifies that the animated points = 37,506 (1)+(3) |
| «CASI 7 VECES LO HABITUAL» — "almost 7 times the usual" | 6.96 | 37,506 / median of the other 13 years 2012–2025 (5,391 hotspots). «Lo habitual» ("the usual") = that median (explained on the sources card). |
| «COMARCA ANDINA · 2026» / «42.000 HA» | 42,266 ha (shown rounded down to the thousand) | MODIS Jan–Mar 2026 inside the box −71.80/−42.62/−71.05/−41.75 (2) |
| «7 VECES MÁS QUE EN 2025» — "7 times more than in 2025" | 7.01 (42,266 / 6,025 ha) | same box, Jan–Mar 2025 (2) |
| Closing: «YA NO FALTAN DATOS. / FALTA RESPONSABILIDAD.» — "We no longer lack data. / We lack accountability." | — | editorial conclusion, over the map of everything that burned 2012–2025 (MODIS burn scar + the 2,550,467 VIIRS hotspots) |

## Satellite images on screen (all Copernicus Sentinel-2 L2A, true color TCI)

License: Copernicus Sentinel data with free, full and open access (EU Delegated Regulation 1159/2013); required attribution: "Contains modified Copernicus Sentinel data [year]" — on the card, in Spanish: «Imágenes: datos Copernicus Sentinel-2 modificados (2020–2026)». Download: Microsoft Planetary Computer mirror, collection `sentinel-2-l2a`, cropped and reprojected to EPSG:4326 with `s2zoom/s2_date.py` (a single date per image; no retouching, resampling only).

| Moment | Place / box (lon/lat) | Overpass date and time | Product(s) | Clouds | What is visible |
|---|---|---|---|---|---|
| Final Tucumán zoom | **Burruyacú, Tucumán** (one of the 12 EEAOC sugarcane departments): −65.04 / −26.875 / −64.86 / −26.715 | 2025-09-23, 11:17 (Argentina time), height of the harvest | S2B_MSIL2A_20250923T141709_R010_T20JKR_20250923T194254 + …_T20JLR_… | 0.02 % / 0.17 % | two smoke columns from active burns and freshly burned plots. The VIIRS hotspots from that same afternoon (15:10, 23 detections inside the box) fall on the source of both columns (e.g. −64.937/−26.750, FRP 127 MW). |
| Final Entre Ríos zoom | **Paraná Delta islands (Victoria, Entre Ríos) opposite Rosario**: −60.75 / −33.05 / −60.40 / −32.70 | 2020-09-23, 11:00 | S2B_MSIL2A_20200923T140059_R067_T20HQJ_20200926T100603 | 11.2 % (the "clouds" are smoke) | several smoke columns over the islands and large areas already burned; Rosario on the left (label «ROSARIO»). VIIRS hotspots from that afternoon (14:03 and 15:43, 96 daytime detections inside the box). |
| Comarca Andina (unchanged since v4) | −71.80 / −42.62 / −71.05 / −41.75 | 2024-12-25 → 2025-04-06 → 2026-04-04 | 5 granules of orbit R053 per date | 0 % | before/after with the MODIS 2025 (amber) and 2026 (red) burn scars |

How the Tucumán dates were chosen: every harvest day (Jun–Oct) 2022–2025 with a Sentinel-2 overpass of < 10 % cloud over the sugarcane core was crossed against the number of VIIRS hotspots that day in the 12 departments (`data/tuc_cane_viirs_2022_2025.csv`). 2025-09-23 (96 hotspots in the sugarcane zone, 0–0.2 % cloud, full overpass) showed sharp smoke columns; 2025-08-27, 2024-08-27, 2024-08-12 and 2023-10-02 were discarded (partial overpass or no smoke visible at 10 m). The same was done for the Delta in Jun–Oct 2020: 2020-09-23 is the day with the most hotspots (129) among those with a usable image. Hotspots from those afternoons: `data/s2_day_hotspots.json`.

**Ground photo of Tucumán:** searched again (2026-10-13) on Wikimedia Commons («quema caña Tucumán», «quema de caña», «zafra Tucumán», «incendio cañaveral», «quema cañaveral», category Wildfires in Argentina) for a CC0/PD/CC BY photo verifiably taken in Tucumán: there is none (the only CC0 result of burned sugarcane is from Roquetas de Mar, Spain). That is why the v8 Queensland photo is removed and not replaced with another photo: Tucumán is shown with satellite imagery only.

**Honest caveat about the Tucumán zoom:** the image shows burns in a sugarcane department at the height of the harvest; true-color Sentinel-2 does not allow asserting plot by plot that every smoking field is sugarcane (Burruyacú also grows grains). That is why the label gives only place and date, and the figure (89 %) is about departments, not plots.

## Data

1. **NASA FIRMS — VIIRS S-NPP 375 m, yearly per-country archive (Argentina), 2012–2025.** `https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{YEAR}/viirs-snpp_{YEAR}_Argentina.csv`. Filter: `type == 0` and `confidence ∈ {n, h}` → 2,550,467 hotspots. The point map ends in December 2025.
2. **NASA MODIS MCD64A1 C6.1 — monthly burned area, 500 m** (Giglio et al.; DOI 10.5067/MODIS/MCD64A1.061), public University of Maryland SFTP (`fuoco.geog.umd.edu`), windows Win06/Win07, January 2012 – July 2026 with no missing months. A pixel is burned if `burndate > 0`; geodesic area by latitude; only inside the INDEC polygons.
3. **Boundaries:** INDEC provinces (2022 Census); Tucumán departments, IGN via georef (`https://infra.datos.gob.ar/georef/departamentos.geojson`).
4. **Sugarcane per department:** EEAOC, *Reporte Agroindustrial 370* (Jun 2026), Table 1: https://www.eeaoc.gob.ar/wp-content/uploads/2026/06/RA-370.pdf → 12 departments with > 5,000 ha (Leales, Cruz Alta, Burruyacú, Simoca, Monteros, Chicligasta, Río Chico, La Cocha, Famaillá, Graneros, Lules, J. B. Alberdi) = 99.85 % of the province's sugarcane.
5. **Causes 1993–2019:** Ministry of Environment (Ministerio de Ambiente), «Causas y cantidad de incendios por provincia» ("Fire causes and counts by province") (`data/incendios-cantidad-causas-provincia_1993-2019.csv`).
6. **Copernicus Sentinel-2 L2A**, see the table above.

## Flags (shown whenever a province is shown at a stop)
Tucumán (PD; official flag, Law 8.291), Entre Ríos (PD), Chubut (CC BY 4.0, Roxana Vanesa Jones / Gobierno del Chubut), Río Negro (CC BY 4.0, orig. Daniel Cuomo, vector Hellerick). Wikimedia Commons; details in `flags/flags.json`.

## v9 sources card (exact on-screen text, Spanish, 48 px)
```
FUENTES
Focos: NASA FIRMS, VIIRS 375 m, 2012–2025 (1 foco ≠ 1 incendio).
Área quemada: NASA MODIS MCD64A1, 500 m; cada píxel cuenta 1 vez.
Causas: Min. de Ambiente, 1993–2019. Caña: EEAOC. Límites: INDEC.
«Lo habitual»: mediana de los otros 13 años. Comarca: ene–mar.
Imágenes: datos Copernicus Sentinel-2 modificados (2020–2026).
Banderas: Wikimedia Commons (DP; CC BY 4.0: Chubut, R. V. Jones /
Gob. del Chubut; Río Negro, D. Cuomo y Hellerick).
Sol, Tierra, mapas, animación y música: hechos con código.
```

## Contest rules applied (2026 rules / Bases)
- «Historia visual … a través de una visualización única» ("a visual story … through a single visualization"): v9 is a single continuous map; the satellite images are drawn georeferenced inside that map and the camera dives into them; there are no cuts to photos or press cards.
- Rights: all visual material is Copernicus (open, with attribution), PD/CC BY flags with credit, or drawn with code from open data. No AI-generated image. No author name on screen.
- Video ≤ 1 minute: 59.77 s.

## Caveats
- A hotspot is a 375 m pixel with a thermal anomaly, not a fire and not an area.
- MODIS 500 m misses small burns and underestimates fires under canopy: the hectares are a floor.
- The 2025/2026 Comarca comparison uses a fixed box; changing the box changes the absolute values.
- Causes: the series ends in 2019, with 48 % of undetermined cause.
- Sentinel-2 passes mid-morning and VIIRS early afternoon: the hotspots drawn over the images are from the same afternoon, not the same instant.
