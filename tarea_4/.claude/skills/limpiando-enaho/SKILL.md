---
name: limpiando-enaho
description: Limpia los módulos 34 (sumaria) y 02 (miembros) de la ENAHO del INEI y arma una base de personas con pobreza y factor de expansión. Úsala cuando pidan limpiar, unir o analizar la ENAHO, o cuando pregunten por la pobreza monetaria en el Perú a nivel nacional, por departamento o región (como Cusco, Puno o Lima), por área urbana o rural, sexo o edad.
argument-hint: "[año]"
allowed-tools: Bash(uv run *), Read
---
# Limpiar la ENAHO

Año pedido: $ARGUMENTS (si está vacío, usa 2024). Por ahora solo 2024 tiene cifras oficiales para validar.

Trabaja desde la raíz del repositorio.

1. Si salidas/personas_2024.parquet existe y salidas/validacion.txt termina en `RESULTADO: OK`, pasa al paso 4.
2. Si faltan los zip en datos/, pide al usuario bajarlos del INEI (código 966 = 2024). Las URL están en reference.md.
3. Corre exactamente: uv run "${CLAUDE_SKILL_DIR}/scripts/limpiar.py" --anio 2024
4. Lee salidas/validacion.txt. Si dice `RESULTADO: FALLA`, detente y reporta qué falló. No des cifras.
5. Responde con salidas/personas_2024.parquet, usando `uv run python -c` con pandas. Toda cifra va ponderada con facpob07; nunca cuentes filas.
6. Antes de usar una variable o un código de departamento, lee reference.md.