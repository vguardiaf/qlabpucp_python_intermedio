# Python intermedio · Q-Lab PUCP

Tareas del curso **Ciencia de Datos con Python** (Prof. Alexander Quispe).
Autor: Víctor Guardia ([@vguardiaf](https://github.com/vguardiaf)).

Cada tarea está en su propia carpeta y tiene su propio README, entorno y `.gitignore`.

| Tarea | Pregunta | Herramientas | Resultado principal |
|---|---|---|---|
| [Tarea 1](tarea_1/) | ¿Se pueden convertir titulares peruanos en un clasificador de noticias? | Scraping (RSS y HTML), etiquetado con LLM local, fine-tuning de BETO, Streamlit | 383 titulares de El Comercio · F1 macro **0.82** en test (zero-shot: 0.64) [App](https://clasificador-noticias-peru.streamlit.app/) |
| [Tarea 2](tarea_2/) | ¿Qué tan bien leen y escuchan los modelos abiertos documentos y voces peruanas? | PaddleOCR, EasyOCR, faster-whisper, Qwen3-ASR, SpeechBrain (diarización), spaCy (seudonimización), Qwen2.5 (extracción), Streamlit | Resultados Test: WER: **0.19** \| CER: **0.26** \| Acuerdo LLM-Humano: **7/20** · Fuentes: Wikimedia Commons · [App](https://modelos-documentos-audio.streamlit.app/) |
| [Tarea 3](tarea_3/) | ¿Es 2026 un año récord de incendios en el Perú? | Focos VIIRS (FIRMS e INPE), geopandas, rasterio, WorldCover, Sentinel-2 (dNBR), Open-Meteo, d3 | Octubre 2026 **+106 %** (récord desde 2012), aunque la temporada va −16 % · [Dashboard](https://claude.ai/artifact/X8oDTiZ6w59yggsH36ptFu) |
| [Tarea 4](tarea_4/) | ¿Se pueden contar los hallazgos de la tarea 3 en un reel con modelos abiertos? | Qwen3.8 (guion), Qwen3-TTS (voz clonada), Whisper (subtítulos), MusicGen (música), Playwright, Pillow, ffmpeg | Reel vertical de **45 s** narrado con mi voz · [reel.mp4](tarea_4/reel/reel.mp4) |

## Tarea 1 · Noticias peruanas: del titular al clasificador

```
tarea_1/
├── 01_recoleccion.ipynb     # scraping de El Comercio, limpieza y EDA
├── 02_clasificacion.ipynb   # zero-shot, etiquetado con Qwen2.5, split y fine-tuning de BETO
├── app.py                   # dashboard Streamlit: clasifica un titular y da su confianza
├── requirements.txt
└── datos/                   # noticias.csv, etiquetas_llm.csv, auditoria_humana.csv, train/val/test.csv
```

Los pesos del modelo (`modelo/`) no se suben al repo: se regeneran con `02_clasificacion.ipynb`.

```
cd tarea_1
pip install -r requirements.txt
streamlit run app.py
```

## Tarea 2 · Documentos y voces del Perú: OCR, ASR y LLM

Arma dos corpus con licencia libre de Wikimedia Commons: 25 documentos peruanos (impresos, fotos y manuscritos) y
entrevistas callejeras y noticieros en español peruano. Los pasa por OCR y reconocimiento de voz, seudonimiza los
nombres, compara 3 OCR y 3 ASR contra transcripciones manuales y extrae campos estructurados con un LLM local, con
auditoría humana. Detalle, hallazgos y limitaciones en [tarea_2/README.md](tarea_2/README.md).

**Fuentes:** Wikimedia Commons. Los documentos vienen de la Biblioteca Nacional del Perú, de la colección Fitte de la
Academia Nacional de la Historia argentina (sección Perú) y de usuarios de Commons; los audios, de entrevistas
callejeras de 2022 subidas por estudiantes y de noticieros de la Biblioteca Nacional del Perú. No se usaron
archive.org, OpenSLR 73 ni grabaciones propias.

```
tarea_2/
├── 01_extraccion.ipynb     # recolección, OCR, transcripción, limpieza, seudonimización y EDA
├── 02_evaluacion.ipynb     # CER/WER, comparativa de modelos, extracción con LLM y auditoría
├── app.py                  # dashboard Streamlit: explora documentos, audios y resultados
├── requirements.txt        # dependencias de la app
├── datos/                  # documentos.csv, transcripciones.csv, extraccion_llm.csv, fuentes.csv, ejemplos/
└── modelos/                # configuración de OCR, ASR y de la evaluación
```

Los archivos originales, el OCR crudo, el audio y las transcripciones manuales (`datos/raw/`) no se suben al repo:
tienen datos personales o pesan demasiado. El entorno de los notebooks está en el README de la tarea.

```
cd tarea_2
pip install -r requirements.txt
streamlit run app.py
```

## Tarea 3 · Incendios en el Perú 2026 (retos A, E y F)

Compara la temporada 2026 con las de 2012–2025 usando solo S-NPP. Se queda solo con los focos que son
incendio y descarta fuentes fijas, quemas pequeñas o recurrentes y focos sin vegetación. Mide el área quemada
con Sentinel-2 y estima el riesgo de la semana con el pronóstico del clima.

```
tarea_3/
├── src/01_descargar.py … 06_dashboard.py   # pipeline en 6 pasos
├── src/plantilla_dashboard.html            # dashboard d3 (claro/oscuro)
├── data/processed/                          # resultados livianos (JSON, CSV, GeoJSON)
├── docs/index.html                          # dashboard como página HTML completa
├── dashboard/fragmento.html                 # misma página, versión artifact
└── environment.yml                          # entorno conda "geo"
```

Los datos crudos (`data/raw/`), los focos limpios y los GeoTIFF de dNBR no se suben al repo: se regeneran
con los pasos 1, 2 y 5.

```
cd tarea_3
conda env create -f environment.yml
conda activate geo
python src/01_descargar.py   # y así hasta 06_dashboard.py (~20 min)
```

## Tarea 4 · Del tablero al reel

Convierte los hallazgos de la tarea 3 en un reel de 45 s para redes. Hay una persona revisando en el medio:
el guion de Qwen se corrigió a mano contra la fuente antes de narrarlo.

1. **Guion**: Qwen3.8 (chat.qwen.ai) resume los hallazgos en 6 escenas, cada una con frase, cifra y etiqueta.
2. **Revisión**: se corrigió una frase falsa ("Moquegua triplica su máximo": el +337 % es contra el promedio).
3. **Imágenes**: capturas del dashboard que acompañan cada escena (gráficos, mapa del sur andino, Sentinel-2).
4. **Voz**: Qwen3-TTS 1.7B clona mi voz con 13 s de grabación. Whisper vuelve a escuchar cada escena.
5. **Video**: subtítulos palabra por palabra, música de MusicGen (tensa → calma cuando llega la lluvia),
   −14 LUFS, 1080×1920 H.264 + AAC.

```
tarea_4/
├── guion/guion.json   # guion de Qwen corregido, con la lista de correcciones
└── reel/              # reel.mp4, post.md
```

El reel declara la voz y la música generadas con IA, en el video y en `post.md`.

## Uso de IA

Usé Claude como apoyo para escribir código. Revisé y validé cada resultado antes de aceptarlo.

## Licencia

[MIT](LICENSE)
