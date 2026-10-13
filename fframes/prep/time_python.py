"""Wall-clock timing of the v10 Python renderer for a frame range, encoded exactly like v10/chunk_v10.py
(rawvideo pipe -> libx264 veryfast crf 14). Writes nothing into v10/; the clip goes to fframes/build/.
Usage: python3 prep/time_python.py F0 F1 [WORKERS]   (WORKERS parallel processes, like build_v10.sh's 2 workers)"""
import os, subprocess, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
V10 = os.path.join(os.path.dirname(ROOT), "v10")
f0, f1 = int(sys.argv[1]), int(sys.argv[2]); workers = int(sys.argv[3]) if len(sys.argv) > 3 else 2
if os.environ.get("TP_CHILD"):
    sys.path.insert(0, V10)
    import render_v10 as R
    a, b, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[4]
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", "30", "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(a, b): p.stdin.write(R.render_at(f / 30).convert("RGB").tobytes())
    p.stdin.close(); p.wait(); sys.exit(0)
os.makedirs(os.path.join(ROOT, "build", "py"), exist_ok=True)
t0 = time.time()
step = (f1 - f0 + workers - 1) // workers; procs = []
for w in range(workers):
    a, b = f0 + w * step, min(f1, f0 + (w + 1) * step)
    if a >= b: continue
    out = os.path.join(ROOT, "build", "py", f"py_{a:05d}_{b:05d}.mp4")
    procs.append(subprocess.Popen([sys.executable, __file__, str(a), str(b), str(workers), out], env=dict(os.environ, TP_CHILD="1")))
for p in procs: p.wait()
dt = time.time() - t0
print(json.dumps(dict(frames=f1 - f0, workers=workers, seconds=round(dt, 1), fps=round((f1 - f0) / dt, 2))))
