"""Paso 3 · Pobreza y voto: indicadores y hallazgos.

Las correlaciones se ponderan por votos válidos para que un municipio de 1 000 votantes
no pese igual que São Paulo. La correlación dentro de cada estado resta el promedio
del estado: así el resultado no refleja solo que el Nordeste es más pobre y más lulista.
Genera datos/procesados/resultados.json.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "datos" / "procesados"
df = pd.read_csv(PROC / "municipios.csv")


def r_ponderada(x, y, w):
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    return cov / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))


def quitar_estado(serie, pesos, estados):
    media = (serie * pesos).groupby(estados).transform("sum") / pesos.groupby(estados).transform("sum")
    return serie - media


def correlaciones(d, x="pobreza_12"):
    fila = {}
    for y in ["pct_lula_t1", "pct_lula_t2", "cambio_lula"]:
        w = d.validos_t2
        fila[y] = {
            "ponderada": r_ponderada(d[x], d[y], w),
            "sin_ponderar": d[x].corr(d[y]),
            "spearman": spearmanr(d[x], d[y]).statistic,
            "dentro_estado": r_ponderada(quitar_estado(d[x], w, d.uf), quitar_estado(d[y], w, d.uf), w),
        }
    return fila


def agregar(g):
    return {
        "municipios": len(g),
        "poblacion": g.poblacion.sum(),
        "pobreza": 100 * (g.pobreza_12 * g.poblacion).sum() / g.poblacion.sum() / 100,
        "lula_t1": 100 * g.lula_t1.sum() / g.validos_t1.sum(),
        "lula_t2": 100 * g.lula_t2.sum() / g.validos_t2.sum(),
        "cambio": 100 * g.lula_t2.sum() / g.validos_t2.sum() - 100 * g.lula_t1.sum() / g.validos_t1.sum(),
        "votos_ganados": g.lula_t2.sum() - g.lula_t1.sum(),
    }


def tabla(columna):
    return pd.DataFrame({k: agregar(g) for k, g in df.groupby(columna, sort=True)}).T


# Decil 1 = municipios menos pobres, decil 10 = más pobres
df["decil"] = pd.qcut(df.pobreza_12, 10, labels=range(1, 11)).astype(int)
# Quintil 1 = menos pobres, quintil 5 = más pobres; cada uno junta dos deciles
df["quintil"] = (df.decil + 1) // 2

r_todos = correlaciones(df)
r_14 = correlaciones(df, "pobreza_14")
deciles, quintiles, regiones, estados = tabla("decil"), tabla("quintil"), tabla("region"), tabla("uf")
r_region = {k: correlaciones(g)["pct_lula_t2"]["ponderada"] for k, g in df.groupby("region")}

viraron_lula = df[(df.ganador_t1 == "Flávio") & (df.ganador_t2 == "Lula")]
viraron_flavio = df[(df.ganador_t1 == "Lula") & (df.ganador_t2 == "Flávio")]
sin_cambio = df[df.ganador_t1 == df.ganador_t2]
p90, p10 = df.pobreza_12.quantile(0.9), df.pobreza_12.quantile(0.1)
pobres_flavio = df[(df.pobreza_12 >= p90) & (df.ganador_t2 == "Flávio")]
ricos_lula = df[(df.pobreza_12 <= p10) & (df.ganador_t2 == "Lula")]

resultados = {
    "nacional": agregar(df),
    "correlaciones": r_todos,
    "correlaciones_pobreza_14": r_14,
    "correlacion_por_region": r_region,
    "deciles": deciles.reset_index(names="decil").to_dict("records"),
    "quintiles": quintiles.reset_index(names="quintil").to_dict("records"),
    "regiones": regiones.reset_index(names="region").to_dict("records"),
    "estados": estados.reset_index(names="uf").to_dict("records"),
    "ganadores_t2": df.ganador_t2.value_counts().to_dict(),
    "viraron_a_lula": len(viraron_lula),
    "viraron_a_flavio": len(viraron_flavio),
    "pobreza_mediana": {
        "viraron_a_lula": viraron_lula.pobreza_12.median(),
        "viraron_a_flavio": viraron_flavio.pobreza_12.median(),
        "sin_cambio": sin_cambio.pobreza_12.median(),
    },
    "pobres_con_flavio": len(pobres_flavio),
    "ricos_con_lula": len(ricos_lula),
    "umbral_pobres": p90,
    "umbral_ricos": p10,
}
(PROC / "resultados.json").write_text(
    json.dumps(resultados, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
df.to_csv(PROC / "municipios.csv", index=False, encoding="utf-8")

pd.set_option("display.width", 140, "display.max_columns", 20, "display.float_format", "{:,.2f}".format)
print("=== Correlación con pobreza (<= 1/2 salario mínimo) ===")
print(pd.DataFrame(r_todos).T)
print("\n=== Igual, con pobreza extrema (<= 1/4) ===")
print(pd.DataFrame(r_14).T)
print("\n=== Correlación con % Lula 2a vuelta, por región ===")
print(pd.Series(r_region).to_string())
print("\n=== Quintiles de pobreza ===")
print(quintiles)
print("\n=== Deciles de pobreza ===")
print(deciles)
print("\n=== Regiones ===")
print(regiones)
print("\n=== Estados, de mayor a menor subida de Lula ===")
print(estados.sort_values("cambio", ascending=False)[["pobreza", "lula_t1", "lula_t2", "cambio"]])
print("\n=== Ganadores por municipio, 2a vuelta (G1: Lula en 2.874) ===")
print(df.ganador_t2.value_counts().to_string())
print(f"\nViraron a Lula: {len(viraron_lula)} (G1: 211) · Viraron a Flávio: {len(viraron_flavio)}")
print("Pobreza mediana:", {k: round(v, 1) for k, v in resultados["pobreza_mediana"].items()})
print(viraron_lula.nlargest(8, "validos_t2")[["municipio", "uf", "pobreza_12", "pct_lula_t1", "pct_lula_t2"]].to_string(index=False))
print(f"\nMás pobres (>= {p90:.1f}%) donde ganó Flávio: {len(pobres_flavio)} de {(df.pobreza_12 >= p90).sum()}")
print(pobres_flavio.nlargest(5, "validos_t2")[["municipio", "uf", "pobreza_12", "pct_lula_t2"]].to_string(index=False))
print(f"\nMenos pobres (<= {p10:.1f}%) donde ganó Lula: {len(ricos_lula)} de {(df.pobreza_12 <= p10).sum()}")
print(ricos_lula.nlargest(5, "validos_t2")[["municipio", "uf", "pobreza_12", "pct_lula_t2"]].to_string(index=False))