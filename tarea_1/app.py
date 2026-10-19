"""Dashboard Tarea 1: clasificador de titulares de noticias peruanas."""
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from transformers import pipeline

BASE = Path(__file__).parent
DATOS = BASE / "datos"

# Modelo: carpeta local modelo/ (no se sube a GitHub por su peso) o, si se define
# MODELO_HF, un repositorio de Hugging Face Hub (útil para Streamlit Cloud)
RUTA_MODELO = BASE / "modelo"
ORIGEN_MODELO = os.environ.get("MODELO_HF") or RUTA_MODELO
ORIGEN_MODELO_DISPONIBLE = "MODELO_HF" in os.environ or (RUTA_MODELO / "config.json").exists()

# Resultados copiados de 02_clasificacion.ipynb (Paso 1 y Paso 5)
F1_MACRO_TEST = 0.82
F1_ZERO_SHOT = 0.64

ETIQUETAS = {
    "politica": "Política",
    "economia": "Economía",
    "deportes": "Deportes",
    "ciencia_tecnologia": "Ciencia y tecnología",
}
COLORES = {
    "Política": "#B2182B",
    "Economía": "#D6604D",
    "Deportes": "#F4A582",
    "Ciencia y tecnología": "#67001F",
}

st.set_page_config(page_title="Clasificador de noticias peruanas", page_icon="🗞️", layout="wide")


@st.cache_data
def cargar_noticias() -> pd.DataFrame:
    return pd.read_csv(DATOS / "noticias.csv", parse_dates=["fecha"])


@st.cache_data
def cargar_auditoria() -> pd.DataFrame:
    return pd.read_csv(DATOS / "auditoria_humana.csv", index_col=0)


noticias = cargar_noticias()
auditoria = cargar_auditoria()

# --- 1. Encabezado y contexto ---
st.title("🗞️ ¿Pueden convertir titulares peruanos en un clasificador de noticias?")
st.markdown(
    f"""
**Resumen metodológico**

1. **Recolección:** {len(noticias)} noticias de *{", ".join(noticias["medio"].unique())}*
   publicadas entre el {noticias["fecha"].min():%d/%m/%Y} y el {noticias["fecha"].max():%d/%m/%Y},
   normalizadas a 4 categorías: política, economía, deportes y ciencia y tecnología.
2. **Línea base zero-shot:** `Recognai/bert-base-spanish-wwm-cased-xnli`, sin entrenamiento
   (F1 macro = {F1_ZERO_SHOT:.2f}).
3. **Supervisión débil:** un LLM local (Qwen2.5-1.5B) etiquetó el dataset completo, con
   auditoría humana de 20 casos.
4. **Fine-tuning:** BETO (`dccuchile/bert-base-spanish-wwm-cased`) con split estratificado
   70/15/15, evaluado sobre el conjunto de test reservado.
"""
)

# --- 2. Filtros en la barra lateral ---
st.sidebar.header("Filtros")
medios = sorted(noticias["medio"].unique())
sel_medios = st.sidebar.multiselect("Medio", medios, default=medios)
sel_categorias = st.sidebar.multiselect(
    "Categoría", list(ETIQUETAS), default=list(ETIQUETAS), format_func=ETIQUETAS.get
)

filtrado = noticias[noticias["medio"].isin(sel_medios) & noticias["etiqueta"].isin(sel_categorias)]
if filtrado.empty:
    st.warning("No hay noticias para los filtros seleccionados.")

# --- 3. Indicadores clave ---
n_acuerdo = int(auditoria["acuerdo"].sum())
c1, c2, c3 = st.columns(3)
c1.metric(
    "Noticias recolectadas", f"{len(noticias):,}",
    delta=f"{len(filtrado)} con los filtros actuales", delta_color="off",
)
c2.metric(
    "F1 macro en test", f"{F1_MACRO_TEST:.2f}",
    delta=f"+{F1_MACRO_TEST - F1_ZERO_SHOT:.2f} vs. zero-shot",
)
c3.metric(
    "Concordancia LLM vs. auditoría humana", f"{n_acuerdo / len(auditoria):.0%}",
    delta=f"{n_acuerdo}/{len(auditoria)} casos", delta_color="off",
)

st.divider()

# --- 4. Visualización y exploración de datos ---
st.subheader("Distribución de categorías")
if not filtrado.empty:
    dist = (filtrado["etiqueta"].map(ETIQUETAS)
            .value_counts()
            .rename_axis("Categoría")
            .reset_index(name="Noticias"))
    dist["Porcentaje"] = dist["Noticias"] / dist["Noticias"].sum()

    # Título analítico: distingue distribución balanceada, empate en el primer lugar o un líder claro
    p_max, p_min = dist["Porcentaje"].max(), dist["Porcentaje"].min()
    lideres = dist.loc[dist["Porcentaje"] == p_max, "Categoría"].tolist()
    if len(dist) > 1 and p_max - p_min <= 0.05:
        titulo = f"Muestra balanceada: cada categoría reúne entre {p_min:.0%} y {p_max:.0%} de las noticias"
    elif len(lideres) > 1:
        titulo = f"{' y '.join(lideres)} lideran con {p_max:.0%} de las noticias cada una"
    else:
        titulo = f"{lideres[0]} concentra el {p_max:.0%} de las noticias filtradas"
    dist = dist.sort_values("Noticias")   # la barra más larga queda arriba

    fig = px.bar(
        dist, x="Noticias", y="Categoría", orientation="h",
        text=dist["Porcentaje"].map("{:.0%}".format),
        color="Categoría", color_discrete_map=COLORES,
        hover_data={"Porcentaje": ":.1%", "Categoría": False},
        title=f"<b>{titulo}</b>",
    )
    fig.update_layout(showlegend=False, title_x=0.5, height=380,
                      xaxis_title="<b>Número de noticias</b>", yaxis_title="<b>Categoría</b>")
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")

st.subheader("Explorar noticias")
tabla = (filtrado.assign(categoria=filtrado["etiqueta"].map(ETIQUETAS))
         [["fecha", "titular", "bajada", "categoria", "seccion_original", "medio", "url"]]
         .sort_values("fecha", ascending=False))
st.dataframe(
    tabla,
    width="stretch",
    hide_index=True,
    column_config={
        "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
        "titular": st.column_config.TextColumn("Titular", width="large"),
        "bajada": st.column_config.TextColumn("Bajada", width="medium"),
        "categoria": "Categoría",
        "seccion_original": "Sección original",
        "medio": "Medio",
        "url": st.column_config.LinkColumn("Enlace", display_text="Abrir"),
    },
)
st.download_button(
    "⬇️ Descargar CSV filtrado",
    data=tabla.to_csv(index=False).encode("utf-8-sig"),   # utf-8-sig: tildes correctas en Excel
    file_name="noticias_filtradas.csv",
    mime="text/csv",
    disabled=tabla.empty,
)

st.divider()

# --- 5. Probador interactivo en vivo ---
st.subheader("🔎 Prueba el clasificador con un titular nuevo")


@st.cache_resource(show_spinner="Cargando el modelo BETO fine-tuned...")
def cargar_clasificador():
    return pipeline("text-classification", model=str(ORIGEN_MODELO), top_k=None, device=-1)


if not ORIGEN_MODELO_DISPONIBLE:
    st.error(
        f"No se encontró el modelo en `{RUTA_MODELO}`. Ejecuta el paso 4 de "
        "`02_clasificacion.ipynb` o define la variable de entorno `MODELO_HF` "
        "con el repositorio del modelo en Hugging Face Hub."
    )
else:
    with st.form("probador"):
        titular = st.text_area(
            "Escribe o pega un titular",
            placeholder="Ej.: BCR reduce su tasa de referencia a 4,25% ante menor inflación",
            height=90,
        )
        enviado = st.form_submit_button("Clasificar", type="primary")

    if enviado:
        if not titular.strip():
            st.warning("Escribe un titular para clasificar.")
        else:
            probs = cargar_clasificador()([titular.strip()], truncation=True, max_length=64)[0]
            probs = (pd.DataFrame(probs)
                     .assign(Categoría=lambda d: d["label"].map(ETIQUETAS))
                     .sort_values("score", ascending=False))
            mejor = probs.iloc[0]

            col_pred, col_graf = st.columns([1, 2])
            col_pred.metric("Categoría predicha", mejor["Categoría"])
            col_pred.metric("Probabilidad", f"{mejor['score']:.1%}")
            if mejor["score"] < 0.6:
                col_pred.caption("⚠️ Confianza baja: el titular podría pertenecer a más de una categoría.")

            fig_prob = px.bar(
                probs.sort_values("score"), x="score", y="Categoría", orientation="h",
                text=probs.sort_values("score")["score"].map("{:.1%}".format),
                color="Categoría", color_discrete_map=COLORES,
                title="<b>Probabilidad por categoría</b>",
            )
            fig_prob.update_layout(showlegend=False, title_x=0.5, height=300,
                                   xaxis=dict(title="<b>Probabilidad</b>", tickformat=".0%", range=[0, 1.1]),
                                   yaxis_title=None)
            fig_prob.update_traces(textposition="outside", cliponaxis=False)
            col_graf.plotly_chart(fig_prob, width="stretch")
