# Pobreza y voto en Brasil 2026

**Pregunta:** ¿los municipios más pobres votaron más por Lula, y explica la pobreza quién remontó entre vueltas?

- **Dashboard:** https://vguardiaf.github.io/qlabpucp_python_intermedio/tarea_3/web/
- **Reel:** [reel/reel.mp4](reel/reel.mp4)
- **Publicación de LinkedIn:** https://lnkd.in/p/dpfmRNiu

## Proyecto

Flávio Bolsonaro ganó la primera vuelta (47,03 % a 45,16 %) y Lula ganó la segunda con 51,79 %. Este proyecto cruza el voto de los 5.570 municipios de Brasil con su nivel de pobreza para ver quién votó por Lula y dónde remontó.

## Fuentes y metodología

| Dato | Fuente | Fecha |
|---|---|---|
| Votos por municipio y zona | [TSE, Resultados 2026](https://dadosabertos.tse.jus.br/dataset/resultados-2026) | Elecciones del 4 y 25 de octubre de 2026 |
| Ingreso per cápita por municipio | [IBGE, Censo 2022, tabla 10296](https://sidra.ibge.gov.br/tabela/10296) | 2022 |
| Equivalencia de códigos TSE-IBGE | [betafcc/Municipios-Brasileiros-TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE) | |
| Límites municipales | [tbrugz/geodata-br](https://github.com/tbrugz/geodata-br) | |

- **Pobreza:** % de residentes con ingreso per cápita de hasta 1/2 salario mínimo (R$ 606), incluidas las personas sin ingresos. Brasil no tiene línea oficial; es el tramo del censo más cercano a la línea del Banco Mundial que usa el IBGE (R$ 665 en 2022). A nivel nacional da 31,8 %, frente al 31,6 % del IBGE con la PNAD Contínua.
- **Quintiles:** cinco grupos de 1.114 municipios, ordenados por pobreza.
- **Correlación:** Pearson, ponderada por votos válidos, nacional y dentro de cada estado.
- **Validación:** los totales de la segunda vuelta reproducen el resultado final del TSE (Lula, 64.256.232 votos).

## Hallazgos

1. **A más pobreza, más voto por Lula.** Lula sacó 73,6 % en el quintil más pobre y 37,9 % en el menos pobre. La correlación es 0,77, y 0,56 dentro de cada estado.
2. **La remontada no vino de los más pobres.** Lula subió 4,7 puntos en el quintil más pobre y 7,7 en el quintil 2. De 214 municipios que cambiaron de ganador, 168 están en los quintiles 2 y 3.
3. **La pobreza no lo explica todo.** Con pobreza parecida, Lula sacó 69,5 % en Sergipe y 33,4 % en Acre.

## Limitaciones

- Se comparan municipios, no personas, y la correlación no prueba causalidad.
- La pobreza es de 2022 y el voto, de 2026. Es el dato más reciente que cubre todos los municipios.
- Donde Lula ya tenía cerca del 70 %, podía subir menos.
- Se excluyen los votos del exterior (702.533) y los de Boa Esperança do Norte (3.298), municipio instalado en 2025.
- Seis municipios no tienen polígono en el mapa, aunque sí cuentan en los cálculos.

## Cómo reproducirlo

Los datos crudos no están en el repositorio; `01_obtener_datos.py` los descarga.

```
conda activate geo
python scripts/01_obtener_datos.py
python scripts/02_procesar_datos.py
python scripts/03_analizar_datos.py
python scripts/04_datos_web.py
python scripts/05_imagenes_reel.py

conda activate reel
python scripts/06_hacer_reel.py --voz reel/recursos/mi_voz.mp4 --autor "Nombre Apellido"
```

## Uso de inteligencia artificial

Este proyecto se elaboró con el apoyo de Claude (Anthropic), utilizado para la búsqueda de fuentes y la redacción de código y textos. El autor definió la pregunta de investigación, ejecutó el procesamiento de los datos, seleccionó la medición por quintiles de pobreza, revisó los resultados y determinó el contenido y las limitaciones presentadas. La narración usa Qwen3-TTS a partir de la voz del autor, y `reel.py` adapta el código de la Sesión 15 del curso.
