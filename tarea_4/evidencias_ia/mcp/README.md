# Evidencias: servidor MCP del BCRP

| Archivo | Qué muestra |
|---|---|
| `pruebas.txt` | `uv run pytest -v`: **10 passed**. Son las 8 pruebas originales de la Sesión 04 más 2 propias para `graficar_serie` |
| `demo_claude_p.jsonl` | Claude Code (`claude -p`) usa `buscar_series` y luego `resumen` para responder la inflación de Lima 2020-2024 con código (PN01273PM), periodo, máximo (8.81 %, 2022-06) y fuente |

El servidor se desarrolló en la sesión con Claude Code: completó los TODO de `server.py` de la Sesión 04 y agregó las herramientas propias `graficar_serie` y `datos_departamentales`, el recurso `bcrp://serie/{codigo}` y el prompt `informe`. Las rutas locales están ocultas.
