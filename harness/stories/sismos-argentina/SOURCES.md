# Sources — Earthquakes in Argentina, 2015–2024 (example; on-screen text in Spanish)

| On-screen figure | Dataset | Published by | URL | License | Computation (`facts.py`) |
|---|---|---|---|---|---|
| Every dot, the total (869), the ranking, Salta (262), «3 de cada 10» ("3 in 10"), «más de la mitad, en el noroeste» ("more than half, in the northwest") | ANSS Comprehensive Earthquake Catalog (ComCat), M ≥ 4.5, 2015-01-01 to 2024-12-31, box −74/−56/−53/−21, downloaded 2026-10-13 | USGS | https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=2015-01-01&endtime=2025-01-01&minmagnitude=4.5&minlatitude=-56&maxlatitude=-21&minlongitude=-74&maxlongitude=-53 | Public domain (USGS) | only epicenters inside the provinces are kept; region = point in polygon |
| Provincial boundaries | Provinces (simplified to 0.01°) | IGN, via Georef | https://infra.datos.gob.ar/georef/provincias.geojson | CC BY 4.0 | — |
| Context land | Land 1:50m | Natural Earth | https://www.naturalearthdata.com | Public domain | clipped to the frame |

"Northwest" (Noroeste) = Salta, Jujuy, Tucumán, Catamarca, La Rioja and Santiago del Estero. The assignment uses simplified
boundaries: an earthquake very close to a border could fall in the neighbouring province (which is why Salta gives 262 and not an official figure).
