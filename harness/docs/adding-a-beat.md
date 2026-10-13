# Cómo agregar un tipo de beat

Un beat es una escena: sabe cuánto dura, qué texto muestra (para las reglas), cómo se mueve la cámara, qué dibuja
sobre el mapa y qué suena. Ejemplo mínimo: un contador que sube sobre el mapa.

```python
# harness/beats/counter.py
"""counter — a number that counts up over the map.

    - type: counter
      value: "{total}"          # a fact (integer)
      label: "REGISTROS"
"""
from ..core.fx import count, slam
from ..rules import TextBlock
from .base import register
from .cards import MapBeat          # MapBeat = Beat + highlight / spotlight / replay


@register
class Counter(MapBeat):
    type = "counter"
    transition_default = 0.6        # seconds of camera move before the text (if `camera:` is set)

    def text_templates(self):       # raw strings -> the "no hand-typed numbers" check
        return [self.cfg["value"], self.cfg.get("label", "")]

    def resolve(self):              # fill placeholders from facts.json
        self.value = int(self.story.tpl(self.cfg["value"]).replace(".", ""))
        self.label = self.story.tpl(self.cfg.get("label", ""))

    def text_need(self):            # seconds the text must stay (rules: 0.35 s/word + 1 s, min 2.5 s)
        return self.need(str(self.value), self.label)

    def make_blocks(self):          # what the readability check sees
        self.blocks = [TextBlock([str(self.value), self.label], self.text_t0, self.text_t1, self.id, sizes=[150, 66])]

    def draw_ui(self, fr, t, cam, R):
        th = self.theme
        n = self.story.locale.int(count(t, self.text_t0, self.value, 1.0))
        slam(fr, (110, 600), n, th.font("display", 150), th.c["hot"], t, self.text_t0, self.text_t1, glow=0.55)
        slam(fr, (110, 700), self.label, th.font("display", 66), th.c["accent2"], t, self.text_t0 + 0.3, self.text_t1, big=False)

    def cues(self):                 # music: (time, kind, value) — kinds in harness/audio/music.py
        return [(self.text_t0, "hit", 0.9)]
```

Después:

1. Importalo en `harness/beats/__init__.py` (`from . import counter`).
2. Documentá sus claves en `docs/beats.md` (copiá el docstring).
3. Usalo en una historia y corré `python -m harness check` + `qa --preview`.
4. Agregá un test en `tests/` si tiene lógica propia de tiempos.

## Reglas para beats nuevos

- Posiciones y tamaños en **unidades de diseño** (lienzo 1920×1080); `fr.S` escala a la resolución real.
  Pedí fuentes con `self.theme.font(tipo, tamaño)`: rechaza tamaños bajo el mínimo.
- Todo texto visible tiene que estar en algún `TextBlock` (si no, las reglas no lo ven). Rótulos que no son prosa
  (años de un eje) van con `count=False`, pero igual respetan el tamaño mínimo.
- Nada de números literales en el código de dibujo: vienen de `self.story.facts` o de placeholders.
- `draw_map(A, t, cam, R)` trabaja sobre la imagen float (H, W, 3) antes del texto; `draw_ui(fr, t, cam, R)` sobre el `Canvas`.
- Para cosas que deben verse antes/después de la escena: `draw_pre` (en el beat anterior) y `draw_post` (en el siguiente).
- Cámara propia: sobreescribí `camera_at(t)` y `end_camera()` (ver `satellite_zoom`).
