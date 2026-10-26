# Tarea 2 · Documentos y voces del Perú: OCR, ASR y LLM

¿Qué tan bien leen y escuchan los modelos abiertos documentos y voces peruanas? La **Parte 1** arma dos corpus con
licencia libre, los pasa por OCR y ASR, seudonimiza los textos y los explora. La Parte 2 (CER/WER, extracción con LLM
y comparación de modelos) va en `02_evaluacion.ipynb`.

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb        # recolección, OCR, transcripción, limpieza, seudonimización y EDA
├── 02_evaluacion.ipynb        # CER/WER, LLM y comparativa de modelos (Parte 2)
├── app.py                     # aplicación Streamlit
├── requirements.txt           # dependencias exactas, exportadas de uv.lock
├── pyproject.toml, uv.lock    # entorno uv (grupos docai y audio)
├── evidencias_ia/             # capturas de la conversación con IA
├── datos/
│   ├── documentos.csv         # 25 documentos con su texto OCR
│   ├── transcripciones.csv    # 24 clips (66.8 min) con su transcripción diarizada
│   ├── fuentes.csv            # URL, licencia, autor, acceso y SHA-256 de los 50 archivos
│   ├── ejemplos/              # una miniatura por tipo de documento y un SRT diarizado
│   └── raw/                   # originales, OCR crudo, recortes, WAV y SRT (no se versiona)
└── modelos/
    ├── config_ocr.json        # parámetros y versiones de PaddleOCR
    └── config_asr.json        # parámetros de faster-whisper, VAD y diarización
```

## Cómo ejecutarlo

```
cd tarea_2
uv sync --group docai --group audio
uv run python -m ipykernel install --user --name tarea2 --display-name "Python (tarea_2)"
uv run jupyter lab 01_extraccion.ipynb
```

Sin uv: `pip install -r requirements.txt` (incluye el índice de PyTorch para CUDA 12.6).

- El ASR necesita una GPU NVIDIA; con 8 GB alcanza para `large-v3` en `float16`. El OCR corre en CPU.
- La primera ejecución baja unos 185 MB de Commons, más los modelos (Whisper `large-v3`, PP-OCRv5, ECAPA). El OCR toma
  unos 2 minutos por página en CPU y el ASR unos 10 minutos en total.
- Después usa caché: no vuelve a bajar archivos, ni a pasar el OCR o el ASR por lo que ya está en `datos/raw/`.
- Para diarizar con pyannote en lugar de SpeechBrain, define `HF_TOKEN` (hay que aceptar los términos de
  `pyannote/speaker-diarization-community-1` en Hugging Face).

## Corpus

| Corpus | Contenido | Licencias |
|---|---|---|
| 8 impresos | Diarios (*El Comercio* 1842 y 1945, *El Tiempo* 1895, *La Tribuna* 1931), una proclama de 1808, un oficio de 1823, una portada de 1818 y una carta mecanografiada de 1914 | Dominio público, CC0, CC BY-SA 4.0 |
| 8 fotos | Placas conmemorativas de Lima y cartas en exhibición, con sombras, reflejos o inclinación | CC BY-SA, CC BY, CC0, dominio público |
| 9 manuscritos | Cartas y documentos de la Colonia al siglo XX: Biblioteca Nacional del Perú y colección Fitte (sección Perú) de la Academia Nacional de la Historia argentina | Dominio público, CC0 |
| 25 clips | 22 entrevistas callejeras de 2022 (Lima, Callao y Cusco) y 3 noticieros de la Biblioteca Nacional del Perú | CC BY-SA 4.0, CC BY 3.0, CC0 |

Decisiones:

- **Una página por documento.** Los PDF se bajan como la imagen de una sola página, renderizada por Commons.
- **Tamaños estándar de Commons.** Las imágenes se piden a 1920 px de ancho, porque Commons rechaza otros tamaños y limita la descarga de originales.
- **Videos livianos.** De cada video se baja la versión más liviana (240p) y se extrae solo el audio.
- **Sin datos sensibles.** No se incluyen entrevistas sobre identidad de género u orientación sexual, aunque su licencia lo permita.

## Resultados de la Parte 1

| | Impresos | Fotos | Manuscritos |
|---|---|---|---|
| Confianza media del OCR (mediana) | 0.96 | 0.83 | 0.70 |
| Caracteres por página (mediana) | 3022 | 393 | 546 |

- **Limpieza**:
  - Sin duplicados, sin documentos ilegibles con las reglas usadas (menos de 40 caracteres o confianza menor a 0.5).
  - Un clip descartado: `clip_012` tiene 68 s con voz según el VAD, pero es música. Whisper inventó "¡Gracias!" tres veces (0.04 palabras por segundo).
  - Quedan 24 clips y 66.8 minutos.
- **Diarización**:
  - 18 clips con 2 hablantes (entrevistador y entrevistado).
  - Los 3 noticieros salen con 1 hablante (un narrador), como corresponde.
  - 3 entrevistas también salen con 1 hablante: la segunda voz no llega a 5 s o el clustering la une con la primera.
- **Seudonimización**:
  - 258 menciones de personas reemplazadas (202 en OCR, 56 en ASR), sin DNI, teléfonos ni correos en el corpus.
  - El NER marca como persona parte del ruido del OCR. Un filtro deja solo los tramos con forma de nombre y saca los tratamientos ("Señor Don").
  - Una regla extra reemplaza a quien se presenta en una entrevista ("mi nombre es…").
  - Revisión manual de los CSV exportados: los dos nombres que el NER dejó pasar se agregaron a una lista guardada como hash SHA-256, para no publicarlos en el código.
- **Validación**:
  - Los OCR más largos son los diarios (hasta 11 349 caracteres) y los más cortos, placas fotografiadas (61 a 161).
  - Los clips más largos son los noticieros (316 a 354 s).
  - La mediana de 2.3 palabras por segundo de voz está en el rango del habla normal.

## Limitaciones

- **OCR de fotos y manuscritos.** En las placas y los manuscritos, el texto es en buena parte ilegible aunque la confianza del OCR sea alta. La regla de descarte no lo detecta. La Parte 2 lo medirá con CER sobre una muestra transcrita a mano.
- **Diarización.** Usa un umbral fijo (distancia coseno 0.7). Con voces parecidas o mucho ruido de calle puede juntar a dos personas en una.
- **Nombres que se escapan.** El NER no reconoce todos los nombres en el texto ruidoso del OCR. La revisión manual buscó palabras con mayúscula fuera del vocabulario de spaCy, pero un nombre común en un contexto ilegible todavía podría pasar.
- **Atribución.** `fuentes.csv` conserva el autor y la URL de Commons de cada archivo, porque las licencias CC BY y CC BY-SA exigen atribución. Algunos títulos de archivo, en esas URL y en la lista de descarga del notebook, incluyen nombres de personajes públicos.

## Uso de IA

Usé Claude como apoyo para escribir código y buscar fuentes. Revisé y validé cada resultado antes de aceptarlo. Las
capturas de la conversación están en `evidencias_ia/`.
