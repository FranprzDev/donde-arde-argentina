# Capa de datos

Cada entrada de `data:` en el `story.yaml` tiene un `kind` y un `path` (relativo a la carpeta de la historia).

```yaml
data:
  eventos:                       # puntos con tiempo (CSV, Parquet, GeoJSON de puntos o NPZ)
    kind: points
    path: data/eventos.csv
    lon: longitude
    lat: latitude
    time: {column: fecha, unit: month, origin: "2015-01-01"}   # t = meses (fraccionarios) desde origin; unit: month|day|year
    region: assign               # asigna cada punto a una región de map.regions (o el nombre de una columna)
    filter: "mag >= 4.5"         # pandas query (opcional)
    columns: [mag]               # columnas extra disponibles en select/replay/facts
    point_px: 5                  # radio del punto en px de diseño (datos dispersos)
    legend: "1 punto = 1 evento"
  area:                          # ráster lat/lon (GeoTIFF, NPY/NPZ + grid {LON0, LAT1, D}, o pirámide l0..l5)
    kind: raster
    path: data/raw/area_pyr.npz
    grid: data/area_grid.json
    legend: "gris = área afectada"
  img_antes: {kind: image, path: data/s2/zona_2024-01-10.jpg}   # jpg + .json al lado con bbox, fecha y licencia
  tabla: {kind: table, path: data/valores.csv}                  # DataFrame para facts.py
  extra: {kind: json, path: data/extra.json}
```

Regiones del mapa (`map.regions`): GeoJSON (o `.shp`, se convierte con `pyshp`) con una propiedad de id y otra de
nombre. `map.shapes` agrega polígonos extra con nombre (para `highlight: [{shape: ...}]`). `map.neighbours`: contexto.

## Adaptadores incluidos (ejemplos de fuentes abiertas)

| Fuente | Comando | Produce |
|---|---|---|
| NASA FIRMS (focos de calor VIIRS/MODIS, archivo anual por país, sin clave) | `python -m harness.data.firms download --country Chile --years 2020-2024 --out data/raw` · `... points --csv 'data/raw/*.csv' --origin 2020-01 --regions data/regiones.geojson --out data/raw/points.npz` | NPZ de puntos (tipo 0, confianza nominal/alta) con región asignada |
| NASA MODIS MCD64A1 (área quemada mensual, 500 m; SFTP público de UMD) | `python -m harness.data.modis fetch --bbox ... --windows Win06 Win07 --from 2020-01 --to 2024-12 --out data/raw/umd` · `... grid --src data/raw/umd --regions data/regiones.geojson --out data/burned` | pirámide para `kind: raster` + `burned_stats.json` (ha por mes y región, píxel contado una vez) |
| Copernicus Sentinel-2 L2A (color real de una fecha, vía Microsoft Planetary Computer) | `python -m harness.data.sentinel2 --search --bbox ... --from 2024-01-01 --to 2024-01-31` · `... --name data/s2/zona_2024-01-10 --bbox ... --date 2024-01-10 --width 1600` | `zona.jpg` + `zona.json` (bbox, fecha, tiles, nubosidad, licencia) |

Créditos que hay que poner en `sources`: «NASA FIRMS, VIIRS 375 m», «NASA MODIS MCD64A1», «Contiene datos Copernicus
Sentinel-2 modificados (AÑO)». Para otras fuentes, la que pida su licencia.

## Un loader nuevo

Escribí una función que deje un archivo en uno de los formatos de arriba (lo más simple) o agregá un `kind` en
`harness/data/loaders.py::load_dataset`. Mantené el renderer sin saber de dónde vienen los datos.

## facts.py

```python
def compute(ctx):
    ev = ctx.data("eventos")            # Points: .lon .lat .t .region .cols[...] .select("expr") .binned(t0, t1, step)
    df = ctx.table("data/valores.csv")  # pandas
    return {"total": len(ev), "share_top": ..., "ranking": [{"code": "66", "name": "Salta", "value": 262}, ...],
            "dato": {"value": 12.5, "source": "data/valores.csv, columna X"}}   # con procedencia (va a facts.json)
```
