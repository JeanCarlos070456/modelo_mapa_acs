import pandas as pd
import streamlit as st
import folium
from folium.plugins import HeatMapWithTime, LocateControl, Fullscreen, MousePosition
from streamlit_folium import st_folium

def _map_base(tiles_claros: bool):
    center = [-15.80, -47.90]
    tiles = "CartoDB positron" if tiles_claros else "OpenStreetMap"
    m = folium.Map(location=center, zoom_start=11, tiles=tiles, control_scale=True)
    Fullscreen().add_to(m); LocateControl(auto_start=False).add_to(m)
    MousePosition(position="bottomright", separator=" | ", empty_string="", lng_first=True,
                  num_digits=5, prefix="Coordenadas:").add_to(m)
    return m

def render_timeseries_and_animation(visitas: pd.DataFrame, periodo, tiles_claros: bool):
    st.subheader("9.2 — Visualização temporal")
    mask = (visitas["data_visita"].dt.date >= periodo[0]) & (visitas["data_visita"].dt.date <= periodo[1])
    df = visitas.loc[mask].copy()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**9.2.2 — Série por mês**")
        if not df.empty:
            mens = df.groupby("mes").size().reset_index(name="visitas").sort_values("mes")
            st.line_chart(mens.set_index("mes"))
        else:
            st.info("Sem dados no período.")

    with c2:
        st.markdown("**9.2.3 — Série por semana epidemiológica (SE)**")
        if not df.empty:
            se = df.groupby(["ano","semana_epi"]).size().reset_index(name="visitas")
            se["SE"] = se["ano"].astype(str) + "-SE" + se["semana_epi"].astype(str)
            st.line_chart(se.set_index("SE")["visitas"])
        else:
            st.info("Sem dados no período.")

    with st.expander("9.2.4 — Animação do mapa de calor"):
        m = _map_base(tiles_claros)
        if not df.empty:
            df["dia"] = df["data_visita"].dt.date
            data, idx = [], []
            for dia, g in sorted(df.groupby("dia"), key=lambda x: x[0]):
                pts = g[["latitude","longitude"]].dropna().values.tolist()
                if pts:
                    data.append(pts)
                    idx.append(pd.to_datetime(dia).strftime("%d/%m/%Y"))
            if data:
                HeatMapWithTime(data=data, index=idx, radius=10, auto_play=True, max_opacity=0.8).add_to(m)
        st_folium(m, width=None, height=520)
