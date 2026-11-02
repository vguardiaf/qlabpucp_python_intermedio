"""Paso 2 · Limpiar y unir votos, pobreza y códigos de municipio.

Genera datos/procesados/municipios.csv, con una fila por municipio.
Antes de seguir, compara los totales nacionales con los publicados por el TSE.
"""
import zipfile
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "datos" / "originales"
PROC = BASE / "datos" / "procesados"
PROC.mkdir(parents=True, exist_ok=True)

LULA, FLAVIO = 13, 22
PRESIDENTE = 1
REGIONES = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sur", "5": "Centro-Oeste"}
# Códigos de clase de ingreso per cápita en la tabla 10296 del censo
TOTAL, HASTA_1_4, DE_1_4_A_1_2, SIN_INGRESO = "9680", "9681", "9682", "9692"


def leer_presidente():
    cache = PROC / "presidente_municipio.csv"
    if cache.exists():
        print("usando caché de votos")
        return pd.read_csv(cache)
    cols = ["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "CD_CARGO", "NR_CANDIDATO", "QT_VOTOS_NOMINAIS_VALIDOS"]
    partes = []
    with zipfile.ZipFile(RAW / "votacao_candidato_munzona_2026.zip") as z:
        nombre = next(n for n in z.namelist() if n.endswith("_BRASIL.csv"))
        with z.open(nombre) as f:
            lector = pd.read_csv(f, sep=";", encoding="latin-1", usecols=cols, chunksize=1_000_000)
            for i, bloque in enumerate(lector, 1):
                print(f"  bloque {i}")
                partes.append(bloque[bloque.CD_CARGO == PRESIDENTE])
    votos = (pd.concat(partes)
             .groupby(["NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NR_CANDIDATO"], as_index=False)
             ["QT_VOTOS_NOMINAIS_VALIDOS"].sum()
             .rename(columns={"QT_VOTOS_NOMINAIS_VALIDOS": "votos"}))
    votos.to_csv(cache, index=False)
    return votos


def validar(votos):
    print("\n=== Validación contra el TSE ===")
    def revisar(texto, obtenido, esperado):
        estado = "OK" if obtenido == esperado else "DIFERENCIA"
        print(f"{estado}: {texto}: {obtenido:,.2f} (TSE: {esperado:,.2f})")

    t1 = votos[votos.NR_TURNO == 1]
    t2 = votos[votos.NR_TURNO == 2]
    revisar("Flávio, 1a vuelta", t1.loc[t1.NR_CANDIDATO == FLAVIO, "votos"].sum(), 56_104_268)
    revisar("Lula, 1a vuelta", t1.loc[t1.NR_CANDIDATO == LULA, "votos"].sum(), 53_876_617)
    revisar("% Flávio, 1a vuelta", round(100 * t1.loc[t1.NR_CANDIDATO == FLAVIO, "votos"].sum() / t1.votos.sum(), 2), 47.03)
    revisar("% Lula, 1a vuelta", round(100 * t1.loc[t1.NR_CANDIDATO == LULA, "votos"].sum() / t1.votos.sum(), 2), 45.16)
    revisar("% Lula, 2a vuelta", round(100 * t2.loc[t2.NR_CANDIDATO == LULA, "votos"].sum() / t2.votos.sum(), 2), 51.74)
    print(f"Votos de Lula, 2a vuelta: {t2.loc[t2.NR_CANDIDATO == LULA, 'votos'].sum():,}")
    print(f"Votos válidos: 1a vuelta {t1.votos.sum():,}; 2a vuelta {t2.votos.sum():,}")


def tabla_municipal(votos):
    # El exterior (ZZ) cuenta para validar, pero no tiene municipio ni dato de pobreza
    exterior = votos[votos.SG_UF == "ZZ"]
    print(f"\nVotos del exterior excluidos: {exterior.votos.sum():,}")
    v = votos[votos.SG_UF != "ZZ"]

    por_candidato = v[v.NR_CANDIDATO.isin([LULA, FLAVIO])].pivot_table(
        index="CD_MUNICIPIO", columns=["NR_TURNO", "NR_CANDIDATO"], values="votos", aggfunc="sum", fill_value=0)
    por_candidato.columns = [f"{'lula' if c == LULA else 'flavio'}_t{t}" for t, c in por_candidato.columns]
    validos = v.pivot_table(index="CD_MUNICIPIO", columns="NR_TURNO", values="votos", aggfunc="sum")
    validos.columns = [f"validos_t{t}" for t in validos.columns]
    return por_candidato.join(validos).reset_index()


def pobreza():
    censo = pd.read_csv(RAW / "censo2022_tabla10296.csv", dtype=str)
    clase = "Classes de rendimento nominal mensal domiciliar per capita (Código)"
    censo["personas"] = pd.to_numeric(censo["Valor"].replace("-", "0"), errors="coerce")
    print(f"\nCeldas del censo sin dato: {censo.personas.isna().sum()}")
    tabla = censo.pivot_table(index=["Município (Código)", "Município"], columns=clase,
                              values="personas", aggfunc="sum").reset_index()
    # La pobreza incluye a quienes declararon no tener ingresos
    tabla["pobreza_12"] = 100 * (tabla[HASTA_1_4] + tabla[DE_1_4_A_1_2] + tabla[SIN_INGRESO]) / tabla[TOTAL]
    tabla["pobreza_14"] = 100 * (tabla[HASTA_1_4] + tabla[SIN_INGRESO]) / tabla[TOTAL]
    tabla["ibge"] = tabla["Município (Código)"].astype(int)
    nombre_uf = tabla["Município"].str.rsplit(" - ", n=1, expand=True)
    tabla["municipio"], tabla["uf"] = nombre_uf[0], nombre_uf[1]
    tabla["region"] = tabla["Município (Código)"].str[0].map(REGIONES)
    return tabla.rename(columns={TOTAL: "poblacion"})[
        ["ibge", "municipio", "uf", "region", "poblacion", "pobreza_12", "pobreza_14"]]


votos = leer_presidente()
validar(votos)
mun = tabla_municipal(votos)

equiv = pd.read_csv(RAW / "municipios_tse_ibge.csv")[["codigo_tse", "codigo_ibge"]]
mun = mun.merge(equiv, how="left", left_on="CD_MUNICIPIO", right_on="codigo_tse")
sin_equiv = mun[mun.codigo_ibge.isna()]
print(f"Municipios TSE sin código IBGE: {len(sin_equiv)}, con {sin_equiv.validos_t2.sum():,.0f} votos")
print(sin_equiv[["CD_MUNICIPIO", "validos_t2"]].to_string(index=False))

df = pobreza().merge(mun.dropna(subset=["codigo_ibge"]), how="left", left_on="ibge", right_on="codigo_ibge")
print(f"Municipios del censo sin votos: {df.validos_t2.isna().sum()}")
print(df.loc[df.validos_t2.isna(), ["municipio", "uf"]].to_string(index=False))
df = df.dropna(subset=["validos_t1", "validos_t2"]).drop(columns=["CD_MUNICIPIO", "codigo_tse", "codigo_ibge"])

df["pct_lula_t1"] = 100 * df.lula_t1 / df.validos_t1
df["pct_flavio_t1"] = 100 * df.flavio_t1 / df.validos_t1
df["pct_lula_t2"] = 100 * df.lula_t2 / df.validos_t2
df["cambio_lula"] = df.pct_lula_t2 - df.pct_lula_t1
df["ganador_t1"] = (df.lula_t1 > df.flavio_t1).map({True: "Lula", False: "Flávio"})
df["ganador_t2"] = (df.lula_t2 > df.flavio_t2).map({True: "Lula", False: "Flávio"})
df.to_csv(PROC / "municipios.csv", index=False, encoding="utf-8")

print("\n=== Resultado ===")
print(f"{len(df)} municipios; {df.uf.nunique()} estados")
print(f"Pobreza (<= 1/2 salario mínimo): {df.pobreza_12.min():.1f}% a {df.pobreza_12.max():.1f}%, mediana {df.pobreza_12.median():.1f}%")
print(f"% Lula 2a vuelta: {df.pct_lula_t2.min():.1f}% a {df.pct_lula_t2.max():.1f}%")
print(f"Valores vacíos: {df[['pobreza_12', 'pct_lula_t1', 'pct_lula_t2']].isna().sum().sum()}")
print(df.nlargest(3, "pobreza_12")[["municipio", "uf", "pobreza_12", "pct_lula_t2"]].to_string(index=False))
print(df.nsmallest(3, "pobreza_12")[["municipio", "uf", "pobreza_12", "pct_lula_t2"]].to_string(index=False))