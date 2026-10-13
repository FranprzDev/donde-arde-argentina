# v9 — «¿Dónde arde Argentina?» (Historia visual, 59,77 s, 1080p30)

**v9 = v8 + notas del autor (13-10-2026), todas obligatorias:**
1. **Rayos que pegan en la Argentina:** en el globo y en el mapa plano cada rayo del Sol aterriza en un punto dentro del país y su trazo termina ahí (destello + reflejo); antes los primeros rayos caían en cualquier punto del globo.
2. **Tucumán con imagen de Tucumán:** sale la foto de Queensland. La parada termina con un zoom dentro del mismo mapa hasta una imagen Copernicus Sentinel-2 de **Burruyacú (departamento cañero), 23-09-2025, plena zafra**: dos columnas de humo de quemas activas, con los focos VIIRS de esa tarde sobre el origen del humo. No existe foto abierta verificada de una quema de caña en Tucumán (Commons revisado otra vez).
3. **Una sola visualización:** salen los otros dos cortes a foto (pastizal, bosque) y los 4 titulares. Entre Ríos termina con un zoom a Sentinel-2 de **las islas del Delta frente a Rosario, 23-09-2020**; la Comarca conserva su antes/después Sentinel-2 en el lugar. Todo pasa sobre un mapa continuo.
4. **Sin Corrientes:** sale la cicatriz Corrientes 2022 resaltada (se veía desplazada) y el titular de La Nación. Corrientes sólo aparece como nombre en el ranking (puesto 4, dato real).
5. **Menos texto, más grande, más tiempo:** ≤ ~12 palabras por momento; cuerpo ≥ 48 px (cifras 150 px, frases 66–124 px); cada texto ≥ 0,35 s por palabra + 1 s (mín. 2,5 s), verificado por `assert` en `render_v9.py`. Para que entre en 60 s se quitaron beats, no se aceleró: la tarjeta «2.550.467 FOCOS», el segundo título, la fuente gris de las causas, las 24 filas del ranking y las hectáreas del top 5, la nota gris de Tucumán y el encabezado del cierre.

Se mantienen: el contorno de todo el país encendido, el ranking (ahora sólo top 5 con nombres), el mapa final con todo lo que ardió 2012–2025 bajo «YA NO FALTAN DATOS. / FALTA RESPONSABILIDAD.», cifras sólo desde los JSON del pipeline con `assert`, −14 LUFS, sin nombre del autor.

| Tiempo (s) | Imagen / cámara | Texto en pantalla (palabras → tiempo en pantalla) | Música |
|---|---|---|---|
| 0,0–4,6 | Sol → rayos → Tierra → Argentina: todos los rayos aterrizan en el país | «¿DÓNDE ARDE / ARGENTINA?» (0,45–3,85; 3 → 3,4 s) | rugido solar, destello por rayo |
| 4,0–5,45 | Mapa plano: siguen cayendo rayos sobre la Argentina, que se calienta | «EL SOL CALIENTA.» (4,45–7,05; 3 → 2,6 s) | pad cálido |
| 5,55–10,6 | El calor se apaga; una chispa (primer foco VIIRS, ene-2012) | **«LA CHISPA ES HUMANA.»** + «9 DE CADA 10, CON CAUSA CONOCIDA» (5,65–10,6; 11 → 4,95 s) | fósforo, riser |
| 8,3–12,2 | La chispa enciende 14 años de focos VIIRS; año grande + curva mensual (2012 · 2016 · 2020 · 2024) | (el texto de la chispa sigue hasta 10,6) · leyenda «1 punto = 1 foco de calor (satélite)» | golpe, tambores, tic por enero |
| 12,2–13,5 | Todo encendido → ceniza → cicatriz MODIS | — · leyenda «gris = área quemada» | braam, whoosh |
| 13,5–18,7 | Cicatriz nacional | **«26,6 MILLONES DE HA»** / «QUEMADAS: CASI 1 DE CADA 10 DEL PAÍS» (12 → 5,25 s) | boom |
| 18,7–20,4 | Las 24 jurisdicciones se encienden en el mapa (coropleta), sin texto | — | un tic por provincia |
| 20,4–25,8 | Top 5 en el mapa (números) | «5 PROVINCIAS = 53 % DE LO QUEMADO» / 1 FORMOSA · 2 LA PAMPA · 3 SANTA FE · 4 CORRIENTES · 5 SANTIAGO DEL ESTERO (5,4 s) | hit, tambores |
| 25,8–26,8 | Zoom directo a Tucumán | — | whoosh |
| 26,8–31,9 | **Tucumán**: zona cañera contorneada, focos de la zafra; aparece el marco del zoom | [bandera] «TUCUMÁN» / **«89 %»** «DE SUS FOCOS» / «EN ZONA CAÑERA, EN PLENA ZAFRA» (11 → 4,9 s) | hit, tambores |
| 31,8–32,8 | Zoom dentro del mapa hasta el marco | — | whoosh descendente |
| 32,8–35,4 | **Sentinel-2, Burruyacú 23-09-2025**: columnas de humo; focos VIIRS de esa tarde | «BURRUYACÚ, TUCUMÁN» / «23/09/2025 · Sentinel-2» (4 → 2,6 s) | impacto + rugido de fuego |
| 35,4–36,8 | Zoom out y vuelo a Entre Ríos | — | whoosh |
| 36,8–41,5 | **Entre Ríos 2020**: focos del año, cicatriz MODIS 2020 resaltada | [bandera] «ENTRE RÍOS · 2020» / **«37.506»** (cuenta) «FOCOS» / «CASI 7 VECES LO HABITUAL» (10 → 4,7 s) | hit, tambores |
| 41,4–42,4 | Zoom al Delta | — | whoosh |
| 42,4–45,5 | **Sentinel-2, islas frente a Rosario 23-09-2020**: humo sobre las islas, Rosario a la izquierda; focos VIIRS de esa tarde | «ISLAS DEL DELTA» / «23/09/2020 · Sentinel-2» + rótulo «ROSARIO» (6 → 3,1 s) | impacto + rugido |
| 45,5–47,1 | Zoom out y vuelo a la cordillera | — | whoosh, swell |
| 47,1–52,2 | **Comarca Andina**: Sentinel-2 dic-2024 → abr-2025 → abr-2026, cicatrices 2025 (ámbar) / 2026 (rojo) | [banderas] «COMARCA ANDINA · 2026» / **«42.000»** (cuenta) «HA» / «7 VECES MÁS QUE EN 2025» (11 → 5,1 s) · rótulos «DIC 2024 / ABR 2025 / ABR 2026 · Sentinel-2 · ■ 2025 · ■ 2026» | drop, coro |
| 52,2–52,9 | Zoom out al país | — | redoble |
| 52,9–56,8 | **Cierre**: 24 jurisdicciones encendidas; todos los focos 2012–2025 se acumulan sobre la cicatriz MODIS | 53,67 **«YA NO FALTAN DATOS.»** / 53,92 **«FALTA RESPONSABILIDAD.»** (5 → 3,1 s) | silencio 53,4–53,67; boom, taiko, campana |
| 56,8–59,77 | Tarjeta de FUENTES (8 líneas, 48 px) | ver sources.md | decrescendo |

Tamaños: texto mínimo 48 px (leyendas, rótulos, fuentes, años de la curva); encabezados mono 52 px; frases 66 px; cifras 150 px; cierre 124 px.
