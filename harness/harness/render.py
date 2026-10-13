"""Frame compositor + parallel chunked renderer + final mux.

    R = Renderer(story); img = R.frame(12.5)          # one PIL frame
    render_video(story, workers=2)                    # chunks -> concat -> music -> -14 LUFS -> mp4

Chunks (build/chunks/c_00000.mp4 ...) are reused when the story hasn't changed (hash of story.yaml + facts + code),
so an interrupted render resumes where it stopped."""
import hashlib
import json
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import time

import numpy as np
from PIL import Image

from .core.fx import Canvas, clamp, decay, finish, left_shade, mixc, put_text
from .layers import LayerSet

CHUNK = 60


class Renderer:
    def __init__(self, story):
        self.story = story
        self.W, self.H, self.S = story.W, story.H, story.H / 1080
        self.theme = story.theme
        self.world = story.world
        self.fps = story.fps
        self.layers = LayerSet(self)
        m = story.cfg.get("map") or {}
        hc = self.world.camera(m["home_camera"]) if (self.world and m.get("home_camera")) else None
        self.ref_zoom = float(m.get("ref_zoom", hc[2] if hc else 30.0))
        self.density_k = float(m.get("density_k", 1.0))
        self.reveals = sorted(x for b in story.beats for x in b.reveals() if x is not None)
        self.shakes = [(b.text_t0, b.shake) for b in story.beats if b.shake]

    # ---------------- camera ----------------
    def cam_at(self, t, beat=None):
        b = beat or self.story.beat_at(t)
        c = b.camera_at(t)
        if c is None:
            return None
        dx = dy = 0.0
        for t0, amp in self.shakes:
            e = decay(t, t0, 0.13)
            if e > 0.01:
                u = t - t0; dx += amp * e * math.sin(u * 83); dy += amp * e * math.cos(u * 67)
        return (c[0], c[1], c[2], c[3] + dx, c[4] + dy)

    # ---------------- one frame ----------------
    def frame(self, t):
        st = self.story; b = st.beat_at(t)
        fr = b.full_frame(t, self)
        if fr is None and b.is_map and self.world is not None:
            cam = self.cam_at(t, b)
            A = np.asarray(self.world.base_map(cam, self.W, self.H, self.theme), np.float32)
            if b.prev is not None and t < b.start + 1.2:
                A = b.prev.draw_post(A, t, cam, self)
            A = self.layers.draw(A, b, t, cam)
            A = b.draw_map(A, t, cam, self)
            if b.next is not None:
                A = b.next.draw_pre(A, t, cam, self)
            sp = b.cfg.get("spotlight")
            if sp:
                from .beats.base import spotlight
                k = float(sp.get("dim", 0.25)) * clamp((t - b.start - b.tin + 0.3) / 0.5) * (1 - clamp((t - b.end + 0.2) / 0.5))
                A = spotlight(A, self.world, self.world.rings(sp["regions"]), cam, k, self.W, self.H)
            A = left_shade(A, b.shade(t))
            fr = Canvas(self.W, self.H, self.theme, Image.fromarray(np.clip(A, 0, 255).astype(np.uint8)))
            self.outline_all(fr, b, t, cam)
            for bb in st.beats:
                if bb is not b and bb.start - 0.01 <= t < bb.ui_end + 0.4 and bb.is_map:
                    bb.draw_ui(fr, t, cam, self)
            b.draw_ui(fr, t, cam, self)
            self.legend(fr, b, t)
        elif fr is None:
            fr = Canvas(self.W, self.H, self.theme)
            b.draw_ui(fr, t, None, self)
        flash = min(1.0, sum(0.3 * decay(t, x, 0.11) for x in self.reveals))
        return finish(fr, t, self.fps, flash=flash)

    def outline_all(self, fr, b, t, cam):
        mode = b.cfg.get("outline_all")
        if not mode:
            return
        th = self.theme; W = self.world
        prev_has = b.prev is not None and b.prev.cfg.get("outline_all")
        k = 1.0 if prev_has else clamp((t - b.start) / 0.6)
        glow = mode == "glow"
        cw = (clamp((t - b.start - 0.2) / 0.8) if glow else 0.0) * (1 - clamp((t - b.end + 0.3) / 0.5) if (b.next is None or not b.next.cfg.get("outline_all")) else 1)
        al = int((70 + 150 * cw) * k)
        for rs in W.regions.values():
            for r in rs:
                if len(r) < 3:
                    continue
                pts = W.ring_px(r, cam); fr.d.line(pts + pts[:1], fill=th.c["accent2"] + (al,), width=max(1, int((3 if cw > 0.5 else 2) * fr.S)))
                if cw > 0.003:
                    fr.glow_line(pts + pts[:1], mixc((0, 0, 0), th.c["accent2"], 0.55 * cw), 6)
        if cw > 0.003:
            if not hasattr(self, "_all_out"):
                self._all_out = W.outline()
            for r in self._all_out:
                pts = W.ring_px(r, cam); fr.d.line(pts + pts[:1], fill=th.c["hot"] + (int(230 * cw),), width=max(1, int(3 * fr.S)))
                fr.glow_line(pts + pts[:1], mixc((0, 0, 0), th.c["accent"], cw), 12)

    def legend(self, fr, b, t):
        if not b.legend:
            return
        items = self.layers.legends(b)
        if not items:
            return
        a = clamp((t - b.start - 0.3) / 0.4) if (b.prev is None or not b.prev.legend) else 1.0
        if b.next is None or not b.next.legend:
            a *= 1 - clamp((t - b.end + 0.3) / 0.3)
        fl = self.theme.font("body", 48, 600)
        for j, (spec, txt) in enumerate(items):
            la = a * self.layers.alpha(b, spec, t)
            col = b.c(spec.get("legend_color", "muted"))
            put_text(fr, (self.W / self.S - 80 - fr.tw(txt, fl), 1080 - 60 - 62 * j), txt, fl, col, la)

    def activity(self, t):
        return sum(b.activity(t) for b in self.story.beats if b.start - 0.2 <= t < b.end + 0.5)


# ---------------- video ----------------
def story_hash(story):
    h = hashlib.sha1()
    h.update(open(story.path, "rb").read())
    h.update(json.dumps(story.facts, sort_keys=True, default=str).encode())
    here = os.path.dirname(os.path.abspath(__file__))
    for root, _, files in os.walk(here):
        for f in sorted(files):
            if f.endswith(".py"):
                h.update(open(os.path.join(root, f), "rb").read())
    h.update(f"{story.W}x{story.H}@{story.fps}".encode())
    return h.hexdigest()[:12]


_R = None


def _render_chunk(args):
    f0, f1, path, crf = args
    R = _R
    tmp = path + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{R.W}x{R.H}", "-r", str(R.fps), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-profile:v", "high", tmp],
                         stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(R.frame(f / R.fps).convert("RGB").tobytes())
    p.stdin.close(); rc = p.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg failed on chunk {path}")
    os.replace(tmp, path)
    return path


def render_video(story, workers=None, out=None, fresh=False, log=print, music=True):
    global _R
    from .audio.music import make_music
    from .audio.master import master_and_mux
    R = Renderer(story); _R = R
    N = int(round(story.total * story.fps))
    tag = "" if story.scale >= 1 else f"_preview{int(story.scale * 100)}"
    cdir = os.path.join(story.build_dir, "chunks" + tag)
    hsh = story_hash(story)
    stamp = os.path.join(cdir, "HASH")
    if fresh or (os.path.exists(stamp) and open(stamp).read().strip() != hsh):
        shutil.rmtree(cdir, ignore_errors=True)
    os.makedirs(cdir, exist_ok=True); open(stamp, "w").write(hsh)
    crf = int(story.video.get("crf", 20))
    jobs = [(f, min(f + CHUNK, N), os.path.join(cdir, f"c_{f:05d}.mp4"), crf) for f in range(0, N, CHUNK)]
    todo = [j for j in jobs if not os.path.exists(j[2])]
    workers = workers or max(1, min(os.cpu_count() or 1, 4))
    log(f"render {story.slug}: {N} frames {story.W}x{story.H}@{story.fps}, {len(todo)}/{len(jobs)} chunks to do, {workers} workers")
    t0 = time.time()
    if todo:
        if workers == 1:
            for j in todo:
                _render_chunk(j); log(f"  {os.path.basename(j[2])} {time.time() - t0:.0f}s")
        else:
            ctx = mp.get_context("fork")
            with ctx.Pool(workers) as pool:
                for k, pth in enumerate(pool.imap_unordered(_render_chunk, todo)):
                    log(f"  {k + 1}/{len(todo)} {os.path.basename(pth)} {time.time() - t0:.0f}s")
    lst = os.path.join(cdir, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.basename(j[2])}'\n" for j in jobs))
    video_only = os.path.join(story.build_dir, f"video_only{tag}.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video_only], check=True)
    out = out or os.path.join(story.build_dir, f"{story.slug}{tag}.mp4")
    if music:
        wav = make_music(story, R, os.path.join(story.build_dir, f"music{tag}.wav"), log=log)
        rep = master_and_mux(video_only, wav, out, story.total, story.cfg.get("audio") or {}, log=log)
    else:
        import tempfile
        tmp = os.path.join(tempfile.mkdtemp(prefix="harness_mux_"), os.path.basename(out))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video_only, "-c", "copy", "-movflags", "+faststart", tmp], check=True)
        shutil.move(tmp, out)
        rep = {}
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                               capture_output=True, text=True).stdout.strip() or 0)
    if dur < story.total - 0.2:
        raise RuntimeError(f"output is {dur:.2f}s but the story is {story.total:.2f}s: a chunk is missing or truncated (re-run with --fresh)")
    rep.update(dict(out=out, duration=dur, frames=N, seconds_wall=round(time.time() - t0, 1)))
    json.dump(rep, open(os.path.join(story.build_dir, f"render_report{tag}.json"), "w"), indent=1)
    log(f"done: {out} ({dur:.2f}s) {json.dumps({k: v for k, v in rep.items() if k != 'out'})}")
    return rep
