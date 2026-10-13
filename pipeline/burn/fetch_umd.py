"""MODIS MCD64A1 C6.1 monthly burned area, 'Win06'+'Win07' GeoTIFF windows (geographic lat/lon, ~500 m, value = burn day of year,
0 unburned, -1/-2 unmapped/water) from the University of Maryland public SFTP (fuoco.geog.umd.edu, user 'fire', password 'burnt',
documented in the MCD64A1 C6.1 User Guide). Keeps only the Argentina box, saved as int16 npz per month."""
import paramiko, rasterio, numpy as np, os, sys, io
from rasterio.windows import from_bounds
os.makedirs("umd", exist_ok=True)
BOX = (-74.0, -55.2, -53.4, -21.6)
t = paramiko.Transport(("fuoco.geog.umd.edu", 22)); t.connect(username="fire", password="burnt"); s = paramiko.SFTPClient.from_transport(t)
import calendar
for y in range(2012, 2027):
    for m in range(1, 13):
        if (y, m) > (2026, 7): break
        doy = sum(calendar.monthrange(y, k)[1] for k in range(1, m)) + 1
        out = f"umd/{y}-{m:02d}.npz"
        if os.path.exists(out): continue
        res = {}
        for win, box in (("Win06", (-74.0, -35.0, -53.4, -21.6)), ("Win07", (-74.0, -55.2, -54.0, -35.0))):
            fn = f"MCD64monthly.A{y}{doy:03d}.{win}.061.burndate.tif"
            try:
                s.get(f"/data/MODIS/C61/MCD64A1/TIFF/{win}/{y}/{fn}", "umd/tmp.tif")
            except Exception as e:
                print("MISSING", y, m, win, e, flush=True); continue
            with rasterio.open("umd/tmp.tif") as r:
                w = from_bounds(*box, r.transform).round_offsets().round_lengths(); a = r.read(1, window=w); tr = r.window_transform(w)
            res[win] = (a, np.array(tr)[:6], fn)
        if len(res) < 2: continue
        np.savez_compressed(out, a6=res["Win06"][0], t6=res["Win06"][1], a7=res["Win07"][0], t7=res["Win07"][1], files=np.array([res["Win06"][2], res["Win07"][2]]))
        print(y, m, int((res["Win06"][0] > 0).sum()), int((res["Win07"][0] > 0).sum()), flush=True)
print("UMD_DONE")
