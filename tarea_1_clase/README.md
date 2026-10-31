# ¿Es 2026 un año récord de incendios en el Perú?

Retos **E (¿año récord?)**, **F (clima y riesgo)** y **A (área quemada con dNBR)** de la tarea de
Ciencia de Datos con Python.
Dashboard: https://claude.ai/artifact/X8oDTiZ6w59yggsH36ptFu

## Pregunta

¿La temporada de incendios 2026 (desde el 1 de julio) supera a las de 2012–2025, en qué
departamentos, cuánto se quemó realmente en los incendios más grandes y cuáles pueden crecer
esta semana? Se cuentan incendios, no quemas de manejo ni fuentes fijas de calor.

## Datos y fechas

| Dato | Fuente | Tipo | Fechas |
|---|---|---|---|
| Focos de calor 2012–2025 | NASA FIRMS, archivo anual `viirs-snpp` Perú | Puntos (CSV) | 1 ene 2012 – 31 dic 2025 |
| Focos de calor 2026 | INPE Queimadas, archivos mensuales Sudamérica (S-NPP) | Puntos (CSV) | 1 jul – 19 oct 2026 (corte) |
| Límites departamentales | INEI vía `juaneladio/peru-geojson` | Polígonos | — |
| Cobertura del suelo | ESA WorldCover 2021 (10 m, leído a 80 m) | **Raster** | 2021 |
| Imágenes y área quemada | Sentinel-2 L2A vía Earth Search (AWS), bandas B8A, B12 y SCL | **Raster** | 22 jun – 20 oct 2026 |
| Población | WorldPop 2020, 1 km | **Raster** | 2020 |
| Clima | Open-Meteo (sin clave) | API | 14 días pasados + pronóstico desde el 21 oct 2026 |

## Método

1. `src/01_descargar.py`: baja focos y límites. De INPE se queda solo con Perú y S-NPP.
2. `src/02_limpiar.py`: limpia los focos y decide cuáles son incendio.
   - Quita las celdas de ~1 km que FIRMS marca como volcán o fuente fija (minas, refinerías).
   - Asigna cada foco a su departamento y lee la cobertura bajo él con **WorldCover**.
   - Agrupa los focos en **eventos**: focos a ~1 km y a 2 días o menos entre sí.
   - **Regla de incendio** (`es_incendio`): bosque, matorral y humedal cuentan siempre. Pastizal y
     cultivo cuentan solo si el evento es grande (≥ 5 focos o ≥ 2 días) o llega a bosque o matorral
     (quema escapada), **y** la celda de ~1 km no ardió en 8 o más de los otros 14 años (las quemas
     de manejo se repiten en el mismo lugar). Zonas urbanas, suelo desnudo y agua no cuentan.
     La regla se aplica igual a los 15 años.
3. `src/03_comparar.py`: compara la misma ventana (1 jul → corte) en cada año, a nivel nacional
   y por departamento. Sin anomalía % si el promedio es menor de 30 focos.
4. `src/04_incendios_riesgo.py`: agrupa los focos de los últimos 7 días en incendios (≤ 1 km),
   suma la población a 5 km con WorldPop y consulta el pronóstico de Open-Meteo.
   Día crítico = humedad mínima < 30 %, viento ≥ 20 km/h y lluvia < 1 mm.
5. `src/05_dnbr.py`: **Sentinel-2**, en dos partes.
   - **Área quemada** de los 8 incendios activos con más focos. NBR = (B8A − B12) / (B8A + B12) a
     20 m; dNBR = NBR antes − NBR después; nubes enmascaradas con SCL. Antes: la imagen más cercana
     al primer foco con ≥ 85 % de la zona despejada; después: la más reciente. Área quemada =
     dNBR ≥ 0,27 (umbrales USGS). Confiable si ambas imágenes tienen ≤ 25 % de nubes en la zona y
     ≤ 90 días entre ellas.
   - **Validación de la regla del paso 2**: muestra al azar de eventos de 2026 sobre pastizal, cada
     uno con una **zona de control** a ~5 km, sobre pastizal y sin focos, medida con las mismas dos
     imágenes. Lo que se "quema" en el control es el secado de la estación; la diferencia es fuego.
6. `src/06_dashboard.py`: inserta los resultados en `src/plantilla_dashboard.html` y genera `docs/index.html`.

Solo se usa S-NPP porque es el único satélite con registro continuo desde 2012: sumar NOAA-20
y NOAA-21 inflaría los años recientes.

## Hallazgos (corte: 19 de octubre de 2026)

1. **Octubre de 2026 es el más intenso desde 2012**: 10 814 focos de incendio del 1 al 19 de
   octubre, **+106 %** sobre el promedio 2012–2025 para esas mismas fechas (puesto 1 de 15).
2. **La temporada completa no es récord**: 36 996 focos desde el 1 de julio, **−16,3 %** frente al
   promedio (puesto 12 de 15). Ucayali (−17 %), San Martín (−30 %) y Huánuco (−37 %) van por debajo.
3. **El récord está en el sur andino**: Moquegua (+337 %), Apurímac (+221 %), Arequipa (+171 %),
   Lima (+163 %) y Tacna ya superan su máximo de 2012–2025; Ancash (+121 %) está en el puesto 2.
4. **Sentinel-2 confirma los grandes incendios**: en 7 de los 8 más grandes la medición es
   confiable. El de Arequipa quemó 1 562 ha en solo 5 días y el de Apurímac 1 252 ha en 12 días.
   En uno de Junín, Sentinel-2 ve solo 33 ha y confirma el 29 % de sus focos: no es un incendio grande.
5. **Viene la lluvia**: 180 de 182 incendios activos tienen riesgo climático bajo para la semana
   (mediana de 40 mm de lluvia pronosticada). Solo uno, en Arequipa, tiene riesgo alto.

De los 45 983 focos S-NPP de la temporada 2026, la regla deja 36 996 como incendio y descarta
6 982 quemas pequeñas y 758 quemas recurrentes en pastizal o cultivo, más 1 247 focos sin vegetación.

### Área quemada (dNBR ≥ 0,27)

| Incendio | Antes (nubes) | Después (nubes) | Ha quemadas | Focos confirmados | Confiable |
|---|---|---|---|---|---|
| Arequipa, 15,49° S 72,99° O | 15 oct (0 %) | 20 oct (9 %) | 1 562 | 99 % | Sí |
| Ucayali, 8,17° S 74,80° O | 18 jul (6 %) | 16 oct (5 %) | 1 341 | 100 % | Sí |
| Apurímac, 13,64° S 72,42° O | 5 oct (1 %) | 17 oct (5 %) | 1 252 | 88 % | Sí |
| Ucayali, 8,49° S 74,53° O | 14 ago (1 %) | 16 oct (12 %) | 1 069 | 77 % | Sí |
| Cusco, 13,73° S 72,13° O | 15 set (10 %) | 17 oct (9 %) | 983 | 100 % | Sí |
| Moquegua, 16,71° S 70,73° O | 10 oct (1 %) | 17 oct (10 %) | 401 | 94 % | Sí |
| Junín, 11,41° S 75,53° O | 3 oct (0 %) | 13 oct (11 %) | 33 | 29 % | Sí |
| Junín, 11,84° S 73,86° O | 22 jun (0 %) | 8 oct (0 %) | 4 587 | 100 % | No: 108 días entre imágenes |

### Validación de la regla en pastizal

| Clasificados como | Eventos | Focos (mediana) | Quemado en la zona | Control sin focos | Ha netas (mediana) |
|---|---|---|---|---|---|
| Incendio | 4 | 8 | 30 % | 0,7 % | 310 |
| Quema pequeña | 6 | 2 | 15 % | 4,1 % | 36 |

- La medición es sólida: en los controles casi no aparece quemado, así que el secado de la
  estación no explica el resultado. El 100 % de los focos de la muestra son fuego real (dNBR ≥ 0,27).
- La regla va en la dirección correcta (los "incendios" queman ~9 veces más), pero con 10 eventos
  la diferencia no es significativa (Mann-Whitney, p = 0,24) y hay casos que se cruzan: una
  "quema pequeña" de 1 foco en Ayacucho quemó 143 ha.
- Las quemas recurrentes no se pudieron validar: ninguna tuvo un control válido (caen en selva,
  sin pastizal limpio a 5 km).

## Mapa

El dashboard incluye un mapa interactivo con la anomalía por departamento, los focos de los
últimos 7 días y los incendios activos coloreados por riesgo, más un mapa de severidad dNBR
por cada incendio medido con Sentinel-2.

## Limitaciones

- **El satélite no ve la intención.** Un foco sobre pastizal es fuego real, pero si fue una quema
  para renovar pasto o un incendio se infiere por tamaño, duración y recurrencia, y no es exacto
  (ver la validación).
- La roza y quema en la selva aparece sobre "bosque" si la tala es posterior a 2021 y se cuenta
  como incendio. Separarla requiere un dato de pérdida de bosque (p. ej. Global Forest Watch).
- WorldCover es de 2021 y se aplica a todos los años.
- Las nubes esconden el fuego, sobre todo en la selva: menos focos puede significar más nubes.
- S-NPP pasa dos veces al día (~01:30 y ~13:30); los fuegos cortos entre pasadas no se ven.
- 2026 viene de INPE y 2012–2025 de FIRMS. Son el mismo sensor y el profesor midió una diferencia
  mensual de −1,4 % a +0,9 % entre ambas fuentes, pero no es exactamente el mismo procesamiento.
- El dNBR mezcla fuego con cualquier otra pérdida de verdor entre las dos fechas. Solo se
  midieron 8 incendios, y los activos se miden hasta la fecha de la imagen de después.
- El riesgo usa umbrales simples sobre un pronóstico; no reemplaza a SENAMHI, COEN, INDECI ni SERFOR.
- WorldPop 2020 es una estimación, no un censo.

## Cómo correrlo

Desde la carpeta `tarea_3`:

```
conda env create -f environment.yml
conda activate geo
python src/01_descargar.py
python src/02_limpiar.py
python src/03_comparar.py
python src/04_incendios_riesgo.py
python src/05_dnbr.py
python src/06_dashboard.py
```

Tarda unos 20 minutos: la descarga de INPE (~150 MB por mes, se filtra al leer), WorldCover
(la primera vez) y las lecturas de Sentinel-2 del paso 5.
