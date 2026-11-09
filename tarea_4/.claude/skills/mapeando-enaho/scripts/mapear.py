"""Mapea la pobreza monetaria de la ENAHO por departamento.

Decisiones de método:
- Se une por código, ubigeo[:2] con FIRST_IDDP, nunca por nombre: el GeoJSON trae los
  nombres en mayúsculas y sin tildes, y la ENAHO no trae nombres.
- Se exigen 25 departamentos con dato. Lima (15) y Callao (07) van separados.
- El mapa se pondera con facpob07. Las referencias de la clase usan factor07 x mieperho
  en los hogares, así que se validan con ese mismo método y no con las cifras del mapa:
  entre ambos ponderadores hay hasta 0.51 puntos por departamento (Huánuco).
- Se compara con los 25 departamentos de referencias/pobreza_departamento_2024.csv (la
  referencia de la Sesión 16, con un decimal) y se guarda salidas/comparacion_mapa.csv. Si
  algún departamento se aleja más de 0.1 puntos, el script se detiene sin guardar el mapa.
- La escala va de claro a oscuro desde 0, en un solo color.
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = Path(__file__).resolve().parents[4]
SALIDAS = BASE / "salidas"
MAPAS = BASE / "mapas"
LIMITES = BASE / "datos" / "peru_departamental_simple.geojson"

TOTAL_DEPARTAMENTOS = 25
TOLERANCIA = 0.1
REFERENCIA = Path(__file__).resolve().parents[1] / "referencias" / "pobreza_departamento_2024.csv"


def pobreza_por_departamento(base):
    peso = base["facpob07"].astype("float64")
    tabla = pd.DataFrame(
        {"departamento": base["departamento"], "peso": peso, "peso_pobre": peso * base["pobre"]}
    )
    sumas = tabla.groupby("departamento")[["peso", "peso_pobre"]].sum()
    return (100 * sumas["peso_pobre"] / sumas["peso"]).rename("pobreza").reset_index()


def unir(limites, pobreza):
    limites["FIRST_IDDP"] = limites["FIRST_IDDP"].astype(str).str.strip()
    assert limites["FIRST_IDDP"].str.len().eq(2).all(), "FIRST_IDDP perdió ceros a la izquierda"
    assert len(limites) == TOTAL_DEPARTAMENTOS, "el GeoJSON no trae 25 departamentos"
    mapa = limites.merge(
        pobreza, left_on="FIRST_IDDP", right_on="departamento", how="left", validate="1:1"
    )
    sin_dato = mapa.loc[mapa["pobreza"].isna(), "NOMBDEP"].tolist()
    assert not sin_dato, f"departamentos sin dato: {sin_dato}"
    return mapa

def pobreza_como_referencia(base):
    hogares = base.drop_duplicates(["conglome", "vivienda", "hogar"])
    peso = hogares["factor07"].astype("float64") * hogares["mieperho"]
    pobres = peso * hogares["pobre"]
    departamento = hogares["departamento"]
    return 100 * pobres.groupby(departamento).sum() / peso.groupby(departamento).sum()

def validar(base, mapa):
    """Compara los 25 departamentos con la referencia de la Sesión 16 y guarda la tabla."""
    referencia = pd.read_csv(REFERENCIA, dtype={"ccdd": str})
    assert len(referencia) == TOTAL_DEPARTAMENTOS, "la referencia no trae 25 departamentos"
    hogares = pobreza_como_referencia(base).rename("calculado_hogares")
    personas = mapa.set_index("FIRST_IDDP")["pobreza"].rename("mapa_personas")
    tabla = referencia.rename(columns={"pobreza_pct": "referencia_sesion16"}).set_index("ccdd")
    tabla = tabla.join(hogares).join(personas)
    assert tabla[["calculado_hogares", "mapa_personas"]].notna().all().all(), "faltan departamentos al comparar"
    tabla["diferencia"] = (tabla["calculado_hogares"] - tabla["referencia_sesion16"]).round(3)
    tabla["dentro_tolerancia"] = tabla["diferencia"].abs() <= TOLERANCIA
    tabla[["calculado_hogares", "mapa_personas"]] = tabla[["calculado_hogares", "mapa_personas"]].round(3)
    tabla.reset_index().to_csv(SALIDAS / "comparacion_mapa.csv", index=False, encoding="utf-8")
    fallas = tabla.index[~tabla["dentro_tolerancia"]].tolist()
    print(f"Comparación con la Sesión 16: {tabla['dentro_tolerancia'].sum()}/25 dentro de ±{TOLERANCIA} "
          f"(diferencia máxima {tabla['diferencia'].abs().max():.3f}). Guardado salidas/comparacion_mapa.csv")
    if fallas:
        sys.exit(f"Departamentos fuera de la referencia: {fallas}. No se guarda el mapa.")

def dibujar(mapa, anio, ruta):
    fig, ax = plt.subplots(figsize=(7, 9))
    mapa.plot(
        column="pobreza",
        ax=ax,
        cmap="Blues",
        vmin=0,
        vmax=mapa["pobreza"].max(),
        edgecolor="white",
        linewidth=0.5,
        legend=True,
        legend_kwds={"label": "% de personas", "shrink": 0.6},
    )
    ax.set_axis_off()
    ax.set_title(f"Pobreza monetaria por departamento, Perú {anio}", loc="left", fontweight="bold")
    fig.text(0.05, 0.03, f"Fuente: INEI, ENAHO {anio}", fontsize=9)
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--anio", type=int, default=2024)
    anio = parser.parse_args().anio

    entrada = SALIDAS / f"personas_{anio}.parquet"
    if not entrada.exists():
        sys.exit(f"Falta {entrada.name}. Usa primero la skill limpiando-enaho.")
    if not LIMITES.exists():
        sys.exit(f"Falta datos/{LIMITES.name}. Bájalo del repo del curso, la URL está en SKILL.md.")

    base = pd.read_parquet(entrada)
    mapa = unir(gpd.read_file(LIMITES), pobreza_por_departamento(base))

    for fila in mapa.sort_values("pobreza", ascending=False).itertuples():
        print(f"{fila.FIRST_IDDP} {fila.NOMBDEP}: {fila.pobreza:.1f} %")
    validar(base, mapa)

    MAPAS.mkdir(exist_ok=True)
    ruta = MAPAS / "pobreza_departamento.png"
    dibujar(mapa, anio, ruta)
    print(f"Guardado {ruta.relative_to(BASE)}: {len(mapa)} departamentos con dato")


if __name__ == "__main__":
    main()