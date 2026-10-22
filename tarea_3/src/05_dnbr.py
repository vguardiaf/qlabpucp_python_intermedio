"""Paso 5 · Área quemada con Sentinel-2 (dNBR) en los incendios activos más grandes.

Un foco VIIRS dice "aquí hubo calor". Sentinel-2 (10-20 m) dice si la vegetación
realmente se quemó: el NBR = (NIR - SWIR2) / (NIR + SWIR2) cae cuando el bosque o el
pastizal pasa a ceniza. dNBR = NBR antes - NBR después.

Decisiones de método:
- Imagen "antes": la más cercana al primer foco del incendio en la temporada (hasta 60
  días antes) con >= 85 % de la zona despejada. La más cercana y no la más limpia:
  entre junio y octubre la vegetación se seca sola y eso también baja el NBR.
- Imagen "después": la más reciente desde el inicio del incendio con >= 85 % despejado.
  Si el incendio sigue activo, mide lo quemado hasta esa fecha.
- Confiable: ambas imágenes con <= 25 % de nubes en la zona y <= 90 días entre ellas.
- Nubes: se usa la capa SCL de Sentinel-2. Solo cuentan píxeles de vegetación, suelo
  o agua (SCL 4, 5, 6). Se reporta el % de nubes de cada imagen dentro de la zona.
- Severidad con los umbrales del USGS (Key y Benson): 0,10 / 0,27 / 0,44 / 0,66.
  Área quemada = dNBR >= 0,27, el mismo umbral que usó el profesor en Curahuasi.
- Bandas B8A (NIR) y B12 (SWIR2), ambas a 20 m, en la zona UTM del incendio.
- Confirmación: % de focos VIIRS del incendio con algún píxel dNBR >= 0,10 a <= 200 m.
"""
import base64
import io
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin, rowcol
from rasterio.vrt import WarpedVRT
import rasterio.mask
import shapely.affinity
from scipy.ndimage import maximum_filter
from scipy.stats import mannwhitneyu
from shapely.geometry import box, mapping
from shapely.ops import unary_union

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
OUT_TIF = PROC / "dnbr"
OUT_TIF.mkdir(exist_ok=True)

STAC = "https://earth-search.aws.element84.com/v1/search"
N_INCENDIOS = 8   # los de más focos en la última semana
RES = 20          # metros
UMBRALES = [0.10, 0.27, 0.44, 0.66]
CLASES = ["No quemado", "Baja", "Moderada baja", "Moderada alta", "Alta"]
SCL_VALIDO = [4, 5, 6]

hoy = pd.Timestamp.now(tz="America/Lima").normalize().tz_localize(None)
inc = gpd.read_file(PROC / "incendios_activos.geojson")
sel = inc.sort_values("focos", ascending=False).head(N_INCENDIOS)

focos = pd.read_csv(PROC / "focos_limpios.csv.gz", parse_dates=["fecha"])
focos = focos[focos.es_incendio & (focos.fecha >= "2026-07-01")]
focos = gpd.GeoDataFrame(focos, geometry=gpd.points_from_xy(focos.lon, focos.lat), crs=4326)


def buscar(zona4326, t0, t1):
    """Escenas = cuadrantes de una misma pasada (satélite + día) que juntos cubren la zona.
    Un incendio en el borde de dos cuadrantes necesita los dos."""
    r = requests.post(STAC, timeout=120, json={
        "collections": ["sentinel-2-l2a"], "intersects": mapping(zona4326),
        "datetime": f"{t0:%Y-%m-%d}T00:00:00Z/{t1:%Y-%m-%d}T23:59:59Z",
        "limit": 100})
    r.raise_for_status()
    pasadas = {}
    for f in r.json()["features"]:
        clave = (f["properties"]["platform"], f["properties"]["datetime"][:10])
        pasadas.setdefault(clave, []).append(f)
    escenas = [items for items in pasadas.values()
               if unary_union([box(*f["bbox"]) for f in items]).contains(zona4326)]
    # De la más reciente a la más antigua: "antes" queda lo más cerca posible del inicio
    return sorted(escenas, key=lambda items: items[0]["properties"]["datetime"], reverse=True)


def leer(escena, banda, grilla, remuestreo):
    """Lee la banda de todos los cuadrantes de la escena sobre la grilla del incendio."""
    crs, transform, ancho, alto = grilla
    salida = np.full((alto, ancho), np.nan, dtype="float32")
    for item in escena:
        with rasterio.open(item["assets"][banda]["href"]) as src, WarpedVRT(
                src, crs=crs, transform=transform, width=ancho, height=alto, resampling=remuestreo) as vrt:
            arr = vrt.read(1).astype("float32")
        if banda == "scl":
            vals = arr
        else:
            meta = item["assets"][banda].get("raster:bands", [{}])[0]
            vals = arr * meta.get("scale", 1e-4) + meta.get("offset", 0)  # baseline >= 4.0 trae offset -0,1
        llenar = np.isnan(salida) & (arr != 0)
        salida[llenar] = vals[llenar]
    return salida


def mejor_imagen(escenas, grilla, en_zona, minimo=0.85):
    """Recorre las escenas de la más reciente a la más antigua y se queda con la primera
    que tenga al menos `minimo` de la zona despejada (según SCL). Si ninguna llega,
    devuelve la más despejada de las revisadas."""
    mejor = None
    for escena in escenas[:10]:
        if np.mean([f["properties"]["eo:cloud_cover"] for f in escena]) > 80:
            continue
        scl = leer(escena, "scl", grilla, Resampling.nearest)
        validos = np.isin(scl, SCL_VALIDO) & en_zona
        frac = validos.sum() / en_zona.sum()
        if mejor is None or frac > mejor[1]:
            mejor = (escena, frac, validos)
        if frac >= minimo:
            break
    return mejor


def png_severidad(clase, nir_post, valido):
    """Fondo: NIR posterior en grises. Encima: severidad en una rampa naranja."""
    gris = np.clip(np.nan_to_num(nir_post) / 0.4, 0, 1)
    rgb = np.dstack([gris, gris, gris]) * 0.85 + 0.1
    colores = {1: (0.98, 0.80, 0.62), 2: (0.94, 0.55, 0.30), 3: (0.83, 0.32, 0.16), 4: (0.55, 0.15, 0.06)}
    for c, col in colores.items():
        rgb[(clase == c) & valido] = col
    rgb[~valido] = rgb[~valido] * 0.35 + np.array([0.55, 0.65, 0.78]) * 0.65  # nube o sin dato
    buf = io.BytesIO()
    plt.imsave(buf, np.clip(rgb, 0, 1), format="png")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def medir(geom4326, lon, buffer_m, focos_conf, inicio=None, post_hasta=None, tif=None, imagen=True,
          fechas=None):
    """dNBR en la zona = geom4326 + buffer_m. focos_conf: focos VIIRS a confirmar.
    inicio: primer día del fuego (si es None, el primer foco de la temporada en la zona).
    fechas: (antes, después) para forzar las mismas imágenes que otra medición."""
    zona_utm_epsg = 32700 + int((lon + 180) // 6) + 1
    geom = gpd.GeoSeries([geom4326], crs=4326).to_crs(zona_utm_epsg)
    zona = geom.buffer(buffer_m).iloc[0]
    zona4326 = gpd.GeoSeries([zona], crs=zona_utm_epsg).to_crs(4326).iloc[0]
    x0, y0, x1, y1 = zona.bounds
    ancho, alto = int(np.ceil((x1 - x0) / RES)), int(np.ceil((y1 - y0) / RES))
    transform = from_origin(x0, y1, RES, RES)
    grilla = (f"EPSG:{zona_utm_epsg}", transform, ancho, alto)
    en_zona = ~geometry_mask([zona], (alto, ancho), transform)

    if inicio is None:
        inicio = focos[focos.within(zona4326)].fecha.min()
    if fechas:
        pre, post = buscar(zona4326, *[pd.Timestamp(fechas[0])] * 2), buscar(zona4326, *[pd.Timestamp(fechas[1])] * 2)
    else:
        pre = buscar(zona4326, inicio - pd.Timedelta(days=60), inicio - pd.Timedelta(days=1))
        post = buscar(zona4326, inicio + pd.Timedelta(days=1), post_hasta or hoy)
    if not pre or not post:
        return None
    item_pre, frac_pre, val_pre = mejor_imagen(pre, grilla, en_zona)
    item_post, frac_post, val_post = mejor_imagen(post, grilla, en_zona)

    nbr = []
    for item in (item_pre, item_post):
        nir = leer(item, "nir08", grilla, Resampling.bilinear)
        swir = leer(item, "swir22", grilla, Resampling.bilinear)
        with np.errstate(divide="ignore", invalid="ignore"):
            nbr.append((nir - swir) / (nir + swir))
    dnbr = nbr[0] - nbr[1]
    valido = val_pre & val_post & np.isfinite(dnbr)
    clase = np.digitize(np.nan_to_num(dnbr), UMBRALES)

    ha_px = RES * RES / 1e4
    ha_clase = {CLASES[c]: round(float(((clase == c) & valido).sum() * ha_px), 1) for c in range(5)}
    quemado = (clase >= 2) & valido

    # Confirmación: focos con algún píxel dNBR >= 0,10 a <= 200 m
    vecindad = maximum_filter(np.where(valido, np.nan_to_num(dnbr), -1), size=2 * 10 + 1)
    fu = focos_conf.to_crs(zona_utm_epsg)
    filas, cols = rowcol(transform, fu.geometry.x.values, fu.geometry.y.values)
    filas, cols = np.clip(filas, 0, alto - 1), np.clip(cols, 0, ancho - 1)
    confirmados = float((vecindad[filas, cols] >= UMBRALES[0]).mean()) if len(fu) else None
    confirmados_027 = float((vecindad[filas, cols] >= UMBRALES[1]).mean()) if len(fu) else None

    if tif:
        perfil = {"driver": "GTiff", "height": alto, "width": ancho, "count": 1, "dtype": "float32",
                  "crs": grilla[0], "transform": transform, "nodata": np.nan, "compress": "deflate"}
        with rasterio.open(OUT_TIF / tif, "w", **perfil) as dst:
            dst.write(np.where(valido, dnbr, np.nan).astype("float32"), 1)

    r = {
        "inicio_temporada": f"{inicio:%Y-%m-%d}",
        "pre_fecha": item_pre[0]["properties"]["datetime"][:10], "pre_nubes_pct": round(100 * (1 - frac_pre), 1),
        "post_fecha": item_post[0]["properties"]["datetime"][:10], "post_nubes_pct": round(100 * (1 - frac_post), 1),
        "pre_id": [i["id"] for i in item_pre], "post_id": [i["id"] for i in item_post],
        "zona_ha": round(float(en_zona.sum() * ha_px), 0),
        "zona_valida_pct": round(100 * valido.sum() / en_zona.sum(), 1),
        "area_quemada_ha": round(float(quemado.sum() * ha_px), 0),
        "ha_por_severidad": ha_clase,
        "focos_confirmados_pct": None if confirmados is None else round(100 * confirmados, 0),
        "focos_confirmados_027_pct": None if confirmados_027 is None else round(100 * confirmados_027, 0),
        "dnbr_medio": round(float(np.nanmean(np.where(valido, dnbr, np.nan))), 3) if valido.any() else None,
        "quemado_pct_zona": round(100 * quemado.sum() / max(valido.sum(), 1), 1),
        "dias_entre_imagenes": (pd.Timestamp(item_post[0]["properties"]["datetime"][:10])
                                - pd.Timestamp(item_pre[0]["properties"]["datetime"][:10])).days,
    }
    if imagen:
        r["imagen"] = png_severidad(clase, leer(item_post, "nir08", grilla, Resampling.bilinear), valido)
    # Con muchas nubes o meses entre imágenes, el dNBR mezcla fuego con cambio de estación
    r["confiable"] = bool(r["pre_nubes_pct"] <= 25 and r["post_nubes_pct"] <= 25 and r["dias_entre_imagenes"] <= 90)
    return r


# --- 1. Los incendios activos más grandes ---
resultados = []
for _, f in sel.iterrows():
    nombre = f"{f.departamento} ({abs(f.lat):.2f}° S, {abs(f.lon):.2f}° O)"
    zona = gpd.GeoSeries([f.geometry], crs=4326).to_crs(32718).buffer(1500).to_crs(4326).iloc[0]
    f7 = focos[focos.within(zona) & (focos.fecha > pd.Timestamp(f.ultimo_foco) - pd.Timedelta(days=7))]
    r = medir(f.geometry, f.lon, 1500, f7, tif=f"dnbr_incendio_{f.incendio}.tif")
    if r is None:
        print(f"{nombre}: sin imágenes Sentinel-2 que cubran la zona")
        continue
    r = {"incendio": int(f.incendio), "departamento": f.departamento, "lat": f.lat, "lon": f.lon,
         "focos_7d": int(f.focos)} | r
    resultados.append(r)
    print(f"{nombre}: {r['area_quemada_ha']:,.0f} ha quemadas (dNBR >= 0,27) | "
          f"antes {r['pre_fecha']} ({r['pre_nubes_pct']} % nubes), después {r['post_fecha']} "
          f"({r['post_nubes_pct']} % nubes) | focos confirmados {r['focos_confirmados_pct']} %")

(PROC / "dnbr_incendios.json").write_text(json.dumps(resultados, ensure_ascii=False), encoding="utf-8")

# --- 2. Validación de la regla del paso 2 en pastizal ---
# Muestra al azar (semilla fija) de eventos de 2026 sobre pastizal, entre el 1 de agosto y el
# 5 de octubre para que haya imagen posterior. Si la regla funciona, los "incendios" deberían
# dejar una cicatriz quemada continua y las "quemas" casi nada.
todos = pd.read_csv(PROC / "focos_limpios.csv.gz", parse_dates=["fecha"])
pz = todos[(todos.cobertura_cod == 30) & todos.fecha.between("2026-08-01", "2026-10-05")].dropna(subset=["evento"])
# Control: la misma zona desplazada ~5 km a un pastizal sin focos en la temporada, medida
# con LAS MISMAS dos imágenes. Lo que "se quema" ahí es el secado de la estación; la
# diferencia evento - control es lo que quemó el fuego.
WC_DIR = BASE / "data" / "raw" / "worldcover"
todos_gdf = gpd.GeoDataFrame(todos[todos.fecha >= "2026-07-01"], crs=4326,
                             geometry=gpd.points_from_xy(todos.lon[todos.fecha >= "2026-07-01"],
                                                         todos.lat[todos.fecha >= "2026-07-01"]))


def frac_pastizal(geom4326):
    pts = geom4326.representative_point()
    lat0, lon0 = int(np.floor(pts.y / 3) * 3), int(np.floor(pts.x / 3) * 3)
    tif = WC_DIR / f"worldcover_80m_{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}W{abs(lon0):03d}.tif"
    if not tif.exists():
        return 0
    with rasterio.open(tif) as src:
        arr, _ = rasterio.mask.mask(src, [geom4326], crop=True, nodata=0)
    a = arr[0][arr[0] > 0]
    return float((a == 30).mean()) if a.size else 0


def control(geom4326, lon, fechas):
    """Prueba 8 direcciones a 5 km y usa la primera zona con >= 60 % pastizal y sin focos."""
    utm = gpd.GeoSeries([geom4326], crs=4326).to_crs(32718).iloc[0]
    for ang in range(0, 360, 45):
        dx, dy = 5000 * np.cos(np.radians(ang)), 5000 * np.sin(np.radians(ang))
        g = gpd.GeoSeries([shapely.affinity.translate(utm, dx, dy)], crs=32718).to_crs(4326).iloc[0]
        zona = gpd.GeoSeries([g], crs=4326).to_crs(32718).buffer(750).to_crs(4326).iloc[0]
        if frac_pastizal(zona) < 0.6 or todos_gdf.within(zona).any():
            continue
        r = medir(g, lon, 750, todos_gdf.iloc[0:0], inicio=pd.Timestamp(fechas[0]), fechas=fechas, imagen=False)
        if r is not None:
            return r
    return None


muestra = {"Incendio en pastizal o cultivo": 10, "Quema pequeña en pastizal o cultivo": 10,
           "Quema recurrente en pastizal o cultivo": 10}
validacion = []
for motivo, n in muestra.items():
    candidatos = pz[pz.motivo == motivo].evento.drop_duplicates()
    eventos = candidatos.sample(min(n, len(candidatos)), random_state=7)
    for e in eventos:
        fe = todos[todos.evento == e]
        fe = gpd.GeoDataFrame(fe, geometry=gpd.points_from_xy(fe.lon, fe.lat), crs=4326)
        geom = fe.to_crs(32718).buffer(375).union_all()
        geom4326 = gpd.GeoSeries([geom], crs=32718).to_crs(4326).iloc[0]
        r = medir(geom4326, fe.lon.mean(), 750, fe, inicio=fe.fecha.min(),
                  post_hasta=fe.fecha.max() + pd.Timedelta(days=40), imagen=False)
        if r is None or not r["confiable"]:
            continue
        c = control(geom4326, fe.lon.mean(), (r["pre_fecha"], r["post_fecha"]))
        if c is None or not c["confiable"]:
            continue
        r = {"motivo": motivo, "evento": int(e), "departamento": fe.departamento.iloc[0], "focos": len(fe),
             "dias": int(fe.fecha.nunique()), "lat": round(fe.lat.mean(), 3), "lon": round(fe.lon.mean(), 3)} | r
        r["control_quemado_pct"] = c["quemado_pct_zona"]
        r["control_dnbr_medio"] = c["dnbr_medio"]
        r["neto_quemado_pct"] = round(r["quemado_pct_zona"] - c["quemado_pct_zona"], 1)
        r["neto_ha"] = round(r["neto_quemado_pct"] / 100 * r["zona_ha"] * r["zona_valida_pct"] / 100, 0)
        validacion.append(r)
        print(f"[{motivo}] {r['departamento']} {r['focos']} focos/{r['dias']} d: quemado {r['quemado_pct_zona']} % "
              f"vs control {c['quemado_pct_zona']} % -> neto {r['neto_ha']:,.0f} ha | "
              f"confirmados (>=0,27) {r['focos_confirmados_027_pct']} %")

val = pd.DataFrame(validacion)
resumen_val = val.groupby("motivo").agg(
    eventos=("evento", "size"), focos_mediana=("focos", "median"),
    quemado_pct_mediana=("quemado_pct_zona", "median"), control_pct_mediana=("control_quemado_pct", "median"),
    neto_ha_mediana=("neto_ha", "median"),
    confirmados_027_mediana_pct=("focos_confirmados_027_pct", "median")).reset_index()
print(resumen_val.to_string())
# ¿La diferencia entre "incendio" y "quema pequeña" es estadísticamente distinguible?
a = val.loc[val.motivo == "Incendio en pastizal o cultivo", "neto_ha"]
b = val.loc[val.motivo == "Quema pequeña en pastizal o cultivo", "neto_ha"]
p = float(mannwhitneyu(a, b, alternative="greater").pvalue) if len(a) and len(b) else None
print(f"Mann-Whitney (incendio > quema pequeña en ha netas): p = {p}")
resumen_val = resumen_val.assign(p_incendio_vs_pequena=p)
(PROC / "validacion_reglas.json").write_text(json.dumps({
    "eventos": validacion, "resumen": json.loads(resumen_val.to_json(orient="records"))},
    ensure_ascii=False), encoding="utf-8")
