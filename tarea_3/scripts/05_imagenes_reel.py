"""Paso 5 · Mapas y gráficos de cada escena del reel.

Genera reel/recursos/escena_1.png a escena_7.png, con el mismo fondo oscuro del video.
Todas las cifras salen de datos/procesados/municipios.csv.
"""
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

BASE = Path(__file__).resolve().parents[1]
SALIDA = BASE / "reel" / "recursos"
SALIDA.mkdir(parents=True, exist_ok=True)

FONDO, TEXTO, SUAVE, GRIS = "#1C1A17", "#F7F3EC", "#B8AE9F", "#3A3732"
LULA, FLAVIO, VIRO = "#F08A4B", "#4A90E2", "#2FD08F"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": TEXTO, "axes.labelcolor": SUAVE,
                     "xtick.color": SUAVE, "ytick.color": SUAVE})

df = pd.read_csv(BASE / "datos" / "procesados" / "municipios.csv")
df["quintil"] = (df.decil + 1) // 2
mapa = gpd.read_file(BASE / "datos" / "originales" / "municipios.geojson")
mapa["ibge"] = mapa["id"].astype(int)
mapa["geometry"] = mapa.geometry.simplify(0.01, preserve_topology=True)
mapa = mapa.merge(df, on="ibge", how="inner")


def figura():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100, facecolor=FONDO)
    ax.set_facecolor(FONDO)
    return fig, ax


def guardar(fig, n):
    fig.savefig(SALIDA / f"escena_{n}.png", facecolor=FONDO)
    plt.close(fig)


def dibujar_mapa(ax, **estilo):
    mapa.plot(ax=ax, linewidth=0, **estilo)
    ax.set_axis_off()


def leyenda(ax, elementos):
    for color, texto in elementos:
        ax.scatter([], [], c=color, s=90, marker="s", label=texto)
    ax.legend(loc="lower left", frameon=False, fontsize=15, labelcolor=TEXTO)


def coma(v, signo=False):
    return f"{v:+.1f}".replace(".", ",").replace("-", "−") if signo else f"{v:.1f}".replace(".", ",")


# Escena 1: ganador en la 2.a vuelta
fig, ax = figura()
dibujar_mapa(ax, color=mapa.ganador_t2.map({"Lula": LULA, "Flávio": FLAVIO}).tolist())
leyenda(ax, [(LULA, "Ganó Lula"), (FLAVIO, "Ganó Flávio")])
guardar(fig, 1)

# Escena 2: pobreza
fig, ax = figura()
violeta = LinearSegmentedColormap.from_list("pobreza", ["#2B2850", "#7C6FE0", "#E4DFFF"])
dibujar_mapa(ax, column="pobreza_12", cmap=violeta, vmin=0, vmax=80)
ax.text(0.02, 0.05, "Más claro = más pobreza", transform=ax.transAxes, fontsize=16, color=TEXTO)
guardar(fig, 2)

# Escenas 3 y 4: quintiles
filas = []
for k, g in df.groupby("quintil"):
    t1, t2 = 100 * g.lula_t1.sum() / g.validos_t1.sum(), 100 * g.lula_t2.sum() / g.validos_t2.sum()
    filas.append({"quintil": k, "pobreza": (g.pobreza_12 * g.poblacion).sum() / g.poblacion.sum(), "lula": t2, "cambio": t2 - t1})
q = pd.DataFrame(filas).set_index("quintil")
print(q.round(2).to_string())
nombres = [f"Q{i}\n{coma(p)} % pobres" for i, p in zip(q.index, q.pobreza)]


def barras(valores, colores, textos, n):
    fig, ax = figura()
    b = ax.bar(nombres, valores, color=colores, width=0.68)
    for r, t in zip(b, textos):
        ax.text(r.get_x() + r.get_width() / 2, r.get_height(), t, ha="center", va="bottom", fontsize=22, fontweight="bold")
    ax.set_ylim(0, max(valores) * 1.2)
    ax.yaxis.set_visible(False)
    ax.tick_params(axis="x", length=0, labelsize=14)
    for lado in ax.spines.values():
        lado.set_visible(False)
    fig.tight_layout()
    guardar(fig, n)


barras(q.lula, [LULA] * 5, [f"{coma(v)} %" for v in q.lula], 3)
destacar = q.cambio.idxmax()
barras(q.cambio, [VIRO if i == destacar else "#6A665E" for i in q.index], [coma(v, True) for v in q.cambio], 4)

# Escena 5: municipios que cambiaron de ganador
viraron = mapa.ganador_t1 != mapa.ganador_t2
fig, ax = figura()
dibujar_mapa(ax, color=viraron.map({True: VIRO, False: GRIS}).tolist())
rio = mapa[mapa.municipio == "Rio de Janeiro"].geometry.centroid.iloc[0]
ax.annotate("Río de Janeiro", (rio.x, rio.y), xytext=(rio.x + 2.5, rio.y - 5), fontsize=16, color=TEXTO,
            arrowprops={"arrowstyle": "-", "color": TEXTO})
leyenda(ax, [(VIRO, "Cambió de ganador")])
guardar(fig, 5)

# Escena 6: Acre y Sergipe
fig, ax = figura()
dibujar_mapa(ax, color=mapa.uf.map({"AC": FLAVIO, "SE": LULA}).fillna(GRIS).tolist())
for uf, nombre, dx, dy in [("AC", "Acre", 0, 3.2), ("SE", "Sergipe", 2.4, -3.5)]:
    c = mapa[mapa.uf == uf].union_all().centroid
    ax.annotate(nombre, (c.x, c.y), xytext=(c.x + dx, c.y + dy), fontsize=18, fontweight="bold", color=TEXTO, ha="center",
                arrowprops={"arrowstyle": "-", "color": TEXTO})
ax.set_xlim(ax.get_xlim()[0], ax.get_xlim()[1] + 4)
guardar(fig, 6)

# Escena 7: voto por Lula
fig, ax = figura()
divergente = LinearSegmentedColormap.from_list("voto", [FLAVIO, "#D9D6CE", LULA])
dibujar_mapa(ax, column="pct_lula_t2", cmap=divergente, vmin=20, vmax=80)
ax.text(0.02, 0.05, "% de voto por Lula", transform=ax.transAxes, fontsize=16, color=TEXTO)
guardar(fig, 7)
print(f"Imágenes en {SALIDA}")
