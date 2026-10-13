# ¿Dónde arde Argentina?

Código, datos y documentación del video de visualización de datos «¿Dónde arde Argentina?» (focos de calor y área quemada en la Argentina, 2012–2025).

Todo lo que aparece en el video se genera con código a partir de datos abiertos: el mapa, la animación, los números y la música. No hay imágenes generadas por IA. Este repositorio existe para que cualquiera pueda verificar cada cifra y reproducir el video.

## Qué hay acá

| Carpeta | Contenido |
|---|---|
| `pipeline/` | Scripts de descarga, procesamiento, render de cuadros, música y armado final |
| `data/` | Datos procesados chicos (CSV, JSON, GeoJSON) y estadísticas que lee el render |
| `docs/` | Guion con tiempos (`script.md`), fuentes y verificación de cada número (`sources.md`), descripción metodológica |
| `assets_meta/` | Licencia, autor y URL de cada foto y titular usado |
| `fonts/` | Tipografías abiertas (OFL) |

Los datos crudos pesados (archivo FIRMS, rásters MODIS, Sentinel-2) no están en el repo: se bajan con los scripts.

## Fuentes de datos

- **Focos de calor:** NASA FIRMS, VIIRS S-NPP 375 m, archivo país Argentina 2012–2025 (tipo 0, confianza nominal o alta).
- **Área quemada:** NASA MODIS MCD64A1 Colección 6.1 (500 m, mensual), servidor SFTP de la Universidad de Maryland.
- **Causas de incendios 1993–2019:** Ministerio de Ambiente de la Nación (datos abiertos).
- **Límites:** INDEC (provincias, radios del Censo 2022) e IGN.
- **Caña de azúcar en Tucumán:** EEAOC (departamentos cañeros).
- **Imágenes satelitales:** Copernicus Sentinel-2.
- Fotos, titulares de prensa y cifras puntuales: ver `docs/sources.md` y `assets_meta/`.

## Cómo se genera

```
pipeline/prep_data.py        # FIRMS VIIRS -> data/raw/points.npz + stats
pipeline/burn/fetch_umd.py   # descarga MCD64A1 (UMD)
pipeline/prep_burn.py        # área quemada por provincia, cicatrices
pipeline/causas.py           # causas (Min. Ambiente)
pipeline/prep_tucuman.py     # focos en la zona cañera durante la zafra
pipeline/prep_v2.py, prep_v4.py, prep_v7.py   # estadísticas y ranking provincial
pipeline/v8/render_v8.py # (v8, versión actual) imprime todos los números que salen en pantalla
pipeline/v8/build_v8.sh      # render de cuadros en paralelo + música + armado
```

Requisitos: Python 3.10+, numpy, scipy, Pillow, OpenCV, rasterio, pyproj, ffmpeg.

Ningún número está tipeado a mano en el render: todos se leen de los JSON de `data/`, y `render_v7.py` tiene un `assert` por cada redondeo verbal («casi», «más de») y por cada valor del ranking.

## Uso de IA

Un asistente de IA ayudó, bajo supervisión del autor, a escribir el código de procesamiento de datos, la animación y la música sintetizada por código, y a revisar las fuentes. No se usaron imágenes ni videos generados por IA.

## Licencia

Código: MIT. Datos derivados: siguen la licencia de cada fuente original (ver `docs/sources.md`).
