# Datos de __NAME__

Poné acá **solo datos abiertos** y anotá cada uno en `../SOURCES.md` (quién lo publica, URL, fecha de descarga, licencia, filtros aplicados).

- Archivos chicos (CSV, GeoJSON, JSON) → se commitean.
- Crudos pesados (rásters, archivos de satélite, > 5 MB) → `data/raw/` (está en `.gitignore`) + un script `prepare.py` que los baja.
- `provincias_ign.geojson` y `contexto_tierra.geojson` son geometría de arranque (IGN CC BY 4.0 / Natural Earth DP): reemplazalas si tu mapa es otro.
