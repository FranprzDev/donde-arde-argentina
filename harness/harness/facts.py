"""The facts step: every number that appears on screen is computed here, written to build/facts.json and asserted.

A story provides `facts.py` with

    def compute(ctx):            # ctx.data("name"), ctx.json("data/x.json"), ctx.table("data/x.csv"), ctx.world
        return {"total": 123, "share": 0.53, "rows": [...]}

A fact may also be returned as {"value": v, "source": "...", "note": "..."} to keep provenance in facts.json.
story.yaml then binds text to facts with placeholders and guards every verbal rounding with an assert:

    text: "{share|pct} % DE LO QUEMADO"          # filters: int, dec:1, pct, pct:1, div:1e6, round, upper, abs
    facts:
      asserts:
        - "round(share * 100) == 53"
      literals:                                   # numbers typed in the text must be justified here
        "1 DE CADA 10": "0.09 < share_country < 0.10"

Hand-typed digits in on-screen text that are neither a placeholder nor covered by `literals` FAIL the build."""
import importlib.util
import json
import math
import os
import re

from .errors import FactsError

PH = re.compile(r"\{([A-Za-z_][\w\.]*)((?:\|[^{}|]+)*)\}")


class Locale:
    def __init__(self, code="es"):
        self.code = code
        self.dsep, self.tsep = (",", ".") if code in ("es", "pt", "de", "it", "fr") else (".", ",")

    def int(self, x):
        return f"{int(round(float(x))):,}".replace(",", "\0").replace("\0", self.tsep)

    def dec(self, x, d=1):
        s = f"{float(x):,.{d}f}"
        return s.replace(",", "\0").replace(".", self.dsep).replace("\0", self.tsep)


def _lookup(facts, key):
    cur = facts
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, (list, tuple)) and part.isdigit():
            cur = cur[int(part)]
        else:
            raise FactsError(f"placeholder '{{{key}}}' has no value in facts.json (known facts: {sorted(facts)[:40]})")
    return cur


def apply_filters(v, filters, loc):
    for f in filters:
        name, _, arg = f.partition(":")
        name = name.strip(); arg = arg.strip()
        if name == "int":
            v = loc.int(v)
        elif name == "dec":
            v = loc.dec(v, int(arg or 1))
        elif name == "pct":
            v = loc.int(float(v) * 100) if not arg else loc.dec(float(v) * 100, int(arg))
        elif name == "div":
            v = float(v) / float(arg)
        elif name == "mul":
            v = float(v) * float(arg)
        elif name == "round":
            v = round(float(v), int(arg or 0)); v = int(v) if not arg else v
        elif name == "floor":
            q = float(arg or 1); v = int(math.floor(float(v) / q) * q)
        elif name == "upper":
            v = str(v).upper()
        elif name == "abs":
            v = abs(float(v))
        else:
            raise FactsError(f"unknown filter '|{name}' (int, dec:N, pct, pct:N, div:X, mul:X, round:N, floor:Q, upper, abs)")
    return v


def render_template(s, facts, loc):
    if not isinstance(s, str):
        return s

    def sub(m):
        v = _lookup(facts, m.group(1))
        filters = [x for x in m.group(2).split("|") if x]
        v = apply_filters(v, filters, loc)
        if isinstance(v, float) and not filters:
            raise FactsError(f"'{{{m.group(1)}}}' is a float ({v}); add a format filter like |dec:1 or |int so the rounding is explicit")
        return str(v)
    return PH.sub(sub, s)


def literal_digits_problems(template, literals):
    """digits typed by hand in a template (outside placeholders) that no `literals` entry covers"""
    bare = PH.sub(" ", template)
    covered = [k for k in literals if k in template]
    probs = []
    for m in re.finditer(r"\d+(?:[.,]\d+)*", bare):
        num = m.group(0)
        if not any(num in k for k in covered):
            probs.append(num)
    return probs


class FactsContext:
    def __init__(self, story):
        self.story = story
        self.dir = story.dir
        self.world = story.world

    def path(self, rel):
        return os.path.join(self.dir, rel)

    def data(self, name):
        return self.story.dataset(name)

    def json(self, rel):
        return json.load(open(self.path(rel)))

    def table(self, rel):
        from .data.loaders import load_table
        return load_table(self.path(rel))


def compute_facts(story, write=True):
    cfg = story.cfg.get("facts") or {}
    script = cfg.get("script", "facts.py")
    p = os.path.join(story.dir, script)
    facts, meta = {}, {}
    if os.path.exists(p):
        spec = importlib.util.spec_from_file_location(f"facts_{story.slug.replace('-', '_')}", p)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        try:
            raw = mod.compute(FactsContext(story))
        except FactsError:
            raise
        except Exception as e:
            raise FactsError(f"{script}: compute() failed: {type(e).__name__}: {e}") from e
        for k, v in raw.items():
            if isinstance(v, dict) and "value" in v and set(v) <= {"value", "source", "note", "unit"}:
                facts[k] = v["value"]; meta[k] = {kk: vv for kk, vv in v.items() if kk != "value"}
            else:
                facts[k] = v
    elif cfg.get("values") is None:
        raise FactsError(f"no {script} in {story.dir} and no facts.values in story.yaml")
    facts.update(cfg.get("values") or {})
    # asserts: every verbal rounding / ranking order / label must be guarded
    env = dict(facts); env.update(dict(round=round, abs=abs, min=min, max=max, len=len, sum=sum, int=int, float=float,
                                       sorted=sorted, math=math, all=all, any=any, str=str))
    fails = []
    for a in cfg.get("asserts", []) or []:
        try:
            ok = eval(a, {"__builtins__": {}}, env)
        except Exception as e:
            fails.append(f"assert error in `{a}`: {type(e).__name__}: {e}"); continue
        if not ok:
            fails.append(f"assert failed: `{a}`")
    for lit, a in (cfg.get("literals") or {}).items():
        try:
            ok = eval(a, {"__builtins__": {}}, env)
        except Exception as e:
            fails.append(f"literal '{lit}' assert error in `{a}`: {e}"); continue
        if not ok:
            fails.append(f"literal '{lit}' is not backed by the data: `{a}` is False")
    if fails:
        raise FactsError("facts check failed:\n" + "\n".join("  - " + f for f in fails))
    if write:
        os.makedirs(story.build_dir, exist_ok=True)
        json.dump({"facts": facts, "provenance": meta, "asserts": cfg.get("asserts", []), "literals": cfg.get("literals", {})},
                  open(os.path.join(story.build_dir, "facts.json"), "w"), ensure_ascii=False, indent=1, default=_jsonable)
    return facts


def _jsonable(o):
    try:
        import numpy as np
        if isinstance(o, np.generic):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
    except Exception:
        pass
    return str(o)
