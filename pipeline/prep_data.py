"""Prep: NASA FIRMS VIIRS S-NPP 375 m country archive (Argentina, 2012-2025) -> points + stats.
Filter: type == 0 ("presumed vegetation fire") AND confidence in {nominal, high} (low-confidence detections dropped, conservative).
Province: point-in-polygon against INDEC Censo 2022 province polygons (dissolved radios, ../contar-con-datos-agua/v7/data/natgeo_v7.json);
points that fall in no polygon (coast/border simplification) -> nearest province centroid-free: nearest polygon by distance.
Outputs data/points.npz (lon, lat, t = fractional month index since 2012-01, prov idx) and data/stats.json."""
import json, numpy as np, pandas as pd, shapely
D = '../data/raw/'
G = json.load(open('../data/natgeo_v7.json'))
NAMES = {'02':'CABA','06':'Buenos Aires','10':'Catamarca','14':'Córdoba','18':'Corrientes','22':'Chaco','26':'Chubut','30':'Entre Ríos',
 '34':'Formosa','38':'Jujuy','42':'La Pampa','46':'La Rioja','50':'Mendoza','54':'Misiones','58':'Neuquén','62':'Río Negro','66':'Salta',
 '70':'San Juan','74':'San Luis','78':'Santa Cruz','82':'Santa Fe','86':'Santiago del Estero','90':'Tucumán','94':'Tierra del Fuego'}
codes = sorted(G['prov']); polys = [shapely.MultiPolygon([shapely.Polygon(r) for r in G['prov'][c]]).buffer(0) for c in codes]
d = pd.read_parquet(D + 'viirs_all.parquet')
tot_all = len(d); n_type0 = int((d.type == 0).sum()); n_type0_low = int(((d.type == 0) & (d.confidence == 'l')).sum())
d = d[(d.type == 0) & (d.confidence != 'l')].copy()
dt = pd.to_datetime(d.acq_date)
d['t'] = (dt.dt.year - 2012) * 12 + (dt.dt.month - 1) + (dt.dt.day - 1) / dt.dt.days_in_month + d.acq_time.astype(int) // 100 / 24 / 30
lon, lat = d.longitude.values, d.latitude.values
prov = np.full(len(d), -1)
for i, p in enumerate(polys):
    shapely.prepare(p); m = (prov < 0) & shapely.contains_xy(p, lon, lat); prov[m] = i
miss = np.where(prov < 0)[0]
pts = shapely.points(lon[miss], lat[miss])
dist = np.stack([shapely.distance(p, pts) for p in polys], 1)
prov[miss] = dist.argmin(1)
d['prov'] = [codes[i] for i in prov]
print('type0', len(d), 'of', tot_all, 'unmatched->nearest', len(miss), 'max dist deg', dist.min(1).max() if len(miss) else 0)
np.savez_compressed(D + 'points.npz', lon=lon.astype(np.float32), lat=lat.astype(np.float32), t=d.t.values.astype(np.float32), prov=prov.astype(np.int8), conf=(d.confidence.map({'l':0,'n':1,'h':2}).values).astype(np.int8))
S = {}
S['total_used'] = int(len(d)); S['total_all_types'] = int(tot_all); S['type0_all_conf'] = n_type0; S['type0_low_conf_dropped'] = n_type0_low
S['by_year'] = {int(k): int(v) for k, v in d.groupby('year').size().items()}
yrs = S['by_year']; others = [v for k, v in yrs.items() if k != 2020]
S['mean_excl_2020'] = float(np.mean(others)); S['median_excl_2020'] = float(np.median(others))
S['ratio_2020_vs_median_others'] = yrs[2020] / S['median_excl_2020']
S['by_prov'] = {NAMES[c]: int(v) for c, v in d.groupby('prov').size().sort_values(ascending=False).items()}
S['by_prov_year'] = {NAMES[c]: {int(y): int(v) for y, v in g.groupby('year').size().items()} for c, g in d.groupby('prov')}
d['m'] = dt.dt.month
S['by_month_all'] = {int(k): int(v) for k, v in d.groupby('m').size().items()}
S['by_year_month'] = {f'{y}-{m:02d}': int(v) for (y, m), v in d.groupby(['year', 'm']).size().items()}
S['peak_month'] = max(S['by_year_month'], key=S['by_year_month'].get)
json.dump(S, open(D + 'stats.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: S[k] for k in ['total_used','type0_all_conf','type0_low_conf_dropped','by_year','mean_excl_2020','median_excl_2020','ratio_2020_vs_median_others','peak_month']}, indent=1))
print(list(S['by_prov'].items())[:10])
for p in ['Entre Ríos','Córdoba','Corrientes','Chaco','Chubut','Río Negro','Neuquén']: print(p, S['by_prov_year'][p])
print(S['by_month_all'])

T = S['total_used']; P = S['by_prov']
REG = {'NEA': ['Formosa','Chaco','Corrientes','Misiones'], 'NOA': ['Salta','Jujuy','Tucumán','Santiago del Estero','Catamarca','La Rioja'],
       'Patagonia': ['Neuquén','Río Negro','Chubut','Santa Cruz','Tierra del Fuego']}
S['regions'] = REG
S['share_norte_NEA_NOA'] = sum(P.get(p, 0) for r in ['NEA','NOA'] for p in REG[r]) / T
S['share_patagonia'] = sum(P.get(p, 0) for p in REG['Patagonia']) / T
S['share_aug_sep'] = (S['by_month_all'][8] + S['by_month_all'][9]) / T
S['years_peak_in_aug_sep'] = [y for y in range(2012, 2026) if max(range(1, 13), key=lambda m: S['by_year_month'].get(f'{y}-{m:02d}', 0)) in (8, 9)]
json.dump(S, open(D + 'stats.json', 'w'), ensure_ascii=False, indent=1)
for k in ['share_norte_NEA_NOA','share_patagonia','share_aug_sep','years_peak_in_aug_sep']: print(k, S[k])
