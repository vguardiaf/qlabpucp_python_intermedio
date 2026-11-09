"""Evalúa las 10 preguntas en dos modos: A sin MCP ni Skills, B con el MCP bcrp y las Skills del proyecto.

    uv run evaluacion/evaluar.py                 # 20 llamadas a claude -p
    uv run evaluacion/evaluar.py --modos B       # solo un modo

Decisiones de método (adaptado de evaluar.py de la Sesión 04 y de la evaluación de enaho-skill):
- Cada pregunta va en una sesión independiente (claude -p --no-session-persistence), mismo modelo y misma
  instrucción en ambos modos, y respuesta en JSON con un solo número (--json-schema).
- Modo A: sin herramientas (--tools ""), sin MCP (--strict-mcp-config sin config), sin Skills, en una carpeta
  temporal vacía fuera del repositorio: no puede leer salidas/ ni las respuestas esperadas.
- Modo B: desde tarea_4/ con --setting-sources project (solo las Skills del proyecto), el MCP bcrp por
  --mcp-config y permisos para el MCP, las Skills, Read y uv run. Sin WebSearch ni WebFetch.
- Las respuestas esperadas están en preguntas.csv y se fijaron antes de correr (ver git log).
"""
import argparse
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
LOGS = AQUI / "logs"
ESQUEMA = {"type": "object", "required": ["valor", "fuente"],
           "properties": {"valor": {"type": ["number", "null"]}, "unidad": {"type": "string"},
                          "fuente": {"type": "string"}}}
INSTRUCCION = ("Responde con un solo número en «valor», en la unidad que pide la pregunta. Si no puedes saberlo "
               "con certeza, pon valor null: no estimes. En «fuente» di de dónde sale la cifra.\n\n")
MODOS = {
    "A": ["--tools", "", "--strict-mcp-config", "--disallowedTools", "Skill"],
    "B": ["--setting-sources", "project", "--strict-mcp-config", "--mcp-config", str(RAIZ / ".mcp.json"),
          "--allowedTools", "mcp__bcrp", "Skill", "Read", "Glob", "Bash(uv run *)", "PowerShell(uv run *)"],
}
HERRAMIENTAS_HABILITADAS = {
    "A": "ninguna (sin herramientas de Claude Code, sin MCP, sin Skills; carpeta temporal vacía)",
    "B": "MCP bcrp (buscar_series, serie, resumen, graficar_serie, datos_departamentales); Skills del proyecto; Read, Glob, uv run",
}


def preguntar(q, modo, modelo):
    cwd = RAIZ if modo == "B" else Path(tempfile.mkdtemp(prefix="eval_modo_a_"))
    cmd = ["claude", "-p", INSTRUCCION + q.pregunta, "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo, *MODOS[modo]]
    entorno = {**os.environ, "ECC_GATEGUARD": "off"}
    entorno.pop("VIRTUAL_ENV", None)
    t = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=600, cwd=cwd, env=entorno)
        salida, error = proc.stdout, ""
    except subprocess.TimeoutExpired:
        salida, error = "", "timeout 600 s"
    segundos = round(time.time() - t, 1)
    (LOGS / f"{q.id}_{modo}.jsonl").write_text(salida, encoding="utf-8")

    herramientas, r, resultado = [], {}, {}
    for linea in salida.splitlines():
        try:
            e = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "assistant":
            for p in e["message"]["content"]:
                if p.get("type") == "tool_use":
                    n = p["name"]
                    herramientas.append(f"Skill:{p['input'].get('skill')}" if n == "Skill" else n)
        elif e.get("type") == "result":
            resultado = e
            r = e.get("structured_output") or {}
    if not resultado and not error:
        error = "sin respuesta final"
    return {"valor": r.get("valor"), "unidad": r.get("unidad", ""),
            "fuente_declarada": r.get("fuente", (resultado.get("result") or "")[:200]),
            "herramientas": ";".join(dict.fromkeys(h for h in herramientas if h != "ToolSearch")),
            "segundos": segundos, "turnos": resultado.get("num_turns"), "error": error}


def calificar(valor, verdad, tolerancia):
    if valor is None:
        return "no responde"
    return "correcta" if abs(float(valor) - verdad) <= tolerancia else "incorrecta"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["A", "B"], choices=list(MODOS))
    p.add_argument("--modelo", default="sonnet")
    p.add_argument("--paralelo", type=int, default=4)
    a = p.parse_args()
    LOGS.mkdir(exist_ok=True)

    preguntas = pd.read_csv(AQUI / "preguntas.csv")
    casos = [(q, m) for m in a.modos for q in preguntas.itertuples()]
    print(f"{len(casos)} llamadas a claude -p con {a.modelo}...", flush=True)
    with ThreadPoolExecutor(a.paralelo) as ex:
        respuestas = list(ex.map(lambda c: preguntar(c[0], c[1], a.modelo), casos))

    filas = [{"id": q.id, "tipo": q.tipo, "modo": m, "pregunta": q.pregunta, "respuesta_esperada": q.verdad,
              "tolerancia": q.tolerancia, "respuesta_generada": r["valor"], "unidad": r["unidad"],
              "resultado": calificar(r["valor"], q.verdad, q.tolerancia), "fuente_esperada": q.fuente,
              "fuente_declarada": r["fuente_declarada"], "herramientas_usadas": r["herramientas"],
              "herramientas_habilitadas": HERRAMIENTAS_HABILITADAS[m], "segundos": r["segundos"],
              "turnos": r["turnos"], "error": r["error"], "modelo": a.modelo}
             for (q, m), r in zip(casos, respuestas)]
    res = pd.DataFrame(filas)
    destino = AQUI / "resultados.csv"
    if destino.exists() and len(a.modos) == 1:      # al correr un solo modo, conservar el otro
        previo = pd.read_csv(destino)
        res = pd.concat([previo[previo.modo != a.modos[0]], res])
    res.to_csv(destino, index=False, encoding="utf-8")

    tabla = res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    tabla["segundos_promedio"] = res.groupby("modo").segundos.mean().round(1)
    print(res.pivot(index="id", columns="modo", values="resultado").to_string())
    print("\n" + tabla.to_string())


if __name__ == "__main__":
    main()
