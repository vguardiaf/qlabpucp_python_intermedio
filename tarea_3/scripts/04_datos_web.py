"""Paso 4 · Preparar los datos del dashboard.

Simplifica los límites municipales y escribe web/data/datos.js. Se usa un .js y no un
.json para que web/index.html también abra con doble clic, sin servidor.
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "datos" / "originales"
PROC = BASE / "datos" / "procesados"
WEB = BASE / "web" / "data"
WEB.mkdir(parents=True, exist_ok=True)
LULA = 13

df = pd.read_csv(PROC / "municipios.csv")
campos = ["ibge", "municipio", "uf", "region", "poblacion", "pobreza_12", "pobreza_14", "pct_lula_t1",
          "pct_lula_t2", "cambio_lula", "ganador_t1", "ganador_t2", "decil", "lula_t1", "validos_t1",
          "lula_t2", "validos_t2"]
tabla = df[campos].copy()
for c in ["pobreza_12", "pobreza_14", "pct_lula_t1", "pct_lula_t2", "cambio_lula"]:
    tabla[c] = tabla[c].round(2)
for c in ["poblacion", "lula_t1", "validos_t1", "lula_t2", "validos_t2"]:
    tabla[c] = tabla[c].astype(int)

# Resultado oficial: incluye los votos del exterior
votos = pd.read_csv(PROC / "presidente_municipio.csv")
oficial = {}
for t in [1, 2]:
    v = votos[votos.NR_TURNO == t]
    oficial[f"lula_t{t}"] = round(100 * v.loc[v.NR_CANDIDATO == LULA, "votos"].sum() / v.votos.sum(), 2)

# Límites simplificados para que la página pese poco
mapa = gpd.read_file(RAW / "municipios.geojson")
mapa["ibge"] = mapa["id"].astype(int)
print(f"Municipios sin límite en el mapa: {len(set(df.ibge) - set(mapa.ibge))}")
mapa["geometry"] = mapa.geometry.simplify(0.015, preserve_topology=True)
geo = json.loads(mapa[["ibge", "geometry"]].to_json(drop_id=True))
for f in geo["features"]:
    f["id"] = f["properties"]["ibge"]
    f["properties"] = {}
    # 3 decimales = ~100 m, suficiente para un mapa nacional
    f["geometry"] = json.loads(json.dumps(f["geometry"]), parse_float=lambda x: round(float(x), 3))

datos = {"campos": campos, "filas": tabla.values.tolist(), "oficial": oficial, "geo": geo}
texto = "const DATOS = " + json.dumps(datos, ensure_ascii=False, separators=(",", ":"), default=int) + ";\n"
(WEB / "datos.js").write_text(texto, encoding="utf-8")
print(f"Oficial: {oficial}")
print(f"datos.js: {len(texto.encode('utf-8')) / 1024 / 1024:.1f} MB, {len(tabla)} municipios")