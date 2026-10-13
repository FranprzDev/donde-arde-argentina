# Data for __NAME__

Put **open data only** here and record each file in `../SOURCES.md` (publisher, URL, download date, license, filters applied).

- Small files (CSV, GeoJSON, JSON) → committed.
- Heavy raw files (rasters, satellite archives, > 5 MB) → `data/raw/` (it is in `.gitignore`) + a `prepare.py` script that downloads them.
- `provincias_ign.geojson` and `contexto_tierra.geojson` are starter geometry (IGN CC BY 4.0 / Natural Earth PD): replace them if your map is different.
