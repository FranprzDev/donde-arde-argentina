# Data layer

Each entry under `data:` in `story.yaml` has a `kind` and a `path` (relative to the story folder).

```yaml
data:
  events:                        # points with time (CSV, Parquet, point GeoJSON or NPZ)
    kind: points
    path: data/events.csv
    lon: longitude
    lat: latitude
    time: {column: date, unit: month, origin: "2015-01-01"}    # t = (fractional) months since origin; unit: month|day|year
    region: assign               # assigns each point to a region of map.regions (or the name of a column)
    filter: "mag >= 4.5"         # pandas query (optional)
    columns: [mag]               # extra columns available in select/replay/facts
    point_px: 5                  # point radius in design px (sparse data)
    legend: "1 punto = 1 evento" # on-screen text (Spanish in these stories): "1 dot = 1 event"
  area:                          # lat/lon raster (GeoTIFF, NPY/NPZ + grid {LON0, LAT1, D}, or pyramid l0..l5)
    kind: raster
    path: data/raw/area_pyr.npz
    grid: data/area_grid.json
    legend: "gris = área afectada"   # "grey = affected area"
  img_before: {kind: image, path: data/s2/zone_2024-01-10.jpg}  # jpg + a .json next to it with bbox, date and license
  table: {kind: table, path: data/values.csv}                   # DataFrame for facts.py
  extra: {kind: json, path: data/extra.json}
```

Map regions (`map.regions`): GeoJSON (or `.shp`, converted with `pyshp`) with an id property and a name
property. `map.shapes` adds extra named polygons (for `highlight: [{shape: ...}]`). `map.neighbours`: context.

## Included adapters (examples of open sources)

| Source | Command | Produces |
|---|---|---|
| NASA FIRMS (VIIRS/MODIS fire hotspots, yearly per-country archive, no key) | `python -m harness.data.firms download --country Chile --years 2020-2024 --out data/raw` · `... points --csv 'data/raw/*.csv' --origin 2020-01 --regions data/regions.geojson --out data/raw/points.npz` | Points NPZ (type 0, nominal/high confidence) with assigned region |
| NASA MODIS MCD64A1 (monthly burned area, 500 m; public UMD SFTP) | `python -m harness.data.modis fetch --bbox ... --windows Win06 Win07 --from 2020-01 --to 2024-12 --out data/raw/umd` · `... grid --src data/raw/umd --regions data/regions.geojson --out data/burned` | pyramid for `kind: raster` + `burned_stats.json` (ha per month and region, each pixel counted once) |
| Copernicus Sentinel-2 L2A (single-date true color, via Microsoft Planetary Computer) | `python -m harness.data.sentinel2 --search --bbox ... --from 2024-01-01 --to 2024-01-31` · `... --name data/s2/zone_2024-01-10 --bbox ... --date 2024-01-10 --width 1600` | `zone.jpg` + `zone.json` (bbox, date, tiles, cloud cover, license) |

Credits required in `sources`: "NASA FIRMS, VIIRS 375 m", "NASA MODIS MCD64A1", "Contains modified Copernicus
Sentinel-2 data (YEAR)" (on a Spanish-language screen: «Contiene datos Copernicus Sentinel-2 modificados (AÑO)»).
For other sources, whatever their license requires.

## A new loader

Write a function that leaves a file in one of the formats above (simplest) or add a `kind` in
`harness/data/loaders.py::load_dataset`. Keep the renderer unaware of where the data comes from.

## facts.py

```python
def compute(ctx):
    ev = ctx.data("events")             # Points: .lon .lat .t .region .cols[...] .select("expr") .binned(t0, t1, step)
    df = ctx.table("data/values.csv")   # pandas
    return {"total": len(ev), "share_top": ..., "ranking": [{"code": "66", "name": "Salta", "value": 262}, ...],
            "value_x": {"value": 12.5, "source": "data/values.csv, column X"}}   # with provenance (goes to facts.json)
```
