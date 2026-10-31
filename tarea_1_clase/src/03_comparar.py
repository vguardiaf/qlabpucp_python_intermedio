"""Paso 3 · ¿Es 2026 un año récord? (reto E)

Compara la temporada 2026 (1 de julio -> último día completo) con la MISMA ventana
de cada año 2012-2025, a nivel nacional y por departamento. Solo cuenta focos sobre
los focos clasificados como incendio.
"""
import json
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"

todos = pd.read_csv(PROC / "focos_limpios.csv.gz", parse_dates=["fecha"])
# Solo focos que el paso 2 clasifica como incendio (no quemas de manejo ni fuentes fijas)
focos = todos[todos.es_incendio].copy()

# El día más reciente con datos llega incompleto (falta alguna pasada),
# así que el corte es el día anterior.
corte = focos.loc[focos.anio == 2026, "fecha"].max() - pd.Timedelta(days=1)
print(f"Corte: {corte:%Y-%m-%d}")

# Día de temporada: 0 = 1 de julio. Misma ventana para todos los años.
inicio = pd.to_datetime(focos.anio.astype(str) + "-07-01")
focos["dia"] = (focos.fecha - inicio).dt.days
dia_corte = (corte - pd.Timestamp("2026-07-01")).days
temp = focos[(focos.dia >= 0) & (focos.dia <= dia_corte)]

# --- Nacional ---
por_anio = temp.groupby("anio").size()
hist = por_anio.drop(2026)
nacional = {
    "corte": f"{corte:%Y-%m-%d}",
    "focos_2026": int(por_anio[2026]),
    "promedio_hist": round(float(hist.mean())),
    "anomalia_pct": round(100 * (por_anio[2026] / hist.mean() - 1), 1),
    "puesto_2026": int(por_anio.rank(ascending=False)[2026]),
    "anio_max_hist": int(hist.idxmax()),
    "max_hist": int(hist.max()),
    "por_anio": {int(k): int(v) for k, v in por_anio.items()},
}
print(json.dumps({k: v for k, v in nacional.items() if k != "por_anio"}, indent=1))

# Cuántos focos de la temporada 2026 se descartaron y por qué cobertura
t26 = todos[(todos.anio == 2026) & (todos.fecha >= "2026-07-01") & (todos.fecha <= corte)]
nacional["focos_2026_sin_filtro"] = len(t26)
nacional["motivo_2026"] = t26.motivo.value_counts().to_dict()
print(f"Temporada 2026 sin filtro: {len(t26):,}; por motivo: {nacional["motivo_2026"]}")

# Octubre por separado: es el mes que el profesor marcó como récord
dia_oct = (pd.Timestamp("2026-10-01") - pd.Timestamp("2026-07-01")).days
octubre = temp[temp.dia >= dia_oct].groupby("anio").size()
nacional["octubre_2026"] = int(octubre[2026])
nacional["octubre_anomalia_pct"] = round(100 * (octubre[2026] / octubre.drop(2026).mean() - 1), 1)
nacional["octubre_puesto"] = int(octubre.rank(ascending=False)[2026])
nacional["octubre_por_anio"] = {int(k): int(v) for k, v in octubre.items()}
print(f"Octubre: {octubre[2026]:,} focos, {nacional['octubre_anomalia_pct']:+.1f} % vs promedio, puesto {nacional['octubre_puesto']}")

# --- Serie diaria y acumulada por año ---
diaria = temp.groupby(["anio", "dia"]).size().unstack(0).reindex(range(dia_corte + 1)).fillna(0)
serie = {
    "dias": [f"{(pd.Timestamp('2026-07-01') + pd.Timedelta(days=d)):%Y-%m-%d}" for d in diaria.index],
    "media7": {int(a): diaria[a].rolling(7, min_periods=1).mean().round(1).tolist() for a in diaria},
    "acumulado": {int(a): diaria[a].cumsum().astype(int).tolist() for a in diaria},
}

# --- Por departamento ---
tabla = temp.groupby(["departamento", "anio"]).size().unstack(fill_value=0)
tabla = tabla.reindex(columns=range(2012, 2027), fill_value=0)
h = tabla.drop(columns=2026)
dep = pd.DataFrame({
    "focos_2026": tabla[2026],
    "promedio_hist": h.mean(axis=1).round(0),
    "max_hist": h.max(axis=1),
    "anio_max_hist": h.idxmax(axis=1),
    "puesto_2026": tabla.rank(axis=1, ascending=False, method="min")[2026].astype(int),
})
dep["anomalia_pct"] = (100 * (dep.focos_2026 / dep.promedio_hist - 1)).round(1)
# Con menos de 30 focos de promedio la anomalía % no es interpretable
dep.loc[dep.promedio_hist < 30, "anomalia_pct"] = None
dep["record"] = dep.focos_2026 > dep.max_hist
dep = dep.sort_values("focos_2026", ascending=False)
print(dep.to_string())

dep.reset_index().to_csv(PROC / "departamentos_comparacion.csv", index=False)
(PROC / "comparacion.json").write_text(json.dumps({
    "nacional": nacional,
    "serie": serie,
    "departamentos": json.loads(dep.reset_index().to_json(orient="records")),
}, ensure_ascii=False), encoding="utf-8")
