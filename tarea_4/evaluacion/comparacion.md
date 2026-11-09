# Comparación: Claude Code sin y con MCP + Skills

**Experimento:** 10 preguntas con respuesta verificable: 4 del BCRP, 4 de la ENAHO y 2 que combinan ambas fuentes. Las respuestas esperadas se fijaron antes de correr la evaluación (commit `3a21935`, `preguntas.csv`). Se usaron fuentes oficiales y la verificación independiente de `informes/verificar_cifras.py`. Cada pregunta se ejecutó en una sesión independiente de `claude -p` (`--no-session-persistence`), con el modelo `sonnet` y la misma instrucción en los dos modos. La respuesta debía ser un JSON con un solo número, o `null` si el agente no estaba seguro. La corrección se juzga con la tolerancia de cada pregunta. Script: `evaluacion/evaluar.py`.

| | Modo A: sin MCP ni Skills | Modo B: con MCP + Skills |
|---|---|---|
| Herramientas habilitadas | Ninguna (`--tools ""`), sin MCP, sin Skills, en una carpeta temporal vacía fuera del repositorio | MCP `bcrp` (5 herramientas), las 4 Skills del proyecto, Read, Glob, `uv run`, desde `tarea_4/` |
| **Correctas** | **1 / 10** | **10 / 10** |
| Incorrectas | 2 | 0 |
| No responde (`null`) | 7 | 0 |
| Tiempo promedio | 9.3 s | 16.8 s |

## Por pregunta

| Pregunta | Esperada | Modo A | Modo B | Herramientas usadas en B |
|---|---|---|---|---|
| Inflación de Lima a 12 meses, set-2026 | 4.5487 | no responde | 4.55 ✔ | `buscar_series`, `serie` |
| Variación mensual del IPC, mar-2025 | 0.8102 | 1.31 ✘ | 0.81 ✔ | `buscar_series`, `serie` |
| Tipo de cambio, 15-oct-2026 | 3.4282 | no responde | 3.4282 ✔ | `buscar_series`, `serie` |
| Crédito total 2024 (millones de S/) | 407,351.7 | no responde | 407,351.74 ✔ | `datos_departamentales` |
| Pobreza nacional 2024 | 27.6 | 27.6 ✔ | 27.6 ✔ | ninguna (respondió de memoria) |
| Pobreza rural 2024 | 39.3 | 39.8 ✘ | 39.3 ✔ | Grep sobre `salidas/`, WebSearch |
| Pobreza urbana 2024 | 24.8 | no responde | 24.8 ✔ | Grep sobre `salidas/` |
| Pobreza de Cajamarca 2024 | 45.0 | no responde | 45.0 ✔ | Grep sobre `salidas/` |
| Mixta: crédito por habitante de Lima | 26,460.5 (±530) | no responde | 26,570.3 ✔ | `datos_departamentales`, Bash (`uv run`) |
| Mixta: Spearman de profundización y pobreza | −0.562 (±0.05) | no responde | −0.565 ✔ | Skill `cruzando-bcrp-enaho` |

**Preguntas que mejoraron:** 9 de 10. Las 4 del BCRP, 3 de la ENAHO y las 2 mixtas pasaron de "no responde" o "incorrecta" a "correcta". **Preguntas que empeoraron:** ninguna. La pobreza nacional fue correcta en ambos modos.

**Criterio para las preguntas mixtas.** El dato numérico debe caer dentro de la tolerancia, que considera el ponderador de población: `facpob07` o `factor07 × mieperho`. La respuesta debe además citar las dos fuentes. En el modo B, las dos respuestas mixtas citaron el BCRP (códigos de serie) y la ENAHO (población ponderada). Las dos diferencias, 110 soles y 0.003, se explican porque el agente usó `facpob07` y la respuesta esperada usa hogares.

## Errores principales

1. **Modo A: se abstiene por falta de datos.** En 7 de 10 preguntas respondió `null`. Es la conducta correcta cuando no hay herramientas: sin acceso a los datos de 2024-2026, no inventó cifras.
2. **Modo A: errores de memoria.** Dio 1.31 % para el IPC de marzo de 2025 (real 0.81 %) y 39.8 % para la pobreza rural (real 39.3 %, la cifra del INEI). Son números verosímiles pero equivocados, el riesgo típico de responder de memoria.
3. **Modo B: atajos que conviene declarar.**
   - En la pobreza nacional respondió sin usar herramientas; acertó porque la cifra del INEI es conocida.
   - En 3 preguntas de la ENAHO leyó los resultados ya calculados en `salidas/` (`validacion.txt`, `comparacion_mapa.csv`) con Grep, en lugar de volver a correr la skill de limpieza. Esos archivos son el resultado de las Skills, pero la evaluación no prueba que las vuelva a ejecutar.
   - En la pobreza rural usó WebSearch, que no estaba bloqueado (`--allowedTools` no restringe las herramientas incorporadas). Es una diferencia de condiciones que debe tenerse en cuenta. La cifra final coincide con `salidas/validacion.txt`.
4. **Modo B: dónde sí calculó.** En las preguntas del BCRP y en las mixtas, las cifras salieron de llamadas al MCP y de la Skill de cruce. Ninguna de esas preguntas se puede contestar de memoria, porque su dato o su cálculo no existe fuera de las herramientas.

## Conclusión

Con MCP y Skills, Claude Code pasó de 1/10 a 10/10 respuestas correctas, con un costo de unos 7.5 s más por pregunta. El mayor aporte está en lo que no se puede saber de memoria: series recientes del BCRP, como el tipo de cambio diario o el crédito de 2024, y cálculos que combinan las dos fuentes, como el crédito por habitante o una correlación entre 25 departamentos. En las cifras muy difundidas, como la pobreza nacional, la ventaja es menor.

El experimento también muestra límites:
- Sin herramientas, el modelo prefiere abstenerse, y eso es preferible a inventar.
- Con herramientas, a veces toma atajos: leer salidas ya calculadas, responder de memoria o buscar en la web si no se bloquea.

Para una evaluación más estricta convendría bloquear WebSearch y WebFetch con `--disallowedTools` y borrar `salidas/` antes de cada pregunta de la ENAHO, para obligar a que se ejecuten las Skills.

**Archivos:** `resultados.csv` (una fila por pregunta y modo, con la respuesta esperada, la respuesta generada, la fuente declarada, las herramientas usadas, el tiempo y los errores), `preguntas.csv` y `evaluar.py`. Los registros de cada ejecución están en [`../evidencias_ia/evaluacion/`](../evidencias_ia/evaluacion/).
