# CLAUDE.md

Leé y seguí [`AGENTS.md`](AGENTS.md): flujo, reglas no negociables y mapa del código de este harness.

Atajos:
- Validar rápido: `python -m harness check stories/<slug>` (segundos; corré esto después de cada cambio al YAML o a facts.py).
- Ver cómo queda: `python -m harness qa stories/<slug> --preview` y abrí `stories/<slug>/build/qa/contact_sheet.png`.
- Render: `make video STORY=stories/<slug>/story.yaml`.
- Tests: `pytest -q`.

No relajes reglas de lectura ni asserts para que un build pase; cambiá el guion. No agregues números a mano. No uses imágenes generadas por IA.
