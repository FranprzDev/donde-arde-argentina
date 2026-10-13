"""Every number on screen for the toy story, computed from the bundled CSV (USGS ComCat, public domain)."""
import numpy as np

NOA = ["66", "38", "90", "10", "46", "86"]       # Salta, Jujuy, Tucumán, Catamarca, La Rioja, Santiago del Estero


def compute(ctx):
    q = ctx.data("sismos")                        # Points: lon, lat, t (months since 2015-01), region (province code)
    total = len(q)
    codes, counts = np.unique(q.region, return_counts=True)
    names = ctx.world.names
    rows = sorted([{"code": c, "name": names[c], "value": int(n)} for c, n in zip(codes, counts)], key=lambda r: -r["value"])
    for c in ctx.world.regions:                   # provinces with zero quakes still belong to the ranking
        if c not in codes:
            rows.append({"code": c, "name": names[c], "value": 0})
    top_n = 3
    top_share = sum(r["value"] for r in rows[:top_n]) / total
    first = rows[0]
    years = 2015 + (q.t // 12).astype(int)
    return {
        "total": {"value": total, "source": "data/sismos_usgs_2015_2024.csv (USGS ComCat, M>=4.5, epicentro en la Argentina)"},
        "min_mag": float(q.cols["mag"].min()),
        "year_first": int(years.min()), "year_last": int(years.max()),
        "ranking": rows,
        "top_n": top_n,
        "top_share": top_share,
        "first_name": first["name"].upper(), "first_code": first["code"], "first_n": first["value"],
        "first_share": first["value"] / total,
        "noa_share": float(np.isin(q.region, NOA).mean()),
    }
