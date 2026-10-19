# 🗞️ Tarea 1 – Noticias peruanas: del titular al clasificador

## Pregunta del proyecto

**¿Pueden convertir titulares peruanos en un clasificador de noticias?**

Sí. Con 383 titulares de El Comercio, etiquetados de forma semi-supervisada con un LLM local, un modelo BETO fine-tuned clasifica titulares nuevos en 4 categorías (`politica`, `economia`, `deportes`, `ciencia_tecnologia`) con **F1 macro de 0.82 en test**, frente a 0.64 de la línea base zero-shot.

## Medio y fechas de extracción

| | |
|---|---|
| **Medio** | Opción B: El Comercio (`https://elcomercio.pe/`) |
| **Fecha de descarga** | 16-10-2026 |
| **Ventana de publicación** | 06-10-2026 al 16-10-2026 |
| **Fuentes** | RSS por sección (`/arc/outboundfeeds/rss/category/<seccion>/`), complementado con el archivo HTML por sección y el sitemap, respetando `robots.txt` y con pausas entre peticiones |
| **Volumen final** | 383 noticias: economía 100 · deportes 100 · ciencia y tecnología 92 · política 91 |

Se descartaron las secciones que no encajan en las 4 categorías (`ecdata`, `opinion`, `ruedas-tuercas`, entre otras); el detalle está en `01_recoleccion.ipynb`.

## Metodología y resultados

| Etapa | Detalle | Resultado |
|---|---|---|
| Línea base zero-shot | `Recognai/bert-base-spanish-wwm-cased-xnli`, 40 titulares | F1 macro 0.64 |
| Supervisión débil | Qwen2.5-1.5B-Instruct local, dataset completo | Auditoría humana 18/20 (90%) |
| Split | Estratificado 70/15/15, `random_state=42` | 268 / 57 / 58 |
| Fine-tuning | BETO (`dccuchile/bert-base-spanish-wwm-cased`), 3 épocas, batch 16, mejor época por F1 macro | F1 macro val 0.84 |
| **Evaluación en test** | 58 titulares reservados | **Accuracy 0.86 · F1 macro 0.82** |

## Hallazgos

1. Medidos contra la sección original del diario sobre el mismo test, el modelo fine-tuned obtiene F1 macro 0.80 y el LLM que generó sus etiquetas, 0.77. Al aprender de cientos de ejemplos, BETO generaliza los patrones dominantes y corrige parte del ruido de las etiquetas individuales del LLM, con ~14 veces menos parámetros.
2. **Economía es la categoría más difícil.** Tiene el F1 más bajo en test (0.62, recall 0.50), aunque ciencia y tecnología alcanza 0.94. Economía comparte actores y vocabulario con política (ministros, MEF, BCR, Congreso, leyes mineras), y el LLM ya asignaba solo el 14.9% del dataset a economía cuando la sección original tiene 26%. Ejemplo: *"Julio Velarde: 'En el BCR hay mucha gente que puede sustituirme, pero no cualquiera tampoco'"* es económico por el BCR, pero habla de una designación, y el modelo lo clasifica como política.

## Limitaciones técnicas

1. **Etiquetas débiles con sesgo heredado.** El modelo aprende de las etiquetas de un LLM pequeño (1.5B) que coincide con la sección original solo en el 78% de los casos y sobrerrepresenta política (34.7% frente a 23.8%). Ese sesgo pasa al clasificador y explica parte de los errores en economía.
2. **Datos escasos y poco diversos.** 383 titulares de un solo medio en una ventana de 10 días: el test tiene apenas 58 titulares (8 de economía), así que un acierto más o menos cambia mucho las métricas, y el vocabulario depende de la coyuntura de esas fechas. Además, el modelo solo ve el titular, sin la bajada.
