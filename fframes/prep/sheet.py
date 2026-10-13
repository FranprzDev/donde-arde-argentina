"""Side-by-side QA contact sheet: Python v10 frame (left) vs fframes frame (right) at the same timestamps.
Usage: python3 prep/sheet.py OUT.jpg PYDIR FFDIR t1 t2 ...  (frames named <t>s.png)"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
out, pyd, ffd, ts = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
w, h = 800, 450; pad = 8; lab = 34
f = ImageFont.truetype(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media", "Inter600.ttf"), 22)
sheet = Image.new("RGB", (2 * w + 3 * pad, len(ts) * (h + lab) + pad), (30, 30, 34)); d = ImageDraw.Draw(sheet)
for i, t in enumerate(ts):
    y = pad + i * (h + lab)
    for j, (dd, name) in enumerate(((pyd, "Python v10"), (ffd, "fframes"))):
        try: im = Image.open(f"{dd}/{t}s.png").convert("RGB").resize((w, h), Image.LANCZOS)
        except FileNotFoundError: im = Image.new("RGB", (w, h), (60, 0, 0))
        x = pad + j * (w + pad); sheet.paste(im, (x, y + lab - 4))
        d.text((x + 4, y + 2), f"{name}  t = {t} s", font=f, fill=(235, 230, 222))
sheet.save(out, quality=88); print(out, sheet.size)
