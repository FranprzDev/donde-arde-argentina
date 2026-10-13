# Fuentes y verificación de cada número en pantalla — v9 «¿Dónde arde Argentina?»

Cadena de datos: `prep_*.py` → `data/*.json` → `render_v9.py`, con un `assert` por cada cifra, redondeo y palabra que depende de un dato (`python3 render_v9.py --nums` las imprime). v9 no agrega cifras nuevas; agrega dos imágenes Sentinel-2 y los focos VIIRS de esas mismas tardes. Consultas: 12/13-10-2026.

## Novedades v9 (13-10-2026)

1. **Intro:** todos los rayos del Sol (en el globo y en el mapa plano) aterrizan dentro de la Argentina y el trazo termina visiblemente ahí (en v8 los primeros rayos iban a puntos al azar de la cara iluminada y parecían errarle al país).
2. **Una sola visualización:** salen los 3 cortes a foto y los 4 titulares de prensa. Tucumán y Entre Ríos terminan con un **zoom dentro del mismo mapa** hasta una imagen satelital real Copernicus Sentinel-2, georreferenciada en su lugar, con los focos VIIRS de esa misma tarde encima. La Comarca Andina conserva su antes/después Sentinel-2 en el lugar.
3. **Sale la visualización de Corrientes 2022** (cicatriz resaltada bajo el titular de La Nación) y ese titular.
4. **Mucho menos texto:** ≤ ~12 palabras por momento, cuerpo ≥ 48 px, cada texto en pantalla ≥ 0,35 s por palabra + 1 s (mínimo 2,5 s; verificado con `assert` en el script). Salieron: la tarjeta «2.550.467 FOCOS», el segundo título, la fuente gris de las causas, las 24 filas del ranking y sus hectáreas, la línea de base gris de Tucumán, el encabezado del cierre.

## Cifras en pantalla (todas con `assert`)

| Pantalla v9 | Valor exacto | Cálculo / fuente |
|---|---|---|
| «9 DE CADA 10, CON CAUSA CONOCIDA» (bajo «LA CHISPA ES HUMANA.») | 90,2 % | 105.576 incendios de causa humana (negligencia + intencional) / 117.034 con causa conocida, 1993–2019 (5). En el 47,9 % no se determinó la causa (no se muestra en pantalla; consta en la descripción metodológica). |
| «26,6 MILLONES DE HA» / «QUEMADAS: CASI 1 DE CADA 10 DEL PAÍS» | 26.642.264 ha; 9,53 % | píxeles MODIS que ardieron al menos una vez 2012–2025 (cada píxel cuenta una vez) / 279.462.711 ha de las 24 jurisdicciones en la misma grilla (2)+(3) |
| «5 PROVINCIAS = 53 % DE LO QUEMADO» + 1 Formosa · 2 La Pampa · 3 Santa Fe · 4 Corrientes · 5 Santiago del Estero | 53,3 % (14.205.536 / 26.642.264 ha) | `data/ranking_v7.json`: Formosa 3.182.339 · La Pampa 3.041.100 · Santa Fe 2.837.162 · Corrientes 2.685.422 · Santiago del Estero 2.459.513 ha. Corrientes aparece sólo como nombre en este ranking. |
| «TUCUMÁN» / «89 % DE SUS FOCOS» / «EN ZONA CAÑERA, EN PLENA ZAFRA» | 89,17 % (53.625 de 60.136) | focos de Tucumán 2012–2025 en los 12 departamentos cañeros del EEAOC y en mayo–noviembre (1)+(3)+(4). Línea de base (fuera de pantalla en v9): esos departamentos son el 69,5 % de la provincia; con reparto parejo en superficie y en el año se esperaría ≈ 40 %. Advertencia: departamentos, no lotes. |
| «ENTRE RÍOS · 2020» / «37.506 FOCOS» | 37.506 | focos VIIRS 2020 dentro de Entre Ríos (INDEC); el render verifica que los puntos animados = 37.506 (1)+(3) |
| «CASI 7 VECES LO HABITUAL» | 6,96 | 37.506 / mediana de los otros 13 años 2012–2025 (5.391 focos). «Lo habitual» = esa mediana (aclarado en la tarjeta de fuentes). |
| «COMARCA ANDINA · 2026» / «42.000 HA» | 42.266 ha (se muestra redondeado hacia abajo al millar) | MODIS ene–mar 2026 dentro de la caja −71,80/−42,62/−71,05/−41,75 (2) |
| «7 VECES MÁS QUE EN 2025» | 7,01 (42.266 / 6.025 ha) | misma caja, ene–mar 2025 (2) |
| Cierre: «YA NO FALTAN DATOS. / FALTA RESPONSABILIDAD.» | — | conclusión editorial, sobre el mapa de todo lo que ardió 2012–2025 (cicatriz MODIS + los 2.550.467 focos VIIRS) |

## Imágenes satelitales en pantalla (todas Copernicus Sentinel-2 L2A, color verdadero TCI)

Licencia: datos Copernicus Sentinel de acceso libre, completo y abierto (Reglamento Delegado UE 1159/2013); atribución exigida: «Contiene datos modificados de Copernicus Sentinel [año]» — en la tarjeta: «Imágenes: datos Copernicus Sentinel-2 modificados (2020–2026)». Descarga: espejo Microsoft Planetary Computer, colección `sentinel-2-l2a`, recorte y reproyección a EPSG:4326 con `s2zoom/s2_date.py` (una sola fecha por imagen; no hay retoque, sólo remuestreo).

| Momento | Lugar / caja (lon/lat) | Fecha y hora de pasada | Producto(s) | Nubes | Qué se ve |
|---|---|---|---|---|---|
| Zoom final de Tucumán | **Burruyacú, Tucumán** (uno de los 12 departamentos cañeros del EEAOC): −65,04 / −26,875 / −64,86 / −26,715 | 23-09-2025, 11:17 (hora argentina), plena zafra | S2B_MSIL2A_20250923T141709_R010_T20JKR_20250923T194254 + …_T20JLR_… | 0,02 % / 0,17 % | dos columnas de humo de quemas activas y lotes recién quemados. Los focos VIIRS de esa misma tarde (15:10 h, 23 detecciones dentro de la caja) caen sobre el origen de ambas columnas (p. ej. −64,937/−26,750, FRP 127 MW). |
| Zoom final de Entre Ríos | **Islas del Delta del Paraná (Victoria, Entre Ríos) frente a Rosario**: −60,75 / −33,05 / −60,40 / −32,70 | 23-09-2020, 11:00 | S2B_MSIL2A_20200923T140059_R067_T20HQJ_20200926T100603 | 11,2 % (el «nublado» es humo) | varias columnas de humo sobre las islas y grandes superficies ya quemadas; Rosario a la izquierda (rótulo «ROSARIO»). Focos VIIRS de esa tarde (14:03 y 15:43 h, 96 detecciones diurnas dentro de la caja). |
| Comarca Andina (sin cambios desde v4) | −71,80 / −42,62 / −71,05 / −41,75 | 25-12-2024 → 06-04-2025 → 04-04-2026 | 5 granulos de la órbita R053 por fecha | 0 % | antes/después con las cicatrices MODIS 2025 (ámbar) y 2026 (rojo) |

Cómo se eligieron las fechas de Tucumán: se cruzaron todos los días de zafra (jun–oct) 2022–2025 con pasada Sentinel-2 de < 10 % de nubes sobre el núcleo cañero contra la cantidad de focos VIIRS ese día en los 12 departamentos (`data/tuc_cane_viirs_2022_2025.csv`). El 23-09-2025 (96 focos en la zona cañera, 0–0,2 % de nubes, pasada completa) mostró columnas de humo nítidas; 2025-08-27, 2024-08-27, 2024-08-12 y 2023-10-02 se descartaron (pasada parcial o sin humo visible a 10 m). Para el Delta se hizo lo mismo en jun–oct 2020: 23-09-2020 es el día con más focos (129) entre los de imagen utilizable. Focos de esas tardes: `data/s2_day_hotspots.json`.

**Foto de tierra de Tucumán:** se buscó otra vez (13-10-2026) en Wikimedia Commons («quema caña Tucumán», «quema de caña», «zafra Tucumán», «incendio cañaveral», «quema cañaveral», categoría Wildfires in Argentina) una foto CC0/DP/CC BY verificablemente tomada en Tucumán: no hay ninguna (el único resultado de caña quemada con CC0 es de Roquetas de Mar, España). Por eso la foto de Queensland de v8 sale y no se reemplaza por otra foto: Tucumán se muestra sólo con satélite.

**Advertencia honesta sobre el zoom de Tucumán:** la imagen muestra quemas en un departamento cañero en plena zafra; Sentinel-2 en color verdadero no permite asegurar lote por lote que cada campo humeante sea caña (Burruyacú también tiene granos). Por eso el rótulo dice sólo lugar y fecha, y la cifra (89 %) habla de departamentos, no de lotes.

## Datos

1. **NASA FIRMS — VIIRS S-NPP 375 m, archivo anual por país (Argentina), 2012–2025.** `https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{AÑO}/viirs-snpp_{AÑO}_Argentina.csv`. Filtro: `type == 0` y `confidence ∈ {n, h}` → 2.550.467 focos. El mapa de puntos termina en diciembre de 2025.
2. **NASA MODIS MCD64A1 C6.1 — área quemada mensual, 500 m** (Giglio et al.; DOI 10.5067/MODIS/MCD64A1.061), SFTP público de la Universidad de Maryland (`fuoco.geog.umd.edu`), ventanas Win06/Win07, enero 2012 – julio 2026 sin meses faltantes. Píxel quemado si `burndate > 0`; área geodésica por latitud; sólo dentro de los polígonos INDEC.
3. **Límites:** provincias INDEC (Censo 2022); departamentos de Tucumán, IGN vía georef (`https://infra.datos.gob.ar/georef/departamentos.geojson`).
4. **Caña por departamento:** EEAOC, *Reporte Agroindustrial 370* (jun-2026), Tabla 1: https://www.eeaoc.gob.ar/wp-content/uploads/2026/06/RA-370.pdf → 12 departamentos con > 5.000 ha (Leales, Cruz Alta, Burruyacú, Simoca, Monteros, Chicligasta, Río Chico, La Cocha, Famaillá, Graneros, Lules, J. B. Alberdi) = 99,85 % de la caña de la provincia.
5. **Causas 1993–2019:** Ministerio de Ambiente, «Causas y cantidad de incendios por provincia» (`data/incendios-cantidad-causas-provincia_1993-2019.csv`).
6. **Copernicus Sentinel-2 L2A**, ver tabla de arriba.

## Banderas (cada vez que se muestra una provincia en una parada)
Tucumán (DP; bandera oficial, Ley 8.291), Entre Ríos (DP), Chubut (CC BY 4.0, Roxana Vanesa Jones / Gobierno del Chubut), Río Negro (CC BY 4.0, orig. Daniel Cuomo, vector Hellerick). Wikimedia Commons; detalle en `flags/flags.json`.

## Tarjeta de fuentes v9 (texto exacto, 48 px)
```
FUENTES
Focos: NASA FIRMS, VIIRS 375 m, 2012–2025 (1 foco ≠ 1 incendio).
Área quemada: NASA MODIS MCD64A1, 500 m; cada píxel cuenta 1 vez.
Causas: Min. de Ambiente, 1993–2019. Caña: EEAOC. Límites: INDEC.
«Lo habitual»: mediana de los otros 13 años. Comarca: ene–mar.
Imágenes: datos Copernicus Sentinel-2 modificados (2020–2026).
Banderas: Wikimedia Commons (DP; CC BY 4.0: Chubut, R. V. Jones /
Gob. del Chubut; Río Negro, D. Cuomo y Hellerick).
Sol, Tierra, mapas, animación y música: hechos con código.
```

## Reglas del concurso aplicadas (Bases 2026)
- «Historia visual … a través de una visualización única»: v9 es un solo mapa continuo; las imágenes satelitales se dibujan georreferenciadas dentro de ese mapa y la cámara entra en ellas; no hay cortes a fotos ni tarjetas de prensa.
- Derechos: todo el material visual es Copernicus (abierto, con atribución), banderas DP/CC BY acreditadas, o dibujado con código a partir de datos abiertos. Ninguna imagen generada por IA. Sin nombre del autor en pantalla.
- Video ≤ 1 minuto: 59,77 s.

## Advertencias
- Un foco es un píxel de 375 m con anomalía térmica, no un incendio ni una superficie.
- MODIS 500 m omite quemas chicas y subestima incendios bajo dosel: las hectáreas son un piso.
- La comparación 2025/2026 de la Comarca usa una caja fija; cambiar la caja cambia los valores absolutos.
- Causas: serie que termina en 2019, con 48 % sin causa determinada.
- Sentinel-2 pasa a media mañana y VIIRS a primera hora de la tarde: los focos dibujados sobre las imágenes son de la misma tarde, no del mismo instante.
