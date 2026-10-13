"""v4 render assets (deterministic, from saved data): scar pyramids (MODIS MCD64A1), event masks, CABA tile placement over the
Corrientes 2022 scar, the Tucumán cane-zone outline (EEAOC departments), photo cards and re-typeset headline cards."""
import json, os, math, numpy as np, cv2, shapely
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
OUT = "assets"; os.makedirs(OUT, exist_ok=True)
G = json.load(open("data/scar_grid.json")); H, W, D, LON0, LAT1 = G["H"], G["W"], G["D"], G["LON0"], G["LAT1"]
FONTS = "../../contar-con-datos-agua/fonts"
def font(kind, size, wt=None):
    f = ImageFont.truetype(os.path.join(FONTS, {"anton": "Anton.ttf", "inter": "Inter.ttf", "mono": "JetBrainsMono.ttf"}[kind]), size)
    try:
        if kind == "inter": f.set_variation_by_axes([min(32, max(14, size)), wt or 400])
        elif kind == "mono": f.set_variation_by_axes([wt or 400])
    except Exception: pass
    return f
# ---------- scar pyramids ----------
def pyramid(a, name, levels=6):
    if os.path.exists(f"{OUT}/{name}.npz"): return
    out = {}
    cur = a.astype(np.float32)
    for k in range(levels):
        out[f"l{k}"] = np.clip(cur, 0, 255).astype(np.uint8)
        cur = cv2.resize(cur, (max(1, cur.shape[1] // 2), max(1, cur.shape[0] // 2)), interpolation=cv2.INTER_AREA)
    np.savez_compressed(f"{OUT}/{name}.npz", **out)
cnt = np.load("data/scar_count.npy")
with np.errstate(divide="ignore"): inten = np.where(cnt > 0, 110 + 145 * np.clip(np.log1p(cnt.astype(np.float32) - 1) / math.log1p(7), 0, 1), 0)   # 1 burn -> 110, 8+ -> 255
pyramid(inten, "scar_all")
for k in ("er_2020", "corr_2022", "pat_2025", "pat_2026"):
    m = np.unpackbits(np.load(f"data/scar_{k}.npy"))[:H * W].reshape(H, W)
    pyramid(m.astype(np.float32) * 255, f"scar_{k}")
# ---------- CABA silhouettes over the Corrientes Jan-Feb 2022 scar ----------
B = json.load(open("data/burn_stats.json"))
ring = np.array(B["caba_ring"]); cx, cy = ring[:, 0].mean(), ring[:, 1].mean()
rel = ring - [cx, cy]
rel[:, 0] *= math.cos(math.radians(cy)) / math.cos(math.radians(-28.9))   # keep real km size at Corrientes latitude
N = int(math.floor(B["n_caba_corr"]))                       # whole Capitals that fit in the scar area (46.6 -> 46)
cosl = math.cos(math.radians(-28.9))
bw, bh = np.ptp(rel[:, 0]) * 1.04, np.ptp(rel[:, 1]) * 1.04
mco = np.unpackbits(np.load("data/scar_corr_2022.npy"))[:H * W].reshape(H, W).astype(np.float32)
cells = []
for lat in np.arange(-31.0, -26.9, bh):
    for lon in np.arange(-60.0, -55.4, bw):
        r0 = int((LAT1 - (lat + bh / 2)) / D); r1 = int((LAT1 - (lat - bh / 2)) / D); c0 = int((lon - bw / 2 - LON0) / D); c1 = int((lon + bw / 2 - LON0) / D)
        f = mco[max(0, r0):r1, max(0, c0):c1].mean() if r1 > r0 and c1 > c0 else 0
        cells.append((float(f), float(lon), float(lat)))
cells.sort(reverse=True)
tiles = [(lon, lat) for f, lon, lat in cells[:N]]
# order of appearance: north -> south sweep
tiles.sort(key=lambda p: (-p[1], p[0]))
json.dump(dict(rel=rel.tolist(), tiles=tiles, N=N, min_fill=cells[N - 1][0]), open(f"{OUT}/caba_tiles.json", "w"))
print("CABA tiles", N, "lowest scar fraction in a used cell", round(cells[N - 1][0], 3))
# ---------- Tucumán cane zone outline (12 departments, EEAOC RA 370) ----------
T = json.load(open("data/tucuman_stats.json")); import unicodedata
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(".", "").replace(" ", ""); return {"jbalberdi": "juanbautistaalberdi"}.get(s, s)
DEP = json.load(open("data/departamentos.geojson"))
u = shapely.union_all([shapely.geometry.shape(f["geometry"]).buffer(0) for f in DEP["features"] if f["properties"]["provincia"]["id"] == "90" and norm(f["properties"]["nombre"]) in set(T["cane12"])])
u = u.buffer(0.005).buffer(-0.005).simplify(0.004)
json.dump([list(map(list, g.exterior.coords)) for g in (u.geoms if hasattr(u, "geoms") else [u]) if g.area > 0.005], open(f"{OUT}/tuc_cane_zone.json", "w"))
# ---------- photo cards ----------
def card(src, name, w=480, h=320, crop=None):
    im = Image.open(src).convert("RGB")
    if crop: im = im.crop(crop)
    r = max(w / im.width, h / im.height); im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
    x0 = (im.width - w) // 2; y0 = (im.height - h) // 2; im = im.crop((x0, y0, x0 + w, y0 + h))
    pad = 18; out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0); ImageDraw.Draw(sh).rectangle((pad + 4, pad + 8, pad + w + 4, pad + h + 8), fill=200)
    out.paste(Image.new("RGBA", out.size, (0, 0, 0, 255)), (0, 0), sh.filter(ImageFilter.GaussianBlur(8)))
    out.paste(im, (pad, pad)); ImageDraw.Draw(out).rectangle((pad - 2, pad - 2, pad + w + 1, pad + h + 1), outline=(242, 240, 236, 255), width=3)
    out.save(f"{OUT}/{name}.png")
card("photos/c_05.jpg", "ph_delta")
card("photos/c_19.jpg", "ph_corr")
card("photos/c_23.jpg", "ph_brig")
card("photos/c_32.jpg", "ph_forest")
# ---------- headline cards: verbatim text, re-typeset; outlet + date as citation ----------
HL = json.load(open("headlines/selected.json"))
def wrap(s, f, maxw):
    words = s.split(); lines = [""]
    for wd in words:
        t = (lines[-1] + " " + wd).strip()
        if f.getlength(t) <= maxw: lines[-1] = t
        else: lines.append(wd)
    return lines
for i, h in enumerate(HL):
    fq = font("inter", 40, 700); fo = font("mono", 36, 800)
    lines = wrap("«" + h["show"] + "»", fq, 700)
    assert len(lines) <= 3, (h["show"], lines)
    wd = 760; ht = 36 + 46 + 52 * len(lines) + 28
    pad = 18; out = Image.new("RGBA", (wd + 2 * pad, ht + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0); ImageDraw.Draw(sh).rectangle((pad + 4, pad + 8, pad + wd + 4, pad + ht + 8), fill=200)
    out.paste(Image.new("RGBA", out.size, (0, 0, 0, 255)), (0, 0), sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(out)
    d.rectangle((pad, pad, pad + wd, pad + ht), fill=(242, 238, 230, 255))
    d.rectangle((pad, pad, pad + 10, pad + ht), fill=(255, 110, 30, 255))
    d.text((pad + 34, pad + 30), f"{h['outlet'].upper()} · {h['date']}", font=fo, fill=(150, 60, 20, 255), anchor="lt")
    for j, ln in enumerate(lines): d.text((pad + 34, pad + 30 + 52 + j * 52), ln, font=fq, fill=(20, 18, 18, 255), anchor="lt")
    out.save(f"{OUT}/hl_{i}.png")
    print("headline card", i, out.size, lines)
