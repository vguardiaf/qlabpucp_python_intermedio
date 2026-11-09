# Tarea 4: Agente de investigación socioeconómica (MCP del BCRP + Skills de la ENAHO)

**Pregunta de investigación:** ¿La profundización financiera departamental, entendida como créditos y depósitos, se asocia con menores niveles de pobreza en 2024?

**Informe final:** [`informes/informe_final.md`](informes/informe_final.md)

## 1. Objetivo

Construir un agente sobre Claude Code que responda preguntas socioeconómicas del Perú con datos oficiales y cifras verificables. Las cifras del BCRP se consultan con un servidor MCP propio; los microdatos de la ENAHO 2024 del INEI se procesan con Skills que limpian, validan, grafican, mapean y cruzan los datos. Así ninguna cifra sale de la memoria del modelo.

## 2. Arquitectura

```text
Pregunta en lenguaje natural
        │
   Claude Code (agente)
   ├── MCP bcrp (mcp/server.py, FastMCP) ── API del BCRP ── series nacionales y por departamento
   │     buscar_series · serie · resumen · graficar_serie · datos_departamentales
   │     recurso bcrp://serie/{codigo} · prompt informe
   └── Skills (.claude/skills/)
         limpiando-enaho ─► salidas/personas_2024.parquet, validacion.txt, indicadores.csv
         graficando-enaho ─► figuras/pobreza_*.png
         mapeando-enaho ─► mapas/pobreza_departamento.png, salidas/comparacion_mapa.csv
         cruzando-bcrp-enaho ─► une BCRP y ENAHO por código de departamento ─► correlaciones y dispersión
        │
   informes/informe_final.md  +  verificación independiente (informes/verificar_cifras.py)
```

Las Skills de gráficos, mapas y cruce corren antes `limpiando-enaho` si no existe la base procesada. La skill de cruce pide los datos del BCRP a la herramienta MCP `datos_departamentales` si faltan.

## 3. Herramientas MCP (`mcp/server.py`)

| Herramienta | Qué hace |
|---|---|
| `buscar_series(texto, frecuencia, limite)` | Busca series del catálogo oficial del BCRP (17 mil series) por palabras |
| `serie(codigo, desde, hasta)` | Descarga los datos de una serie. Acepta fechas como `2025`, `2025-03`, `2025-T1` o `2025-03-15`, salta los "n.d.", reintenta si la API responde HTML y guarda en caché |
| `resumen(codigo, desde, hasta)` | Primero, último, cambio, variación %, promedio, máximo y mínimo con su periodo, calculados en Python |
| **`graficar_serie`** (propia) | Guarda un PNG en `figuras/` con el código, el periodo, la fuente y una línea de referencia opcional |
| **`datos_departamentales`** (propia) | Trae una serie regional para los 25 departamentos en una sola llamada a la API, les asigna el código INEI (`ubigeo[:2]`) y guarda `salidas/bcrp_<etiqueta>_<anio>.csv` |
| Recurso `bcrp://serie/{codigo}` | Ficha descriptiva de una serie |
| Prompt `informe(tema, desde, hasta)` | Pide un informe que cite el código, el periodo y la fuente de cada cifra |

**Pruebas:** `uv run pytest -q` → **10 passed**. Son las 8 pruebas originales de la Sesión 04 en `mcp/test_server.py`, sin cambios (idéntico byte a byte), más 2 propias para `graficar_serie`, agregadas al final del mismo archivo. Las 71 líneas originales quedan idénticas byte a byte. Registro: [`evidencias_ia/mcp/pruebas.txt`](evidencias_ia/mcp/pruebas.txt).

## 4. Skills (`.claude/skills/`)

| Skill | Qué hace | Validación |
|---|---|---|
| `limpiando-enaho` | Lee los módulos 34 y 02 sin perder ceros en las llaves. Filtra residentes habituales con `((p204==1)&(p205==2))\|((p204==2)&(p206==1))`, une con `merge(validate="m:1")`, construye pobreza, departamento y área, y escribe `salidas/validacion.txt` e `indicadores.csv` | 13 chequeos OK y se detiene si alguno falla. Pobreza 27.58 % (INEI 27.6), 108,664 residentes, 25 códigos, urbana 24.81 / rural 39.30 |
| `graficando-enaho` | Barras ponderadas por área, sexo, edad o departamento, con un título analítico calculado a partir de los datos, la unidad, el periodo y la fuente | Pondera con `facpob07` |
| `mapeando-enaho` | Mapa coroplético que une `ubigeo[:2]` con `FIRST_IDDP`, nunca por nombre. Lima y Callao van separados y la escala parte de 0 | 25/25 departamentos dentro de ±0.1 de la referencia de la Sesión 16 (diferencia máxima 0.049) |
| `cruzando-bcrp-enaho` | Crédito y depósitos por habitante frente a la pobreza departamental: correlación de Spearman con 25 y con 23 departamentos (sin Lima ni Callao) y gráfico de dispersión | Une por código y exige los 25 |

Las demostraciones están en [`evidencias_ia/skills/`](evidencias_ia/skills/) y cubren: invocación con `/graficando-enaho sexo`, activación por lenguaje natural, y encadenamiento en el que `mapeando-enaho` corre antes `limpiando-enaho` porque se borró la base.

## 5. Datos y descarga

| Fuente | Archivo | Enlace |
|---|---|---|
| INEI, ENAHO 2024, módulo 34 (sumaria) | `datos/966-Modulo34.zip` | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip |
| INEI, ENAHO 2024, módulo 02 (miembros) | `datos/966-Modulo02.zip` | https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip |
| Límites departamentales | `datos/peru_departamental_simple.geojson` | https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson |
| BCRP, series estadísticas | consultado por API desde el MCP | https://estadisticas.bcrp.gob.pe/estadisticas/series/ |

`datos/` está en `.gitignore`. Hay que bajar los tres archivos a `tarea_4/datos/` sin descomprimirlos. El catálogo del BCRP (unos 7 MB) se baja solo la primera vez a `mcp/datos/`.

## 6. Instalación con `uv`

```bash
cd tarea_4
uv sync
```

## 7. Conectar el MCP a Claude Code

`.mcp.json` ya está en el repositorio. Para recrearlo:

```bash
claude mcp add --scope project bcrp -- uv run mcp/server.py
```

Hay que abrir `claude` desde `tarea_4/`, para que encuentre `.mcp.json` y `.claude/skills/`, y aprobar el servidor `bcrp` la primera vez.

## 8. Reproducir el procesamiento y las pruebas

```bash
uv run pytest -q                                                        # 10 passed
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024    # base y validación
uv run .claude/skills/graficando-enaho/scripts/graficar.py --por departamento
uv run .claude/skills/mapeando-enaho/scripts/mapear.py
uv run .claude/skills/cruzando-bcrp-enaho/scripts/cruzar.py --anio 2024 # requiere salidas/bcrp_*_2024.csv (MCP)
uv run informes/verificar_cifras.py                                     # verificación independiente
uv run evaluacion/evaluar.py                                            # experimento A/B (20 llamadas a claude -p)
```

## 9. Resultados de la evaluación

Las mismas 10 preguntas (4 del BCRP, 4 de la ENAHO y 2 mixtas) se corrieron con `claude -p` y el modelo sonnet, cada una en una sesión independiente:

| Modo | Correctas | Incorrectas | No responde | Tiempo promedio |
|---|---|---|---|---|
| A: sin MCP ni Skills | **1/10** | 2 | 7 | 9.3 s |
| B: con MCP + Skills | **10/10** | 0 | 0 | 16.8 s |

Mejoraron 9 preguntas y no empeoró ninguna. En el modo B también hubo atajos (leer salidas ya calculadas, una búsqueda web, una respuesta de memoria); están documentados en [`evaluacion/comparacion.md`](evaluacion/comparacion.md). Detalle por pregunta: [`evaluacion/resultados.csv`](evaluacion/resultados.csv).

## 10. Limitaciones y problemas encontrados

- **Diseño del análisis:** es un corte de 25 departamentos en un solo año. Mide asociaciones, no efectos causales, y puede haber causalidad inversa. El BCRP asigna el crédito al lugar donde se otorga: Lima concentra el 73.3 %, por la sede de las empresas.
- **Falta de datos:** el BCRP no publica el crédito por tipo (MYPE, consumo o hipotecario) por departamento, solo por moneda. El desglose por tipo solo existe a nivel nacional.
- **Dos ponderadores:** las cifras por persona (`facpob07`) y por hogar (`factor07 × mieperho`) difieren hasta 0.5 puntos por departamento. Las comparaciones con cifras oficiales usan el método de hogares.
- **Pruebas en vivo:** las pruebas del MCP consultan la API en vivo; si esta limita los pedidos, el servidor reintenta.
- **Primera pregunta descartada:** primero se trabajó con una pregunta sobre inflación y PBI entre 2020 y 2024. Después se cambió a la pregunta actual sobre profundización financiera. La primera versión está en [`evidencias_ia/integracion/version_1_inflacion/`](evidencias_ia/integracion/version_1_inflacion/).
- **Modo B de la evaluación:** no bloqueó WebSearch, y en las preguntas de la ENAHO leyó salidas ya calculadas; ver `comparacion.md`.

## 11. Ejemplo de una ejecución completa

Pedido a Claude Code (`claude -p`, desde `tarea_4/`, con el MCP y las Skills del proyecto): la pregunta de investigación y estos pasos:

1. Escribir un plan.
2. Usar el MCP del BCRP para crédito y depósitos por departamento.
3. Usar las Skills de la ENAHO para limpiar, mapear y cruzar.
4. Contrastar con las cifras oficiales.
5. Escribir `informes/informe_final.md` con 7 secciones, sin cifras de memoria.

En 138 s el agente usó `buscar_series`, `datos_departamentales`, `resumen` y `graficar_serie` (MCP), y `limpiando-enaho`, `mapeando-enaho` y `cruzando-bcrp-enaho` (Skills), y escribió el informe. Resultado principal: Spearman de **−0.57** entre profundización por habitante y pobreza con los 25 departamentos, y de **−0.74** sin Lima ni Callao. El pedido completo está en [`evidencias_ia/integracion/prompt_agente.txt`](evidencias_ia/integracion/prompt_agente.txt), y el registro y su análisis en [`evidencias_ia/integracion/`](evidencias_ia/integracion/).

## 12. Evidencias del uso de IA

**Bitácora de uso de IA:** [`evidencias_ia/bitacora_uso_ia.md`](evidencias_ia/bitacora_uso_ia.md). Separa, fase por fase, lo que decidí y aprobé yo de lo que hizo Claude Code.

Las conversaciones con asistentes de IA están en [`evidencias_ia/`](evidencias_ia/), organizadas por etapa y con la información sensible oculta:

- [`mcp/`](evidencias_ia/mcp/): las 10 pruebas y la demostración del MCP con Claude Code.
- [`skills/`](evidencias_ia/skills/): invocación directa, activación por lenguaje natural y encadenamiento de Skills.
- [`integracion/`](evidencias_ia/integracion/): la ejecución del agente con MCP y Skills, el manejo de errores y la primera versión.
- [`evaluacion/`](evidencias_ia/evaluacion/): las 20 ejecuciones del experimento A/B.

Cada carpeta tiene un `README.md` que explica sus archivos. Los `.jsonl` son registros `stream-json` de Claude Code con cada instrucción, llamada a herramienta y respuesta.
