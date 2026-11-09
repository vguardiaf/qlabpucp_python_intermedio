# Evidencia de integración MCP + Skills

Las ejecuciones se hicieron con Claude Code en modo no interactivo (`claude -p`), desde `tarea_4/`, con `--setting-sources project`, `--strict-mcp-config --mcp-config .mcp.json` y salida `stream-json`. Cada `.jsonl` registra todas las llamadas a herramientas y sus resultados.

## 1. Ejecución final del agente: `ejecucion_agente.jsonl`

- **Pregunta:** ¿La profundización financiera departamental, entendida como créditos y depósitos, se asocia con menores niveles de pobreza en 2024?
- **Instrucción completa:** [`prompt_agente.txt`](prompt_agente.txt). Antes de correr se borraron `figuras/`, `mapas/` y `salidas/`: todo lo que usa el informe se generó en esta ejecución.
- **Duración:** 138 s, 25 turnos.
- **Resultado:** [`informes/informe_final.md`](../../informes/informe_final.md).

| Herramienta | Tipo | Llamadas | Para qué |
|---|---|---|---|
| `buscar_series` | MCP | 2 | Ubicar los grupos de crédito y de depósitos por departamento |
| `datos_departamentales` | MCP | 2 | Traer los 25 departamentos de 2024 → `salidas/bcrp_credito_2024.csv` y `salidas/bcrp_depositos_2024.csv` |
| `resumen` | MCP | 1 | RD16202DA 2015-2024: cambio, variación y máximo |
| `graficar_serie` | MCP | 2 | Gráfico RD16202DA (se regeneró una vez porque el título se cortaba) |
| `limpiando-enaho` | Skill | 1 | Base validada con 13/13 chequeos OK |
| `mapeando-enaho` | Skill | 1 | Mapa y comparación 25/25 con la Sesión 16 |
| `cruzando-bcrp-enaho` | Skill | 1 | Crédito y depósitos por habitante, correlaciones de Spearman y gráfico de dispersión |

En total se usaron **4 herramientas MCP distintas y 3 skills distintas** en una misma ejecución. El mínimo exigido era 2 y 2.

## 2. Manejo de errores: `manejo_errores.jsonl`

| Pregunta imposible | Qué hizo el agente | ¿Inventó una cifra? |
|---|---|---|
| Inflación de Lima en enero de 1850 | Llamó a `serie` y recibió *"no tiene datos entre 1850-01 y 1850-01"*. Lo informó, aclaró que la serie empieza en 1950 y ofreció consultar ese año | No |
| Pobreza ENAHO 2019 | Cargó `limpiando-enaho` y revisó `reference.md` y `datos/`. Informó que la skill solo valida 2024 y que no hay archivos de 2019 | No |
| Serie `ZZ12345` | `serie` devolvió *"No existe el código de serie 'ZZ12345'"* y el agente transmitió ese error | No |

## 3. Versión anterior: `version_1_inflacion/`

Primero se corrió el agente con otra pregunta, sobre inflación, PBI y brechas de pobreza entre 2020 y 2024. Después se cambió a la pregunta final sobre profundización financiera. Se conservan el registro, el informe y la verificación de esa primera versión como parte del proceso de desarrollo.
