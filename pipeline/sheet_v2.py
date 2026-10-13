"""QA contact sheet: python3 sheet_v2.py out.png [--phone] t1 t2 ... (renders frames, labels timestamps)"""
import sys
from PIL import Image, ImageDraw
import render_v2 as R
out = sys.argv[1]; args = sys.argv[2:]; phone = "--phone" in args
ts = [float(x) for x in args if x != "--phone"]
w, h = (640, 360) if phone else (960, 540); cols = 3 if phone else 2
S = Image.new("RGB", (cols * w, ((len(ts) + cols - 1) // cols) * (h + 24)), (40, 40, 40)); d = ImageDraw.Draw(S)
for i, t in enumerate(ts):
    im = R.render_at(t); x, y = (i % cols) * w, (i // cols) * (h + 24)
    S.paste(im.resize((w, h), Image.LANCZOS), (x, y + 24)); d.text((x + 6, y + 4), f"t={t:.2f}s", fill=(255, 255, 0))
S.convert("RGB").save(out.replace(".png", ".jpg"), quality=85); print(out)
