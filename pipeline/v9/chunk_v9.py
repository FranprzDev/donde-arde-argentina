import sys, os, subprocess
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import render_v9 as R
f0, f1 = int(sys.argv[1]), int(sys.argv[2])
os.makedirs("build", exist_ok=True)
out = f"build/c_{f0:05d}.mp4"
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1920x1080", "-r", "30", "-i", "-",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", out + ".tmp.mp4"], stdin=subprocess.PIPE)
for f in range(f0, f1): p.stdin.write(R.render_at(f / 30).convert("RGB").tobytes())
p.stdin.close(); p.wait(); os.replace(out + ".tmp.mp4", out); print("done", out, flush=True)
