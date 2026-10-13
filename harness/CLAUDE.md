# CLAUDE.md

Read and follow [`AGENTS.md`](AGENTS.md): workflow, non-negotiable rules and a map of this harness's code.

Shortcuts:
- Quick validation: `python -m harness check stories/<slug>` (seconds; run it after every change to the YAML or to facts.py).
- See how it looks: `python -m harness qa stories/<slug> --preview` and open `stories/<slug>/build/qa/contact_sheet.png`.
- Render: `make video STORY=stories/<slug>/story.yaml`.
- Tests: `pytest -q`.

Do not relax readability rules or asserts to make a build pass; change the script. Do not add numbers by hand. Do not use AI-generated images.
