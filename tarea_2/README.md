# Tarea 2 · Documentos y voces del Perú: OCR, ASR y LLM

**¿Qué tan bien leen y escuchan los modelos abiertos documentos y voces peruanas?**

Se armaron dos corpus con licencia libre, se pasaron por OCR y reconocimiento de voz, se seudonimizaron, se midió el
error de varios modelos contra transcripciones manuales y se extrajeron campos estructurados con un LLM local.

**Dashboard:** [modelos-documentos-audio.streamlit.app](https://modelos-documentos-audio.streamlit.app/)

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb        # recolección, OCR, transcripción, limpieza, seudonimización, EDA y muestra de evaluación
├── 02_evaluacion.ipynb        # CER/WER, comparativa de modelos, extracción con LLM y auditoría humana
├── app.py                     # dashboard Streamlit (solo lee los CSV)
├── requirements.txt           # dependencias de la app
├── README.md
├── .gitignore                 # deja fuera datos/raw/ (originales, OCR crudo, audio, referencias sin seudonimizar)
├── evidencias_ia/             # capturas de la conversación con IA
├── datos/
│   ├── documentos.csv         # 25 documentos con su texto OCR
│   ├── transcripciones.csv    # 24 clips (66.8 min) con su transcripción diarizada
│   ├── extraccion_llm.csv     # campos JSON extraídos por el LLM
│   ├── fuentes.csv            # URL, licencia, autor, acceso y SHA-256 de los 50 archivos
│   └── ejemplos/              # una miniatura por tipo de documento y un SRT diarizado
└── modelos/                   # configuración de OCR, ASR y de la evaluación
```

## Corpus y fuentes

**Fuentes:** Wikimedia Commons. No se usaron archive.org, OpenSLR 73 ni grabaciones propias. Las fechas de extracción
son el **25 y 26 de octubre de 2026**, y el detalle de cada archivo está en `datos/fuentes.csv`.

| Corpus | Contenido | Licencias |
|---|---|---|
| 8 impresos | Diarios *El Comercio* (1842, 1945), *El Tiempo* (1895) y *La Tribuna* (1931), una proclama de 1808, un oficio de 1823, una portada de 1818 y una carta mecanografiada de 1914 | Dominio público, CC0, CC BY-SA 4.0 |
| 8 fotos | Placas conmemorativas de Lima y cartas en exhibición | CC BY-SA 3.0 y 4.0, CC BY 2.0, CC0, dominio público |
| 9 manuscritos | Cartas y documentos de la Biblioteca Nacional del Perú y de la colección Fitte (sección Perú) de la Academia Nacional de la Historia argentina | Dominio público, CC0 |
| 25 clips (24 tras la limpieza) | 22 entrevistas callejeras de 2022 en Lima, el Callao y Cusco, y 3 noticieros de la Biblioteca Nacional del Perú | CC BY-SA 4.0, CC BY 3.0, CC0 |

Los nombres de personas se reemplazan por marcadores (`[PERSONA_3]`) en todos los textos publicados. La muestra de
evaluación (10 documentos y 10 clips) se transcribió a mano.

## Hallazgos

1. **El OCR depende del tipo de documento mucho más que del modelo.** PaddleOCR lee los impresos casi sin errores
   (CER 0.06), pero en los manuscritos ningún modelo baja de 0.30. Ese texto ilegible arrastra al LLM: las 4
   extracciones de documentos que la auditoría marcó como incorrectas son manuscritos, y en ellas el modelo inventa
   contenido. El preprocesamiento de la Parte 1 (CLAHE) empeoró las fotos de placas: el CER pasó de 0.30 a 0.52.
2. **faster-whisper large-v3 en GPU es el más preciso y también el más rápido.** Tiene un WER de 0.19 y un RTF de 0.08,
   frente a 0.32 de la línea base (small en CPU) y 0.24 de Qwen3-ASR. Los noticieros de estudio casi no tienen errores
   (WER 0.01–0.06); las entrevistas en la calle quedan entre 0.08 y 0.32, por el ruido y el habla espontánea.

## Limitaciones

1. **Muestra pequeña.** Las métricas salen de 10 documentos y 10 clips, y en audio solo del primer minuto de cada uno.
   Las diferencias entre modelos de unos pocos puntos de WER no son concluyentes.
2. **El LLM no sirve para contar hablantes ni para leer texto ilegible.** Falla `numero_hablantes` en 9 de 10 audios
   (cuenta turnos, no personas), y la auditoría da 7/20 extracciones completamente correctas (35 %). Además, la
   seudonimización por NER deja falsos positivos ("Julio", "Dios") y obligó a una revisión manual de los nombres.

## Cómo ejecutar

**Dashboard (local):**

```
cd tarea_2
python -m venv .venv
.venv\Scripts\activate          # en Linux o macOS: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

**Notebooks:** necesitan Python 3.12 y una GPU NVIDIA (8 GB alcanzan). Los datos originales se descargan de Commons
la primera vez y quedan en `datos/raw/`.

```
cd tarea_2
uv venv --python 3.12
uv pip install --extra-index-url https://download.pytorch.org/whl/cu126 --index-strategy unsafe-best-match ^
  torch==2.14.1+cu126 torchvision==0.29.1+cu126 torchaudio==2.11.0+cu126 nvidia-cublas-cu12==12.9.2.10 ^
  nvidia-cudnn-cu12==9.27.0.42 paddlepaddle==3.2.0 paddleocr==3.7.0 opencv-python-headless==5.0.0.93 ^
  faster-whisper==1.2.1 speechbrain==1.1.2 pyannote-audio==4.0.7 scikit-learn==1.9.1 soundfile==0.14.0 ^
  transformers==5.20.2 accelerate==1.15.0 jiwer==4.0.0 easyocr==1.7.2 spacy==3.8.16 ^
  "es-core-news-md @ https://github.com/explosion/spacy-models/releases/download/es_core_news_md-3.8.0/es_core_news_md-3.8.0-py3-none-any.whl" ^
  imageio-ffmpeg==0.6.0 pandas==3.1.0 plotly==7.1.0 pillow==13.0.0 requests==2.34.2 ipykernel==7.4.0 ^
  nbconvert==7.17.2 nbformat==5.11.1
uv run python -m ipykernel install --user --name tarea2 --display-name "Python (tarea_2)"
```

Después se abren `01_extraccion.ipynb` y `02_evaluacion.ipynb` con el kernel **Python (tarea_2)**. La evaluación
necesita las transcripciones manuales en `datos/raw/referencias/`, que no se publican porque tienen nombres reales.

## Uso de IA

Usé Claude como apoyo para escribir código y buscar fuentes. Revisé y validé cada resultado antes de aceptarlo. Las
transcripciones de referencia y la auditoría de las extracciones del LLM las hice a mano. Las capturas de la
conversación están en `evidencias_ia/`.
