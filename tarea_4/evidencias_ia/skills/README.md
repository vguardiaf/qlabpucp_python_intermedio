# Evidencias: Skills de la ENAHO

| Archivo | Pedido | Qué hizo Claude Code |
|---|---|---|
| `01_slash_graficando_sexo.jsonl` | `/graficando-enaho sexo` | Invocó la skill con el argumento y respondió 27.7 % para mujeres y 27.4 % para hombres, con la figura |
| `02_lenguaje_natural_area.jsonl` | "¿Qué tan distinta era la pobreza urbana y rural…? Hazme un gráfico." | Activó `graficando-enaho` por sí mismo: 39.4 % rural y 24.7 % urbana, una brecha de 14.7 puntos |
| `03_encadenamiento_mapa.jsonl` | "Haz un mapa de la pobreza monetaria por departamento con ENAHO 2024." (con la base borrada) | `mapeando-enaho` detectó que faltaba la base, corrió antes `limpiando-enaho` y luego hizo el mapa: 25/25 contra la Sesión 16 |

La skill `cruzando-bcrp-enaho` se usa en la ejecución del agente (`../integracion/`) y en la pregunta mixta de la evaluación (`../evaluacion/mixta_spearman_B.jsonl`).
