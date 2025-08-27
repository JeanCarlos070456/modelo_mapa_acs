import os
import streamlit as st
from core.config import Settings, load_settings
from core.data import load_visitas, load_geojson_layers
from features.map_view import render_spatial_view
from features.timeseries import render_timeseries_and_animation
from features.alerts import render_alerts

st.set_page_config(page_title="Painel de Visitas – ACS", layout="wide")

settings: Settings = load_settings()
st.markdown("<h1 style='margin-bottom:0.2rem;'>Modelo de Mapa de Calor — Visitas ACS (DF)</h1>", unsafe_allow_html=True)
st.caption("Monitoramento diário, territorial e temporal das visitas dos ACS no DF.")

# ======== LOAD DATA/LAYERS ========
visitas = load_visitas(settings.csv_path)
layers  = load_geojson_layers(settings)

# ======== SIDEBAR (filtros) ========
with st.sidebar:
    st.subheader("Filtros")
    dias = sorted(visitas["data"].unique())
    dia_especifico = st.date_input("Dia específico", dias[-1], min_value=dias[0], max_value=dias[-1])
    turno = st.selectbox("Turno", ["integral", "manhã", "tarde"], index=0)

    st.markdown("---")
    data_min = visitas["data_visita"].min().date()
    data_max = visitas["data_visita"].max().date()
    periodo = st.slider("Período (séries & animação)", min_value=data_min, max_value=data_max,
                        value=(max(data_min, data_max), data_max))

    st.markdown("---")
    nivel = st.selectbox("Agregação", ["Distrito Federal", "Região de Saúde", "Região Administrativa", "UBS", "Equipe", "Profissional"])

    st.markdown("---")
    tiles_claros = st.checkbox("Tiles CartoDB Positron", value=True)
    overlay_df   = st.checkbox("Sobrepor DF", value=False, disabled=(layers.df is None))
    overlay_rs   = st.checkbox("Sobrepor Regiões de Saúde", value=(layers.rs is not None))
    overlay_ra   = st.checkbox("Sobrepor Regiões Administrativas", value=False, disabled=(layers.ra is None))
    mostrar_pontos = st.checkbox("Marcadores individuais", value=False)

    st.markdown("---")
    janela = st.selectbox("Áreas sem visita nos últimos…", ["30 dias", "90 dias", "180 dias", "365 dias"])
    limiar_baixo = st.number_input("Baixo volume por ACS (visitas)", min_value=0, value=5, step=1)

# ======== VISUALIZAÇÃO ESPACIAL (mapa + KPI + clique) ========
render_spatial_view(
    visitas=visitas,
    dia_especifico=dia_especifico,
    turno=turno,
    nivel=nivel,
    tiles_claros=tiles_claros,
    overlay_df=overlay_df, overlay_rs=overlay_rs, overlay_ra=overlay_ra,
    layers=layers,
    mostrar_pontos=mostrar_pontos
)

# ======== SÉRIES & ANIMAÇÃO ========
render_timeseries_and_animation(visitas=visitas, periodo=periodo, tiles_claros=tiles_claros)

# ======== ALERTAS ========
render_alerts(visitas=visitas, janela_label=janela, limiar_baixo_mov=limiar_baixo, periodo=periodo)
