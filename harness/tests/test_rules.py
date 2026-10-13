import copy
import os

import pytest
import yaml

from harness.errors import FactsError, ReadabilityError
from harness.facts import Locale, literal_digits_problems, render_template
from harness.rules import Rules, words
from harness.story import Story

HERE = os.path.dirname(os.path.abspath(__file__))
TOY = os.path.join(HERE, "..", "stories", "sismos-argentina", "story.yaml")


def test_words_and_need():
    assert words("12,5 MILLONES DE PERSONAS") == 4
    assert words("3 PROVINCIAS = 73 %") == 3
    r = Rules()
    assert r.need(1) == 2.5 and abs(r.need(12) - 5.2) < 1e-9


def test_templates_and_literals():
    loc = Locale("es")
    assert render_template("{n|int} sismos", {"n": 12345}, loc) == "12.345 sismos"
    assert render_template("{x|div:1e6|dec:1} M", {"x": 12_500_000}, loc) == "12,5 M"
    assert render_template("{s|pct} %", {"s": 0.734}, loc) == "73 %"
    with pytest.raises(FactsError):
        render_template("{x}", {"x": 0.5}, loc)          # floats need an explicit format
    assert literal_digits_problems("CASI 3 DE CADA 10", {}) == ["3", "10"]
    assert literal_digits_problems("CASI 3 DE CADA 10", {"3 DE CADA 10": "True"}) == []
    assert literal_digits_problems("{total|int} SISMOS", {}) == []


def _story_with(tmp_path, mutate):
    cfg = yaml.safe_load(open(TOY, encoding="utf-8"))
    mutate(cfg)
    src = os.path.dirname(TOY)
    for f in os.listdir(src):
        if f not in ("story.yaml", "build"):
            p = os.path.join(src, f); q = tmp_path / f
            if not q.exists():
                os.symlink(p, q)
    (tmp_path / "story.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return Story.load(str(tmp_path / "story.yaml"), scale=0.5)


def test_toy_passes_rules():
    s = Story.load(TOY, scale=0.5).prepare()
    assert s.total <= s.video["max_duration"]
    assert s.facts["total"] == 869


def test_hold_too_short_fails(tmp_path):
    def m(cfg):
        b = next(b for b in cfg["beats"] if b["id"] == "total"); b["duration"] = 2.0
    with pytest.raises(ReadabilityError, match="needs"):
        _story_with(tmp_path, m).prepare()


def test_too_many_words_fails(tmp_path):
    def m(cfg):
        b = next(b for b in cfg["beats"] if b["id"] == "total"); b["subline"] = "UNA LINEA DEMASIADO LARGA PARA LEER EN TAN POCO TIEMPO SIN PAUSAR"
    with pytest.raises(ReadabilityError, match="words on screen"):
        _story_with(tmp_path, m).prepare()


def test_hand_typed_number_fails(tmp_path):
    def m(cfg):
        b = next(b for b in cfg["beats"] if b["id"] == "total"); b["unit"] = "SISMOS EN 10 AÑOS"
    with pytest.raises(FactsError, match="typed by hand"):
        _story_with(tmp_path, m).prepare()


def test_small_font_fails(tmp_path):
    def m(cfg):
        b = next(b for b in cfg["beats"] if b["id"] == "total"); b["subline_size"] = 30
    with pytest.raises(ReadabilityError):
        _story_with(tmp_path, m).prepare()


def test_too_long_fails(tmp_path):
    def m(cfg):
        cfg["video"]["max_duration"] = 20
    with pytest.raises(ReadabilityError, match="total duration"):
        _story_with(tmp_path, m).prepare()


def test_failed_assert_fails(tmp_path):
    def m(cfg):
        cfg["facts"]["asserts"].append("total == 870")
    with pytest.raises(FactsError, match="assert failed"):
        _story_with(tmp_path, m).prepare()
