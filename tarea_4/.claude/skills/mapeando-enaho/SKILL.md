---
name: mapeando-enaho
description: Hace un mapa de la pobreza monetaria por departamento del Perú con la ENAHO del INEI, unido por código a los límites de los 25 departamentos, y lo guarda en mapas/. Úsala cuando pidan un mapa de la pobreza, un mapa por departamento o región, o ver la pobreza en el territorio peruano.
allowed-tools: Bash(uv run *), Read
---
# Mapear la ENAHO

Trabaja desde la raíz del repositorio.

1. Si no existe salidas/personas_2024.parquet, usa primero la skill limpiando-enaho.
2. Si falta datos/peru_departamental_simple.geojson, pide al usuario bajarlo de https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson
3. Corre exactamente: uv run "${CLAUDE_SKILL_DIR}/scripts/mapear.py"
4. Si el script falla, detente y reporta el error. El mapa va con facpob07; la comparación con referencias/pobreza_departamento_2024.csv (Sesión 16) se hace con factor07 x mieperho, el mismo método de la referencia, y debe dar 25/25 dentro de ±0.1 puntos.
5. Responde con los departamentos de mayor y menor pobreza, el resultado de la comparación (salidas/comparacion_mapa.csv) y la ruta del mapa.

El script fija las reglas: une ubigeo[:2] con FIRST_IDDP como texto, nunca por nombre; exige 25 departamentos con dato; deja Lima (15) y Callao (07) separados; usa un color de claro a oscuro desde 0, nunca arcoíris; y pone la leyenda en % de personas. No hagas el mapa por otra vía.