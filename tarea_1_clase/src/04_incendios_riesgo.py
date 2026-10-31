"""Paso 4 · Incendios activos, población expuesta y riesgo climático (reto F).

1. Incendios: focos de los últimos 7 días a <= 1 km entre sí forman un mismo
   incendio (se unen buffers de 500 m). Solo se guardan los de >= 5 focos.
2. Población (raster): WorldPop 2020 a 1 km, suma de personas a <= 5 km del incendio.
3. Clima: Open-Meteo, 14 días pasados + 7 de pronóstico en el centro de cada incendio.
   Un "día crítico" tiene humedad mínima < 30 %, viento máximo >= 20 km/h y lluvia < 1 mm:
   las condiciones en que un incendio se propaga con facilidad.
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.mask import mask

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"
UTM = "EPSG:32718"  # metros, cubre casi todo el Perú
WORLDPOP = "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/2020/PER/per_ppp_2020_1km_Aggregated.tif"

corte = pd.Timestamp(json.loads((PROC / "comparacion.json").read_text(encoding="utf-8"))["nacional"]["corte"])
focos = pd.read_csv(PROC / "focos_limpios.csv.gz", parse_dates=["fecha"])
focos = focos[focos.es_incendio]  # solo incendios (paso 2)
f7 = focos[(focos.fecha > corte - pd.Timedelta(days=7)) & (focos.fecha <= corte)]
print(f"Focos {corte - pd.Timedelta(days=6):%d %b} - {corte:%d %b}: {len(f7):,}")

# --- 1. Agrupar focos en incendios ---
pts = gpd.GeoDataFrame(f7, geometry=gpd.points_from_xy(f7.lon, f7.lat), crs=4326).to_crs(UTM)
manchas = gpd.GeoDataFrame(geometry=list(pts.buffer(500).union_all().geoms), crs=UTM)
manchas["incendio"] = range(len(manchas))
pts = gpd.sjoin(pts, manchas, predicate="within")

inc = pts.groupby("incendio").agg(
    focos=("frp", "size"), frp_total=("frp", "sum"),
    primer_foco=("fecha", "min"), ultimo_foco=("fecha", "max"),
    departamento=("departamento", lambda s: s.mode()[0]),
)
inc = inc[inc.focos >= 5]
geom = manchas.set_index("incendio").loc[inc.index, "geometry"]
inc = gpd.GeoDataFrame(inc, geometry=geom, crs=UTM)
centro = inc.geometry.centroid.to_crs(4326)
inc["lat"], inc["lon"] = centro.y.round(4), centro.x.round(4)
inc["area_focos_ha"] = (inc.area / 1e4).round(0)
print(f"Incendios con >= 5 focos: {len(inc)}")

# --- 2. Población a 5 km (raster) ---
tif = RAW / "worldpop_2020_1km_per.tif"
if not tif.exists():
    tif.write_bytes(requests.get(WORLDPOP, timeout=300).content)
with rasterio.open(tif) as src:
    zonas = inc.buffer(5000).to_crs(src.crs)
    pob = []
    for g in zonas:
        arr, _ = mask(src, [g], crop=True, nodata=src.nodata)
        a = arr[0]
        pob.append(float(a[(a != src.nodata) & (a > 0)].sum()))
    # Total nacional sin contar dos veces a quien vive cerca de dos incendios
    arr, _ = mask(src, list(zonas.union_all().geoms), crop=True, nodata=src.nodata)
    a = arr[0]
    pob_total = int(round(float(a[(a != src.nodata) & (a > 0)].sum()), -3))
inc["poblacion_5km"] = np.round(pob, -1).astype(int)
print(f"Personas a <= 5 km de algún incendio (sin duplicar): {pob_total:,}")

# --- 3. Clima con Open-Meteo ---
r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=120, params={
    "latitude": ",".join(map(str, inc.lat)),
    "longitude": ",".join(map(str, inc.lon)),
    "daily": "temperature_2m_max,relative_humidity_2m_min,wind_speed_10m_max,precipitation_sum",
    "past_days": 14, "forecast_days": 7, "timezone": "America/Lima",
})
r.raise_for_status()
resp = r.json()
resp = resp if isinstance(resp, list) else [resp]

hoy = pd.Timestamp.now(tz="America/Lima").normalize().tz_localize(None)
clima = []
for d in resp:
    df = pd.DataFrame(d["daily"])
    df["time"] = pd.to_datetime(df.time)
    pasado, pron = df[df.time < hoy], df[df.time >= hoy]
    critico = (pron.relative_humidity_2m_min < 30) & (pron.wind_speed_10m_max >= 20) & (pron.precipitation_sum < 1)
    clima.append({
        "lluvia_14d_mm": round(pasado.precipitation_sum.sum(), 1),
        "lluvia_7d_pron_mm": round(pron.precipitation_sum.sum(), 1),
        "hr_min_pron": round(pron.relative_humidity_2m_min.mean(), 0),
        "viento_max_pron": round(pron.wind_speed_10m_max.max(), 0),
        "tmax_pron": round(pron.temperature_2m_max.max(), 1),
        "dias_criticos": int(critico.sum()),
        "pronostico": {
            "fecha": pron.time.dt.strftime("%Y-%m-%d").tolist(),
            "hr_min": pron.relative_humidity_2m_min.tolist(),
            "viento": pron.wind_speed_10m_max.tolist(),
            "lluvia": pron.precipitation_sum.tolist(),
        },
    })
inc = inc.join(pd.DataFrame(clima, index=inc.index))
inc["riesgo"] = np.select(
    [(inc.dias_criticos >= 3) & (inc.lluvia_7d_pron_mm < 5), inc.dias_criticos >= 1],
    ["Alto", "Medio"], "Bajo")

# Clima propicio (0-1): aire seco, viento fuerte y poca lluvia pronosticada.
# Se usan los valores continuos y no solo los días críticos, porque casi todos
# los incendios tienen 0 días críticos y empatarían.
inc["clima_propicio"] = pd.concat([
    (-inc.hr_min_pron).rank(pct=True), inc.viento_max_pron.rank(pct=True),
    (-inc.lluvia_7d_pron_mm).rank(pct=True)], axis=1).mean(axis=1).round(2)

# Prioridad 0-100: tamaño, clima, gente cerca y si sigue activo. Cada factor es un
# percentil (0-1) y se promedian con igual peso: simple y explicable.
activo = (inc.ultimo_foco >= corte - pd.Timedelta(days=1)).astype(float)
inc["prioridad"] = (100 * pd.concat([
    inc.focos.rank(pct=True), inc.clima_propicio,
    inc.poblacion_5km.rank(pct=True), activo], axis=1).mean(axis=1)).round(0).astype(int)
inc = inc.sort_values("prioridad", ascending=False)

cols = ["departamento", "focos", "area_focos_ha", "poblacion_5km", "dias_criticos",
        "lluvia_7d_pron_mm", "hr_min_pron", "viento_max_pron", "riesgo", "prioridad", "ultimo_foco"]
print(inc[cols].head(15).to_string())
print(inc.riesgo.value_counts().to_string())

salida = inc.to_crs(4326).reset_index()
salida["primer_foco"] = salida.primer_foco.dt.strftime("%Y-%m-%d")
salida["ultimo_foco"] = salida.ultimo_foco.dt.strftime("%Y-%m-%d")
salida["pronostico"] = salida.pronostico.apply(json.dumps)
salida.to_file(PROC / "incendios_activos.geojson", driver="GeoJSON")
f7[["lat", "lon", "fecha", "frp", "departamento"]].to_csv(PROC / "focos_7d.csv", index=False)
(PROC / "resumen_incendios.json").write_text(json.dumps({
    "focos_7d": len(f7), "incendios": len(inc), "poblacion_5km_total": pob_total,
    "riesgo": inc.riesgo.value_counts().to_dict(),
    "lluvia_7d_pron_mediana_mm": float(inc.lluvia_7d_pron_mm.median()),
    "fecha_pronostico": f"{hoy:%Y-%m-%d}",
}), encoding="utf-8")
