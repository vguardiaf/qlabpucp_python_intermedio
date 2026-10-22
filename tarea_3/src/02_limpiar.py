"""Paso 2 · Limpiar focos y asignarlos a departamentos.

Decisiones de método:
- Solo S-NPP: es el único satélite con registro continuo desde 2012, así los años
  son comparables (NOAA-20 y NOAA-21 llegaron después y duplicarían la cuenta).
- Fuera fuentes fijas y volcanes: FIRMS marca con type=1 (volcán) y type=2 (fuente
  fija: refinerías, minas, fábricas) los píxeles que arden todo el año. Las celdas
  de ~1 km donde aparecen se excluyen en TODOS los años, incluido 2026 (INPE no trae
  esa marca), para que el filtro sea el mismo para todos.
- Se conservan todas las confianzas (baja, nominal, alta), igual que INPE.
- Cobertura del suelo (ESA WorldCover 2021) bajo cada foco.
- ¿Incendio o quema de manejo? Un satélite no ve la intención, pero sí el
  comportamiento del fuego. La columna es_incendio vale True si el foco está:
    * sobre bosque, matorral, humedal o manglar (siempre), o
    * sobre pastizal o cultivo, dentro de un evento grande (>= 5 focos o >= 2 días)
      o que llega a bosque/matorral (quema escapada), y en una celda que NO arde casi
      todos los años (las quemas de manejo se repiten en el mismo lugar).
  La regla se aplica igual a los 15 años. Los pasos siguientes solo usan es_incendio.
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.transform import rowcol
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
OUT = BASE / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

CELDA = 0.01  # grados, ~1.1 km
WC = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"


def celda(lat, lon):
    return (lat / CELDA).round().astype(int).astype(str) + "_" + (lon / CELDA).round().astype(int).astype(str)


# --- FIRMS 2012-2025 ---
firms = pd.concat([pd.read_csv(f) for f in sorted(RAW.glob("firms_snpp_*_peru.csv"))], ignore_index=True)
firms = firms.rename(columns={"latitude": "lat", "longitude": "lon"})
firms["fecha"] = pd.to_datetime(firms.acq_date)
print(f"FIRMS: {len(firms):,} focos; por tipo:\n{firms.type.value_counts().sort_index()}")

fijas = set(celda(firms.lat, firms.lon)[firms.type.isin([1, 2])])
print(f"Celdas de fuente fija o volcán: {len(fijas):,}")

# --- INPE 2026 ---
inpe = pd.concat([pd.read_csv(f) for f in sorted(RAW.glob("inpe_snpp_2026*_peru.csv"))], ignore_index=True)
inpe["fecha"] = pd.to_datetime(inpe.data_hora_gmt).dt.normalize()
inpe = inpe.drop_duplicates("id")

focos = pd.concat([
    firms.loc[firms.type == 0, ["lat", "lon", "fecha", "frp"]].assign(fuente="FIRMS"),
    inpe[["lat", "lon", "fecha", "frp"]].assign(fuente="INPE"),
], ignore_index=True)
antes = len(focos)
focos = focos[~celda(focos.lat, focos.lon).isin(fijas)]
print(f"Quitados por fuente fija: {antes - len(focos):,}")

# --- Departamento de cada foco ---
deptos = gpd.read_file(RAW / "departamentos.geojson")
deptos = deptos[["NOMBDEP", "geometry"]].rename(columns={"NOMBDEP": "departamento"})
TILDES = {"Apurimac": "Apurímac", "Huanuco": "Huánuco", "Junin": "Junín", "San Martin": "San Martín",
          "Madre De Dios": "Madre de Dios"}
deptos["departamento"] = deptos.departamento.str.title().replace(TILDES)

pts = gpd.GeoDataFrame(focos, geometry=gpd.points_from_xy(focos.lon, focos.lat), crs="EPSG:4326")
pts = gpd.sjoin(pts, deptos.to_crs(4326), how="inner", predicate="within").drop(columns=["index_right", "geometry"])
print(f"Focos dentro del Perú: {len(pts):,} (fuera de límites: {len(focos) - len(pts):,})")

# --- Cobertura del suelo bajo cada foco (ESA WorldCover 2021) ---
# Un foco en zona urbana, suelo desnudo o agua no es un incendio de vegetación. Uno en
# pastizal o cultivo puede ser una quema de manejo o un incendio: se decide más abajo
# por el tamaño, la duración y la recurrencia del evento. WorldCover es de 10 m; se usa su versión reducida a 80 m,
# que basta para un píxel VIIRS de 375 m y baja ~60 veces menos datos.
WC_DIR = RAW / "worldcover"
WC_DIR.mkdir(exist_ok=True)
CLASES = {10: "Bosque", 20: "Matorral", 30: "Pastizal", 40: "Cultivo", 50: "Urbano", 60: "Suelo desnudo",
          70: "Nieve", 80: "Agua", 90: "Humedal", 95: "Manglar", 100: "Musgo y liquen", 0: "Sin dato"}
LENOSA = [10, 20, 90, 95, 100]   # bosque, matorral, humedal, manglar, musgo: cuentan siempre
MANEJO = [30, 40]                # pastizal y cultivo: se queman a propósito todos los años
EVENTO_FOCOS, EVENTO_DIAS = 5, 2  # evento grande: >= 5 focos o >= 2 días con focos
RECURRENTE = 8                    # celda que ardió en >= 8 de los otros 14 años = quema de manejo


def cuadrante(lat0, lon0):
    return f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}"


pts["lat0"] = (np.floor(pts.lat / 3) * 3).astype(int)
pts["lon0"] = (np.floor(pts.lon / 3) * 3).astype(int)
pts["cobertura_cod"] = 0
for (lat0, lon0), idx in pts.groupby(["lat0", "lon0"]).groups.items():
    local = WC_DIR / f"worldcover_80m_{cuadrante(lat0, lon0)}.tif"
    if not local.exists():
        try:
            with rasterio.open(WC.format(t=cuadrante(lat0, lon0))) as src:
                arr = src.read(1, out_shape=(src.height // 8, src.width // 8))
                perfil = src.profile | {"height": arr.shape[0], "width": arr.shape[1], "driver": "GTiff",
                                        "transform": src.transform * Affine.scale(8), "compress": "deflate"}
        except rasterio.errors.RasterioIOError:
            print(f"  sin cuadrante WorldCover {cuadrante(lat0, lon0)} (mar)")
            continue
        with rasterio.open(local, "w", **perfil) as dst:
            dst.write(arr, 1)
        print(f"  WorldCover {cuadrante(lat0, lon0)} descargado")
    with rasterio.open(local) as src:
        arr = src.read(1)
        filas, cols = rowcol(src.transform, pts.loc[idx, "lon"].values, pts.loc[idx, "lat"].values)
        filas = np.clip(filas, 0, arr.shape[0] - 1)
        cols = np.clip(cols, 0, arr.shape[1] - 1)
        pts.loc[idx, "cobertura_cod"] = arr[filas, cols]

pts["cobertura"] = pts.cobertura_cod.map(CLASES)
pts = pts.drop(columns=["lat0", "lon0"]).reset_index(drop=True)
pts["anio"] = pts.fecha.dt.year
print("Focos por cobertura:")
print(pts.cobertura.value_counts().to_string())

# --- Eventos: focos a ~1 km y <= 2 días entre sí forman un mismo evento ---
# Celdas de 0,005° (~550 m): dos focos en celdas vecinas están a <= ~1,6 km. Cada
# (celda, día) es un nodo; se une con sus vecinos de los 2 días siguientes y se buscan
# los componentes conexos del grafo.
veg = pts.cobertura_cod.isin(LENOSA + MANEJO)
v = pts[veg]
cel = pd.DataFrame({"cx": (v.lon / 0.005).round().astype(int), "cy": (v.lat / 0.005).round().astype(int),
                    "d": (v.fecha - pd.Timestamp("2012-01-01")).dt.days}, index=v.index)
nodos = cel.drop_duplicates().reset_index(drop=True)
nodos["nodo"] = np.arange(len(nodos))
aristas = []
for dx in (-1, 0, 1):
    for dy in (-1, 0, 1):
        for dd in (0, 1, 2):
            if (dx, dy, dd) == (0, 0, 0):
                continue
            vecino = nodos.assign(cx=nodos.cx - dx, cy=nodos.cy - dy, d=nodos.d - dd)
            m = nodos.merge(vecino, on=["cx", "cy", "d"], suffixes=("", "_v"))
            aristas.append(m[["nodo", "nodo_v"]].to_numpy())
aristas = np.vstack(aristas)
grafo = coo_matrix((np.ones(len(aristas)), (aristas[:, 0], aristas[:, 1])), shape=(len(nodos), len(nodos)))
_, nodos["evento"] = connected_components(grafo, directed=False)
pts.loc[v.index, "evento"] = cel.merge(nodos, on=["cx", "cy", "d"], how="left").evento.to_numpy()

ev = pts[veg].groupby("evento").agg(ev_focos=("fecha", "size"), ev_dias=("fecha", "nunique"),
                                     ev_lenosa=("cobertura_cod", lambda c: c.isin(LENOSA).any()))
pts = pts.join(ev, on="evento")
print(f"Eventos: {len(ev):,}; el más grande tiene {ev.ev_focos.max():,} focos y {ev.ev_dias.max()} días")

# --- Recurrencia: años distintos en que ardió cada celda de ~1 km ---
pts["celda"] = celda(pts.lat, pts.lon)
anios_celda = pts[veg].groupby("celda").anio.nunique()
pts["otros_anios"] = pts.celda.map(anios_celda).fillna(1).astype(int) - 1

# --- Regla final ---
lenosa = pts.cobertura_cod.isin(LENOSA)
manejo = pts.cobertura_cod.isin(MANEJO)
grande = (pts.ev_focos >= EVENTO_FOCOS) | (pts.ev_dias >= EVENTO_DIAS)
escapada = pts.ev_lenosa.fillna(False).astype(bool)
recurrente = pts.otros_anios >= RECURRENTE
pts["es_incendio"] = lenosa | (manejo & (grande | escapada) & ~recurrente)
pts["motivo"] = np.select(
    [lenosa, manejo & ~(grande | escapada), manejo & recurrente, manejo],
    ["Bosque o matorral", "Quema pequeña en pastizal o cultivo", "Quema recurrente en pastizal o cultivo",
     "Incendio en pastizal o cultivo"],
    "Sin vegetación")
print(pts.groupby("motivo").size().to_string())
print(f"Cuentan como incendio: {pts.es_incendio.mean():.1%}")
pts = pts.drop(columns=["celda"])
pts.to_csv(OUT / "focos_limpios.csv.gz", index=False)
deptos.to_file(OUT / "departamentos.geojson", driver="GeoJSON")
print(pts.groupby("anio").size().to_string())
