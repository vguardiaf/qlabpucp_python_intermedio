> **Versión anterior archivada.** Corresponde a la primera pregunta (inflación, PBI y pobreza 2020-2024). Sus figuras se regeneraron para la pregunta final, así que las imágenes y rutas de este archivo ya no existen. Se conserva como evidencia del proceso.

# Inflación, actividad económica y pobreza monetaria en el Perú (2020-2024)

## 1. Pregunta de investigación

**Tema.** La evolución macroeconómica reciente del Perú y la distribución territorial de la pobreza monetaria.

**Pregunta.** ¿Cómo evolucionaron la inflación y la actividad económica del Perú entre 2020 y 2024, y qué brechas urbana/rural y departamentales mostraba la pobreza monetaria en 2024?

**Objetivo.** Describir la trayectoria de la inflación de Lima Metropolitana y del crecimiento del PBI real en 2020-2024 con series oficiales del BCRP, y cuantificar las brechas de pobreza monetaria por área de residencia y por departamento en 2024 con los microdatos de la ENAHO del INEI.

**Delimitación.**
- Macroeconomía: enero de 2020 a diciembre de 2024 (inflación, mensual) y 2020-2024 (PBI, anual).
- Pobreza: solo el año 2024, población residente habitual, 25 departamentos (Lima y Callao por separado), área urbana y rural.
- Es un estudio descriptivo: no estima efectos causales.

## 2. Fuentes y metodología

### Datos

| Fuente | Contenido | Acceso |
|---|---|---|
| BCRP, estadísticas en línea | `PN01273PM`: Índice de precios Lima Metropolitana (var% 12 meses) - IPC, mensual | Servidor MCP `bcrp` (`mcp/server.py`) |
| BCRP, estadísticas en línea | `PM04923AA`: Producto bruto interno por tipo de gasto (variaciones porcentuales reales) - PBI, anual | Servidor MCP `bcrp` |
| INEI, ENAHO 2024 (código 966) | Módulo 34 (sumaria) y módulo 02 (miembros del hogar) | `datos/966-Modulo34.zip`, `datos/966-Modulo02.zip` |
| Límites departamentales | 25 departamentos | `datos/peru_departamental_simple.geojson` |

### Procesamiento

1. **BCRP.** Las series se ubicaron con `buscar_series` (texto "ipc 12 meses", frecuencia Mensual; y "pbi variaciones porcentuales", frecuencia Anual). Las cifras se obtuvieron con `serie` (datos) y `resumen` (promedio, máximo, mínimo, primero y último), que hacen las cuentas en Python. El gráfico se hizo con `graficar_serie` con una línea de referencia en 3 % (techo del rango meta del BCRP).
2. **ENAHO.** La skill `limpiando-enaho` une el módulo 34 (hogar) con el módulo 02 (personas) en una unión m:1, se queda con los residentes habituales y guarda `salidas/personas_2024.parquet`. Luego valida contra conteos y tasas oficiales (`salidas/validacion.txt`, resultado: **OK** en las 13 pruebas).
3. **Cortes y mapa.** La skill `graficando-enaho` calcula las tasas por área y por departamento y las grafica; `mapeando-enaho` une `ubigeo[:2]` con `FIRST_IDDP` del GeoJSON (por código, como texto) y compara con la referencia de la Sesión 16.

### Indicadores

- **Inflación a 12 meses** (%) de Lima Metropolitana, mensual.
- **Crecimiento del PBI real** (%), anual.
- **Tasa de pobreza monetaria** (%): personas cuyo hogar tiene un gasto per cápita por debajo de la línea de pobreza (`pobreza` ≤ 2).

### Ponderación

- Las tasas por persona se ponderan con el factor de expansión `facpob07`: suma de `facpob07` de los pobres entre la suma de `facpob07` del grupo. Nunca se cuentan filas.
- Para comparar con las cifras oficiales se usa además el método de hogares, `factor07 × mieperho`, que es el método del INEI y de la referencia de la Sesión 16.
- Como control, `salidas/validacion.txt` muestra que la proporción simple sin ponderar (25.61 %) difiere de la ponderada (27.53 %). Por eso solo se usan cifras ponderadas.

## 3. Resultados

**Hallazgo 1. La inflación de Lima pasó de valores bajos en 2020 a un pico en 2022 y volvió debajo del techo de la meta en 2024.**
- En el periodo 2020-01 a 2024-12, la inflación a 12 meses promedió **4.47 %**. Su mínimo fue **1.60 %** (2020-06) y su máximo **8.81 %** (2022-06) (BCRP, `PN01273PM`, `resumen` 2020-01 a 2024-12, n = 60).
- Superó el techo de 3 % por primera vez en 2021-06 (**3.25 %**). El último mes sobre ese umbral fue 2024-03 (**3.05 %**) y en 2024-04 bajó a **2.42 %** (BCRP, `PN01273PM`, `serie` 2020-01 a 2024-12).
- Valores de diciembre: **1.97 %** (2020-12), **6.43 %** (2021-12), **8.46 %** (2022-12), **3.24 %** (2023-12) y **1.97 %** (2024-12) (BCRP, `PN01273PM`, `serie`).

**Hallazgo 2. La actividad económica tuvo una caída fuerte en 2020, un rebote en 2021 y después un crecimiento moderado e irregular.**
- Crecimiento del PBI real: **−10.93 %** en 2020, **13.42 %** en 2021, **2.82 %** en 2022, **−0.35 %** en 2023 y **3.52 %** en 2024 (BCRP, `PM04923AA`, `serie` 2020-2024).
- El promedio simple de las tasas anuales de 2020-2024 fue **1.69 %**. Es un promedio de tasas, no el crecimiento acumulado (BCRP, `PM04923AA`, `resumen` 2020-2024, n = 5).

**Hallazgo 3. En 2024 la pobreza monetaria rural superaba a la urbana en casi 15 puntos.**
- Pobreza nacional: **27.5 %** de las personas (`facpob07`; 27.53 %). Con el método de hogares da **27.58 %**, frente al **27.6 %** oficial del INEI, dentro de la tolerancia de ±0.1 (`salidas/validacion.txt`, `salidas/indicadores.csv`).
- Rural: **39.4 %**. Urbana: **24.7 %**. Brecha: **14.7 puntos porcentuales** (`salidas/indicadores.csv`; salida del script de `graficando-enaho`).
- Con el método de hogares, la tasa es 39.30 % rural y 24.81 % urbana, que coincide con las cifras oficiales de 39.3 % y 24.8 % (`salidas/validacion.txt`).
- Pobreza extrema nacional: **5.50 %** (`salidas/validacion.txt`).

**Hallazgo 4. La pobreza variaba mucho entre departamentos.**
- La tasa más alta es la de **Cajamarca (45.0 %)** y la más baja la de **Ica (5.9 %)**. La de Cajamarca es **7.6 veces** la de Ica (`salidas/indicadores.csv`; título calculado por `graficando-enaho`).
- **10 de 25** departamentos superan el promedio nacional. Tras Cajamarca vienen Loreto (**42.6 %**), Puno (**40.4 %**), Huánuco (**39.5 %**) y Pasco (**39.3 %**). Las tasas más bajas, después de Ica, son las de Moquegua (**10.9 %**), Madre de Dios (**11.1 %**) y Lambayeque (**14.1 %**) (`salidas/indicadores.csv`).
- Callao (**33.8 %**) supera al departamento de Lima (**26.9 %**). Lima Metropolitana (dominio 8) registra **28.03 %** (`salidas/indicadores.csv`, `salidas/validacion.txt`).

**Hallazgo 5. Las cifras de la ENAHO procesada coinciden con las fuentes oficiales.**
- Nacional: 27.58 % (hogares) y 27.53 % (personas), frente al 27.6 % del INEI. Ambas están dentro de ±0.1 (`salidas/validacion.txt`).
- Mapa: **25 de 25** departamentos coinciden con la referencia de la Sesión 16 dentro de ±0.1 puntos, con una diferencia máxima absoluta de **0.049** (Amazonas: 25.749 calculado frente a 25.7 de referencia) (`salidas/comparacion_mapa.csv`).

## 4. Visualizaciones

![Inflación de Lima Metropolitana 2020-2024 con referencia de 3 %](../figuras/bcrp_PN01273PM_2020-01_2024-12.png)

*Lectura:* la línea queda por encima de la referencia de 3 % desde junio de 2021 hasta marzo de 2024. Llega a su máximo de 8.81 % en junio de 2022 y en 2024 vuelve a niveles parecidos a los de 2020 (BCRP, `PN01273PM`).

![Pobreza monetaria por área de residencia, 2024](../figuras/pobreza_area.png)

*Lectura:* la barra rural (39.4 %) queda muy por encima del promedio nacional (27.5 %), mientras que la urbana (24.7 %) queda por debajo. La brecha es de 14.7 puntos (`salidas/indicadores.csv`).

![Pobreza monetaria por departamento, 2024](../figuras/pobreza_departamento.png)

*Lectura (barras complementarias):* hay 10 departamentos por encima del promedio nacional, encabezados por Cajamarca (45.0 %). Ica cierra el ranking con 5.9 %.

![Mapa de la pobreza monetaria por departamento, 2024](../mapas/pobreza_departamento.png)

*Lectura:* los tonos más oscuros están en Cajamarca y Loreto, en el norte y la Amazonía, y en Puno, Huánuco y Pasco, en la sierra. Los más claros están en la costa sur (Ica y Moquegua) y en Madre de Dios (`salidas/comparacion_mapa.csv`, columna `mapa_personas`).

## 5. Interpretación

- **Un ciclo de precios completo.** En 2020-2024 la inflación de Lima recorrió un ciclo entero: niveles bajos en 2020, una subida desde mediados de 2021, una meseta por encima del 8 % durante gran parte de 2022 y comienzos de 2023, y una vuelta al rango meta desde abril de 2024. El periodo fuera del rango duró casi tres años.
- **Actividad volátil.** La actividad no siguió un camino simple. Después de la caída de 2020 y el rebote de 2021, el PBI creció poco en 2022, se contrajo levemente en 2023, mientras la inflación seguía alta en la primera mitad del año, y repuntó en 2024 junto con la vuelta de la inflación al rango meta. Que la inflación baje y el crecimiento repunte el mismo año es una **coincidencia temporal**. Estos datos no permiten afirmar que una cosa haya causado la otra.
- **Pobreza ligada al territorio.** En 2024 la pobreza muestra un patrón territorial claro. La brecha rural-urbana es de 14.7 puntos y entre departamentos la diferencia llega a ser de 7.6 veces. Las tasas más altas se concentran en departamentos de sierra y selva (Cajamarca, Loreto, Puno, Huánuco, Pasco) y las más bajas en la costa sur.
- **No todo es rural.** El área urbana tiene una tasa menor, pero Callao (33.8 %) y Lima Metropolitana (28.03 %) superan el promedio nacional. Además, por su tamaño, el departamento de Lima es el de mayor población expandida en `salidas/indicadores.csv` (11.2 millones). La pobreza no es solo un fenómeno rural.
- **Por qué se presentan juntos los dos bloques.** El bloque macro y el bloque de pobreza dan contexto el uno al otro. Por ejemplo, la pobreza de 2024 se mide después de un periodo de inflación alta. Sin embargo, con un solo año de ENAHO no se puede vincular estadísticamente la evolución macro con el nivel o la distribución de la pobreza.

## 6. Limitaciones

- **Cobertura temporal.** Las series del BCRP cubren 2020-2024, pero la ENAHO se analiza solo para 2024. No hay una serie de pobreza 2020-2024 en este análisis, así que no se observa cómo cambió la pobreza durante el ciclo de inflación.
- **Niveles de agregación distintos.** La inflación mide los precios de **Lima Metropolitana**, no del país ni de cada departamento. El PBI es un agregado **nacional**. La pobreza viene de **microdatos de hogares y personas**. Estas cifras no se pueden cruzar directamente ni sacar conclusiones de una escala a otra (falacia ecológica).
- **Calidad de los datos.** La ENAHO es una muestra. Las tasas departamentales tienen error muestral y no se calcularon intervalos de confianza: diferencias pequeñas entre departamentos (por ejemplo, Huánuco 39.5 % y Pasco 39.3 %) podrían no ser significativas. Además, las tasas por personas (`facpob07`) y por hogares (`factor07 × mieperho`) difieren ligeramente (por ejemplo, Huánuco: 39.47 % frente a 38.96 % en `salidas/comparacion_mapa.csv`). Las cifras anuales del PBI de los años más recientes pueden ser revisadas por el BCRP.
- **Alcance.** Se usa solo la pobreza monetaria (gasto frente a la línea de pobreza), no la pobreza multidimensional ni la desigualdad. Los cortes son solo de área y departamento, sin desagregación provincial.
- **Asociaciones, no causas.** Todos los patrones descritos, como la coincidencia entre la baja de la inflación y el repunte del PBI en 2024 o la mayor pobreza en zonas rurales y de sierra y selva, son **asociaciones descriptivas**. No se estimó ningún modelo que permita atribuir causalidad.
- **Incidencias de herramientas.** Ninguna herramienta falló. La primera versión del gráfico del BCRP tenía el título cortado por el ancho de la figura, así que se regeneró con un título más corto.

## 7. Reproducibilidad

Todo se ejecuta desde la raíz de `tarea_4/`.

**BCRP (servidor MCP `bcrp`, `mcp/server.py`, configurado en `.mcp.json`):**

| Herramienta | Argumentos |
|---|---|
| `buscar_series` | `texto="ipc 12 meses"`, `frecuencia="Mensual"` → `PN01273PM` |
| `buscar_series` | `texto="pbi variaciones porcentuales"`, `frecuencia="Anual"` → `PM04923AA` |
| `resumen` / `serie` | `codigo="PN01273PM"`, `desde="2020-01"`, `hasta="2024-12"` |
| `resumen` / `serie` | `codigo="PM04923AA"`, `desde="2020"`, `hasta="2024"` |
| `graficar_serie` | `codigo="PN01273PM"`, `desde="2020-01"`, `hasta="2024-12"`, `referencia=3`, `titulo="Inflación de Lima sobre el 3 % de jun-2021 a mar-2024; pico de 8.8 % en jun-2022"` |

Fuentes de los datos:
- https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PN01273PM/json/2020-1/2024-12
- https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PM04923AA/json/2020/2024

**ENAHO 2024 (skills del proyecto):**

```bash
uv run .claude/skills/limpiando-enaho/scripts/limpiar.py --anio 2024
uv run .claude/skills/graficando-enaho/scripts/graficar.py --por area
uv run .claude/skills/graficando-enaho/scripts/graficar.py --por departamento
uv run .claude/skills/mapeando-enaho/scripts/mapear.py
```

**Archivos de entrada:** `datos/966-Modulo34.zip`, `datos/966-Modulo02.zip`, `datos/peru_departamental_simple.geojson`.

**Archivos generados:**
- `salidas/personas_2024.parquet` (108,664 personas)
- `salidas/validacion.txt`
- `salidas/indicadores.csv`
- `salidas/comparacion_mapa.csv`
- `figuras/bcrp_PN01273PM_2020-01_2024-12.png`
- `figuras/pobreza_area.png`
- `figuras/pobreza_departamento.png`
- `mapas/pobreza_departamento.png`

## 8. Verificación de cifras

Después de que el agente escribió el informe, se volvieron a calcular algunas cifras por una vía independiente con `uv run informes/verificar_cifras.py`. Ese script no usa el servidor MCP ni las skills: llama directo a la API del BCRP y lee la sumaria directo del zip del INEI (`factor07 × mieperho`). Los resultados quedan en [`verificacion_independiente.csv`](verificacion_independiente.csv). También se contrastó con las cifras oficiales publicadas por el INEI.

| # | Afirmación del informe | Valor del informe | Valor verificado | Fuente o procedimiento | ¿Coincide? | Diferencia |
|---|---|---|---|---|---|---|
| 1 | Máximo de la inflación de Lima 2020-2024 | 8.81 % (2022-06) | 8.81 % (2022-06) | API BCRP `PN01273PM/json/2020-1/2024-12`, máximo con pandas | Sí | 0 |
| 2 | Inflación de Lima en dic-2024 | 1.97 % | 1.97 % | Misma API, periodo 2024-12 | Sí | 0 |
| 3 | Meses sobre el 3 % entre jun-2021 y mar-2024 | "casi tres años" (jun-2021 a mar-2024) | 34 meses con valor > 3 % en 2020-2024 | Misma API, conteo con pandas | Sí | 0 |
| 4 | Crecimiento del PBI real 2020 y 2021 | −10.93 % y 13.42 % | −10.93 % y 13.42 % | API BCRP `PM04923AA/json/2020/2024` | Sí | 0 |
| 5 | Crecimiento del PBI real 2024 | 3.52 % | 3.52 % | Misma API | Sí | 0 |
| 6 | Pobreza monetaria nacional 2024 | 27.58 % (hogares) | 27.58 % recalculada; 27.6 % oficial INEI | Sumaria del zip, `factor07 × mieperho`; informe técnico del INEI | Sí | −0.02 frente al INEI (redondeo) |
| 7 | Pobreza rural y urbana 2024 | 39.30 % y 24.81 % (hogares) | 39.30 % y 24.81 %; 39.3 % y 24.8 % INEI | Sumaria del zip, `estrato` 1-5 urbano y 6-8 rural | Sí | ≤ 0.01 |
| 8 | Pobreza de Cajamarca 2024 | 45.0 % (personas) | 45.01 % (hogares) | Sumaria del zip, `ubigeo[:2] == "06"` | Sí | 0.01 |
| 9 | Pobreza de Ica 2024 | 5.9 % (personas) | 6.01 % (hogares); 6.0 % Sesión 16 | Sumaria del zip, `ubigeo[:2] == "11"` | Sí, con nota | 0.11 por el ponderador |

**Nota sobre la diferencia observada.** La cifra de Ica del informe (5.9 %) se calculó con el factor de personas `facpob07`. La verificación usa el método de hogares (`factor07 × mieperho`), que da 6.01 %, igual que la referencia de la Sesión 16. La diferencia de 0.11 puntos viene del ponderador, no de un error de cálculo: los dos métodos difieren hasta 0.5 puntos por departamento (ver `salidas/comparacion_mapa.csv`). Las cifras de comparación oficial del informe usan el método de hogares.

**Manejo de errores.** En otra ejecución se le pidieron al agente datos que no existen: la inflación de 1850, la ENAHO 2019 (el proyecto solo valida 2024) y un código de serie inexistente. Esa ejecución está en `evidencias_ia/integracion/manejo_errores.jsonl` y su análisis en `evidencias_ia/integracion/README.md`.

## Registro de herramientas usadas

| Herramienta | Tipo | Para qué se usó |
|---|---|---|
| `buscar_series` | MCP `bcrp` | Encontrar los códigos de la inflación de Lima a 12 meses (`PN01273PM`) y del crecimiento del PBI real (`PM04923AA`) |
| `resumen` | MCP `bcrp` | Promedio, máximo, mínimo, primer y último valor de ambas series en 2020-2024, calculados en Python |
| `serie` | MCP `bcrp` | Datos mensuales de la inflación y anuales del PBI 2020-2024, y URL de la fuente |
| `graficar_serie` | MCP `bcrp` | Gráfico de la inflación 2020-2024 con referencia de 3 % y título analítico (se corrió dos veces para corregir el título cortado) |
| `limpiando-enaho` | Skill | Limpiar y unir los módulos 34 y 02, crear la base de personas validada y comparar con el 27.6 % del INEI (`salidas/validacion.txt`) |
| `graficando-enaho` | Skill | Gráficos ponderados de pobreza por área (`figuras/pobreza_area.png`) y por departamento (`figuras/pobreza_departamento.png`) |
| `mapeando-enaho` | Skill | Mapa departamental (`mapas/pobreza_departamento.png`) y comparación con la Sesión 16 (`salidas/comparacion_mapa.csv`, 25/25 dentro de ±0.1) |
