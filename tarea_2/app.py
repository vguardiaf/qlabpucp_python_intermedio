"""Dashboard Tarea 2: ¿qué tan bien leen y escuchan los modelos abiertos documentos y voces peruanas?

Solo lee los CSV de datos/ (textos ya seudonimizados). OCR, ASR y LLM corrieron antes en los notebooks.
"""
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote

import pandas as pd
import plotly.express as px
import streamlit as st

BASE = Path(__file__).parent
DATOS = BASE / "datos"

# Resultados copiados de 02_evaluacion.ipynb (sección 4): error por caso en la muestra de evaluación
CER = {
    "PaddleOCR base (CPU)": {"doc_001": 0.041, "doc_007": 0.06, "doc_008": 0.062, "doc_011": 0.013, "doc_013": 0.815,
                             "doc_016": 0.063, "doc_018": 0.498, "doc_019": 0.354, "doc_021": 0.3, "doc_023": 0.347},
    "PaddleOCR + CLAHE, Parte 1 (CPU)": {"doc_001": 0.041, "doc_007": 0.06, "doc_008": 0.062, "doc_011": 0.176,
                                         "doc_013": 0.694, "doc_016": 0.696, "doc_018": 0.498, "doc_019": 0.354,
                                         "doc_021": 0.3, "doc_023": 0.347},
    "EasyOCR (GPU)": {"doc_001": 0.266, "doc_007": 0.205, "doc_008": 0.147, "doc_011": 0.061, "doc_013": 0.452,
                      "doc_016": 0.253, "doc_018": 0.77, "doc_019": 0.766, "doc_021": 0.633, "doc_023": 0.835},
}
WER = {
    "faster-whisper small (CPU)": {"clip_004": 0.431, "clip_005": 0.743, "clip_009": 0.438, "clip_011": 0.318,
                                   "clip_016": 0.281, "clip_018": 0.18, "clip_019": 0.083, "clip_022": 0.315,
                                   "clip_023": 0.36, "clip_025": 0.014},
    "faster-whisper large-v3 (GPU)": {"clip_004": 0.324, "clip_005": 0.236, "clip_009": 0.286, "clip_011": 0.264,
                                      "clip_016": 0.173, "clip_018": 0.188, "clip_019": 0.075, "clip_022": 0.274,
                                      "clip_023": 0.056, "clip_025": 0.014},
    "Qwen3-ASR 0.6B (GPU)": {"clip_004": 0.363, "clip_005": 0.336, "clip_009": 0.371, "clip_011": 0.209,
                             "clip_016": 0.194, "clip_018": 0.286, "clip_019": 0.1, "clip_022": 0.268,
                             "clip_023": 0.146, "clip_025": 0.099},
}
# Factor de tiempo real (tiempo de proceso / duración). En el primer clip de Qwen3-ASR se suma la carga del modelo,
# por eso el resumen usa la mediana.
RTF = {
    "faster-whisper small (CPU)": {"clip_004": 0.481, "clip_005": 0.219, "clip_009": 0.144, "clip_011": 0.161,
                                   "clip_016": 0.147, "clip_018": 0.126, "clip_019": 0.316, "clip_022": 0.354,
                                   "clip_023": 0.66, "clip_025": 0.239},
    "faster-whisper large-v3 (GPU)": {"clip_004": 0.109, "clip_005": 0.073, "clip_009": 0.203, "clip_011": 0.073,
                                      "clip_016": 0.07, "clip_018": 0.063, "clip_019": 0.057, "clip_022": 0.071,
                                      "clip_023": 0.054, "clip_025": 0.035},
    "Qwen3-ASR 0.6B (GPU)": {"clip_004": 2.107, "clip_005": 0.097, "clip_009": 0.143, "clip_011": 0.11,
                             "clip_016": 0.094, "clip_018": 0.096, "clip_019": 0.093, "clip_022": 0.101,
                             "clip_023": 0.082, "clip_025": 0.057},
}
SEGUNDOS_POR_PAGINA = {"PaddleOCR base (CPU)": 29.4, "EasyOCR (GPU)": 2.1}
CONDICION = {"clip_004": "entrevista, exterior", "clip_005": "entrevista, manifestación",
             "clip_009": "entrevista, calle (Cusco)", "clip_011": "entrevista, calle", "clip_016": "entrevista, feria",
             "clip_018": "entrevista, centro comercial", "clip_019": "entrevista, centro comercial",
             "clip_022": "entrevista, interior", "clip_023": "noticiero con música", "clip_025": "noticiero con música"}

# Auditoría humana de 20 extracciones del LLM (02_evaluacion.ipynb, sección 7)
RESUMEN_MAL = "resumen no coincide con el contenido del documento"
HABLANTES_MAL = "numero_hablantes incorrecto"
AUDITORIA = {
    "doc_004": (True, ""), "doc_016": (True, ""), "doc_019": (False, RESUMEN_MAL), "doc_017": (False, RESUMEN_MAL),
    "doc_015": (True, ""), "doc_025": (False, RESUMEN_MAL), "doc_005": (True, ""), "doc_009": (True, ""),
    "doc_011": (True, ""), "doc_018": (False, RESUMEN_MAL),
    "clip_004": (False, HABLANTES_MAL), "clip_017": (False, HABLANTES_MAL), "clip_020": (False, HABLANTES_MAL),
    "clip_018": (False, "tema y resumen no reflejan las preguntas; " + HABLANTES_MAL),
    "clip_016": (False, HABLANTES_MAL), "clip_025": (False, HABLANTES_MAL), "clip_005": (False, HABLANTES_MAL),
    "clip_009": (False, HABLANTES_MAL), "clip_011": (False, HABLANTES_MAL), "clip_019": (True, ""),
}

# Publicación de archivos originales: se enlazan desde Wikimedia Commons, nunca se copian al repositorio
SIN_IMAGEN = {"doc_011": "carta de 1972 que incluye el domicilio de una persona particular"}
AUDIO_PUBLICO = {  # noticieros de la Biblioteca Nacional del Perú (CC0): sin voces ni nombres de particulares
    "clip_023": "https://upload.wikimedia.org/wikipedia/commons/transcoded/5/53/Tarma%2C_la_ciudad_florida_de_la_sierra.webm/Tarma%2C_la_ciudad_florida_de_la_sierra.webm.240p.vp9.webm",
    "clip_024": "https://upload.wikimedia.org/wikipedia/commons/transcoded/6/6f/Visiones_de_la_provincia_de_Cajamarca.webm/Visiones_de_la_provincia_de_Cajamarca.webm.240p.vp9.webm",
    "clip_025": "https://upload.wikimedia.org/wikipedia/commons/transcoded/4/4b/Visiones_de_la_provincia_de_Huancayo.webm/Visiones_de_la_provincia_de_Huancayo.webm.240p.vp9.webm",
}
ORDEN_TIPOS = ["impreso", "foto", "manuscrito"]

st.set_page_config(page_title="Documentos y voces del Perú", page_icon="📜", layout="wide")


@st.cache_data
def cargar():
    fuentes = pd.read_csv(DATOS / "fuentes.csv", keep_default_na=False)
    llm = pd.read_csv(DATOS / "extraccion_llm.csv", keep_default_na=False)[["id", "campos_json"]]
    meta = fuentes[["id", "tipo", "licencia", "autor", "fuente_url", "fecha_extraccion"]]
    docs = (pd.read_csv(DATOS / "documentos.csv", keep_default_na=False)
            .drop(columns="tipo").merge(meta, on="id").merge(llm, on="id", how="left"))
    clips = (pd.read_csv(DATOS / "transcripciones.csv", keep_default_na=False)
             .merge(meta, on="id").merge(llm, on="id", how="left"))
    docs["caracteres"] = docs.texto_ocr.str.len()
    clips["palabras"] = clips.texto_asr.str.replace(r"\[HABLANTE_[^\]]*\]", " ", regex=True).str.split().str.len()
    return docs, clips


def tabla_larga(metricas, columna):
    return pd.DataFrame([{"modelo": m, "id": i, columna: v} for m, casos in metricas.items() for i, v in casos.items()])


def url_imagen(fuente_url, ancho=900):
    """Render de Commons (los PDF salen como su primera página)."""
    nombre = unquote(fuente_url.split("/wiki/File:")[-1])
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(nombre)}?width={ancho}"


def turnos(texto):
    """Separa una transcripción diarizada en (hablante, texto)."""
    partes = re.split(r"\[(HABLANTE_[^\]]+)\]", texto)
    return [(h.replace("_", " ").title(), t.strip()) for h, t in zip(partes[1::2], partes[2::2]) if t.strip()]


docs, clips = cargar()
cer_largo = tabla_larga(CER, "CER").merge(docs[["id", "tipo"]], on="id")
wer_largo = tabla_larga(WER, "WER").merge(tabla_larga(RTF, "RTF"), on=["modelo", "id"]).assign(
    condicion=lambda d: d.id.map(CONDICION))

# --- 1. Encabezado y contexto ---
st.title("📜 ¿Qué tan bien leen y escuchan los modelos abiertos documentos y voces peruanas?")
st.markdown(
    f"""
**Resumen metodológico**

1. **Corpus:** {len(docs)} documentos peruanos de Wikimedia Commons (impresos, fotos y manuscritos de 1808 a 1985) y
   {len(clips)} clips de audio ({clips.duracion_seg.sum() / 60:.0f} min): entrevistas callejeras de 2022 y noticieros
   de los años 40. Todos con licencia libre, extraídos el {docs.fecha_extraccion.iloc[0]}.
2. **Extracción:** OCR con PaddleOCR 3.7 y transcripción con faster-whisper large-v3, con VAD y diarización. Los
   nombres de personas se reemplazan por marcadores como `[PERSONA_3]` antes de publicar.
3. **Evaluación:** 10 documentos y 10 clips transcritos a mano. Se comparan 3 OCR (CER) y 3 ASR (WER y velocidad).
4. **Extracción con LLM:** Qwen2.5-3B local convierte cada texto en un JSON (tema, resumen, emisor, fecha…), con
   auditoría humana de 20 casos.
"""
)

# --- 2. Filtros ---
st.sidebar.header("Filtros")
busqueda = st.sidebar.text_input("Buscar palabra en los textos OCR y ASR", placeholder="p. ej. Lima, patria, guerra")
sel_tipos = st.sidebar.multiselect("Tipo de documento", ORDEN_TIPOS, default=ORDEN_TIPOS)
sel_audio = st.sidebar.multiselect("Tipo de audio", ["entrevista", "noticiero"], default=["entrevista", "noticiero"])
dur_min, dur_max = int(clips.duracion_seg.min()), int(clips.duracion_seg.max()) + 1
sel_duracion = st.sidebar.slider("Duración del clip (s)", dur_min, dur_max, (dur_min, dur_max))
licencias = sorted(set(docs.licencia) | set(clips.licencia))
sel_licencias = st.sidebar.multiselect("Licencia de la fuente", licencias, default=licencias)
st.sidebar.markdown("**Modelos evaluados**")
sel_ocr = st.sidebar.multiselect("OCR", list(CER), default=list(CER))
sel_asr = st.sidebar.multiselect("ASR", list(WER), default=list(WER))


def contiene(serie):
    return serie.str.contains(re.escape(busqueda), case=False) if busqueda else pd.Series(True, index=serie.index)


docs_f = docs[docs.tipo.isin(sel_tipos) & docs.licencia.isin(sel_licencias) & contiene(docs.texto_ocr)]
clips_f = clips[clips.tipo.isin(sel_audio) & clips.licencia.isin(sel_licencias) & contiene(clips.texto_asr)
                & clips.duracion_seg.between(*sel_duracion)]
cer_f = cer_largo[cer_largo.modelo.isin(sel_ocr) & cer_largo.tipo.isin(sel_tipos)]
wer_f = wer_largo[wer_largo.modelo.isin(sel_asr)]
if busqueda:
    st.sidebar.caption(f"«{busqueda}» aparece en {len(docs_f)} documentos y {len(clips_f)} clips.")

# --- 3. Indicadores clave ---
correctas = sum(ok for ok, _ in AUDITORIA.values())
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Documentos procesados", len(docs_f), help="Con los filtros actuales; 25 en total")
c2.metric("Minutos de audio transcritos", f"{clips_f.duracion_seg.sum() / 60:.1f}", help="Con los filtros actuales")
if not cer_f.empty:
    mejor = cer_f.groupby("modelo").CER.mean().sort_values()
    c3.metric("Mejor CER (10 documentos)", f"{mejor.iloc[0]:.3f}", help=mejor.index[0])
if not wer_f.empty:
    mejor = wer_f.groupby("modelo").WER.mean().sort_values()
    c4.metric("Mejor WER (10 clips)", f"{mejor.iloc[0]:.3f}", help=mejor.index[0])
c5.metric("Concordancia LLM vs. auditoría", f"{correctas / len(AUDITORIA):.0%}", help=f"{correctas} de {len(AUDITORIA)} "
          "extracciones completamente correctas según la revisión humana")

tab_res, tab_docs, tab_audios, tab_datos = st.tabs(["📊 Resultados", "📄 Documentos", "🎙️ Audios", "🗂️ Datos y descarga"])

# --- 4. Resultados de la evaluación ---
with tab_res:
    st.subheader("OCR: CER sobre 10 documentos transcritos a mano")
    if cer_f.empty:
        st.info("Selecciona al menos un modelo OCR y un tipo de documento.")
    else:
        cols = st.columns(len(sel_ocr))
        for col, (modelo, valor) in zip(cols, cer_f.groupby("modelo").CER.mean().items()):
            col.metric(modelo, f"{valor:.3f}", help=f"{SEGUNDOS_POR_PAGINA.get(modelo, 'sin medir')} s por página")
        fig = px.bar(cer_f.groupby(["modelo", "tipo"], as_index=False).CER.mean(), x="tipo", y="CER", color="modelo",
                     barmode="group", category_orders={"tipo": ORDEN_TIPOS}, labels={"CER": "CER medio"},
                     title="Los impresos se leen casi sin errores; en manuscritos ningún OCR baja de 0.37")
        st.plotly_chart(fig, width="stretch")

    st.subheader("ASR: WER sobre 10 clips transcritos a mano (primer minuto)")
    if wer_f.empty:
        st.info("Selecciona al menos un modelo ASR.")
    else:
        resumen = wer_f.groupby("modelo").agg(WER=("WER", "mean"), RTF=("RTF", "median"))
        cols = st.columns(len(resumen))
        for col, (modelo, r) in zip(cols, resumen.iterrows()):
            col.metric(modelo, f"WER {r.WER:.3f}", help=f"RTF mediano {r.RTF:.2f} (tiempo de proceso / duración)")
        fig = px.bar(wer_f, x="id", y="WER", color="modelo", barmode="group", hover_data=["condicion", "RTF"],
                     labels={"id": "clip"}, title="Los noticieros de estudio se transcriben mejor que las entrevistas en la calle")
        st.plotly_chart(fig, width="stretch")
        fig = px.scatter(resumen.reset_index(), x="RTF", y="WER", text="modelo", log_x=True,
                         labels={"RTF": "RTF mediano (escala log)", "WER": "WER medio"},
                         title="large-v3 en GPU es a la vez el más preciso y el más rápido")
        fig.update_traces(textposition="top center", marker_size=12)
        st.plotly_chart(fig, width="stretch")

    st.subheader("Extracción con LLM: auditoría humana de 20 casos")
    auditoria = pd.DataFrame([{"id": i, "modalidad": "documento" if i.startswith("doc") else "audio",
                               "resultado": "correcta" if ok else "con errores", "motivo": motivo}
                              for i, (ok, motivo) in AUDITORIA.items()])
    fig = px.histogram(auditoria, x="modalidad", color="resultado", barmode="group",
                       color_discrete_map={"correcta": "#2E7D32", "con errores": "#C62828"},
                       title="El LLM acierta 6 de 10 documentos, pero falla el número de hablantes en 9 de 10 audios")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(auditoria[auditoria.resultado != "correcta"], hide_index=True, width="stretch")

# --- 5. Explorador de documentos ---
with tab_docs:
    if docs_f.empty:
        st.warning("Ningún documento cumple los filtros.")
    else:
        izq, der = st.columns([1, 2])
        conteo = docs_f.groupby("tipo", as_index=False).size()
        izq.plotly_chart(px.bar(conteo, x="tipo", y="size", category_orders={"tipo": ORDEN_TIPOS},
                                labels={"size": "documentos"}, title="Documentos por tipo"), width="stretch")
        der.dataframe(docs_f[["id", "tipo", "licencia", "caracteres", "texto_ocr"]], hide_index=True,
                      width="stretch", height=320)

        doc_id = st.selectbox("Documento", docs_f.id, format_func=lambda i: f"{i} · {docs.set_index('id').loc[i, 'tipo']}")
        d = docs.set_index("id").loc[doc_id]
        col_img, col_txt = st.columns([1, 2])
        with col_img:
            if doc_id in SIN_IMAGEN:
                st.info(f"Sin vista previa: {SIN_IMAGEN[doc_id]}. El texto y los metadatos siguen disponibles.")
            else:
                st.image(url_imagen(d.fuente_url), width="stretch")
            st.caption(f"Fuente: [Wikimedia Commons]({d.fuente_url}) · {d.licencia} · {d.autor}")
        with col_txt:
            st.markdown("**Texto OCR (seudonimizado)**")
            st.text_area("Texto OCR", d.texto_ocr, height=220, label_visibility="collapsed")
            if d.texto_referencia:
                st.markdown("**Transcripción manual de referencia**")
                st.text_area("Referencia", d.texto_referencia, height=160, label_visibility="collapsed")
                st.dataframe(pd.DataFrame({"modelo": list(CER), "CER": [CER[m][doc_id] for m in CER]}),
                             hide_index=True, width="stretch")
            else:
                st.caption("Este documento no está en la muestra de evaluación: no tiene referencia manual ni CER.")
            st.markdown("**Campos extraídos por el LLM**")
            st.json(json.loads(d.campos_json))
            if doc_id in AUDITORIA:
                ok, motivo = AUDITORIA[doc_id]
                st.caption("Auditoría humana: " + ("correcta" if ok else f"con errores ({motivo})"))

# --- 6. Explorador de audios ---
with tab_audios:
    if clips_f.empty:
        st.warning("Ningún clip cumple los filtros.")
    else:
        izq, der = st.columns([1, 2])
        izq.plotly_chart(px.histogram(clips_f, x="duracion_seg", color="tipo", nbins=12,
                                      labels={"duracion_seg": "duración (s)"}, title="Duración de los clips"),
                         width="stretch")
        der.dataframe(clips_f[["id", "tipo", "duracion_seg", "n_hablantes", "licencia", "texto_asr"]], hide_index=True,
                      width="stretch", height=320)

        clip_id = st.selectbox("Clip", clips_f.id, format_func=lambda i: f"{i} · {clips.set_index('id').loc[i, 'tipo']}")
        c = clips.set_index("id").loc[clip_id]
        col_audio, col_txt = st.columns([1, 2])
        with col_audio:
            st.metric("Duración", f"{c.duracion_seg:.0f} s")
            st.metric("Hablantes (diarización)", c.n_hablantes)
            if clip_id in AUDIO_PUBLICO:
                st.audio(AUDIO_PUBLICO[clip_id])
            else:
                st.info("Audio no disponible: es una entrevista a personas particulares y su voz y su nombre las "
                        "identifican. La transcripción seudonimizada sí está disponible.")
            st.caption(f"Fuente: [Wikimedia Commons]({c.fuente_url}) · {c.licencia}")
        with col_txt:
            st.markdown("**Transcripción ASR con marcas de hablante (seudonimizada)**")
            for hablante, texto in turnos(c.texto_asr):
                st.markdown(f"**{hablante}:** {texto}")
            if c.texto_referencia:
                st.markdown("**Comparación de modelos en el primer minuto**")
                st.dataframe(pd.DataFrame({"modelo": list(WER), "WER": [WER[m][clip_id] for m in WER],
                                           "RTF": [RTF[m][clip_id] for m in WER]}), hide_index=True,
                             width="stretch")
                with st.expander("Transcripción manual de referencia"):
                    st.write(c.texto_referencia)
            st.markdown("**Campos extraídos por el LLM**")
            st.json(json.loads(c.campos_json))
            if clip_id in AUDITORIA:
                ok, motivo = AUDITORIA[clip_id]
                st.caption("Auditoría humana: " + ("correcta" if ok else f"con errores ({motivo})"))

# --- 7. Datos y descarga ---
with tab_datos:
    st.caption("Todos los textos están seudonimizados. Las tablas respetan los filtros de la barra lateral.")
    for titulo, tabla, archivo in [
        ("Documentos (OCR)", docs_f[["id", "tipo", "fuente", "texto_ocr", "modelo_ocr", "texto_referencia"]],
         "documentos.csv"),
        ("Transcripciones (ASR)", clips_f[["id", "tipo", "duracion_seg", "idioma", "texto_asr", "modelo_asr",
                                           "n_hablantes", "texto_referencia"]], "transcripciones.csv"),
        ("Extracción con LLM", pd.concat([docs_f, clips_f])[["id", "campos_json"]], "extraccion_llm.csv"),
    ]:
        st.markdown(f"**{titulo}** · {len(tabla)} filas")
        st.dataframe(tabla, hide_index=True, width="stretch", height=250)
        st.download_button(f"Descargar {archivo}", tabla.to_csv(index=False).encode("utf-8"), archivo, "text/csv",
                           key=archivo)
