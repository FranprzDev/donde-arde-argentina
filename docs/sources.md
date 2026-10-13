# Fuentes y verificación de cada número en pantalla — v8 «¿Dónde arde Argentina?»

Cadena de datos sin cambios respecto de v7 (`prep_*.py` → `data/*.json` → `render_v8.py`, con un `assert` por cada cifra y redondeo; `python3 render_v8.py --nums` las imprime). v8 no agrega ninguna cifra nueva: las de Entre Ríos ya estaban calculadas y verificadas desde v3–v5 (`data/stats_v4.json`). Consultas: 12/13-10-2026.

## Novedades v8 (13-10-2026)

**Estructura:** mapa nacional (focos, 26,6 M ha, ranking) → 3 paradas «mapa → foto real»: Tucumán (caña), Entre Ríos / Delta 2020 (pastizal), Comarca Andina (bosque) → cierre con el país entero y todo lo quemado.

**Cifras en pantalla en v8** (todas con `assert`):

| Pantalla v8 | Valor exacto | Cálculo / fuente |
|---|---|---|
| «2.550.467 FOCOS» | 2.550.467 | FIRMS VIIRS 2012–2025 (1) |
| «26,6 MILLONES DE HA» / «CASI 1 DE CADA 10 HECTÁREAS DEL PAÍS» | 26.642.264 ha; 9,53 % | MODIS, ardió al menos una vez (2)+(3) — ver v7 |
| Ranking top 5 / «53 %» | ver v7 | `data/ranking_v7.json` |
| «TUCUMÁN · … 89 % DE SUS FOCOS» / gris «Esos departamentos = 69 % de la provincia» | 89,2 % (53.625 / 60.136); 69,5 % | ver v4/v7 (4) |
| **«ENTRE RÍOS · ISLAS DEL DELTA · 2020» / «37.506 FOCOS»** | 37.506 | focos VIIRS 2020 dentro de Entre Ríos (INDEC); el render verifica además que la cantidad de puntos animados = 37.506 (`assert len(EV_ER) == ER_N`) (1)+(3) |
| **«CASI 7 VECES SU MEDIANA 2012–2025»** | 6,96 | 37.506 / mediana de los otros 13 años 2012–2025 (5.391 focos); se muestra la referencia más larga y conservadora (con 2012–2019 daría 10,8×) (1)+(3) |
| «COMARCA ANDINA · 42.000 HA EN 2026» / «7 VECES MÁS QUE EN 2025» | 42.266 ha; 7,01 | MODIS ene–mar, caja de la Comarca (2) |
| Cierre «TODO LO QUE ARDIÓ · 2012–2025» | — | sin cifra: cicatriz MODIS 2012–2025 (`assets/scar_all.npz`, de `data/scar_count.npy`, sólo meses ≤ 2025) + los 2.550.467 focos VIIRS 2012–2025 |

**Salieron de pantalla en v8:** «SABEMOS DÓNDE Y CUÁNDO ARDE.» y su nota «Norte: ago–sep · Cordillera: dic–mar» (cifras de respaldo abajo, sin cambios), «NO QUEMES. SI VES FUEGO, LLAMÁ AL 911.» y la línea «Avisar es obligatorio (Ley 26.815)», la parada Corrientes («CASI 1 MILLÓN DE HA», «MÁS DE 46 CIUDADES DE BUENOS AIRES»; siguen verificadas abajo), «2025: 166 CASAS PERDIDAS Y 1 MUERTO», «Quemar está prohibido (Ley 6253)», y las 3 fotos chicas de v7 (Landsat 9 Corrientes, brigadistas santafesinos, «Restos de incendios»).

**Por qué Entre Ríos / Delta como parada de pastizal (y no Corrientes o La Pampa):** es la única de las tres con foto abierta (CC BY 4.0) de un pastizal ardiendo tomada en el mismo lugar y año que los datos (Delta del Paraná, 2020), cifra fuerte y propia (37.506 focos, casi 7 veces su mediana) y un titular verificado sobre el mismo evento (Clarín, «8 mil quemas de pastizales en las islas de Entre Ríos»). Corrientes 2022 sólo tenía imagen satelital (Landsat), y La Pampa no tenía foto ni titular.

### Titulares en pantalla (citas textuales re-tipografiadas, sin capturas ni logos; art. 10, Ley 11.723)

| Momento | Medio · fecha | Se muestra | Titular completo | URL |
|---|---|---|---|---|
| Cicatriz nacional (16,4–18,5 s), pin Esteros del Iberá; cicatriz Corrientes ene–feb 2022 resaltada | La Nación · 15/02/2022 | «Tragedia ecológica en Corrientes: los incendios llegaron a los Esteros del Iberá…» | «… y amenazan su amplia biodiversidad» | https://www.lanacion.com.ar/sociedad/tragedia-ecologica-en-corrientes-los-incendios-llegaron-a-los-esteros-del-ibera-y-amenazan-su-amplia-nid15022022/ |
| Tucumán (29,7–31,9 s), pin autopista a Famaillá | La Gaceta · 28/06/2025 | completo | «Choques, humo y gritos: el horror en la autopista a Famaillá» | https://www.lagaceta.com.ar/nota/1090058/seguridad/choques-humo-gritos-horror-autopista-famailla.html |
| Entre Ríos (36,1–38,4 s), pin Rosario | Clarín · 27/07/2020 | «Rosario irrespirable por el humo…» | «… en el año detectaron 8 mil quemas de pastizales en las islas de Entre Ríos» | https://www.clarin.com/sociedad/rosario-irrespirable-humo-ano-detectaron-8-mil-quemas-pastizales-islas-rios_0_D3R6eQaiM.html |
| Comarca (43,6–45,8 s), pin El Bolsón | Infobae · 01/02/2025 | completo | «Un hombre murió en los incendios en El Bolsón y el fuego sigue avanzando» | https://www.infobae.com/sociedad/2025/02/02/un-hombre-murio-en-los-incendios-en-el-bolson-y-el-fuego-sigue-avanzando/ |

Tarjetas: `assets/hl_0..hl_3.png` (generadas por `prep_assets.py` de v4: medio + fecha en mono 36 px, cita en Inter 40 px). Datos: `headlines/selected.json`.

### Fotos en pantalla (corte a pantalla completa, 1,6 s cada una) — `photos/v8/credits.json`

| Momento | Archivo (Wikimedia Commons) | Autor | Licencia | Pie en pantalla | URL |
|---|---|---|---|---|---|
| Tras Tucumán | Cane fire in the Burdekin.jpg (09-08-2009) | cytoon (Flickr) | CC BY 2.0 | «Quema de caña antes de la cosecha · foto: Queensland, Australia» | https://commons.wikimedia.org/wiki/File:Cane_fire_in_the_Burdekin.jpg |
| Tras Entre Ríos | Incendio en delta del paraná 2020 - Parques Nacionales.jpg (01-08-2020) | Ministerio de Ambiente de la Nación (argentina.gob.ar/ambiente/conciencia-ambiental/incendios-delta) | CC BY 4.0 | «Islas del Delta del Paraná · 2020» | https://commons.wikimedia.org/wiki/File:Incendio_en_delta_del_paran%C3%A1_2020_-_Parques_Nacionales.jpg |
| Tras la Comarca | Foco de incendio 2.jpg (25-01-2026; «incendio forestal de interfase activo en la zona de Puerto Patriada») | CatrielGB | CC BY-SA 4.0 | «Puerto Patriada, Chubut · enero de 2026» + bandera del Chubut | https://commons.wikimedia.org/wiki/File:Foco_de_incendio_2.jpg |

- **Caña:** se buscó en Commons una quema de caña en Tucumán/Argentina con licencia abierta («quema de caña», «zafra Tucumán», «cañaveral fuego», «quema cañaveral», etc.): no hay. Se eligió la mejor CC BY (sin personas identificables) y el pie declara el lugar real (Australia) para no sugerir que es Tucumán. Alternativas CC BY descartadas: CSIRO ScienceImage 1559 (persona en primer plano), «Cane fire in Australia» (persona), «Burning sugar cane field in Queensland a» (sólo humo).
- **Bosque:** no se encontró foto DP ni CC BY de un incendio forestal activo en la Comarca 2025–2026 (búsqueda ya documentada en v4); se usa CC BY-SA 4.0 con atribución. La brigadista del Delta está de espaldas; ninguna foto muestra caras identificables. Ninguna imagen es generada por IA.
- **Recorte:** sólo encuadre 16:9 y un oscurecido inferior para el texto; sin otra manipulación.

### Banderas (cada vez que se muestra una provincia en una parada)
Tucumán (DP), Entre Ríos (DP), Chubut (CC BY 4.0, Roxana Vanesa Jones / Gobierno del Chubut), Río Negro (CC BY 4.0, orig. Daniel Cuomo, vector Hellerick); Wikimedia Commons, ver `flags/flags.json`. Bandera del Chubut también en el pie de la foto de Puerto Patriada.

### Tarjeta de fuentes v8 (texto exacto, 9 líneas)
1. Focos: NASA FIRMS, VIIRS S-NPP 375 m, 2012–2025. Un foco no es un incendio.
2. Área quemada: MODIS MCD64A1 C6.1, 500 m (NASA, UMD); cada píxel cuenta una vez.
3. Causas 1993–2019: Min. de Ambiente. Caña: EEAOC. Límites: INDEC, IGN. País: 279,5 M ha.
4. Titulares (citas textuales): Clarín 27/07/2020 · La Nación 15/02/2022 ·
5. Infobae 01/02/2025 · La Gaceta 28/06/2025. Satélite: Copernicus Sentinel-2 (2024–2026).
6. Fotos (Wikimedia Commons): cañaveral, cytoon/Flickr (CC BY 2.0); pastizal, Ministerio
7. de Ambiente (CC BY 4.0); bosque, CatrielGB (CC BY-SA 4.0).
8. Banderas: Wikimedia Commons (DP; CC BY 4.0: Chubut, R. V. Jones / Gob. del Chubut;
9. Río Negro, D. Cuomo y Hellerick). Sol, Tierra, mapas, animación y música: con código.

Los nombres que aparecen son sólo los créditos que exigen las licencias (fotógrafos y autores de banderas); el autor del video no aparece en pantalla (regla de seudónimo).

---

## (v7 y anteriores — respaldo)

Ningún número está tipeado a mano en el render. Cadena: `../prep_data.py` → `../data/points.npz`; `causas.py` + `prep_v2.py` → `data/stats_v2.json`; `burn/fetch_umd.py` → `burn/umd/*.npz` → `prep_burn.py` → `data/burn_stats.json` + rásters; `prep_tucuman.py` → `data/tucuman_stats.json`; `prep_v4.py` junta todo en `data/stats_v4.json`; `prep_v7.py` → `data/ranking_v7.json` (ranking provincial, v7: superficie distinta); `render_v7.py` lee todo y tiene un `assert` por cada redondeo verbal («casi», «más de») y por cada valor del ranking. `python3 render_v7.py --nums` imprime todos. Única excepción: cifras humanas de la Patagonia (casas, muerto, ha oficiales de 2026), que no salen de un dataset: están en `data/patagonia_facts.json` con su URL y cita textual. Consultas: 12/13-10-2026.

## Novedades v7 (13-10-2026) — cambia la definición del área quemada

**Definición única en todo el video: «superficie que ardió al menos una vez, 2012–2025».** Cada píxel MODIS MCD64A1 de 500 m cuenta **una sola vez** si se quemó en cualquier mes de 2012–2025 (`data/scar_count.npy` > 0), con área geodésica por latitud, asignado a su jurisdicción con los límites INDEC. v6 sumaba re-quemas (un humedal que arde 5 años contaba 5 veces), lo que inflaba a Santa Fe (islas del Paraná) y Formosa (bañados). Script `prep_v7.py` → `data/ranking_v7.json`; `assert`: la suma de las 24 jurisdicciones = total nacional de píxeles quemados.

| Pantalla v7 | Valor exacto | Cálculo |
|---|---|---|
| «ARDIÓ AL MENOS UNA VEZ · MODIS 2012–2025» / «26,6 MILLONES DE HA» | 26.642.264 ha | píxeles con al menos un mes quemado 2012–2025, suma de áreas |
| «= CASI 1 DE CADA 10 HECTÁREAS DEL PAÍS» | 9,53 % | 26.642.264 / 279.462.711 ha (superficie de las 24 jurisdicciones INDEC en la misma grilla) |
| Encabezado del ranking «SUPERFICIE QUE ARDIÓ AL MENOS UNA VEZ · MODIS 2012–2025» | — | misma definición |
| 1 FORMOSA 3,2 M HA | 3.182.339 ha (42,0 % de la provincia) | |
| 2 LA PAMPA 3,0 M HA | 3.041.100 ha (21,3 %) | |
| 3 SANTA FE 2,8 M HA | 2.837.162 ha (21,3 %) | |
| 4 CORRIENTES 2,7 M HA | 2.685.422 ha (30,1 %) | «CORRIENTES · PUESTO 4» sigue siendo correcto con la nueva definición |
| 5 SANTIAGO DEL ESTERO 2,5 M HA | 2.459.513 ha (18,2 %) | |
| «5 PROVINCIAS = 53 % DE TODO LO QUEMADO» | 53,3 % | 14.205.536 / 26.642.264 |
| (resto) 6 Chaco 2.393.250 · 7 Salta 1.614.248 · 8 San Luis 1.491.863 · 9 Río Negro 1.309.556 · 10 Córdoba 1.007.091 · 11 Buenos Aires 986.381 · 12 Mendoza 845.518 · 13 Entre Ríos 684.995 · 14 Tucumán 566.207 · 15 Chubut 319.771 · … · 24 CABA 0 | | |

- Con la definición v6 (re-quemas) el top 5 era Santa Fe, Formosa, Santiago del Estero, Corrientes, La Pampa = 60,3 % de 44.093.983 ha. Ese total («44 MILLONES») **ya no sale en pantalla**; queda abajo como respaldo.
- **«= 8 CANCHAS DE FÚTBOL POR MINUTO» (v6), verificado y retirado:** 44.093.983 ha / 0,714 ha (cancha 105 × 68 m) = 61.756.279 canchas; 1-1-2012 a 1-1-2026 = 5.114 días (4 bisiestos) = 7.364.160 min → **8,39 canchas/min** (una cada 7,15 s). La cuenta era correcta, pero se apoya en el total con re-quemas; con la superficie distinta daría 5,07/min, una tasa difícil de explicar en una línea. Se reemplazó por la referencia explícita al país (9,5 %).
- **Tucumán, línea de base nueva (gris):** «Esos departamentos = 69 % de la provincia»: los 12 departamentos cañeros del EEAOC suman 15.687 km² de 22.583 km² (límites IGN/georef) = 69,5 %. El 89 % de los focos cae ahí y en mayo–noviembre (7 de 12 meses); si los focos se repartieran parejo en superficie y en el año, se esperaría ≈ 69,5 % × 7/12 ≈ 40 %. La nota «Quemar está prohibido (Ley 6253)» pasa a una segunda línea.
- Tarjeta de fuentes: «Ranking y total: superficie que ardió al menos una vez, 2012–2025.» y «Capital: límite IGN, 20.562 ha. País: 279,5 M ha (INDEC); cada píxel cuenta una vez.» (sale la línea de la cancha FIFA).

## Novedades v6 (13-10-2026)

**Qué salió de pantalla en v6 (menos texto):** la parada Entre Ríos 2020, la tarjeta de causas (sus cifras pasan a la introducción), los 4 titulares de prensa, la foto del Delta (Min. de Ambiente), las notas grises «27 M ha distintas…», «Área quemada MODIS: 959.000 ha…», «Mediana de los otros 13 años…» y los rótulos «SEQUÍA (SMN)» / «PARANÁ EN BAJANTE (INA)». Siguen documentados abajo como respaldo, pero **no se muestran**.

### Ranking provincial (v6; reemplazado en v7, ver arriba)
- **Métrica en pantalla v6:** «HECTÁREAS QUEMADAS POR PROVINCIA · MODIS 2012–2025» = suma de los píxeles MCD64A1 quemados cada mes de 2012–2025 dentro de cada jurisdicción (límites INDEC), **contando re-quemas** (misma definición que los «44 millones» nacionales; la suma de las 24 provincias = 44.093.983 ha, verificado con `assert`). No usa focos VIIRS: un foco no es una hectárea.
- Script `prep_v6.py` → `data/ranking_v6.json`. Datos de entrada ya existentes: `data/burn_stats.json` (`by_prov_total_ha_2012_2025`, de `prep_burn.py`), `data/scar_count.npy`, `../data/points.npz`.
- Las 24 jurisdicciones pasan en ~3 s (de la 24.ª a la 1.ª); luego quedan las 5 primeras:

| Puesto | Provincia | Ha quemadas 2012–2025 (con re-quemas) | En pantalla | Ha distintas | % de su superficie quemada al menos una vez | Focos VIIRS 2012–2025 (puesto) |
|---|---|---|---|---|---|---|
| 1 | Santa Fe | 7.055.951 | 7,1 M HA | 2.837.162 | 21,3 % | 370.502 (2.º) |
| 2 | Formosa | 6.940.269 | 6,9 M HA | 3.182.339 | 42,0 % | 386.790 (1.º) |
| 3 | Santiago del Estero | 4.504.813 | 4,5 M HA | 2.459.513 | 18,2 % | 240.553 (5.º) |
| 4 | Corrientes | 4.318.744 | 4,3 M HA | 2.685.422 | 30,1 % | 280.336 (3.º) |
| 5 | La Pampa | 3.783.631 | 3,8 M HA | 3.041.100 | 21,3 % | 85.771 (8.º) |
| … | Tucumán (11.º) | 1.202.841 | — | 566.207 | 25,0 % | 60.136 (12.º; 4.º en focos por km²) |
| … | Río Negro (9.º) / Chubut (17.º) | 1.420.534 / 331.168 | — | | | |

- «5 PROVINCIAS = 60 % DE TODO LO QUEMADO»: 26.603.408 / 44.093.983 = 60,3 %. (Por focos VIIRS, las 5 primeras —Formosa, Santa Fe, Corrientes, Chaco, Santiago del Estero— suman 59,9 % de los 2.550.467 focos: el patrón coincide con otra métrica y otro sensor.)
- «CORRIENTES · PUESTO 4»: su puesto en ese ranking 2012–2025 (no en 2022).
- Advertencia: MODIS 500 m es un piso (omite quemas chicas y bajo dosel); sumar re-quemas favorece humedales y pastizales que arden casi todos los años (Delta/islas del Paraná en Santa Fe y Entre Ríos, bañados de Formosa). Por superficie distinta, el orden cambia (Formosa 1.ª, La Pampa 2.ª).

### Introducción (nuevo): «EL SOL CALIENTA. / LA CHISPA ES HUMANA.»
- Sol, rayos, reflejos, Tierra y mapa: dibujados con código (numpy/OpenCV); ninguna imagen generada ni manipulada por IA. Es una **analogía**: el calor es contexto; no se afirma que el sol cause incendios.
- «EN 9 DE CADA 10 INCENDIOS CON CAUSA CONOCIDA» + «Ministerio de Ambiente, 1993–2019»: 105.576 incendios de causa humana (negligencia + intencional) / 117.034 con causa conocida = **90,2 %** (dataset 5, sin cambios desde v3; en el 47,9 % no se determinó la causa: ese dato ya no se muestra, sigue en esta tabla).
- Respaldo oficial adicional (no se muestra en pantalla, coherente con la cifra mostrada, que es más conservadora): Servicio Nacional de Manejo del Fuego, «¿Cómo se originan los incendios?»: «El 95 % de los incendios son causados por actividades humanas» — https://www.argentina.gob.ar/seguridad/servicio-nacional-de-manejo-del-fuego/que-es-y-como-funciona-el-servicio-nacional-de-3 (consultado 13-10-2026; la página no indica período ni método, por eso en pantalla se usa el dataset abierto 1993–2019).
- La chispa se dibuja en la posición del primer foco VIIRS de la serie (enero 2012, −61,69 / −24,42); de ahí arranca el timelapse.

### Tarjeta de fuentes v6 (10 líneas)
Focos (FIRMS VIIRS) · Área quemada (MCD64A1 C6.1, UMD) · Ranking (área quemada por provincia, sumando re-quemas) · Causas (Min. de Ambiente), Caña (EEAOC), Límites (INDEC, IGN) · Comarca 2025: Gob. de Río Negro (casas), Infobae (víctima) · Fotos: NASA EO (DP), Gob. de Santa Fe y CatrielGB (CC BY-SA) · Banderas: Wikimedia Commons · Satélite: Copernicus Sentinel-2 · Cancha FIFA y Capital (IGN) · Ley 26.815.

## Datos

1. **NASA FIRMS — VIIRS S-NPP 375 m, archivo anual por país (Argentina), 2012–2025.** `https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{AÑO}/viirs-snpp_{AÑO}_Argentina.csv`. Filtro: `type == 0` y `confidence ∈ {n, h}` → **2.550.467 focos**. El archivo 2026 todavía no existe en FIRMS (404 el 13-10-2026): **el mapa de puntos termina en diciembre de 2025**; 2026 se muestra sólo con área quemada MODIS y cifras oficiales.
2. **NASA MODIS MCD64A1 Colección 6.1 — área quemada mensual, 500 m** (Giglio et al.; DOI 10.5067/MODIS/MCD64A1.061). Descarga: servidor SFTP público de la Universidad de Maryland documentado en la guía de usuario MCD64A1 C6.1 (`fuoco.geog.umd.edu`, usuario `fire`, clave pública `burnt`), ventanas GeoTIFF `Win06` (−10° a −35°) y `Win07` (−35° a −56°), grilla lat/lon de 0,00439453125°, valor = día juliano de quema. **Enero 2012 – julio 2026, 175 meses, ninguno faltante.** (La copia de Microsoft Planetary Computer, `modis-64A1-061`, se probó primero pero le faltan 2023-09, 2024-07 y meses de 2025–2026, por eso se usó UMD.) Un píxel cuenta como quemado si `burndate > 0`; área del píxel = (R·Δ)²·cos(lat), R = 6.371.007,181 m (esfera MODIS). Sólo píxeles dentro de los polígonos provinciales del INDEC.
3. **Límites provinciales:** INDEC, Censo 2022 (`/workspace/work/contar-con-datos-agua/v7/data/natgeo_v7.json`). **Ciudad de Buenos Aires** (silueta y área): IGN vía georef (`https://infra.datos.gob.ar/georef/provincias.geojson`, id 02): **20.561,8 ha** calculadas geodésicamente (WGS84). **Departamentos de Tucumán:** IGN vía georef (`https://infra.datos.gob.ar/georef/departamentos.geojson`).
4. **Caña de azúcar por departamento:** EEAOC, *Reporte Agroindustrial 370* (jun-2026), Tabla 1, zafra 2026: https://www.eeaoc.gob.ar/wp-content/uploads/2026/06/RA-370.pdf → `data/eeaoc_ra370_cana_departamentos.csv`. «Zona cañera» = los 12 departamentos con más de 5.000 ha cosechables (Leales, Cruz Alta, Burruyacu, Simoca, Monteros, Chicligasta, Río Chico, La Cocha, Famaillá, Graneros, Lules, J. B. Alberdi) = 99,85 % de las 302.320 ha de caña de la provincia.
5. **Causas 1993–2019:** Ministerio de Ambiente, «Causas y cantidad de incendios por provincia» (sin cambios desde v2/v3; copia del Internet Archive, ver v3/sources.md). 
6. **Copernicus Sentinel-2 L2A** (TCI color verdadero), espejo Microsoft Planetary Computer, colección `sentinel-2-l2a`; mosaico de 5 granulos de la misma pasada (órbita R053) recortado a la caja de la Comarca Andina (−71,80/−42,62/−71,05/−41,75): 25-12-2024, 06-04-2025 y 04-04-2026, nubosidad 0 %. Licencia Copernicus (uso libre con atribución): «Contiene datos modificados de Copernicus Sentinel 2024–2026». Script `s2/s2.py`; metadatos `s2/comarca_*.json`.

## Cada número en pantalla

| Beat | Pantalla | Valor exacto | Cálculo | Fuente |
|---|---|---|---|---|
| Timelapse | «2.550.467 FOCOS · EN 14 AÑOS · 2012–2025» | 2.550.467 | suma 2012–2025 | (1) |
| Lo que deja el fuego (v6; en v7 fuera de pantalla) | «44 MILLONES DE HA» | 44.093.983 ha | suma de los 168 meses 2012–2025 de píxeles quemados (repeticiones incluidas) | (2)+(3) |
| | «= MÁS DE 8 CANCHAS DE FÚTBOL POR MINUTO» | 8,39/min (una cada 7,15 s) | 44.093.983 ha / 0,714 ha / 441.849.600 s (1-1-2012 a 1-1-2026) × 60. Cancha FIFA recomendada 105 × 68 m = 0,714 ha | (2) |
| v7 en pantalla | «26,6 MILLONES DE HA» / «= CASI 1 DE CADA 10 HECTÁREAS DEL PAÍS» | 26.642.264 ha; 9,53 % | píxeles quemados al menos una vez / superficie de las 24 jurisdicciones en la misma grilla (279.462.711 ha) | (2)+(3) |
| Entre Ríos 2020 (no se usa en v6) | «37.506 FOCOS» | 37.506 | focos ER 2020 | (1)+(3) |
| | «CASI 7 VECES SU MEDIANA 2012–2025» / «Mediana de los otros 13 años: 5.391 focos» | 6,96 | 37.506 / mediana de 2012–2019 y 2021–2025 (5.391). Alternativa pre-evento (v3): 10,8× la mediana 2012–2019 (3.476); se eligió la referencia más larga y conservadora | (1)+(3) |
| | rótulo «PARANÁ EN BAJANTE (INA)» | — | INA, Informe bajante 31-05-2020 | contexto |
| Corrientes ene–feb 2022 | «CASI 1 MILLÓN DE HA» / «Área quemada MODIS: 959.000 ha en dos meses» | 958.776 ha | MCD64A1 enero + febrero 2022 dentro de Corrientes. Contraste: INTA Corrientes informó 1.042.514 ha al 27-02-2022 (Infobae 10-03-2022); Dymaxion Labs 959.063 ha (La Nación) | (2)+(3) |
| | «MÁS DE 46 CIUDADES DE BUENOS AIRES» + 46 siluetas | 46,63 | 958.776 / 20.561,8. Se dibujan 46 siluetas enteras a escala real (ancho ajustado por cos(lat)), en las celdas más quemadas; su área total iguala el área quemada, no su forma | (2)+(3) |
| | rótulo «SEQUÍA (SMN)» | — | NASA EO 18-02-2022 citando al SMN (<20 mm en feb vs 162 mm normales) | contexto |
| Comarca Andina | «42.000 HA EN 2026» | 42.266 ha | MCD64A1 ene–mar 2026 dentro de la caja Comarca (−71,80/−42,62/−71,05/−41,75: El Bolsón, Mallín Ahogado, Lago Puelo, El Hoyo, Epuyén, Cholila) | (2) |
| | «7 VECES MÁS QUE EN 2025» / «2025: 6.000 ha» | 7,01; 6.025 ha | misma caja, ene–mar 2025. MODIS 500 m subestima incendios bajo dosel; las cifras oficiales 2025 (Epuyén 3.530 ha + El Bolsón ~3.600 ha) y 2026 (Puerto Patriada >30.000 ha, más parte de Los Alerces/Cholila) son del mismo orden | (2) |
| | «166 casas perdidas» | 166 | Gobierno de Río Negro, «En cifras, el impacto del incendio en El Bolsón», 19-02-2025: «el fuego alcanzó 221 viviendas. De ese total, 166 sufrieron pérdidas totales» https://rionegro.gov.ar/articulo/52954/en-cifras-el-impacto-del-incendio-en-el-bolson | oficial |
| | «1 muerto» | 1 | Infobae 01-02-2025, confirmado por el gobernador Weretilneck y el intendente Pogliano (Mallín Ahogado) | prensa |
| | Puntos rojos | — | focos VIIRS ene–mar 2025 en Chubut y Río Negro al oeste de 70,9° O (no hay focos 2026 en el archivo) | (1) |
| Tucumán | «89 % DE SUS FOCOS · EN LA ZONA CAÑERA, EN PLENA ZAFRA» | 89,17 % (53.625 de 60.136) | focos de Tucumán 2012–2025 en los 12 departamentos cañeros y en mayo–noviembre. Además: 96,2 % de los focos de la provincia caen en mayo–nov. Advertencia: departamentos, no lotes; incluye quema de pastizales y rastrojos dentro de esos departamentos | (1)+(3)+(4) |
| | «Quemar está prohibido (Ley 6253, art. 38)» | — | Ley 6253 (Tucumán, 1991), art. 38: «Prohíbase en todo el Territorio de la Provincia la quema de vegetación (arraigada o seca)…» https://www.magyp.gob.ar/sitio/areas/producciones_sostenibles/legislacion/provincial/_archivos/000005-Legislaci%C3%B3n%20Ambiental%20General/000023-Tucum%C3%A1n/006253-LeyN%C2%B06253%20Normas%20grales%20y%20metod%20de%20aplicaci%C3%B3n.pdf (modificado por Ley 7459 de 2004 para nombrar la caña) | ley |
| Causas (v6: en la intro, «EN 9 DE CADA 10 INCENDIOS CON CAUSA CONOCIDA») | «9 DE CADA 10 · INCENDIOS CON CAUSA CONOCIDA: HUMANA» / «En el 48 % no se determinó la causa (1993–2019)» | 90,2 %; 47,9 % | sin cambios desde v3 | (5) |
| | «La sequía y el calor lo agravan (INA, SMN)» | — | contexto, no causalidad: INA (bajante 2020), SMN vía NASA EO (sequía Corrientes 2022; calor extremo ene–feb 2025, NASA EO «Fires Rage in Patagonia») | contexto |
| Cierre | «SABEMOS DÓNDE Y CUÁNDO ARDE.» + nota gris «Norte: ago–sep · Cordillera: dic–mar» (v5; en v4 las proporciones salían en pantalla: «Ago–sep: 4 de cada 10 focos del país · norte: 6 de cada 10» / «Cordillera patagónica: 8 de cada 10 entre diciembre y marzo») | 40,6 %; 61,7 %; 83,0 % | ago+sep / total; NOA+NEA / total; focos de Neuquén, Río Negro, Chubut y Santa Cruz al oeste de 70,5° O en dic–mar / todos los de esa zona (31.449) | (1)+(3) |
| | «YA NO FALTAN DATOS. FALTA RESPONSABILIDAD.» | — | conclusión editorial del autor, apoyada en los datos anteriores (calendario y geografía del fuego conocidos; 9 de cada 10 incendios con causa conocida son humanos) | editorial |
| | «NO QUEMES. SI VES FUEGO, LLAMÁ AL 911.» | — | 911: «Ante cualquier situación de emergencia, comunicate de inmediato con la Protección Civil local o llamá al 911» (https://www.argentina.gob.ar/seguridad/emergencias). Ley 26.815, art. 16: toda persona que conozca un incendio «está obligada a formular de inmediato la denuncia ante la autoridad más cercana» | oficial |
| Fuentes | «Cancha FIFA 105 × 68 m = 0,714 ha. Capital: límite IGN, 20.562 ha.» | | calculado en `prep_burn.py` | |

## Titulares (v4/v5; no se usan en v6–v7; **vuelven en v8**, ver arriba) (4; citas textuales re-tipografiadas, sin capturas ni logos; art. 10, Ley 11.723)
Cada uno se verificó contra el `og:title`/`<h1>` de la página (`headlines/fetched.json`; assert en el script de verificación). Cuando se muestra un fragmento, es un prefijo textual con «…».
| Parada | Medio · fecha | Titular completo | Se muestra | URL |
|---|---|---|---|---|
| Delta | Clarín · 27/07/2020 | «Rosario irrespirable por el humo: en el año detectaron 8 mil quemas de pastizales en las islas de Entre Ríos» | «Rosario irrespirable por el humo…» | https://www.clarin.com/sociedad/rosario-irrespirable-humo-ano-detectaron-8-mil-quemas-pastizales-islas-rios_0_D3R6eQaiM.html |
| Corrientes | La Nación · 15/02/2022 | «Tragedia ecológica en Corrientes: los incendios llegaron a los Esteros del Iberá y amenazan su amplia biodiversidad» | «Tragedia ecológica en Corrientes: los incendios llegaron a los Esteros del Iberá…» | https://www.lanacion.com.ar/sociedad/tragedia-ecologica-en-corrientes-los-incendios-llegaron-a-los-esteros-del-ibera-y-amenazan-su-amplia-nid15022022/ |
| Patagonia | Infobae · 01/02/2025 (22:47, hora argentina) | «Un hombre murió en los incendios en El Bolsón y el fuego sigue avanzando» | completo | https://www.infobae.com/sociedad/2025/02/02/un-hombre-murio-en-los-incendios-en-el-bolson-y-el-fuego-sigue-avanzando/ |
| Tucumán | La Gaceta · 28/06/2025 | «Choques, humo y gritos: el horror en la autopista a Famaillá» | completo | https://www.lagaceta.com.ar/nota/1090058/seguridad/choques-humo-gritos-horror-autopista-famailla.html (la nota atribuye el humo a una quema de pastizales en la ruta 38, zona cañera) |

Verificados pero no usados (límite de 4): La Nación 17-06-2020 («"El aire es irrespirable"…»), Infobae 06-08-2020, Clarín 14-02-2022, Infobae 10-03-2022, Clarín 12-02-2025, La Nación 29-03-2026, Infobae 03-02-2026, La Nación 27-06-2025, La Gaceta 05-07-2025 (ver `headlines/fetched.json`).

## Imágenes (créditos completos)
| Uso | Archivo | Autor | Licencia | URL |
|---|---|---|---|---|
| Foto, Delta 2020 (**no se usa en v6**) | Incendio en delta del paraná 2020.jpg | Ministerio de Ambiente de la Nación (fuente: argentina.gob.ar/ambiente/conciencia-ambiental/incendios-delta) | CC BY 4.0 | https://commons.wikimedia.org/wiki/File:Incendio_en_delta_del_paran%C3%A1_2020.jpg |
| Foto, Corrientes 2022 (flash 0,5 s) | Wildfires Ravage Corrientes as seen by Landsat 9.jpg | NASA Earth Observatory (Lauren Dauphin), datos Landsat del USGS | Dominio público | https://commons.wikimedia.org/wiki/File:Wildfires_Ravage_Corrientes_as_seen_by_Landsat_9.jpg |
| Foto, brigadistas en Chubut 2026 (flash 0,5 s; de espaldas) | Brigadistas forestales santafesinos durante los incendios en Chubut en 2026 02.jpg | Gobierno de la Provincia de Santa Fe (fuente: santafe.gob.ar/noticias/noticia/285194/) | CC BY-SA 2.5 | https://commons.wikimedia.org/wiki/File:Brigadistas_forestales_santafesinos_durante_los_incendios_en_Chubut_en_2026_02.jpg |
| Foto, bosque quemado, Comarca Andina 2026 (flash 0,5 s) | Restos de Incendios.jpg | CatrielGB | CC BY-SA 4.0 | https://commons.wikimedia.org/wiki/File:Restos_de_Incendios.jpg |
| Satélite en su lugar, Comarca Andina | Sentinel-2 L2A TCI, 25-12-2024 / 06-04-2025 / 04-04-2026 | Copernicus (ESA/UE) | Licencia Copernicus, uso libre con atribución | colección `sentinel-2-l2a`, Microsoft Planetary Computer |
| Banderas | Entre Ríos (DP), Corrientes (DP), Chubut (CC BY 4.0, Roxana Vanesa Jones / Gobierno del Chubut), Río Negro (CC BY 4.0, orig. Daniel Cuomo, vector Hellerick), Tucumán (DP; bandera oficial por Ley 8.291 de 2010) | | | ver `flags/flags.json` |

Por qué hay dos CC BY-SA: no se encontró ninguna foto en dominio público ni CC BY de brigadistas o bosque quemado en la Patagonia 2025–2026 (búsqueda en Commons por Epuyén, El Bolsón, Puerto Patriada, Lanín, Los Alerces, Cholila). Ninguna foto muestra caras identificables. No se usó ninguna imagen generada por IA. Fotos sin licencia abierta (diarios, gobiernos sin licencia explícita) fueron descartadas.

## Reglas del concurso aplicadas (Bases 2026)
- «Historia visual … a través de una visualización única»: todo ocurre sobre un solo mapa; fotos y titulares son tarjetas chicas (4 fotos, 4 titulares) unidas por una línea a su lugar exacto; la imagen Sentinel-2 se dibuja georreferenciada dentro del mapa.
- Punto 13 / formulario: el autor declara tener los derechos o el permiso de uso de todo el material y cede uso, reproducción y transformación: por eso sólo DP, CC BY, CC BY-SA (con atribución) y Copernicus; titulares como cita breve re-tipografiada.
- Anexo A (IA): declaración en la descripción metodológica; sin imágenes generadas.
- Video ≤ 1 minuto: 59,77 s (v7).

## Advertencias
- Un foco es un píxel de 375 m con anomalía térmica, no un incendio ni una superficie.
- MODIS 500 m omite quemas chicas y subestima incendios bajo dosel: las hectáreas son un piso.
- v7 muestra sólo la superficie distinta (26,6 M ha): cada lugar cuenta una vez aunque haya ardido varios años. El total con re-quemas (44 M ha) queda documentado, no se muestra.
- La comparación 2025/2026 de la Comarca usa una caja fija; cambiar la caja cambia los valores absolutos.
- Causas: serie que termina en 2019, con 48 % sin causa determinada.
