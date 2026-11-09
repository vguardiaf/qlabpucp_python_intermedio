# Evidencias: experimento con y sin MCP y Skills

Registros `stream-json` de las 20 ejecuciones de `evaluacion/evaluar.py`: 10 preguntas en 2 modos, en sesiones independientes de `claude -p` con el modelo sonnet.

- `<id>_A.jsonl`: modo A, sin herramientas, sin MCP y sin Skills, en una carpeta temporal vacía.
- `<id>_B.jsonl`: modo B, con el MCP `bcrp` y las Skills del proyecto.

Resultado: **A 1/10 y B 10/10**. El análisis está en [`../../evaluacion/comparacion.md`](../../evaluacion/comparacion.md) y el detalle en [`../../evaluacion/resultados.csv`](../../evaluacion/resultados.csv).
