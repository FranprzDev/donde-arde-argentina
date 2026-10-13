# data-video — harness para videos de historias con datos

Un `story.yaml` + datos abiertos → un video corto (≤ 60 s), legible en el celular, con cada número verificable.
Todo se dibuja con código: mapa, globo, animación, tipografía y música. **Sin imágenes generadas por IA.**

Pensado para que lo use una persona o un agente de código (Codex, Claude Code, Cursor): ver [`AGENTS.md`](AGENTS.md).

![estilo: fondo oscuro, glow, tipografía condensada, paleta naranja](docs/img/contact_sheet_sismos.jpg)

## Inicio rápido

```bash
cd harness
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # Python 3.10+ y ffmpeg en el PATH

make check STORY=stories/sismos-argentina/story.yaml   # valida YAML, calcula facts.json, chequea reglas de lectura
make qa    STORY=stories/sismos-argentina/story.yaml   # capturas + contact sheet + hoja "celular" + reporte de tiempos
make video STORY=stories/sismos-argentina/story.yaml   # render completo → stories/sismos-argentina/build/sismos-argentina.mp4
make test                                              # pytest: renderiza el ejemplo chico de punta a punta
```

Sin `make`: `python -m harness check|qa|render|still <story>` · `python -m harness new "Mi historia"` · `python -m harness beats`.

Con Docker: `docker build -t data-video . && docker run --rm -v "$PWD:/app" data-video make video STORY=stories/sismos-argentina/story.yaml`

El ejemplo **`stories/sismos-argentina/`** (sismos M ≥ 4,5 con epicentro en la Argentina, 2015–2024, USGS) trae sus datos
en el repo, no usa red y renderiza en ~1 minuto a 960×540.

## Cómo funciona

```
data/ (abiertos) ──► facts.py ──► build/facts.json ──► story.yaml (beats con {placeholders}) ──► chequeo de reglas
                                                                                                    │
         build/<slug>.mp4 ◄── mux + −14 LUFS ◄── música procedural ◄── cuadros en paralelo ◄────────┘
```

1. **Datos** (`data:` en el YAML): loaders para CSV / Parquet / GeoJSON / shapefile (puntos, regiones), rásters
   (GeoTIFF/NPY), imágenes georreferenciadas. Adaptadores de ejemplo: NASA FIRMS (focos), MODIS MCD64A1 (área
   quemada), Copernicus Sentinel-2 (imágenes de una fecha) — ver [`docs/data.md`](docs/data.md).
2. **Facts**: `facts.py` calcula *todos* los números que salen en pantalla → `build/facts.json`. El YAML los usa con
   `{nombre|filtro}` y cada redondeo verbal («casi», «más de la mitad») lleva un `assert`. Un número tipeado a mano en
   un texto **frena el build**.
3. **Beats** (escenas): `globe_intro`, `timeline`, `big_number`, `ranking`, `satellite_zoom`, `before_after`,
   `statement`, `closing`, `map`, `sources` → [`docs/beats.md`](docs/beats.md).
4. **Reglas de lectura, en código** (el build falla con un mensaje claro): texto ≥ 48 px (a 1080p), ≤ 12 palabras a la
   vez por escena, cada texto en pantalla ≥ 0,35 s/palabra + 1 s (mín. 2,5 s), duración total ≤ `max_duration`.
5. **Audio**: música sintetizada con numpy a partir de los tiempos de cada escena + normalización a −14 LUFS
   (true peak ≤ −1,5 dBTP) con ffmpeg.
6. **QA**: contact sheet, hoja tamaño celular, reporte de tiempos, duración y loudness del mp4.

## Estructura

```
harness/            el paquete (core/ dibujo y mapa · beats/ escenas · data/ loaders y adaptadores · audio/ · qa · cli)
stories/            una carpeta por historia: story.yaml, facts.py, data/, SOURCES.md, build/ (no se commitea)
templates/story/    lo que copia `harness new`
docs/               beats.md · data.md · style-guide.md · adding-a-beat.md
tests/              pytest (reglas + render del ejemplo)
```

## Reglas del proyecto (resumen de AGENTS.md)

- Solo **datos abiertos**, con fuente y licencia en `SOURCES.md` y en la tarjeta final.
- **Ningún número inventado** ni tipeado a mano: todo sale de `facts.py` y tiene `assert`.
- **Sin imágenes ni video generados por IA** (para concursos suele estar prohibido). Fotos/satélite solo con licencia abierta y crédito.
- No se commitean videos ni datos crudos pesados (`.gitignore`).

Licencia: MIT (código). Los datos de ejemplo mantienen su licencia (ver `stories/*/SOURCES.md`).
