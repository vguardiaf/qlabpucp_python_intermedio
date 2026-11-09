"""Verificación independiente de cifras del informe: no usa el servidor MCP ni las skills.

    uv run informes/verificar_cifras.py      # escribe informes/verificacion_independiente.csv

- BCRP: llama directo a la API pública (otra ruta de código que mcp/server.py) y calcula con pandas.
- ENAHO: lee la sumaria directo del zip del INEI y calcula la pobreza ponderada con
  factor07 x mieperho, el método oficial a nivel de hogares, sin pasar por limpiar.py.
Las cifras de referencia oficiales (INEI) se escriben aquí solo como punto de comparación.
"""
import io
import json
import time
import zipfile
from pathlib import Path

import httpx
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8,
         "Set": 9, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12}


def bcrp(codigo, desde, hasta):
    url = f"{API}/{codigo}/json/{desde}/{hasta}"
    for intento in range(4):
        try:
            datos = json.loads(httpx.get(url, timeout=60).content.decode("utf-8-sig"))
            break
        except json.JSONDecodeError:
            time.sleep(3 * (intento + 1))
    filas = []
    for p in datos["periods"]:
        try:
            filas.append((p["name"], float(p["values"][0])))
        except ValueError:
            pass
    df = pd.DataFrame(filas, columns=["nombre", "valor"])
    if "." in df["nombre"].iloc[0]:
        mes, anio = df["nombre"].str.split(".", expand=True).T.values
        df["periodo"] = [f"{a}-{MESES[m]:02d}" for m, a in zip(mes, anio)]
    else:
        df["periodo"] = df["nombre"]
    return df.set_index("periodo")["valor"], url


def sumaria():
    with zipfile.ZipFile(RAIZ / "datos" / "966-Modulo34.zip") as z:
        nombre = next(n for n in z.namelist() if n.endswith("/sumaria-2024.dta"))
        df = pd.read_stata(io.BytesIO(z.read(nombre)), convert_categoricals=False)
    df.columns = df.columns.str.lower()
    df["peso"] = df["factor07"].astype(float) * df["mieperho"]
    df["pobre"] = df["pobreza"] <= 2
    df["dep"] = df["ubigeo"].astype(str).str.zfill(6).str[:2]
    return df


def tasa(df):
    return round(100 * (df["peso"] * df["pobre"]).sum() / df["peso"].sum(), 2)


# Códigos anuales "(total)" del BCRP: van de 3 en 3 y en el mismo orden que los códigos INEI 01..25.
CREDITO = [f"RD16{127 + 3 * i}DA" for i in range(25)]
DEPOSITOS = [f"RD16{205 + 3 * i}DA" for i in range(25)]
DEPS = [f"{i:02d}" for i in range(1, 26)]


def bcrp_varias(codigos, anio):
    url = f"{API}/{'-'.join(codigos)}/json/{anio}/{anio}"
    for intento in range(4):
        try:
            datos = json.loads(httpx.get(url, timeout=60).content.decode("utf-8-sig"))
            break
        except json.JSONDecodeError:
            time.sleep(3 * (intento + 1))
    return pd.Series([float(v) for v in datos["periods"][0]["values"]], index=DEPS), url


def main():
    filas = []
    s = sumaria()
    zip34 = "datos/966-Modulo34.zip (sumaria-2024.dta), factor07 x mieperho"
    filas.append(("ENAHO", "Pobreza monetaria nacional 2024 (%)", tasa(s), "2024", zip34))

    credito, url_c = bcrp_varias(CREDITO, 2024)
    depositos, url_d = bcrp_varias(DEPOSITOS, 2024)
    total_c, url_tc = bcrp("RD16202DA", "2024", "2024")
    filas += [
        ("BCRP", "Crédito total, suma de 25 departamentos 2024 (millones S/)", round(credito.sum(), 1), "2024", url_c),
        ("BCRP", "Crédito total, serie Total RD16202DA 2024 (millones S/)", round(total_c.iloc[0], 1), "2024", url_tc),
        ("BCRP", "Crédito Lima RD16169DA 2024 (millones S/)", round(credito["15"], 1), "2024", url_c),
        ("BCRP", "Participación de Lima en el crédito 2024 (%)", round(100 * credito["15"] / credito.sum(), 1), "2024", url_c),
        ("BCRP", "Depósitos, suma de 25 departamentos 2024 (millones S/)", round(depositos.sum(), 1), "2024", url_d),
    ]

    # Población y pobreza por departamento con el método de hogares (otra vía que la skill, que usa facpob07)
    g = s.groupby("dep").apply(lambda d: pd.Series({"poblacion": d["peso"].sum(), "pobreza": tasa(d)}))
    df = g.join(pd.DataFrame({"credito": credito, "depositos": depositos}))
    df["credito_pc"] = df["credito"] * 1e6 / df["poblacion"]
    df["prof_pc"] = (df["credito"] + df["depositos"]) * 1e6 / df["poblacion"]
    sin_capital = df.drop(index=["15", "07"])
    rho = lambda d, v: round(d[v].rank().corr(d["pobreza"].rank()), 3)
    proc = "API BCRP directa + sumaria (factor07 x mieperho), Spearman = Pearson sobre rangos"
    filas += [
        ("Cruce", "Crédito por habitante Huancavelica 2024 (S/)", round(df.at["09", "credito_pc"], 1), "2024", proc),
        ("Cruce", "Crédito por habitante Lima 2024 (S/)", round(df.at["15", "credito_pc"], 1), "2024", proc),
        ("Cruce", "Spearman crédito pc vs pobreza, 25 dptos", rho(df, "credito_pc"), "2024", proc),
        ("Cruce", "Spearman profundización pc vs pobreza, 25 dptos", rho(df, "prof_pc"), "2024", proc),
        ("Cruce", "Spearman profundización pc vs pobreza, sin Lima ni Callao", rho(sin_capital, "prof_pc"), "2024", proc),
    ]
    tabla = pd.DataFrame(filas, columns=["fuente", "indicador", "valor_independiente", "periodo", "procedimiento"])
    tabla.to_csv(RAIZ / "informes" / "verificacion_independiente.csv", index=False, encoding="utf-8")
    print(tabla.to_string(index=False))


if __name__ == "__main__":
    main()
