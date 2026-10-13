"""Load a story.yaml, compute facts, build and schedule the beats, and check every rule before a single frame renders.

    story = Story.load("stories/x/story.yaml")      # parses + validates the YAML
    story.prepare()                                 # facts.json, beats, schedule, readability check (raises on failure)
    story.total, story.beats, story.facts"""
import copy
import os

import yaml

from .core.fx import Theme
from .errors import FactsError, StoryError
from .facts import Locale, compute_facts, literal_digits_problems, render_template
from .rules import Rules

VIDEO_DEFAULTS = dict(width=1920, height=1080, fps=30, max_duration=60.0, crf=20)


class Story:
    def __init__(self, path, cfg, scale=1.0):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.cfg = cfg
        self.slug = cfg.get("slug") or os.path.basename(self.dir)
        self.title = cfg.get("title", self.slug)
        v = dict(VIDEO_DEFAULTS); v.update(cfg.get("video") or {})
        self.video = v
        self.scale = scale
        self.W = int(round(v["width"] * scale / 2) * 2); self.H = int(round(v["height"] * scale / 2) * 2)
        self.fps = v["fps"] if scale >= 1 else v.get("preview_fps", v["fps"])
        self.rules = Rules(cfg.get("rules"))
        th = cfg.get("theme") or {}
        self.theme = Theme(th.get("palette"), th.get("fonts"), th.get("lut"), self.rules.min_font_px, self.dir)
        self.theme.S = self.H / 1080
        self.locale = Locale(cfg.get("locale", "es"))
        self.build_dir = os.path.join(self.dir, "build")
        self._datasets = {}
        self.world = None
        self.facts = None
        self.beats = []
        self.total = 0.0

    # ---------------- loading ----------------
    @classmethod
    def load(cls, path, scale=1.0):
        if os.path.isdir(path):
            path = os.path.join(path, "story.yaml")
        if not os.path.exists(path):
            raise StoryError(f"story file not found: {path}")
        try:
            cfg = yaml.safe_load(open(path, encoding="utf-8"))
        except yaml.YAMLError as e:
            raise StoryError(f"{path}: invalid YAML: {e}") from e
        if not isinstance(cfg, dict) or not cfg.get("beats"):
            raise StoryError(f"{path}: needs at least `title` and a `beats:` list")
        s = cls(path, cfg, scale)
        s._load_world()
        return s

    def _load_world(self):
        from .data.loaders import load_regions
        m = self.cfg.get("map")
        if m:
            spec = dict(m["regions"]) if isinstance(m.get("regions"), dict) else {"path": m.get("regions")}
            for k in ("neighbours", "ref_lat", "shapes"):
                if k in m:
                    spec[k] = m[k]
            self.world = load_regions(spec, self.dir, self.H / 1080)

    def dataset(self, name):
        if name not in self._datasets:
            from .data.loaders import load_dataset
            specs = self.cfg.get("data") or {}
            if name not in specs:
                raise StoryError(f"data '{name}' is not declared in story.yaml `data:` (declared: {sorted(specs)})")
            self._datasets[name] = load_dataset(name, specs[name], self.dir, self.world)
        return self._datasets[name]

    def data_spec(self, name):
        return (self.cfg.get("data") or {}).get(name, {})

    # ---------------- facts + beats ----------------
    def tpl(self, s):
        return render_template(s, self.facts, self.locale)

    def prepare(self, check=True):
        from .beats import make_beat
        self.facts = compute_facts(self)
        literals = (self.cfg.get("facts") or {}).get("literals") or {}
        probs = []
        self.beats = []
        for i, bc in enumerate(self.cfg["beats"]):
            if "type" not in bc:
                raise StoryError(f"beat #{i + 1} has no `type`")
            bc = copy.deepcopy(bc)
            for k in ("camera", "highlight", "spotlight", "replay", "label_points"):      # non-text settings may use facts too
                if k in bc:
                    bc[k] = self._tpl_deep(bc[k])
            b = make_beat(self, bc, i)
            if not b.exempt_readability:
                for tmpl in b.text_templates():
                    for num in literal_digits_problems(tmpl, literals):
                        probs.append(f"beat '{b.id}': number '{num}' typed by hand in \"{tmpl}\". Bind it to a fact "
                                     f"({{name|filter}}) or justify it under facts.literals with an assert.")
            self.beats.append(b)
        if probs:
            raise FactsError("numbers on screen must come from facts.json:\n" + "\n".join("  - " + p for p in probs))
        for b in self.beats:
            b.resolve()
        self.schedule()
        if check:
            self.rules.check(self.beats, self.total, float(self.video["max_duration"]))
        return self

    def _tpl_deep(self, v):
        if isinstance(v, str):
            return self.tpl(v) if "{" in v else v
        if isinstance(v, list):
            return [self._tpl_deep(x) for x in v]
        if isinstance(v, dict):
            return {k: self._tpl_deep(x) for k, x in v.items()}
        return v

    def schedule(self):
        t = 0.0
        prev = None
        for b in self.beats:
            b.plan(t, prev)
            t = b.end
            prev = b
        for i, b in enumerate(self.beats):
            b.prev = self.beats[i - 1] if i else None
            b.next = self.beats[i + 1] if i + 1 < len(self.beats) else None
        self.total = round(t, 3)

    def beat_at(self, t):
        for b in self.beats:
            if b.start <= t < b.end:
                return b
        return self.beats[-1]

    def describe(self):
        return [dict(id=b.id, type=b.type, start=round(b.start, 2), end=round(b.end, 2)) for b in self.beats]
