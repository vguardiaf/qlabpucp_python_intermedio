"""Grafica la pobreza monetaria de la ENAHO por área, sexo, edad o departamento.

Decisiones de método:
- Toda tasa se pondera con facpob07: es la suma de los factores de los pobres entre la
  suma de los factores del grupo.
- Los grupos de edad son 0 a 17, 18 a 29, 30 a 59 y 60 o más.
- El título dice el hallazgo (qué grupo es más pobre y por cuánto), calculado con las cifras
  del gráfico, nunca escrito a mano. El subtítulo dice qué se mide, dónde y cuándo.
- El diseño está fijo aquí para que cada figura salga igual: barras desde cero y ordenadas,
  un solo color (el grupo destacado en un tono más oscuro), el valor escrito, la línea del
  promedio nacional, la fuente y 200 dpi.
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parents[4]
SALIDAS = BASE / "salidas"
FIGURAS = BASE / "figuras"

COLOR = "#7fa6c9"
DESTACADO = "#1f5a8c"
CORTES = {"area": "área", "sexo": "sexo", "edad": "grupo de edad", "departamento": "departamento"}
BORDES_EDAD = [-1, 17, 29, 59, 200]
ETIQUETAS_EDAD = ["0 a 17 años", "18 a 29 años", "30 a 59 años", "60 años o más"]


def agrupar(base, por):
    if por == "area":
        return base["urbano"].map({True: "Urbana", False: "Rural"})
    if por == "sexo":
        return base["p207"].map({1: "Hombres", 2: "Mujeres"})
    if por == "departamento":
        return base["nombre_departamento"]
    return pd.cut(base["p208a"], bins=BORDES_EDAD, labels=ETIQUETAS_EDAD).astype("object")


def tasa(base):
    peso = base["facpob07"].astype("float64")
    return 100 * (peso * base["pobre"]).sum() / peso.sum()


def pobreza_por_grupo(base, por):
    grupo = agrupar(base, por)
    assert grupo.notna().all(), f"hay personas sin grupo en {por}"
    peso = base["facpob07"].astype("float64")
    tabla = pd.DataFrame({"grupo": grupo, "peso": peso, "peso_pobre": peso * base["pobre"]})
    sumas = tabla.groupby("grupo")[["peso", "peso_pobre"]].sum()
    return (100 * sumas["peso_pobre"] / sumas["peso"]).sort_values()


def titulo_analitico(pobreza, por, nacional):
    """Arma el título con el hallazgo, a partir de las cifras del gráfico."""
    alto, bajo = pobreza.idxmax(), pobreza.idxmin()
    brecha = pobreza.max() - pobreza.min()
    if por == "departamento":
        encima = int((pobreza > nacional).sum())
        return (f"La pobreza de {alto} ({pobreza.max():.1f} %) es {pobreza.max() / pobreza.min():.1f} veces la de "
                f"{bajo} ({pobreza.min():.1f} %); {encima} de 25 departamentos superan el promedio nacional")
    if brecha < 1:
        return f"La pobreza es casi igual entre {alto.lower()} ({pobreza.max():.1f} %) y {bajo.lower()} ({pobreza.min():.1f} %)"
    if por == "area":
        return f"La pobreza rural ({pobreza['Rural']:.1f} %) supera a la urbana en {brecha:.1f} puntos porcentuales"
    return f"El grupo de {alto} es el más pobre ({pobreza.max():.1f} %), {brecha:.1f} puntos más que el de {bajo}"


def graficar(pobreza, por, anio, nacional, ruta):
    alto = len(pobreza) * 0.32 + 1.6 if por == "departamento" else 4.5
    fig, ax = plt.subplots(figsize=(9, alto))
    colores = [DESTACADO if g == pobreza.idxmax() else COLOR for g in pobreza.index]
    barras = ax.barh(pobreza.index, pobreza.values, color=colores)
    ax.bar_label(barras, fmt="%.1f %%", padding=4, fontsize=8 if por == "departamento" else 10)
    ax.axvline(nacional, color="#444", linestyle="--", linewidth=1)
    ax.set_ylim(-1.1, len(pobreza) - 0.4)
    ax.text(nacional, -0.95, f" Perú: {nacional:.1f} %", fontsize=8, color="#444", va="bottom")
    ax.set_xlim(0, pobreza.max() * 1.15)
    ax.set_xlabel("% de personas en situación de pobreza monetaria")
    ax.set_title(titulo_analitico(pobreza, por, nacional), loc="left", fontweight="bold", fontsize=10.5, pad=22, wrap=True)
    ax.text(0, 1.01, f"Pobreza monetaria por {CORTES[por]}, Perú {anio}. Estimación ponderada con facpob07.",
            transform=ax.transAxes, fontsize=8.5, color="#555")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=8.5 if por == "departamento" else 10)
    fig.text(0.01, 0.01, f"Fuente: INEI, ENAHO {anio} (módulos 34 y 02). Residentes habituales.", fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(ruta, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--por", required=True, choices=sorted(CORTES))
    parser.add_argument("--anio", type=int, default=2024)
    args = parser.parse_args()

    entrada = SALIDAS / f"personas_{args.anio}.parquet"
    if not entrada.exists():
        sys.exit(f"Falta {entrada.name}. Usa primero la skill limpiando-enaho.")

    base = pd.read_parquet(entrada)
    if args.por == "departamento" and "nombre_departamento" not in base:
        sys.exit("La base no tiene nombre_departamento. Vuelve a correr la skill limpiando-enaho.")
    pobreza = pobreza_por_grupo(base, args.por)
    nacional = tasa(base)

    FIGURAS.mkdir(exist_ok=True)
    ruta = FIGURAS / f"pobreza_{args.por}.png"
    graficar(pobreza, args.por, args.anio, nacional, ruta)

    print(titulo_analitico(pobreza, args.por, nacional))
    print(f"Perú: {nacional:.1f} %")
    for grupo, valor in pobreza.sort_values(ascending=False).items():
        print(f"{grupo}: {valor:.1f} %")
    print(f"Guardado {ruta.relative_to(BASE)}")


if __name__ == "__main__":
    main()
