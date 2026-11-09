> **Versión anterior archivada.** Corresponde a la primera pregunta (inflación, PBI y pobreza 2020-2024). Sus figuras se regeneraron para la pregunta final, así que las imágenes y rutas de este archivo ya no existen. Se conserva como evidencia del proceso.

# Evidencia de integración MCP + Skills

Ambas ejecuciones se hicieron con Claude Code en modo no interactivo (`claude -p`), desde `tarea_4/`, con `--setting-sources project`, `--strict-mcp-config --mcp-config .mcp.json` y salida `stream-json`. Los registros `.jsonl` contienen cada llamada a herramienta y su resultado.

## 1. Ejecución del agente de investigación: `ejecucion_agente.jsonl`

- **Instrucción:** [`prompt_agente.txt`](prompt_agente.txt). Antes de la ejecución se borraron `figuras/`, `mapas/` y `salidas/`, así que todo lo que usa el informe se generó en esta misma ejecución.
- **Duración:** 144 s, 25 turnos.
- **Resultado:** [`informes/informe_final.md`](../../informes/informe_final.md), con 3 figuras y 1 mapa.

Herramientas usadas, en orden:

| # | Herramienta | Tipo | Llamada |
|---|---|---|---|
| 1-3 | `buscar_series` | MCP | "ipc 12 meses" (Mensual) → PN01273PM; "pbi variaciones porcentuales" (Anual) → PM04923AA |
| 4-5 | `resumen` | MCP | PN01273PM 2020-01 a 2024-12; PM04923AA 2020 a 2024 |
| 6-7 | `serie` | MCP | Las mismas dos series y periodos |
| 8 | `graficar_serie` | MCP | PN01273PM con referencia 3 → `figuras/bcrp_PN01273PM_2020-01_2024-12.png` |
| 9 | `limpiando-enaho` | Skill | Base validada con 13/13 chequeos OK |
| 10 | `graficando-enaho` | Skill | Cortes `area` y `departamento` |
| 11 | `mapeando-enaho` | Skill | Mapa y comparación 25/25 con la Sesión 16 |
| 12 | `graficar_serie` | MCP | Se regeneró el gráfico con un título más corto, porque el primero salía cortado |

En total se usaron **4 herramientas MCP distintas y 3 skills distintas** en una sola ejecución. El mínimo exigido era 2 y 2.

## 2. Manejo de errores: `manejo_errores.jsonl`

Se le hicieron al agente tres preguntas sin respuesta posible:

| Pregunta | Qué hizo el agente | ¿Inventó una cifra? |
|---|---|---|
| Inflación de Lima en enero de 1850 | Encontró PN01273PM con `buscar_series` y llamó a `serie`. Recibió el error *"no tiene datos entre 1850-01 y 1850-01"*, lo informó, explicó que la serie empieza en 1950 y ofreció consultar ese año | No |
| Pobreza ENAHO 2019 | Cargó `limpiando-enaho`, leyó `reference.md` y revisó `datos/`. Informó que la skill solo valida 2024 y que no hay archivos de 2019 | No |
| Serie `ZZ12345` | `serie` devolvió *"No existe el código de serie 'ZZ12345'"* y el agente transmitió ese error | No |
