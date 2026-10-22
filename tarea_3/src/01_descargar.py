"""Paso 1 · Descargar datos crudos.

- Focos S-NPP 2012-2025 del Perú (NASA FIRMS, archivo anual por país).
- Focos S-NPP 2026 desde el 1 de julio (INPE, archivos mensuales de Sudamérica,
  filtrados a Perú mientras se leen para no guardar 150 MB por mes).
- Límites departamentales del INEI (peru-geojson).
"""
from pathlib import Path

import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

FIRMS = "https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/{y}/viirs-snpp_{y}_Peru.csv"
INPE = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/mensal/America_Sul/focos_mensal_{ym}.csv"
DEPTOS = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_departamental_simple.geojson"
MESES_2026 = ["202607", "202608", "202609", "202610"]


def bajar(url, destino):
    if destino.exists():
        print(f"  ya existe {destino.name}")
        return
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    destino.write_bytes(r.content)
    print(f"  {destino.name}: {len(r.content) / 1e6:.1f} MB")


print("FIRMS 2012-2025")
for y in range(2012, 2026):
    bajar(FIRMS.format(y=y), RAW / f"firms_snpp_{y}_peru.csv")

print("Límites departamentales")
bajar(DEPTOS, RAW / "departamentos.geojson")

print("INPE 2026 (solo Perú y S-NPP)")
for ym in MESES_2026:
    destino = RAW / f"inpe_snpp_{ym}_peru.csv"
    # El mes en curso siempre se vuelve a bajar porque INPE lo actualiza a diario
    if destino.exists() and ym != MESES_2026[-1]:
        print(f"  ya existe {destino.name}")
        continue
    partes = []
    for chunk in pd.read_csv(INPE.format(ym=ym), chunksize=500_000, encoding="latin-1"):
        partes.append(chunk[(chunk.pais == "Peru") & chunk.satelite.isin(["NPP-375", "NPP-375D"])])
    df = pd.concat(partes)
    df.to_csv(destino, index=False)
    print(f"  {destino.name}: {len(df):,} focos")
