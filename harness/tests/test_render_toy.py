"""Smoke test: render the bundled toy story end-to-end (half size, preview fps), then check duration and loudness."""
import os
import shutil
import subprocess

import pytest

from harness.audio.master import measure
from harness.qa import run_qa
from harness.render import render_video
from harness.story import Story

HERE = os.path.dirname(os.path.abspath(__file__))
TOY = os.path.join(HERE, "..", "stories", "sismos-argentina", "story.yaml")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_render_toy(tmp_path):
    s = Story.load(TOY, scale=0.5).prepare()
    out = str(tmp_path / "toy.mp4")
    rep = render_video(s, workers=2, out=out, fresh=True, log=lambda *a: None)
    assert os.path.exists(out)
    assert abs(rep["duration"] - s.total) < 0.25
    m = measure(out)
    assert abs(m["I_LUFS"] + 14) <= 1.0 and m["TP_dBTP"] <= -1.5
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", out], capture_output=True, text=True).stdout.strip()
    assert probe == f"{s.W},{s.H}"
    ok, summary = run_qa(s, log=lambda *a: None)
    assert ok and os.path.exists(os.path.join(s.build_dir, "qa", "contact_sheet.png"))
