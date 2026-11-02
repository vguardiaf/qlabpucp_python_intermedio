"""Paso 1 · Descargar las fuentes.

- TSE: votos por municipio y zona, elecciones 2026 (zip de ~450 MB).
- IBGE/SIDRA: tabla 10296 del Censo 2022, personas por clase de ingreso per cápita.
- Equivalencia de códigos TSE -> IBGE.
- Límites municipales (GeoJSON).
Si un archivo ya existe, no se vuelve a bajar. Al final imprime qué columnas trae cada fuente.
"""
import json
import time
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "datos" / "originales"
RAW.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0"}

ARCHIVOS = {
    "votacao_candidato_munzona_2026.zip": "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2026.zip",
    "municipios_tse_ibge.csv": "https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/master/municipios_brasileiros_tse.csv",
    "municipios.geojson": "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-100-mun.json",
}
UFS_IBGE = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29,
            31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]
SIDRA = "https://apisidra.ibge.gov.br/values/t/10296/n6/in%20n3%20{uf}/v/allxp/p/all/c386/all"


def descargar(nombre, url):
    destino = RAW / nombre
    if destino.exists():
        print(f"ya existe: {nombre}")
        return
    # Se baja a .part para que una descarga cortada no pase por completa
    parcial = destino.with_suffix(destino.suffix + ".part")
    print(f"bajando {nombre} ...")
    with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
        r.raise_for_status()
        bajado, avisado = 0, 0
        with open(parcial, "wb") as f:
            for bloque in r.iter_content(1024 * 1024):
                f.write(bloque)
                bajado += len(bloque)
                if bajado - avisado >= 50 * 1024 * 1024:
                    print(f"  {bajado / 1024 / 1024:.0f} MB")
                    avisado = bajado
    parcial.rename(destino)
    print(f"listo: {nombre} ({bajado / 1024 / 1024:.1f} MB)")


def sidra_uf(uf):
    for intento in range(4):
        try:
            r = requests.get(SIDRA.format(uf=uf), headers=HEADERS, timeout=120)
            r.raise_for_status()
            filas = r.json()
            # La primera fila trae los nombres de las columnas
            return pd.DataFrame(filas[1:]).rename(columns=filas[0])
        except (requests.RequestException, ValueError) as e:
            print(f"  UF {uf}, intento {intento + 1} falló: {e}")
            time.sleep(3)
    raise RuntimeError(f"SIDRA no respondió para la UF {uf}")


for nombre, url in ARCHIVOS.items():
    descargar(nombre, url)

censo_csv = RAW / "censo2022_tabla10296.csv"
if censo_csv.exists():
    print("ya existe: censo2022_tabla10296.csv")
else:
    partes = []
    for uf in UFS_IBGE:
        partes.append(sidra_uf(uf))
        print(f"  censo UF {uf}: {len(partes[-1])} filas")
    pd.concat(partes, ignore_index=True).to_csv(censo_csv, index=False, encoding="utf-8")

(RAW / "fuentes.json").write_text(json.dumps({
    "fecha_descarga": datetime.now().isoformat(timespec="minutes"),
    "archivos": ARCHIVOS,
    "censo": SIDRA,
}, indent=2), encoding="utf-8")

print("\n=== TSE: archivos dentro del zip ===")
with zipfile.ZipFile(RAW / "votacao_candidato_munzona_2026.zip") as z:
    csvs = [i for i in z.infolist() if i.filename.lower().endswith(".csv")]
    for i in csvs[:5]:
        print(f"  {i.filename}  {i.file_size / 1024 / 1024:.0f} MB")
    print(f"  ... {len(csvs)} CSV en total")
    grande = max(csvs, key=lambda i: i.file_size)
    print(f"\n=== TSE: columnas de {grande.filename} ===")
    with z.open(grande) as f:
        print(f.readline().decode("latin-1").strip())

print("\n=== Censo ===")
censo = pd.read_csv(censo_csv, dtype=str)
print(list(censo.columns))
col = [c for c in censo.columns if c.startswith("Classes de rendimento") and not c.endswith("(Código)")][0]
print(censo[col].value_counts().to_string())
print(f"municipios: {censo['Município (Código)'].nunique()}")
print("valores no numéricos:", censo.loc[~censo["Valor"].str.isnumeric(), "Valor"].value_counts().to_dict())

print("\n=== Equivalencia TSE-IBGE ===")
print(f"{len(pd.read_csv(RAW / 'municipios_tse_ibge.csv'))} municipios")