import sys
from PIL import Image, ImageDraw
fs = sys.argv[2:]; out = sys.argv[1]; cols = 3; w, h = 640, 360
rows = (len(fs) + cols - 1) // cols
S = Image.new("RGB", (cols * w, rows * h), (255, 255, 255)); d = ImageDraw.Draw(S)
for i, f in enumerate(fs):
    im = Image.open(f).convert("RGB").resize((w, h)); S.paste(im, ((i % cols) * w, (i // cols) * h)); d.text(((i % cols) * w + 5, (i // cols) * h + 5), f.split("_")[-1], fill=(0, 255, 0))
S.save(out)
