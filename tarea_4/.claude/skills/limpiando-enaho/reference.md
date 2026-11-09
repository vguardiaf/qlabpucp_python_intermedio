# Referencia de la ENAHO 2024

## Descarga

- Módulo 34: https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip
- Módulo 02: https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip

Se guardan en datos/ sin descomprimir.

## Variables de salidas/personas_2024.parquet

| Variable | Significado |
|---|---|
| conglome, vivienda, hogar, codperso | Llaves, como texto |
| anio | Año de la encuesta |
| ubigeo | Seis dígitos, como texto |
| departamento | ubigeo[:2], como texto |
| nombre_departamento | Nombre con tildes (tabla de abajo) |
| dominio | 8 = Lima Metropolitana |
| estrato | 1 a 5 urbano, 6 a 8 rural |
| urbano | True si estrato <= 5 |
| pobreza | 1 pobre extremo, 2 pobre no extremo, 3 no pobre |
| pobre, extremo | pobreza <= 2 y pobreza == 1 |
| p207 | Sexo: 1 hombre, 2 mujer |
| p208a | Edad en años |
| p203 | Parentesco con el jefe del hogar |
| p204, p205, p206 | Residencia en el hogar |
| mieperho | Miembros del hogar |
| factor07 | Factor de expansión del hogar |
| facpob07 | Factor de expansión de la persona |

Para usar otra variable, agrégala a COLUMNAS_PERSONA o COLUMNAS_HOGAR en scripts/limpiar.py y vuelve a correrlo.

## Departamentos

| Código | Nombre | Código | Nombre | Código | Nombre |
|---|---|---|---|---|---|
| 01 | Amazonas | 10 | Huánuco | 19 | Pasco |
| 02 | Áncash | 11 | Ica | 20 | Piura |
| 03 | Apurímac | 12 | Junín | 21 | Puno |
| 04 | Arequipa | 13 | La Libertad | 22 | San Martín |
| 05 | Ayacucho | 14 | Lambayeque | 23 | Tacna |
| 06 | Cajamarca | 15 | Lima | 24 | Tumbes |
| 07 | Callao | 16 | Loreto | 25 | Ucayali |
| 08 | Cusco | 17 | Madre de Dios | | |
| 09 | Huancavelica | 18 | Moquegua | | |

Lima (15) y Callao (07) van separados. Lima Metropolitana se filtra con dominio == 8, no con el departamento.

## Reglas

- Los códigos se comparan como texto: Cusco es "08", no 8.
- pobreza es una categoría: nunca se promedia.
- Las cifras se ponderan con facpob07. Una tasa por grupo es la suma de facpob07 de los pobres entre la suma de facpob07 del grupo.