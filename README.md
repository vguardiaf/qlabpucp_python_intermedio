# Tarea 1 - Noticias peruanas: del titular al clasificador

## Pregunta del trabajo

¿Pueden convertir titulares peruanos en un clasificador de noticias?

Extraer noticias reales de **La República**, etiquetarlas de forma semi-supervisada con un LLM, entrenarlas en un Transformer ligero (DistilBERT / BETO) y desplegar un dashboard en Streamlit que prediga la categoría de un titular y su nivel de confianza.

## Precisiones

- Categorías fijas: `politica`, `economia`, `deportes`, `ciencia_tecnologia`. Lo que no encaja se descarta y se reporta en el notebook.
- `datos/noticias.csv` tiene **7 columnas**: `titular`, `bajada`, `medio`, `seccion_original`, `url`, `fecha`, `etiqueta`, y **350+ filas reales** con URLs funcionales.
- Scraping respetuoso: se revisa `robots.txt`, `User-Agent` descriptivo, pausas de 1-2 s y máximo 1 reintento. Si hay bloqueo, se usa RSS y se documenta.
- Métricas (F1 y matriz de confusión) **solo sobre el conjunto de test**.
- Los pesos pesados (`.safetensors`, `.bin`, `checkpoint-*/`) están en `.gitignore`.

## Estructura

```
tarea_1/
├── 01_recoleccion.ipynb
├── 02_clasificacion.ipynb
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── datos/
│   ├── noticias.csv
│   └── etiquetas_llm.csv
└── modelo/
```

## Issues como bitácora

- Hay un Issue por parte:
  - **T1 – Parte 1:** Recolección y Limpieza
  - **T1 – Parte 2:** Modelado y Clasificación
  - **T1 – Parte 3:** Dashboard y Despliegue
- En los Issues se anotan avances, bloqueos y decisiones. **No se escribe código en los Issues.**
- Cuando la parte está terminada y revisada, se cierra el Issue.

## Orden de trabajo

1. **Parte 1: Recolección** (`01_recoleccion.ipynb`). Scraping, limpieza y EDA. Produce `datos/noticias.csv`.
2. **Parte 2: Clasificación** (`02_clasificacion.ipynb`). Empieza cuando existe el CSV. Etiquetado con LLM (`datos/etiquetas_llm.csv`), split train/test, fine-tuning y evaluación.
3. **Parte 3: Dashboard** (`app.py` + `README.md`). Empieza cuando hay un modelo entrenado.

## Commits

- Commits **descriptivos y frecuentes** a lo largo de los días, no todo el último día (por ejemplo: `scrape: 400 titulares LR`, `train: distilbert 3 epochs F1 0.81`).
- Antes de empezar a trabajar: **Pull / Fetch**.

## Uso de IA

- Uso de Claude como apoyo, sin aceptar nada sin revisar.

## Revisión antes de entregar

- Se verificó que el CSV tenga las 7 columnas y que las URLs funcionen.
- Se verificó que las métricas se calculen sobre test y no sobre train.
- Se comprobó que `requirements.txt` esté completo y que el dashboard clasifique titulares nuevos en vivo.
- Los 2 notebooks corren de principio a fin y están **ejecutados** (salidas, métricas y gráficos visibles en GitHub).
- `requirements.txt` está completo y el dashboard abre y clasifica en vivo.
- No hay archivos de más de 100 MB en el repo.
- Los 3 Issues están cerrados.
