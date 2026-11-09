"""Limpia los módulos 34 (sumaria) y 02 (miembros) de la ENAHO y arma una base de personas.

Decisiones de método:
- Se lee sumaria-2024.dta por su nombre exacto: el zip trae también sumaria-2024-12g.dta
  y las cifras de referencia salen de la primera.
- Se leen códigos, no etiquetas (convert_categoricals=False), y las llaves quedan como
  texto para conservar los ceros a la izquierda.
- Residentes habituales, según el INEI: miembros que no se ausentaron 30 días o más y
  no miembros que estuvieron presentes 30 días o más.
- ubigeo, dominio y estrato se toman solo de la sumaria, para que la unión no cree
  columnas repetidas con sufijos _x y _y.
- La pobreza se valida de dos formas: sumaria con factor07 x mieperho y personas con
  facpob07. Ambas deben quedar a 0.1 puntos de la cifra oficial.
- El parquet solo se guarda si pasan todas las validaciones. validacion.txt muestra cada chequeo como
  OK o FALLA: conteos, duplicados tras la unión, los 25 códigos territoriales, los factores de
  expansión, y la pobreza nacional, extrema, urbana y rural contra las cifras oficiales.
- salidas/indicadores.csv guarda las tasas por grupo con los dos ponderadores, para que el informe
  cite cifras que salen del procesamiento y no escritas a mano.
"""
import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[4]
DATOS = BASE / "datos"
SALIDAS = BASE / "salidas"

CODIGOS = {2024: 966}  # código de cada año en el portal de microdatos del INEI
OFICIAL = {
    2024: {
        "hogares": 33691,
        "filas_miembros": 117721,
        "residentes": 108664,
        "pobreza": 27.6,
        "extrema": 5.5,
        "urbana": 24.8,
        "rural": 39.3,
        "poblacion_millones": 34.0,  # población proyectada del INEI para 2024, con tolerancia de 1 millón
    }
}

DEPARTAMENTOS = {
    "01": "Amazonas", "02": "Áncash", "03": "Apurímac", "04": "Arequipa", "05": "Ayacucho",
    "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huánuco",
    "11": "Ica", "12": "Junín", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
    "16": "Loreto", "17": "Madre de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
    "21": "Puno", "22": "San Martín", "23": "Tacna", "24": "Tumbes", "25": "Ucayali",
}

LLAVES = ["conglome", "vivienda", "hogar"]
LLAVES_PERSONA = LLAVES + ["codperso"]
COLUMNAS_HOGAR = LLAVES + ["ubigeo", "dominio", "estrato", "pobreza", "mieperho", "factor07"]
COLUMNAS_PERSONA = LLAVES_PERSONA + ["anio", "p203", "p204", "p205", "p206", "p207", "p208a", "facpob07"]


def normalizar(columna):
    columna = columna.lower()
    return "anio" if re.fullmatch(r"a.{1,2}o", columna) else columna


def leer_dta(ruta_zip, nombre):
    if not ruta_zip.exists():
        sys.exit(f"Falta {ruta_zip.name} en datos/. Bájalo del portal de microdatos del INEI.")
    with zipfile.ZipFile(ruta_zip) as z:
        candidatos = [n for n in z.namelist() if n.endswith("/" + nombre)]
        if len(candidatos) != 1:
            sys.exit(f"No encontré {nombre} en {ruta_zip.name}.")
        crudo = z.read(candidatos[0])
    df = pd.read_stata(io.BytesIO(crudo), convert_categoricals=False)
    df.columns = [normalizar(c) for c in df.columns]
    return df


def como_texto(df, columnas):
    for columna in columnas:
        df[columna] = df[columna].astype(str).str.strip()
    return df


def tasa(df, indicador, peso):
    pesos = df[peso].astype("float64")
    return 100 * (pesos * indicador).sum() / pesos.sum()


def _filas(df, mascara_pobre, peso, indicador, metodo, grupos):
    """Una fila por grupo: tasa ponderada, población expandida y tamaño muestral."""
    pesos = df[peso].astype("float64")
    tabla = pd.DataFrame({"grupo": grupos, "peso": pesos, "peso_pobre": pesos * mascara_pobre, "n": 1})
    sumas = tabla.groupby("grupo", sort=True)[["peso", "peso_pobre", "n"]].sum()
    return [
        {"indicador": indicador, "grupo": g, "metodo": metodo,
         "valor_pct": round(100 * s.peso_pobre / s.peso, 4),
         "poblacion_expandida": round(s.peso), "n_muestral": int(s.n)}
        for g, s in sumas.iterrows()
    ]


def indicadores(base, sumaria, anio):
    """Tabla larga con los indicadores que usan los gráficos, el mapa y el informe."""
    P, H = f"personas, facpob07", f"hogares, factor07 x mieperho"
    total = pd.Series("Perú", index=base.index)
    total_h = pd.Series("Perú", index=sumaria.index)
    area = base["urbano"].map({True: "Urbana", False: "Rural"})
    area_h = sumaria["urbano"].map({True: "Urbana", False: "Rural"})
    sexo = base["p207"].map({1: "Hombres", 2: "Mujeres"})
    depto = base["departamento"] + " " + base["nombre_departamento"]
    depto_h = sumaria["departamento"] + " " + sumaria["departamento"].map(DEPARTAMENTOS)
    filas = (
        _filas(base, base["pobre"], "facpob07", "pobreza_monetaria", P, total)
        + _filas(sumaria, sumaria["pobreza"] <= 2, "peso", "pobreza_monetaria", H, total_h)
        + _filas(base, base["extremo"], "facpob07", "pobreza_extrema", P, total)
        + _filas(sumaria, sumaria["pobreza"] == 1, "peso", "pobreza_extrema", H, total_h)
        + _filas(base, base["pobre"], "facpob07", "pobreza_por_area", P, area)
        + _filas(sumaria, sumaria["pobreza"] <= 2, "peso", "pobreza_por_area", H, area_h)
        + _filas(base.loc[sexo.notna()], base.loc[sexo.notna(), "pobre"], "facpob07", "pobreza_por_sexo", P, sexo.dropna())
        + _filas(base, base["pobre"], "facpob07", "pobreza_por_departamento", P, depto)
        + _filas(sumaria, sumaria["pobreza"] <= 2, "peso", "pobreza_por_departamento", H, depto_h)
    )
    tabla = pd.DataFrame(filas)
    tabla.insert(0, "anio", anio)
    tabla["fuente"] = f"INEI, ENAHO {anio}, módulos 34 y 02"
    return tabla


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--anio", type=int, default=2024, choices=sorted(CODIGOS))
    anio = parser.parse_args().anio
    codigo = CODIGOS[anio]
    oficial = OFICIAL[anio]

    SALIDAS.mkdir(exist_ok=True)
    salida = SALIDAS / f"personas_{anio}.parquet"
    salida.unlink(missing_ok=True)

    # 1 y 2. Leer y normalizar
    sumaria = leer_dta(DATOS / f"{codigo}-Modulo34.zip", f"sumaria-{anio}.dta")
    miembros = leer_dta(DATOS / f"{codigo}-Modulo02.zip", f"enaho01-{anio}-200.dta")
    filas_miembros = len(miembros)

    sumaria = como_texto(sumaria[COLUMNAS_HOGAR].copy(), LLAVES + ["ubigeo"])
    miembros = como_texto(miembros[COLUMNAS_PERSONA].copy(), LLAVES_PERSONA)
    assert sumaria["ubigeo"].str.len().eq(6).all(), "ubigeo perdió ceros a la izquierda"
    assert sumaria["conglome"].str.len().eq(6).all(), "conglome perdió ceros a la izquierda"

    # 3. Filtrar residentes habituales
    residente = ((miembros["p204"] == 1) & (miembros["p205"] == 2)) | (
        (miembros["p204"] == 2) & (miembros["p206"] == 1)
    )
    personas = miembros.loc[residente].copy()
    assert not personas.duplicated(LLAVES_PERSONA).any(), "personas repetidas"

    # 4. Unir personas y hogares
    base = personas.merge(sumaria, on=LLAVES, how="left", validate="m:1", indicator=True)
    assert len(base) == len(personas), "la unión duplicó filas"
    assert (base["_merge"] == "both").all(), "hay personas sin hogar en la sumaria"
    base = base.drop(columns="_merge")
    assert base[["pobreza", "facpob07"]].notna().all().all(), "hay pobreza o factor vacíos"
    assert base["pobreza"].isin([1, 2, 3]).all(), "pobreza tiene códigos inesperados"

    # 5. Construir variables
    base["departamento"] = base["ubigeo"].str[:2]
    base["nombre_departamento"] = base["departamento"].map(DEPARTAMENTOS)
    base["urbano"] = base["estrato"] <= 5
    base["pobre"] = base["pobreza"] <= 2
    base["extremo"] = base["pobreza"] == 1
    sumaria["departamento"] = sumaria["ubigeo"].str[:2]
    sumaria["urbano"] = sumaria["estrato"] <= 5
    sumaria["peso"] = sumaria["factor07"].astype("float64") * sumaria["mieperho"]

    # 6. Validar. Cada chequeo: (nombre, valor, esperado, tolerancia); valores lógicos se comparan con True.
    urb_h, rur_h = sumaria[sumaria["urbano"]], sumaria[~sumaria["urbano"]]
    poblacion = base["facpob07"].astype("float64").sum()
    simple = 100 * base["pobre"].mean()                        # sin ponderar: solo para mostrar que se pondera
    ponderada = tasa(base, base["pobre"], "facpob07")
    chequeos = [
        ("hogares en la sumaria", len(sumaria), oficial["hogares"], 0),
        ("filas del modulo 02", filas_miembros, oficial["filas_miembros"], 0),
        ("residentes habituales", len(base), oficial["residentes"], 0),
        ("personas duplicadas tras la union m:1", int(base.duplicated(LLAVES_PERSONA).sum()), 0, 0),
        ("codigos territoriales distintos (ubigeo[:2])", base["departamento"].nunique(), 25, 0),
        ("codigos territoriales = 01..25 con nombre", set(base["departamento"]) == set(DEPARTAMENTOS), True, 0),
        ("factores facpob07 positivos y sin vacios", bool((base["facpob07"] > 0).all()), True, 0),
        ("poblacion expandida con facpob07 (millones)", poblacion / 1e6, oficial["poblacion_millones"], 1.0),
        ("pobreza, sumaria con factor07 x mieperho", tasa(sumaria, sumaria["pobreza"] <= 2, "peso"), oficial["pobreza"], 0.1),
        ("pobreza, personas con facpob07", ponderada, oficial["pobreza"], 0.1),
        ("pobreza extrema, sumaria con factor07 x mieperho", tasa(sumaria, sumaria["pobreza"] == 1, "peso"), oficial["extrema"], 0.1),
        ("pobreza urbana, sumaria con factor07 x mieperho", tasa(urb_h, urb_h["pobreza"] <= 2, "peso"), oficial["urbana"], 0.1),
        ("pobreza rural, sumaria con factor07 x mieperho", tasa(rur_h, rur_h["pobreza"] <= 2, "peso"), oficial["rural"], 0.1),
    ]

    lineas = [f"Validacion ENAHO {anio}", ""]
    fallas = []
    for nombre, valor, esperado, tolerancia in chequeos:
        if isinstance(esperado, bool):
            correcto = valor is esperado
            detalle = f"{valor} (esperado {esperado})"
        else:
            correcto = abs(valor - esperado) <= tolerancia
            detalle = f"{valor:,.2f} (esperado {esperado:,}, tolerancia {tolerancia})"
        lineas.append(f"{'OK   ' if correcto else 'FALLA'} {nombre}: {detalle}")
        if not correcto:
            fallas.append(nombre)

    urbano, rural = base[base["urbano"]], base[~base["urbano"]]
    lima = base[base["dominio"] == 8]
    lineas += [
        "",
        "Informativo, personas con facpob07:",
        f"extrema: {tasa(base, base['extremo'], 'facpob07'):.2f} %",
        f"urbano: {tasa(urbano, urbano['pobre'], 'facpob07'):.2f} %",
        f"rural: {tasa(rural, rural['pobre'], 'facpob07'):.2f} %",
        f"Lima Metropolitana (dominio 8): {tasa(lima, lima['pobre'], 'facpob07'):.2f} %",
        f"proporcion simple sin ponderar (NO se usa): {simple:.2f} % frente a {ponderada:.2f} % ponderada",
        "",
        "RESULTADO: " + ("OK" if not fallas else "FALLA"),
    ]
    texto = "\n".join(lineas)
    (SALIDAS / "validacion.txt").write_text(texto + "\n", encoding="utf-8")
    print(texto)
    if fallas:
        sys.exit(f"Validación fallida, no se guarda la base: {fallas}")

    # 7. Guardar la base y la tabla de indicadores
    base.to_parquet(salida, index=False)
    indicadores(base, sumaria, anio).to_csv(SALIDAS / "indicadores.csv", index=False, encoding="utf-8")
    print(f"Guardado {salida.relative_to(BASE)}: {len(base):,} personas")
    print("Guardado salidas/indicadores.csv")


if __name__ == "__main__":
    main()