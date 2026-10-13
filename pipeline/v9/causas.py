"""Fire CAUSES from the official open dataset «Causas y cantidad de incendios por provincia» (Ministerio de Ambiente y
Desarrollo Sostenible, Programa Nacional de Estadística Forestal; datos.ambiente.gob.ar, dataset 12f60bea…, resource 93c2f293…,
1993-2019). The original portal was retired (URL now 301-redirects to datos.gob.ar, where this resource is no longer listed);
the CSV was retrieved byte-for-byte from the Internet Archive capture of the original download URL.
Human = negligencia + intencional. Shares reported over ALL fires (with 'desconocida' stated) and over fires with KNOWN cause.
Writes data/causas_stats.json."""
import json, os, pandas as pd
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
d = pd.read_csv(os.path.join(D, "incendios-cantidad-causas-provincia_1993-2019.csv"), sep=";", encoding="latin-1")
C = {"incendio_total_numero": "tot", "incendio_negligencia_numero": "neg", "incendio_intencional_numero": "int",
     "incendio_natural_numero": "nat", "incendio_desconocida_numero": "desc"}
d = d.rename(columns=C).rename(columns={"incendio_anio": "anio", "incendio_provincia": "prov"})
for c in C.values(): d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0).astype(int)
d["chk"] = d.neg + d.int + d.nat + d.desc - d.tot
def sh(x):
    T, n, i, na, de = (int(x[c].sum()) for c in ("tot", "neg", "int", "nat", "desc")); k = n + i + na
    return dict(total=T, negligencia=n, intencional=i, natural=na, desconocida=de, conocida=k,
                humana_sobre_total=(n + i) / T if T else None, natural_sobre_total=na / T if T else None,
                desconocida_sobre_total=de / T if T else None, humana_sobre_conocida=(n + i) / k if k else None,
                natural_sobre_conocida=na / k if k else None)
out = dict(rows=len(d), years=[int(d.anio.min()), int(d.anio.max())], n_prov=int(d.prov.nunique()),
           rows_parts_ne_total=int((d.chk != 0).sum()), mismatch_rows=d[d.chk != 0][["anio", "prov", "tot", "chk"]].values.tolist(),
           all_1993_2019=sh(d), y2010_2019=sh(d[d.anio >= 2010]), y2015_2019=sh(d[d.anio >= 2015]),
           sin_BA_1993_2019=sh(d[d.prov != "Buenos Aires"]),
           by_prov={p: sh(g) for p, g in d.groupby("prov")},
           by_year={int(y): sh(g) for y, g in d.groupby("anio")})
json.dump(out, open(os.path.join(D, "causas_stats.json"), "w"), indent=1, ensure_ascii=False, default=int)
if __name__ == "__main__":
    for k in ("all_1993_2019", "y2010_2019", "y2015_2019", "sin_BA_1993_2019"):
        print(k, {a: (round(b, 4) if isinstance(b, float) else b) for a, b in out[k].items()})
    print("mismatch rows", out["rows_parts_ne_total"], out["mismatch_rows"][:10])
    for p in ["Entre Ríos", "Corrientes", "Córdoba", "Chubut", "Santiago del Estero", "Chaco", "Formosa", "Río Negro", "Neuquén", "La Pampa", "Salta", "Buenos Aires"]:
        s = out["by_prov"].get(p); print(p, s and {a: (round(b, 3) if isinstance(b, float) else b) for a, b in s.items()})
    for y, s in out["by_year"].items(): print(y, s["total"], s["desconocida"], round(s["humana_sobre_conocida"] or 0, 3))
    print(sorted(out["by_prov"]))
