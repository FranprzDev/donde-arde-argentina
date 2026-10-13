# AGENTS.md — cómo trabajar en este harness (Codex, Claude Code, Cursor, humanos)

Este directorio (`harness/`, dentro del repo `donde-arde-argentina`) genera videos cortos de historias con datos a partir de un `story.yaml`.
Leé esto entero antes de tocar nada. Los comandos asumen que estás parado en `harness/`.

## Flujo de trabajo para una historia nueva

1. **Pregunta y datos.** Una pregunta, una respuesta visual. Buscá **datos abiertos** (portales oficiales, NASA,
   Copernicus, USGS, INDEC, etc.). Anotá en `stories/<slug>/SOURCES.md`: quién publica, URL, fecha de descarga,
   licencia, filtros. Si no hay dato abierto para algo, **no va en pantalla**.
2. **Scaffold.** `python -m harness new "Nombre"` → `stories/<slug>/` (arranca renderizable con datos reales de ejemplo).
3. **Datos.** Archivos chicos en `stories/<slug>/data/`. Crudos pesados en `data/raw/` (ignorado por git) + un
   `prepare.py` que los baja con los adaptadores (`python -m harness.data.firms|modis|sentinel2 ...`).
4. **Facts.** En `facts.py`, `compute(ctx)` devuelve un dict con **cada número** que va a aparecer (y listas para rankings).
   `ctx.data("nombre")`, `ctx.json("data/x.json")`, `ctx.table("data/x.csv")`, `ctx.world`.
5. **Beats.** Escribí el guion en `story.yaml` (referencia: `docs/beats.md`). Textos con `{fact|filtro}`.
   Cada redondeo verbal → un `assert` en `facts.asserts`. Cada número que tipees a mano (fechas, «1 de cada 10»,
   «Sentinel-2») → una entrada en `facts.literals` con su `assert`.
6. **Chequeo rápido.** `python -m harness check stories/<slug>` (segundos). Si falla, el mensaje dice qué regla y cómo
   arreglarlo. **Nunca aflojes una regla para que pase**: acortá el texto, alargá la escena o sacá una escena.
7. **QA visual.** `python -m harness qa stories/<slug> --preview` → mirá `build/qa/contact_sheet.png` y
   `phone_sheet.png` (texto cortado, superpuesto, poco contraste, algo ilegible en celular).
8. **Render.** `make video STORY=stories/<slug>/story.yaml` (o `python -m harness render ... --workers N`).
   Retoma chunks si se corta. Después `python -m harness qa stories/<slug>` reporta duración y loudness del mp4.
9. **Entrega.** Mostrá el mp4 + `build/qa/timing.md` + resumen de cambios. Versioná historias en iteración como
   `stories/<slug>/` + git; no pises versiones entregadas sin avisar.

## Reglas (no negociables)

- **Datos abiertos únicamente**, citados en `SOURCES.md` y en el beat `sources`, con licencia.
- **Ningún número inventado.** Nada de cifras "ilustrativas", ni promedios estimados a ojo, ni proyecciones sin modelo
  citable. Todo número en pantalla sale de `facts.py` y tiene `assert`. El build rechaza dígitos tipeados a mano.
- **Asociación ≠ causalidad.** Si el dato muestra correlación, el texto no dice "por culpa de".
- **Sin imágenes, video, voces ni música generados por IA** cuando la historia es para un concurso o una publicación
  que lo prohíbe (por defecto: no usar). La IA puede ayudar con código y análisis, y se declara.
- **Créditos y licencias.** Fotos/imágenes solo PD, CC0, CC BY (CC BY-SA si no hay alternativa) o datos abiertos
  (Copernicus: "Contiene datos Copernicus Sentinel modificados AÑO"). Banderas/escudos: verificar licencia.
- **Legibilidad**: ≥ 48 px a 1080p, ≤ 12 palabras a la vez por escena, 0,35 s/palabra + 1 s (mín. 2,5 s), total ≤ el
  límite. Si no entra: sacar escenas o palabras, **nunca acelerar** el texto.
- **Audio**: −14 LUFS integrados, true peak ≤ −1,5 dBTP (lo verifica el render).
- **No commitear** mp4, wav, rásters crudos, `build/`, `data/raw/` (ya están en `.gitignore`).
- **Privacidad**: nada de datos personales, tokens, clientes ni URLs privadas en el repo. Este repo es privado; si
  el harness se publica aparte, las historias privadas (como `stories/incendios-argentina/`) no van.

## Mapa del código

| Archivo | Qué hace |
|---|---|
| `harness/story.py` | Carga el YAML, corre facts, arma y agenda los beats, chequea reglas |
| `harness/facts.py` | `facts.json`, placeholders `{x\|filtro}`, asserts, regla de números a mano |
| `harness/rules.py` | Reglas de lectura (`ReadabilityError` con mensajes accionables) |
| `harness/render.py` | Compositor de cuadros, render paralelo por chunks, mux final |
| `harness/layers.py` | Capas persistentes del mapa: puntos, rásters, imágenes, coropletas |
| `harness/core/fx.py` | Tipografía cinética (slam), glow, viñeta, grano; tamaño mínimo de fuente |
| `harness/core/geo.py` | Proyección, cámaras (fly / zoomto / ease), rásters, imágenes georreferenciadas |
| `harness/core/space.py` | Sol, Tierra y estrellas por código |
| `harness/beats/*.py` | Un archivo por familia de escenas (`@register`) |
| `harness/audio/` | Música procedural por cues + normalización −14 LUFS |
| `harness/data/` | Loaders + adaptadores FIRMS / MODIS / Sentinel-2 |
| `harness/qa.py` | Stills, contact sheet, hoja celular, reporte de tiempos |

## Agregar un tipo de beat

Ver `docs/adding-a-beat.md`. Resumen: subclase de `Beat` en `harness/beats/`, `@register`, `type = "nombre"`,
implementar `text_templates/resolve/text_need/make_blocks/draw_map/draw_ui/cues`, importarlo en
`harness/beats/__init__.py`, documentarlo en `docs/beats.md` y agregar un caso al ejemplo o a `tests/`.

## Comandos de verificación antes de un PR

```bash
python -m harness check stories/sismos-argentina
pytest -q
```
