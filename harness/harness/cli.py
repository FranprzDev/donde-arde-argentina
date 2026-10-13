"""Command line.

  python -m harness check  STORY        validate story.yaml, compute facts.json, check every readability rule (fast)
  python -m harness facts  STORY        compute + print facts.json
  python -m harness still  STORY T...   render single frames to build/qa/still_T.png
  python -m harness qa     STORY        stills + contact sheet + phone sheet + timing report (+ loudness if the mp4 exists)
  python -m harness render STORY        full video -> build/<slug>.mp4   (--preview = half size, preview fps; --workers N; --fresh)
  python -m harness new    NAME         scaffold stories/NAME/ from templates/story
  python -m harness beats               list the available beat types

STORY is a story.yaml path or its folder. Exit code 1 + a readable message on any rule/fact failure."""
import argparse
import json
import os
import sys

from .errors import HarnessError


def _story(path, scale=1.0, check=True):
    from .story import Story
    s = Story.load(path, scale)
    s.prepare(check=check)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(prog="harness", description="Config-driven data-story videos (story.yaml -> mp4).")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "facts", "qa", "render", "still"):
        p = sp.add_parser(name); p.add_argument("story")
        if name == "still":
            p.add_argument("times", nargs="+", type=float)
        if name in ("render", "qa", "still"):
            p.add_argument("--preview", action="store_true", help="half resolution (and video.preview_fps)")
            p.add_argument("--scale", type=float, default=None)
        if name == "render":
            p.add_argument("--workers", type=int, default=None); p.add_argument("--fresh", action="store_true")
            p.add_argument("--no-music", action="store_true"); p.add_argument("--out")
        if name == "qa":
            p.add_argument("--times", nargs="*", type=float, default=[])
    p = sp.add_parser("new"); p.add_argument("name"); p.add_argument("--dir", default="stories")
    sp.add_parser("beats")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "new":
            from .scaffold import new_story
            print(new_story(a.name, a.dir)); return 0
        if a.cmd == "beats":
            from .beats import REGISTRY
            for k, v in sorted(REGISTRY.items()):
                doc = (sys.modules[v.__module__].__doc__ or "").strip().splitlines()
                print(f"{k:16s} {v.__module__.split('.')[-1]}.py")
            return 0
        scale = getattr(a, "scale", None) or (0.5 if getattr(a, "preview", False) else 1.0)
        s = _story(a.story, scale)
        if a.cmd == "check":
            from .qa import timing_report
            _, md = timing_report(s)
            print(md); print(f"OK: {len(s.beats)} beats, {s.total:.2f}s <= {s.video['max_duration']}s, all readability rules pass")
        elif a.cmd == "facts":
            print(json.dumps(s.facts, ensure_ascii=False, indent=1, default=str))
        elif a.cmd == "still":
            from .render import Renderer
            R = Renderer(s); d = os.path.join(s.build_dir, "qa"); os.makedirs(d, exist_ok=True)
            for t in a.times:
                p = os.path.join(d, f"still_{t:06.2f}.png"); R.frame(t).save(p); print(p)
        elif a.cmd == "qa":
            from .qa import run_qa
            ok, _ = run_qa(s, a.times, log=lambda *x: print(*x, flush=True))
            return 0 if ok else 1
        elif a.cmd == "render":
            from .render import render_video
            render_video(s, a.workers, a.out, a.fresh, log=lambda *x: print(*x, flush=True), music=not a.no_music)
    except HarnessError as e:
        print(f"\n✗ {e}\n", file=sys.stderr); return 1
    except FileNotFoundError as e:
        print(f"\n✗ {e}\n", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
