"""Servidor MCP del BCRP. Empiecen aquí: buscar_series ya funciona; completen los TODO hasta que pasen las pruebas.

    uv run pytest                                           # el contrato: las 8 pruebas deben pasar
    uv run server.py                                        # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run server.py # conectarlo a Claude Code

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import calendar
import json
import re
import time
import unicodedata
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, y serie para los datos. No calcules a mano: "
    "cita siempre el código de la serie y el periodo."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


# ---------------------------------------------------------------------------------------------------------------
# Fechas y periodos
#   La API pide 2025-1 (mensual y trimestral), 2025-01-15 (diaria) o 2025 (anual) y devuelve "Ene.2025",
#   "01.Oct.26", "T1.25" o "2025". Aquí se aceptan fechas flexibles y se devuelven periodos uniformes:
#   "2025-01", "2026-10-01", "2025-T1" o "2025".
# ---------------------------------------------------------------------------------------------------------------
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
         "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}
INTENTOS = 4


def _fecha_api(fecha, frecuencia, final):
    """Convierte la fecha que pide el usuario al formato de la API según la frecuencia de la serie."""
    f = str(fecha).strip().upper()
    m = re.fullmatch(r"(\d{4})(?:-(T?)(\d{1,2}))?(?:-(\d{1,2}))?", f)
    if not m:
        raise ToolError(f"Fecha {fecha!r} no válida. Usen 2025, 2025-03, 2025-T1 o 2025-03-15.")
    anio, es_trimestre, parte, dia = m.group(1), m.group(2), m.group(3), m.group(4)
    frecuencia = frecuencia.lower()
    if frecuencia.startswith("anual"):
        return anio
    if frecuencia.startswith("trimestral"):
        if parte is None:
            return f"{anio}-{4 if final else 1}"
        trimestre = int(parte) if es_trimestre else (int(parte) - 1) // 3 + 1  # un mes se lleva a su trimestre
        return f"{anio}-{trimestre}"
    if frecuencia.startswith("mensual"):
        if parte is None:
            return f"{anio}-{12 if final else 1}"
        return f"{anio}-{int(parte)}"
    # diaria
    if parte is None:
        return f"{anio}-12-31" if final else f"{anio}-01-01"
    mes = int(parte)
    if dia is None:
        dia = calendar.monthrange(int(anio), mes)[1] if final else 1
    return f"{anio}-{mes:02d}-{int(dia):02d}"


def _periodo(nombre):
    """Lleva el nombre de periodo de la API a un formato ordenable."""
    n = nombre.strip()
    if m := re.fullmatch(r"(\d{2})\.(\w{3})\.(\d{2})", n):                 # 01.Oct.26
        return f"20{m.group(3)}-{MESES[m.group(2).lower()]:02d}-{m.group(1)}"
    if m := re.fullmatch(r"(\w{3})\.(\d{4})", n):                          # Ene.2025
        return f"{m.group(2)}-{MESES[m.group(1).lower()]:02d}"
    if m := re.fullmatch(r"T(\d)\.(\d{2})", n):                            # T1.25
        return f"20{m.group(2)}-T{m.group(1)}"
    if re.fullmatch(r"\d{4}", n):                                          # 2025
        return n
    raise ToolError(f"Periodo {nombre!r} con un formato que el servidor no reconoce.")


@cache
def _descargar(url):
    """Baja el JSON de la API. Si responde HTML (límite de pedidos), espera y reintenta. Queda en caché."""
    for intento in range(INTENTOS):
        try:
            r = httpx.get(url, timeout=60)
            r.raise_for_status()
            return json.loads(r.content.decode("utf-8-sig"))
        except (json.JSONDecodeError, httpx.HTTPError):
            if intento == INTENTOS - 1:
                raise ToolError(f"La API del BCRP no respondió datos válidos para {url} tras {INTENTOS} intentos.")
            time.sleep(2 * (intento + 1))


def _serie(codigo, desde, hasta):
    codigo = str(codigo).strip().upper()
    ficha = _ficha(codigo)                     # ToolError con el código si no existe
    d = _fecha_api(desde, ficha["frecuencia"], final=False)
    h = _fecha_api(hasta, ficha["frecuencia"], final=True)
    url = f"{API}/{codigo}/json/{d}/{h}"
    crudo = _descargar(url)
    datos = []
    for p in crudo.get("periods", []):
        valor = (p.get("values") or ["n.d."])[0]
        try:
            datos.append({"periodo": _periodo(p["name"]), "valor": float(valor)})
        except ValueError:                     # "n.d." y similares: sin dato
            continue
    if not datos:
        raise ToolError(f"La serie {codigo} no tiene datos entre {desde} y {hasta}. Prueben otro periodo.")
    return {"codigo": codigo, "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"],
            "desde": datos[0]["periodo"], "hasta": datos[-1]["periodo"], "datos": datos, "fuente": url}


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Descarga los datos oficiales de una serie del BCRP entre dos fechas.

    codigo: el código de buscar_series, por ejemplo "PN01273PM". desde y hasta aceptan "2025", "2025-03",
    "2025-T1" o "2025-03-15"; se adaptan a la frecuencia de la serie. Devuelve el nombre, la frecuencia,
    la lista de datos [{"periodo", "valor"}] sin los meses sin dato, y la URL de la fuente para citarla.
    """
    return _serie(codigo, desde, hasta)


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Resume una serie del BCRP en un periodo, con las cuentas hechas en Python (no las hagas a mano).

    Devuelve primero y ultimo ({"periodo", "valor"}), cambio (ultimo - primero, en las unidades de la serie),
    variacion_pct (cambio relativo en %), promedio, maximo y minimo (con su periodo), n (datos usados)
    y la fuente. Cita siempre el código y el periodo al usar estas cifras.
    """
    s = _serie(codigo, desde, hasta)
    df = pd.DataFrame(s["datos"])
    primero, ultimo = s["datos"][0], s["datos"][-1]
    imax, imin = df["valor"].idxmax(), df["valor"].idxmin()
    return {
        "codigo": s["codigo"], "nombre": s["nombre"], "frecuencia": s["frecuencia"],
        "primero": primero, "ultimo": ultimo,
        "cambio": round(ultimo["valor"] - primero["valor"], 6),
        "variacion_pct": None if primero["valor"] == 0 else round(100 * (ultimo["valor"] / primero["valor"] - 1), 4),
        "promedio": round(float(df["valor"].mean()), 6),
        "maximo": {"periodo": df.at[imax, "periodo"], "valor": float(df.at[imax, "valor"])},
        "minimo": {"periodo": df.at[imin, "periodo"], "valor": float(df.at[imin, "valor"])},
        "n": len(df), "fuente": s["fuente"],
    }


# ---------------------------------------------------------------------------------------------------------------
# Herramienta propia: graficar_serie
#   El informe final necesita un gráfico del BCRP con código, periodo y fuente. Que lo haga el servidor
#   garantiza que el gráfico salga de los mismos datos que se citan, y no de cifras copiadas a mano.
# ---------------------------------------------------------------------------------------------------------------
FIGURAS = AQUI.parent / "figuras"


@mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
def graficar_serie(codigo: str, desde: str, hasta: str, titulo: str | None = None,
                   referencia: float | None = None) -> dict:
    """Grafica una serie oficial del BCRP y guarda el PNG en figuras/ para usarlo en un informe.

    codigo, desde y hasta como en serie. titulo: un título analítico opcional (por defecto, el nombre de la serie).
    referencia: un valor opcional que se dibuja como línea horizontal (por ejemplo 3 para el techo de la meta de
    inflación). Devuelve la ruta del PNG, el periodo graficado, el número de datos, el último valor, el máximo y
    la fuente. El gráfico lleva el código, el periodo y la fuente escritos.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = _serie(codigo, desde, hasta)
    df = pd.DataFrame(s["datos"])
    FIGURAS.mkdir(exist_ok=True)
    ruta = FIGURAS / f"bcrp_{s['codigo']}_{s['desde']}_{s['hasta']}.png"

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(range(len(df)), df["valor"], color="#1f5a8c", linewidth=2)
    if referencia is not None:
        ax.axhline(referencia, color="#b23a3a", linestyle="--", linewidth=1)
        ax.annotate(f"referencia: {referencia:g}", (0, referencia), xytext=(4, 4),
                    textcoords="offset points", fontsize=8, color="#b23a3a")
    paso = max(1, len(df) // 8)
    ax.set_xticks(range(0, len(df), paso), df["periodo"].iloc[::paso], rotation=45, ha="right", fontsize=8)
    imax = df["valor"].idxmax()
    ax.annotate(f"máx. {df.at[imax, 'valor']:.2f} ({df.at[imax, 'periodo']})", (imax, df.at[imax, "valor"]),
                xytext=(6, -12), textcoords="offset points", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(titulo or s["nombre"], loc="left", fontweight="bold", fontsize=11, pad=20)
    ax.text(0, 1.015, f"Serie {s['codigo']} · {s['frecuencia']} · {s['desde']} a {s['hasta']}",
            transform=ax.transAxes, fontsize=8, color="#555")
    fig.text(0.01, 0.01, f"Fuente: BCRP, estadísticas en línea, serie {s['codigo']}. {s['nombre']}", fontsize=7)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(ruta, dpi=200)
    plt.close(fig)

    return {"ruta": str(ruta.relative_to(AQUI.parent)).replace("\\", "/"), "codigo": s["codigo"],
            "nombre": s["nombre"], "desde": s["desde"], "hasta": s["hasta"], "n": len(df),
            "ultimo": s["datos"][-1], "maximo": {"periodo": df.at[imax, "periodo"], "valor": float(df.at[imax, "valor"])},
            "fuente": s["fuente"]}


# ---------------------------------------------------------------------------------------------------------------
# Herramienta propia 2: datos_departamentales
#   Las series regionales del BCRP vienen una por departamento. Esta herramienta trae las 25 de un grupo
#   en una sola llamada a la API (códigos unidos con "-"), les pone el código de departamento del INEI
#   (el mismo que ubigeo[:2] de la ENAHO) y guarda un CSV en salidas/ para cruzarlo con la ENAHO.
# ---------------------------------------------------------------------------------------------------------------
UBIGEO = {"amazonas": "01", "ancash": "02", "apurimac": "03", "arequipa": "04", "ayacucho": "05",
          "cajamarca": "06", "callao": "07", "cusco": "08", "huancavelica": "09", "huanuco": "10", "ica": "11",
          "junin": "12", "la libertad": "13", "lambayeque": "14", "lima": "15", "loreto": "16",
          "madre de dios": "17", "moquegua": "18", "pasco": "19", "piura": "20", "puno": "21",
          "san martin": "22", "tacna": "23", "tumbes": "24", "ucayali": "25"}
SALIDAS = AQUI.parent / "salidas"


@mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
def datos_departamentales(grupo: str, anio: int, etiqueta: str) -> dict:
    """Trae el valor anual de una serie regional del BCRP para los 25 departamentos del Perú, en una sola llamada.

    grupo: palabras del grupo de series regionales, por ejemplo "credito directo departamentos" o
    "depositos sistema financiero departamentos". anio: el año, por ejemplo 2024. etiqueta: nombre corto
    para el archivo, por ejemplo "credito". Usa las series anuales "(total)" (moneda nacional + extranjera).
    Devuelve una fila por departamento con el código INEI de 2 dígitos (igual a ubigeo[:2] de la ENAHO),
    el código de serie y el valor; guarda salidas/bcrp_<etiqueta>_<anio>.csv. Si no encuentra los 25, da error.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(grupo).split():
        m &= df.grupo.map(_sin_tildes).str.contains(re.escape(palabra))
    sel = df[m & (df.frecuencia == "Anual") & df.nombre.str.contains(r"\(total\)")].copy()
    sel["clave"] = sel.nombre.str.replace(r"\(total\)", "", regex=True).map(_sin_tildes).str.strip()
    sel = sel[sel.clave.isin(UBIGEO)]
    if sel.clave.nunique() != 25 or sel.grupo.nunique() != 1:
        raise ToolError(f"Con {grupo!r} encontré {sel.clave.nunique()} departamentos en {sel.grupo.nunique()} grupos; "
                        "se necesitan los 25 de un solo grupo. Prueben palabras más precisas.")
    codigos = sel.codigo.tolist()
    url = f"{API}/{'-'.join(codigos)}/json/{anio}/{anio}"
    crudo = _descargar(url)
    periodos = crudo.get("periods", [])
    if not periodos:
        raise ToolError(f"El BCRP no tiene datos de {sel.grupo.iloc[0]!r} para {anio}.")
    valores = periodos[0]["values"]
    filas = []
    for (_, f), v in zip(sel.iterrows(), valores):
        try:
            valor = float(v)
        except ValueError:
            raise ToolError(f"La serie {f.codigo} ({f.clave}) no tiene dato para {anio}.")
        filas.append({"departamento": UBIGEO[f.clave], "nombre": f.nombre.replace("(total)", "").strip(),
                      "codigo": f.codigo, "valor": valor})
    tabla = pd.DataFrame(filas).sort_values("departamento")
    SALIDAS.mkdir(exist_ok=True)
    ruta = SALIDAS / f"bcrp_{etiqueta}_{anio}.csv"
    tabla.assign(anio=anio, grupo=sel.grupo.iloc[0], fuente=url).to_csv(ruta, index=False, encoding="utf-8")
    return {"grupo": sel.grupo.iloc[0], "anio": anio, "n": len(tabla), "total": round(tabla.valor.sum(), 2),
            "ruta": str(ruta.relative_to(AQUI.parent)).replace("\\", "/"), "fuente": url,
            "datos": tabla.to_dict("records")}


# ---------------------------------------------------------------------------------------------------------------
# Recurso y prompt
# ---------------------------------------------------------------------------------------------------------------
@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json")
def ficha_serie(codigo: str) -> dict:
    """Ficha descriptiva de una serie del BCRP: nombre, categoría, frecuencia, inicio y última actualización."""
    return _ficha(str(codigo).strip().upper())


@mcp.prompt
def informe(tema: str, desde: str = "2020", hasta: str = "2024") -> str:
    """Pide un informe breve sobre un indicador del BCRP, con cada cifra trazable a su serie y periodo."""
    return (
        f"Prepara un informe breve sobre: {tema}, entre {desde} y {hasta}.\n"
        "1. Usa buscar_series para encontrar la serie oficial más adecuada y explica por qué la eliges.\n"
        "2. Usa resumen para las cifras (primero, último, cambio, promedio, máximo y mínimo); no hagas cuentas a mano.\n"
        "3. Usa graficar_serie para el gráfico y cita su ruta.\n"
        "4. Cada cifra debe ir con su código de serie, su periodo y la fuente (BCRP).\n"
        "5. Si una herramienta falla o no hay datos, dilo: no inventes valores.\n"
        "6. Describe asociaciones, no causas."
    )


if __name__ == "__main__":
    mcp.run()
