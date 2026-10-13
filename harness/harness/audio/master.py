"""Loudness normalisation + mux with ffmpeg. Target (story `audio:`): integrated -14 LUFS, true peak <= -1.5 dBTP
(measured on the FINAL AAC file, since AAC encoding overshoots peaks). Two-pass `loudnorm` (linear) on the wav, mux,
measure with `ebur128`; if the muxed file's true peak is too hot, it re-runs with a lower ceiling (up to 3 times).

    audio: {lufs: -14, true_peak: -1.5, lra: 11, bitrate: 192k}"""
import json
import os
import re
import shutil
import subprocess
import tempfile


def measure(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    lra = float(re.findall(r"LRA:\s+(-?[\d.]+) LU", r)[-1])
    return dict(I_LUFS=I, TP_dBTP=tp, LRA=lra)


def loudnorm(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af, "-ar", "48000", dst], check=True)
    return dst


def master_and_mux(video, wav, out, duration, cfg=None, log=print):
    cfg = cfg or {}
    I = float(cfg.get("lufs", -14)); TPmax = float(cfg.get("true_peak", -1.5)); lra = float(cfg.get("lra", 11))
    br = str(cfg.get("bitrate", "192k"))
    ceil = TPmax - 0.8
    rep = {}
    # +faststart rewrites the file in place; some mounted/network filesystems refuse that, so mux in a local temp dir
    tmp = os.path.join(tempfile.mkdtemp(prefix="harness_mux_"), os.path.basename(out))
    for attempt in range(4):
        norm = wav.replace(".wav", "_norm.wav")
        loudnorm(wav, norm, I, ceil, lra)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", norm, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", br, "-ar", "48000", "-t", f"{duration:.3f}", "-movflags", "+faststart", tmp], check=True)
        rep = measure(tmp)
        log(f"audio pass {attempt + 1}: I={rep['I_LUFS']} LUFS, TP={rep['TP_dBTP']} dBTP (ceiling {ceil:.1f})")
        if rep["TP_dBTP"] <= TPmax and abs(rep["I_LUFS"] - I) <= 1.0:
            break
        ceil -= max(0.5, rep["TP_dBTP"] - TPmax + 0.2)
    shutil.move(tmp, out)
    rep["audio_ok"] = rep["TP_dBTP"] <= TPmax and abs(rep["I_LUFS"] - I) <= 1.0
    if not rep["audio_ok"]:
        log(f"WARNING: audio not within target (I {I}±1 LUFS, TP <= {TPmax}): {rep}")
    return rep
