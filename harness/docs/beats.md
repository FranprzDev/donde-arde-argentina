# Referencia de beats (escenas)

Generada desde los docstrings de `harness/beats/*.py` (`python -m harness beats` lista los tipos).

## Claves comunes a todos los beats

| clave | qué hace |
|---|---|
| `id` | nombre de la escena (aparece en errores y en el reporte) |
| `type` | tipo de beat |
| `duration` | `auto` (por defecto: lo justo para leer el texto) o segundos |
| `min_duration`, `pad` | piso de duración / segundos extra al final |
| `camera` | `{center: [lon, lat], zoom, anchor}` · `{fit: código(s) \| [lon0,lat0,lon1,lat1], size, anchor}` · `home` · `previous` (por defecto) |
| `transition` | `{mode: auto\|fly\|zoomto\|ease\|cut, dur}`: movimiento de cámara antes del texto |
| `text_delay` | segundos entre el fin del movimiento y el texto |
| `layers` | capas del mapa visibles (ver `harness/layers.py`): puntos `static\|lit\|burnout\|accumulate`, rásters `fill\|event\|outline`, imágenes, `kind: choropleth` |
| `highlight` | contornos con glow: `[{regions: [...]} \| {shape: nombre}, color, width, from}]` |
| `spotlight` | `{regions: [...], dim: 0.25}` oscurece el resto del mapa |
| `outline_all` | `dim` \| `glow`: todas las regiones contorneadas |
| `legend` | mostrar leyendas de capas (abajo a la derecha) |
| `flash`, `shake` | destello al revelar el texto (0–1) / temblor de cámara (px) |

Colores: cualquier clave de la paleta (`text`, `muted`, `accent`, `accent2`, `hot`, `red`, `ash`...) o un hex `"#RRGGBB"`.
Textos: cualquier string acepta `{fact|filtro}`; filtros: `int`, `dec:N`, `pct`, `pct:N`, `div:X`, `mul:X`, `round:N`, `floor:Q`, `upper`, `abs`.

## `globe_intro.py`

```text
globe_intro — Sun -> rays -> Earth -> region, then the flat map .

    - type: globe_intro
      target: all                 # region codes the sun rays land on ('all' = every region of map.regions)
      camera: home                # where the globe lands (default: map.home_camera)
      speed: 1.25                 # slow factor of the space travel
      title: ["SISMOS EN LA", "ARGENTINA"]     # hook, 1-2 lines (2nd line in accent), shown in the first second
      title_size: 132
      flat_text: "EL SOL SALE PARA TODOS."     # optional, while the rays keep landing on the flat map (heat wash)
      spark:                                   # optional turn: a single spark on the map + statement
        at: {first_point: events}              # or [lon, lat]
        lines:
          - {text: "TODO EMPIEZA ACÁ.", size: 116, color: accent}
          - {text: "{first_year}: EL PRIMER REGISTRO", size: 66}
        landing: 2.75                          # seconds from the spark to the end of the beat (next beat lands)
Rays: every streak from the Sun ends on a random point inside `target`.
```

## `timeline.py`

```text
timeline — a points timelapse with a sparkline and a big running label .

    - type: timeline
      data: events                   # a points dataset with a numeric time `t`
      range: [0, 120]                # data-time window (here: months since 2015-01)
      warp: [[0, 12, 0.05], [12, 108, 0.025], [108, 120, 0.04]]   # seconds per data unit by segment (or `duration`)
      bin: 1                         # sparkline bin width in data units (1 month)
      label: {origin: 2015, per: 12, final: "{year_first}–{year_last}"}   # big running year
      ticks: {every: 12, label_every: 36, origin: 2015}                    # axis ticks / labels
      camera: {center: [-64.2, -38.6], zoom: 30, anchor: [1290, 548]}
      transition: {mode: ease, dur: 3.9}      # e.g. a slow push-in during the whole timelapse
      glow_tau: 0.16
At the end of the beat every point is lit (a following beat can use the layer in mode lit / burnout).
```

## `cards.py`

```text
Map beats with text: big_number, statement, closing, map.

big_number — a number card over the map (optionally after flying the camera somewhere):

    - type: big_number
      camera: {fit: ["66"], size: [700, 640], anchor: [1440, 560]}    # or {center: [lon, lat], zoom: 230}
      transition: {mode: zoomto, dur: 1.0}         # camera move BEFORE the text (auto | fly | zoomto | ease | cut)
      head: "SALTA"                                # small mono header (optional), flags: [assets/flags/salta.png]
      number: "{share|pct} %"                      # big number; count_to: "{total}" makes it count up
      unit: "DE LOS SISMOS"
      subline: "EN UNA SOLA PROVINCIA"
      highlight: [{shape: my_zone, color: hot, width: 4}, {regions: ["66"], color: accent2}]
      spotlight: {regions: ["66"], dim: 0.25}      # dim the rest of the map
      replay: {data: events, select: "(region == '66')", time: "(t % 12) / 12", over: 2.4, gain: 0.5}   # time: optional 0..1 order
      layers: [...]                                # see harness/layers.py
      outline_all: dim                             # dim | glow: every region outlined

statement / closing — one to three lines of display type over the map. `closing` defaults: text after 0.8 s (the
map fills first), every region outlined with glow, no legend, big bell in the score.

    - type: closing
      lines: [{text: "MÁS DE LA MITAD,"}, {text: "EN EL NOROESTE.", color: accent, delay: 0.25}]
      size: 124
      layers: [{id: area_raster}, {id: events, mode: accumulate}]

map — no text, just layers/camera (a breathing beat or a camera move). Needs an explicit `duration`.
```

## `ranking.py`

```text
ranking — every region lights up on the map in rank order (choropleth sweep), then the top N with names, bars
and rank numbers on the map.

    - type: ranking
      rows: ranking_rows              # a fact: list of {code, name, value}, any order (sorted desc here)
      top: 5
      header: "{top_n} PROVINCIAS = {top5_pct} % DE LO QUEMADO"
      step: 0.045                     # seconds between regions in the sweep (bottom-up: last rank first)
      camera: {center: [-64.2, -38.6], zoom: 30, anchor: [1430, 548]}
      label_points: {"06": [-60.3, -36.9]}   # optional manual label positions for rank numbers on the map
Words counted for readability: header + the N names (rank digits are labels).
```

## `imagery.py`

```text
Beats with georeferenced imagery (e.g. Copernicus Sentinel-2 crops from harness.data.sentinel2).

satellite_zoom — the camera dives from the current map view INTO a real satellite image placed at its true bbox,
holds with a label (and optional same-day points / pins), then zooms back out:

    - type: satellite_zoom
      image: s2_city                     # data entry of kind image (jpg + sidecar json with bbox/date)
      labels: ["VALLE X", "{s2_city_date} · Sentinel-2"]
      points: day_points                 # optional points dataset drawn as glowing dots once the image fills the frame
      pins: [{lon: -65.41, lat: -24.79, label: "CIUDAD"}]
      zoom: 1.0                          # seconds of the dive
      zoom_out: 0.45                     # seconds of the way back (to the camera it came from)
      announce: 3.5                      # the image frame appears in place this many seconds before the beat (0 = off)
      fill_px: 900                       # image height on screen once zoomed (design px)

before_after — images of the same bbox replaced by a left-to-right wipe, with optional raster overlays and a
big-number card (same keys as big_number: head, number, count_to, unit, subline, flags):

    - type: before_after
      camera: {center: [-65.4, -24.8], zoom: 760, anchor: [1400, 560]}
      images: [img_before, img_mid, img_after]
      labels: ["ENE 2023", "ENE 2024", "ENE 2025"]        # one per image (labels: not counted as prose, keep short)
      wipes: [0.7, 1.85]                                   # seconds after the card starts
      overlays: [{data: change_a, color: accent2, at: 1.15, label: "■ A"}, {data: change_b, color: red, at: 2.3, label: "■ B"}]
      head: ..., number: ..., unit: ..., subline: ...
```

```text
sources — the credits card: every dataset, image and licence. Exempt from words/hold rules (meant to be paused),
    not from the minimum text size.

        - type: sources
          title: "FUENTES"
          lines: ["Sismos: USGS ComCat (dominio público).", "Límites: IGN.", "Mapas, animación y música: hechos con código."]
          duration: 3.0
```
