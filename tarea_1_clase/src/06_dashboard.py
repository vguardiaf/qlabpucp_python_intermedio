"""Paso 6 · Armar el dashboard.

Junta los resultados de los pasos 3, 4 y 5 en un solo objeto DATOS y lo inserta en
la plantilla HTML. Genera dos archivos:
- dashboard/fragmento.html: para publicar como artifact de Claude.
- docs/index.html: página completa para GitHub Pages (Settings > Pages > main, / (root)).
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"

comp = json.loads((PROC / "comparacion.json").read_text(encoding="utf-8"))
resumen = json.loads((PROC / "resumen_incendios.json").read_text(encoding="utf-8"))

# Límites simplificados (~1 km) para que la página pese poco
deptos = gpd.read_file(PROC / "departamentos.geojson")
deptos["geometry"] = deptos.geometry.simplify(0.01, preserve_topology=True)
geo = json.loads(deptos.to_json(drop_id=True))
for f in geo["features"]:  # 3 decimales = ~100 m, suficiente para el mapa
    f["geometry"] = json.loads(json.dumps(f["geometry"]), parse_float=lambda x: round(float(x), 3))

inc = gpd.read_file(PROC / "incendios_activos.geojson")
cols = ["departamento", "lat", "lon", "focos", "frp_total", "area_focos_ha", "primer_foco", "ultimo_foco",
        "poblacion_5km", "dias_criticos", "lluvia_14d_mm", "lluvia_7d_pron_mm", "hr_min_pron",
        "viento_max_pron", "tmax_pron", "riesgo", "clima_propicio", "prioridad", "pronostico"]
inc = pd.DataFrame(inc[cols])
inc["frp_total"] = inc.frp_total.round(0)
# Según la versión de pyogrio, el campo JSON llega como texto o ya como dict
inc["pronostico"] = inc.pronostico.apply(lambda p: json.loads(p) if isinstance(p, str) else p)
inc = inc.sort_values("prioridad", ascending=False)

f7 = pd.read_csv(PROC / "focos_7d.csv")

DATOS = {
    "nacional": comp["nacional"],
    "serie": {"dias": comp["serie"]["dias"], "acumulado": comp["serie"]["acumulado"]},
    "departamentos": comp["departamentos"],
    "resumen": resumen,
    "geo": geo,
    "focos7d": f7[["lon", "lat"]].round(3).values.tolist(),
    "incendios": json.loads(inc.to_json(orient="records", date_format="iso")),
    "dnbr": json.loads((PROC / "dnbr_incendios.json").read_text(encoding="utf-8")),
    "validacion": {"resumen": json.loads((PROC / "validacion_reglas.json").read_text(encoding="utf-8"))["resumen"]},
}

plantilla = (BASE / "src" / "plantilla_dashboard.html").read_text(encoding="utf-8")
datos_js = json.dumps(DATOS, ensure_ascii=False, separators=(",", ":"))
fragmento = plantilla.replace("/*__DATOS__*/null", datos_js)

(BASE / "dashboard").mkdir(exist_ok=True)
(BASE / "dashboard" / "fragmento.html").write_text(fragmento, encoding="utf-8")

(BASE / "docs").mkdir(exist_ok=True)
pagina = ('<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
          f"</head><body>\n{fragmento}\n</body></html>\n")
(BASE / "docs" / "index.html").write_text(pagina, encoding="utf-8")
print(f"dashboard listo: docs/index.html ({len(pagina) / 1e6:.2f} MB)")
