"""QA: stills of every beat, a contact sheet, a phone-size check and a timing report.

    python -m harness qa stories/x/story.yaml [--scale 0.5] [--times 3.2 10.5]

Writes build/qa/: still_<t>.png, contact_sheet.png, phone_sheet.png (each still at 390 px wide = a phone held
upright), timing.md / timing.json (every text block: words, needed vs actual hold), qa.json (summary; also the
final video's duration and loudness when the mp4 exists). Exit code != 0 if a check fails."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

from .core.fx import ASSETS

PHONE_PORTRAIT_W = 390     # CSS px of a typical phone held upright (video plays inline, full width)
PHONE_LANDSCAPE_W = 844    # same phone, full-screen landscape


def key_times(story):
    ts = []
    for b in story.beats:
        if b.blocks:
            blk = max(b.blocks, key=lambda x: x.nwords)
            if blk.t0 is not None and blk.t1 is not None:
                ts.append((b.id, min(b.end - 0.06, blk.t0 + 0.7 * (blk.t1 - blk.t0))))
                continue
        ts.append((b.id, b.start + 0.6 * (b.end - b.start)))
    return ts


def timing_report(story):
    rows = story.rules.report_rows(story.beats)
    md = [f"# Timing — {story.title}", "", f"Total: **{story.total:.2f} s** (max {story.video['max_duration']} s) · "
          f"rules: min font {story.rules.min_font_px:g} px, ≤ {story.rules.max_words_per_beat} words/beat, "
          f"hold ≥ max({story.rules.min_hold}, {story.rules.sec_per_word}·words + {story.rules.base_hold}) s", "",
          "| beat | type | start–end (s) | text | words | on screen (s) | needed (s) | ok |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        hold = "" if r["hold"] is None else f"{r['hold']:.2f}"
        need = "—" if r["need"] is None else f"{r['need']:.2f}"
        md.append(f"| {r['beat']} | {r['type']} | {r['start']:.2f}–{r['end']:.2f} | {r['text']} | {r['words']} | {hold} | {need} | "
                  f"{'✅' if r['ok'] else '❌'} |")
    return rows, "\n".join(md) + "\n"


def sheet(paths_labels, out, tile_w, cols=4, bg=(18, 18, 22)):
    ims = [(Image.open(p).convert("RGB"), lab) for p, lab in paths_labels]
    if not ims:
        return None
    w0, h0 = ims[0][0].size; tw_ = tile_w; th_ = int(h0 * tile_w / w0); lab_h = max(16, int(tile_w * 0.07))
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * tw_ + (cols + 1) * 8, rows * (th_ + lab_h) + (rows + 1) * 8), bg)
    d = ImageDraw.Draw(S)
    f = ImageFont.truetype(os.path.join(ASSETS, "fonts", "JetBrainsMono.ttf"), max(10, int(lab_h * 0.7)))
    for i, (im, lab) in enumerate(ims):
        r, c = divmod(i, cols); x = 8 + c * (tw_ + 8); y = 8 + r * (th_ + lab_h + 8)
        S.paste(im.resize((tw_, th_), Image.LANCZOS), (x, y + lab_h)); d.text((x, y), lab, font=f, fill=(230, 226, 220))
    S.save(out); return out


def run_qa(story, times=None, log=print, render_stills=True):
    from .render import Renderer
    qdir = os.path.join(story.build_dir, "qa"); os.makedirs(qdir, exist_ok=True)
    rows, md = timing_report(story)
    open(os.path.join(qdir, "timing.md"), "w").write(md)
    json.dump(rows, open(os.path.join(qdir, "timing.json"), "w"), indent=1, default=float)
    R = Renderer(story)
    kt = sorted(key_times(story) + [(story.beat_at(float(x)).id, float(x)) for x in (times or [])], key=lambda k: k[1])
    stills = []
    if render_stills:
        for bid, t in kt:
            p = os.path.join(qdir, f"still_{t:06.2f}.png")
            R.frame(t).save(p); stills.append((p, f"{t:5.2f}s {bid}"))
            log(f"still {t:6.2f}s  {bid}")
        sheet(stills, os.path.join(qdir, "contact_sheet.png"), 480)
        sheet(stills, os.path.join(qdir, "phone_sheet.png"), PHONE_PORTRAIT_W, cols=2)
    mf = story.rules.min_font_px
    smallest = min([s for b in story.beats for blk in b.blocks for s in blk.sizes] + [mf])
    used = sorted({s for _, s in story.theme.sizes_used}) if story.theme.sizes_used else []
    if used:
        smallest = min(smallest, used[0])
    phone = dict(smallest_design_px=smallest,
                 portrait_px=round(smallest * PHONE_PORTRAIT_W / 1920, 1),
                 landscape_px=round(smallest * PHONE_LANDSCAPE_W / 1920, 1))
    phone["landscape_ok"] = phone["landscape_px"] >= float((story.cfg.get("qa") or {}).get("phone_min_px", 18))
    summary = dict(title=story.title, total=story.total, max_duration=story.video["max_duration"],
                   timing_ok=all(r["ok"] for r in rows), phone=phone, stills=[p for p, _ in stills])
    mp4 = os.path.join(story.build_dir, f"{story.slug}.mp4")
    if os.path.exists(mp4):
        import subprocess
        from .audio.master import measure
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                                   capture_output=True, text=True).stdout.strip() or 0)
        summary["video"] = dict(path=mp4, duration=dur, duration_ok=dur <= story.video["max_duration"] + 0.05, **measure(mp4))
    json.dump(summary, open(os.path.join(qdir, "qa.json"), "w"), indent=1, default=float)
    ok = summary["timing_ok"] and phone["landscape_ok"] and summary.get("video", {}).get("duration_ok", True)
    log(f"QA {'OK' if ok else 'FAILED'}: total {story.total:.2f}s, smallest text {smallest}px "
        f"(phone upright {phone['portrait_px']}px, landscape {phone['landscape_px']}px) -> {qdir}")
    return ok, summary
