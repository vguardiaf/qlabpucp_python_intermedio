---
name: graficando-enaho
description: Grafica la pobreza monetaria del Perú con la ENAHO del INEI en barras ponderadas por área urbana o rural, sexo, grupos de edad o departamento, con un título que dice el hallazgo, y guarda el PNG en figuras/. Úsala cuando pidan un gráfico, una figura o barras de la pobreza, o comparar la pobreza urbana y rural, por sexo, por edad o entre departamentos o regiones.
argument-hint: "[area|sexo|edad|departamento]"
allowed-tools: Bash(uv run *), Read
---
# Graficar la ENAHO

Trabaja desde la raíz del proyecto (tarea_4/).

1. Si no existe salidas/personas_2024.parquet, usa primero la skill limpiando-enaho.
2. Elige el corte según el pedido: area, sexo, edad o departamento. Si te lo pasan como argumento, usa $ARGUMENTS. Si piden varios, corre el script una vez por corte.
3. Corre exactamente: uv run "${CLAUDE_SKILL_DIR}/scripts/graficar.py" --por <corte>
4. Responde con el título que imprime el script (es el hallazgo), las cifras que imprime y la ruta de la figura.

El script fija las reglas de diseño: pondera con facpob07, barras desde cero y ordenadas, un solo color con el grupo más pobre resaltado, el valor escrito, la línea del promedio nacional, título analítico calculado con las cifras, subtítulo con qué, dónde y cuándo, nota de fuente y PNG a 200 dpi en figuras/. No grafiques por otra vía ni escribas cifras a mano.

Si piden un corte que el script no tiene, avísalo y agrégalo a scripts/graficar.py manteniendo esas reglas.
