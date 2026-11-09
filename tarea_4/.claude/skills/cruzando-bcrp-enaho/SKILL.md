---
name: cruzando-bcrp-enaho
description: Cruza la profundización financiera por departamento del BCRP (crédito y depósitos por habitante) con la pobreza monetaria de la ENAHO del INEI, calcula correlaciones de Spearman con y sin Lima y Callao y grafica la dispersión. Úsala cuando pregunten si el crédito, los depósitos o la profundización financiera regional se asocian con la pobreza por departamento.
argument-hint: "[año]"
allowed-tools: Bash(uv run *), Read
---
# Cruzar BCRP y ENAHO por departamento

Trabaja desde la raíz del proyecto (tarea_4/). Año: $ARGUMENTS (si está vacío, 2024).

1. Si no existe salidas/personas_2024.parquet, usa primero la skill limpiando-enaho.
2. Si faltan salidas/bcrp_credito_2024.csv o salidas/bcrp_depositos_2024.csv, pídelos con la herramienta MCP datos_departamentales: grupo "credito directo departamentos", etiqueta "credito"; y grupo "depositos sistema financiero departamentos", etiqueta "depositos"; anio 2024.
3. Corre exactamente: uv run "${CLAUDE_SKILL_DIR}/scripts/cruzar.py" --anio 2024
4. Responde con las correlaciones que imprime (Spearman con 25 y con 23 departamentos), los extremos y las rutas de salidas/cruce_departamental.csv, salidas/correlaciones.csv y figuras/dispersion_profundizacion_pobreza.png.

El script une por código de departamento, pondera población y pobreza con facpob07 y mide la asociación por rangos. Es una asociación entre 25 departamentos en un solo año: no la presentes como efecto causal, y menciona que Lima concentra el registro de crédito de empresas con sede en la capital.
