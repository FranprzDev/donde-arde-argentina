# Fuentes — Sismos en la Argentina, 2015–2024 (ejemplo)

| Dato en pantalla | Dataset | Publicado por | URL | Licencia | Cálculo (`facts.py`) |
|---|---|---|---|---|---|
| Cada punto, el total (869), el ranking, Salta (262), «3 de cada 10», «más de la mitad, en el noroeste» | ANSS Comprehensive Earthquake Catalog (ComCat), M ≥ 4,5, 2015-01-01 a 2024-12-31, caja −74/−56/−53/−21, descargado 13/10/2026 | USGS | https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=2015-01-01&endtime=2025-01-01&minmagnitude=4.5&minlatitude=-56&maxlatitude=-21&minlongitude=-74&maxlongitude=-53 | Dominio público (USGS) | se conservan solo epicentros dentro de las provincias; región = punto en polígono |
| Límites provinciales | Provincias (simplificadas a 0,01°) | IGN, vía Georef | https://infra.datos.gob.ar/georef/provincias.geojson | CC BY 4.0 | — |
| Tierra de contexto | Land 1:50m | Natural Earth | https://www.naturalearthdata.com | Dominio público | recortada al marco |

«Noroeste» = Salta, Jujuy, Tucumán, Catamarca, La Rioja y Santiago del Estero. La asignación usa límites simplificados:
un sismo muy cerca de un límite podría caer en la provincia vecina (por eso Salta da 262 y no un número oficial).
