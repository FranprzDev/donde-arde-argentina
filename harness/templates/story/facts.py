"""__NAME__ — every number on screen is computed here (never typed in story.yaml).

Starter version: ranks the regions of data/provincias_ign.geojson by their geodesic area, so the scaffold renders
out of the box with REAL numbers. Replace it with your own dataset (see data/README.md)."""
from pyproj import Geod
import shapely

GEOD = Geod(ellps="WGS84")


def compute(ctx):
    w = ctx.world
    rows = []
    for code, rings in w.regions.items():
        # continental + islands only: rings entirely south of 60°S (the Antarctic sector in the IGN layer) are left out
        km2 = sum(abs(GEOD.geometry_area_perimeter(shapely.Polygon(r))[0]) for r in rings if r[:, 1].max() > -60) / 1e6
        rows.append({"code": code, "name": w.names[code], "value": km2})
    rows.sort(key=lambda r: -r["value"])
    total = sum(r["value"] for r in rows)
    return {
        "ranking": rows,
        "top_n": 3,
        "top_share": sum(r["value"] for r in rows[:3]) / total,
        "first_name": rows[0]["name"].upper(),
        "first_code": rows[0]["code"],
        "first_km2": {"value": rows[0]["value"], "source": "geodesic area of data/provincias_ign.geojson north of 60°S (IGN, CC BY 4.0)"},
    }
