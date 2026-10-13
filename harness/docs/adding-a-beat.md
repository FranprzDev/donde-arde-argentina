# How to add a beat type

A beat is a scene: it knows how long it lasts, what text it shows (for the rules), how the camera moves, what it draws
over the map and what it sounds like. Minimal example: a counter that counts up over the map.

```python
# harness/beats/counter.py
"""counter — a number that counts up over the map.

    - type: counter
      value: "{total}"          # a fact (integer)
      label: "RECORDS"
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

Then:

1. Import it in `harness/beats/__init__.py` (`from . import counter`).
2. Document its keys in `docs/beats.md` (copy the docstring).
3. Use it in a story and run `python -m harness check` + `qa --preview`.
4. Add a test in `tests/` if it has its own timing logic.

## Rules for new beats

- Positions and sizes in **design units** (1920×1080 canvas); `fr.S` scales to the real resolution.
  Request fonts with `self.theme.font(kind, size)`: it rejects sizes below the minimum.
- All visible text must be in some `TextBlock` (otherwise the rules cannot see it). Labels that are not prose
  (axis years) use `count=False`, but they still respect the minimum size.
- No literal numbers in drawing code: they come from `self.story.facts` or from placeholders.
- `draw_map(A, t, cam, R)` works on the float image (H, W, 3) before the text; `draw_ui(fr, t, cam, R)` works on the `Canvas`.
- For things that must be visible before/after the scene: `draw_pre` (in the previous beat) and `draw_post` (in the next one).
- Own camera: override `camera_at(t)` and `end_camera()` (see `satellite_zoom`).
