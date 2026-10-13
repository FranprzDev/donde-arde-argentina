"""PRIVATE port of v9: every on-screen number, read from the v9 pipeline outputs (stats_v2/v4, ranking_v7, tucuman_stats)
and the points archive. Same asserts as render_v9.py."""
import os

import numpy as np


def _ddmmyyyy(name):
    y, m, d = name.split("_")[-1].split("-"); return f"{d}/{m}/{y}"


def compute(ctx):
    S = ctx.json("data/stats_v4.json"); V = ctx.json("data/stats_v2.json"); RK = ctx.json("data/ranking_v7.json")
    TUS = ctx.json("data/tucuman_stats.json")
    pts = ctx.data("hotspots")
    monthly = np.array(V["monthly"], float)
    assert int(monthly.sum()) == S["total_focos"] == len(pts)
    er_n = int(((pts.region == "30") & (pts.t >= 96) & (pts.t < 108)).sum())
    rows = [{"code": r["code"], "name": r["name"], "value": r["ha_unique"]} for r in RK["rows"]]
    return {
        "total_focos": S["total_focos"],
        "hum_share_known": S["causas"]["humana_sobre_conocida"],
        "hum_10": int(round(S["causas"]["humana_sobre_conocida"] * 10)),
        "y0": 2012, "y1": 2025,
        "uniq_ha": RK["total_ha_unique"], "share_country": RK["share_country_burned"],
        "ranking": rows, "top_n": 5, "top5_share": RK["top5_share"],
        "tuc_pct": round(100 * S["tuc"]["share_cane_zafra"]), "tuc_cane_zafra": TUS["cane_zafra"],
        "er_2020": S["er_2020"], "er_2020_points": er_n, "er_ratio": S["er_ratio_other13"],
        "pa25": int(S["comarca_2025_ha"] // 1000) * 1000, "pa26": int(S["comarca_2026_ha"] // 1000) * 1000,
        "pa_x": int(S["comarca_ratio"]), "pa_ratio": S["comarca_ratio"],
        "tuc_s2_date": _ddmmyyyy("tuc_2025-09-23"), "er_s2_date": _ddmmyyyy("delta_2020-09-23"),
    }
