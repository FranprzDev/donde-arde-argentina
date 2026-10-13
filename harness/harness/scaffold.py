"""`harness new NAME`: copy templates/story into stories/NAME with the name filled in."""
import os
import re
import shutil

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "story")


def new_story(name, root="stories"):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    dst = os.path.join(root, slug)
    if os.path.exists(dst):
        raise SystemExit(f"{dst} already exists")
    shutil.copytree(TEMPLATE, dst)
    for dp, _, files in os.walk(dst):
        for f in files:
            p = os.path.join(dp, f)
            if f.endswith((".yaml", ".py", ".md")):
                s = open(p, encoding="utf-8").read().replace("__SLUG__", slug).replace("__NAME__", name)
                open(p, "w", encoding="utf-8").write(s)
    return (f"created {dst}/\n  1. put your open data in {dst}/data/ and note its source + licence in {dst}/SOURCES.md\n"
            f"  2. compute every on-screen number in {dst}/facts.py\n  3. write the beats in {dst}/story.yaml\n"
            f"  4. python -m harness check {dst}  ->  python -m harness qa {dst} --preview  ->  make video STORY={dst}/story.yaml")
