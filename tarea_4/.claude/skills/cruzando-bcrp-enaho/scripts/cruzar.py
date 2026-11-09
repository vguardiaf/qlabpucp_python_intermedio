"""Cruza la profundización financiera departamental (BCRP) con la pobreza monetaria (ENAHO).

Decisiones de método:
- Crédito y depósitos vienen de salidas/bcrp_credito_<anio>.csv y bcrp_depositos_<anio>.csv, que
  guarda la herramienta MCP datos_departamentales (millones de S/, saldos a fin de año).
- La población y la pobreza de cada departamento salen de la ENAHO procesada, ponderadas con
  facpob07. Profundización = soles de crédito (o depósitos) por habitante.
- Se une por código de departamento (ubigeo[:2]), nunca por nombre, y se exigen los 25.
- La asociación se mide con la correlación de Spearman (rangos), robusta a valores extremos, y con
  Pearson sobre el logaritmo. Se repite sin Lima y Callao, donde se registra buena parte del
  crédito de empresas con sede en la capital. Es una asociación entre 25 departamentos, no un efecto.
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[4]
SALIDAS = BASE / "salidas"
FIGURAS = BASE / "figuras"
CAPITAL = ["15", "07"]  # Lima y Callao


def leer_bcrp(nombre, anio):
    ruta = SALIDAS / f"bcrp_{nombre}_{anio}.csv"
    if not ruta.exists():
        sys.exit(f"Falta {ruta.name}. Pídelo con la herramienta MCP datos_departamentales "
                 f"(etiqueta '{nombre}', anio {anio}).")
    df = pd.read_csv(ruta, dtype={"departamento": str})
    assert df["departamento"].nunique() == 25, f"{ruta.name} no trae 25 departamentos"
    return df.set_index("departamento")[["codigo", "valor"]].add_prefix(f"{nombre}_")


def enaho(anio):
    ruta = SALIDAS / f"personas_{anio}.parquet"
    if not ruta.exists():
        sys.exit(f"Falta {ruta.name}. Usa primero la skill limpiando-enaho.")
    base = pd.read_parquet(ruta)
    peso = base["facpob07"].astype("float64")
    t = pd.DataFrame({"departamento": base["departamento"], "nombre": base["nombre_departamento"],
                      "poblacion": peso, "pobres": peso * base["pobre"]})
    g = t.groupby("departamento").agg(nombre=("nombre", "first"), poblacion=("poblacion", "sum"),
                                      pobres=("pobres", "sum"))
    g["pobreza_pct"] = 100 * g["pobres"] / g["poblacion"]
    return g.drop(columns="pobres")


def correlaciones(df):
    filas = []
    for muestra, d in [("25 departamentos", df), ("sin Lima ni Callao (23)", df.drop(index=CAPITAL))]:
        for var in ["credito_pc", "depositos_pc", "profundizacion_pc"]:
            filas.append({
                "muestra": muestra, "indicador": var, "n": len(d),
                # Spearman = Pearson sobre los rangos (evita depender de scipy)
                "spearman": round(d[var].rank().corr(d["pobreza_pct"].rank()), 3),
                "pearson_log": round(np.log(d[var]).corr(d["pobreza_pct"]), 3),
            })
    return pd.DataFrame(filas)


def graficar(df, corr, anio, ruta):
    fig, ejes = plt.subplots(1, 2, figsize=(12, 5.4), sharey=True)
    for ax, var, nombre in [(ejes[0], "credito_pc", "Crédito"), (ejes[1], "depositos_pc", "Depósitos")]:
        rho = corr.query("muestra == '25 departamentos' and indicador == @var")["spearman"].iloc[0]
        ax.scatter(df[var], df["pobreza_pct"], color="#1f5a8c", s=28)
        for cod, f in df.iterrows():
            ax.annotate(f["nombre"], (f[var], f["pobreza_pct"]), xytext=(3, 2), textcoords="offset points",
                        fontsize=6.5, color="#333")
        ax.set_xscale("log")
        ax.set_xlabel(f"{nombre} por habitante, S/ (escala logarítmica)")
        ax.set_title(f"{nombre}: Spearman = {rho:.2f}", loc="left", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    ejes[0].set_ylabel("Pobreza monetaria (% de personas)")
    rc = corr.query("muestra == '25 departamentos' and indicador == 'profundizacion_pc'")["spearman"].iloc[0]
    sentido = "menos" if rc < 0 else "más"
    fig.suptitle(f"Los departamentos con más crédito y depósitos por habitante tienden a tener {sentido} pobreza "
                 f"(Spearman {rc:.2f}, {anio})", x=0.01, ha="left", fontweight="bold", fontsize=11)
    fig.text(0.01, 0.01, f"Fuente: BCRP, crédito directo y depósitos por departamento, saldos a fin de {anio} "
             f"(datos_departamentales); INEI, ENAHO {anio}, población y pobreza ponderadas con facpob07. "
             "Asociación entre 25 departamentos, no efecto causal.", fontsize=7)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--anio", type=int, default=2024)
    anio = parser.parse_args().anio

    df = enaho(anio).join(leer_bcrp("credito", anio), how="inner").join(leer_bcrp("depositos", anio), how="inner")
    assert len(df) == 25, f"solo {len(df)} departamentos unidos por código"
    df["credito_pc"] = df["credito_valor"] * 1e6 / df["poblacion"]
    df["depositos_pc"] = df["depositos_valor"] * 1e6 / df["poblacion"]
    df["profundizacion_pc"] = df["credito_pc"] + df["depositos_pc"]
    df["rango_profundizacion"] = df["profundizacion_pc"].rank(ascending=False).astype(int)
    df["rango_pobreza"] = df["pobreza_pct"].rank(ascending=False).astype(int)

    corr = correlaciones(df)
    df.round(2).reset_index().to_csv(SALIDAS / "cruce_departamental.csv", index=False, encoding="utf-8")
    corr.to_csv(SALIDAS / "correlaciones.csv", index=False, encoding="utf-8")
    FIGURAS.mkdir(exist_ok=True)
    ruta = FIGURAS / "dispersion_profundizacion_pobreza.png"
    graficar(df, corr, anio, ruta)

    print(corr.to_string(index=False))
    print()
    cols = ["nombre", "credito_pc", "depositos_pc", "pobreza_pct"]
    print("Más profundización:\n" + df.sort_values("profundizacion_pc", ascending=False)[cols].head(5).round(1).to_string())
    print("Menos profundización:\n" + df.sort_values("profundizacion_pc")[cols].head(5).round(1).to_string())
    print(f"\nGuardado salidas/cruce_departamental.csv, salidas/correlaciones.csv y {ruta.relative_to(BASE)}")


if __name__ == "__main__":
    main()
