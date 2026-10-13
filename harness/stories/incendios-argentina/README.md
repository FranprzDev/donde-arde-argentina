# incendios-argentina — el video v9, portado al harness

Port de `pipeline/v9/render_v9.py` a la estructura genérica del harness: el mismo guion y los mismos números, escritos
como `story.yaml` (beats) + `facts.py` (cada número que sale en pantalla, con sus `assert`).

## Qué hay y qué no

En el repo: `story.yaml`, `facts.py`, banderas (`assets/flags/`) y los datos chicos que lee (`data/*.json`, `*.geojson`,
`*.csv`, metadatos de cada recorte Sentinel-2 en `data/s2/*.json`).

No está en el repo (pesado, ver `.gitignore`), hay que regenerarlo con el pipeline de la raíz antes de renderizar:

| Archivo | De dónde sale |
|---|---|
| `data/raw/points.npz` | `pipeline/prep_data.py` (NASA FIRMS VIIRS 2012–2025) |
| `data/raw/scar_all.npz`, `scar_er_2020.npz`, `scar_pat_2025.npz`, `scar_pat_2026.npz` | `pipeline/burn/fetch_umd.py` + `pipeline/v9/prep_burn.py` + `pipeline/v9/prep_assets.py` (MODIS MCD64A1) |
| `data/s2/tuc_2025-09-23.jpg`, `delta_2020-09-23.jpg` | `pipeline/v9/s2_date.py` |
| `data/s2/comarca_2024.jpg`, `comarca_2025.jpg`, `comarca_2026.jpg` | `pipeline/v9/s2_comarca.py` |

Copiá esos archivos a `data/raw/` y `data/s2/` de esta carpeta (los `.json` de `data/s2/` dicen fecha, producto y caja
de cada recorte).

## Correr

```bash
cd harness
pip install -r requirements.txt
python -m harness check stories/incendios-argentina            # tabla de tiempos + reglas (segundos)
python -m harness qa stories/incendios-argentina --preview     # capturas + contact sheet
python -m harness render stories/incendios-argentina --workers 2   # 1080p, ~5–6 min con 2 vCPU
```

## Diferencias con v9

- Titular del ranking acortado a «5 PROVINCIAS = 53 %» (con el de v9, la regla 0,35 s/palabra + 1 s pasaba de 60 s).
- Música procedural genérica del harness (mismos instrumentos y lógica de cues, no idéntica bit a bit).
- La leyenda muestra solo las capas de la escena actual.
- Duración total 59,63 s (v9: 59,77 s).
