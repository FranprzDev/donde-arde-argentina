# ¿Dónde arde Argentina? — pipeline de datos

Este repositorio contiene únicamente el **pipeline de datos** (adquisición y preparación) de focos de incendio en Argentina.
El harness de video (render) vive en otro repositorio (`reelsmith`) y no forma parte de este.

## Estructura

- `pipeline/` — scripts de adquisición y preparación de datos.
- `data/` — datos procesados y auxiliares (geojson, csv, stats). `data/raw/` está ignorado (pesado).

## Flujo de datos

1. Descargar archivo histórico de NASA FIRMS (VIIRS S-NPP 375 m, Argentina, 2012–2025) y construir el parquet crudo:

   ```bash
   python pipeline/fetch_firms.py --years 2012-2025
   ```

2. Filtrar, asignar provincia (INDEC Censo 2022) y generar `points.npz` + `stats.json`:

   ```bash
   cd pipeline && python prep_data.py
   ```

   (o `python pipeline/prep_data.py` desde la raíz).

3. Datos de área quemada (MODIS MCD64A1): ver `pipeline/burn/` (`fetch_umd.py`, `fetch_mcd64.py`, `prep_burn.py`).

## Requisitos

Python 3.10+ con: `pandas`, `numpy`, `shapely`, `pyarrow`.
