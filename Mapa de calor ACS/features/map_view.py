import numpy as np
import pandas as pd
import streamlit as st
import folium
from folium.plugins import HeatMap, LocateControl, Fullscreen, MousePosition
from streamlit_folium import st_folium
from typing import Dict
from core.data import Layers

def _map_base(tiles_claros: bool):
    center = [-15.80, -47.90]
    tiles = "CartoDB positron" if tiles_claros else "OpenStreetMap"
    m = folium.Map(location=center, zoom_start=11, tiles=tiles, control_scale=True)
    Fullscreen().add_to(m)
    LocateControl(auto_start=False).add_to(m)
    MousePosition(position="bottomright", separator=" | ", empty_string="", lng_first=True,
                  num_digits=5, prefix="Coordenadas:").add_to(m)
    return m

def _add_geojson(m, data, name, color, weight=2):
    if not data: return
    folium.GeoJson(data=data, name=name,
                   style_function=lambda _:{'fill':False,'color':color,'weight':weight}).add_to(m)

def _group_counts(df, nivel: str) -> pd.DataFrame:
    if df.empty: return pd.DataFrame(columns=[nivel, "visitas"])
    chave = {"Distrito Federal":None,"Região de Saúde":"RegiaoSaude","Região Administrativa":"RA",
             "UBS":"UBS","Equipe":"Equipe","Profissional":"Profissional"}[nivel]
    if chave is None: return pd.DataFrame({nivel:["DF"],"visitas":[len(df)]})
    if chave not in df.columns: return pd.DataFrame({nivel:["(sem dado)"],"visitas":[len(df)]})
    out = df.groupby(chave).size().reset_index(name="visitas").rename(columns={chave:nivel})
    return out.sort_values("visitas", ascending=False)

def render_spatial_view(visitas: pd.DataFrame, dia_especifico, turno: str, nivel: str,
                        tiles_claros: bool, overlay_df: bool, overlay_rs: bool, overlay_ra: bool,
                        layers: Layers, mostrar_pontos: bool):
    df_dia = visitas[(visitas["data"] == pd.to_datetime(dia_especifico).date()) &
                     ((visitas["turno"] == turno) if turno != "integral" else visitas["turno"].isin(["manhã","tarde","integral"]))].copy()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Visitas no dia/turno", f"{len(df_dia):,}".replace(",", "."))
    k2.metric("ACS únicos", f"{df_dia['ACS'].nunique():,}".replace(",", "."))
    k3.metric("UBS únicas", f"{df_dia['UBS'].nunique():,}".replace(",", "."))
    k4.metric("Agregação", nivel)

    st.subheader("9.1 — Visualização espacial")
    m = _map_base(tiles_claros)

    if overlay_df and layers.df: _add_geojson(m, layers.df, "DF", "#111")
    if overlay_rs and layers.rs: _add_geojson(m, layers.rs, "Regiões de Saúde", "#d62728")
    if overlay_ra and layers.ra: _add_geojson(m, layers.ra, "Regiões Administrativas", "#1f77b4", weight=1.5)

    pts = df_dia[["latitude","longitude"]].dropna()
    if not pts.empty:
        HeatMap(pts.values.tolist(), radius=12, blur=16, max_zoom=13).add_to(m)

    if mostrar_pontos and not df_dia.empty:
        for _, r in df_dia.iterrows():
            hora_txt = r["hora"].strftime("%H:%M") if pd.notnull(r.get("hora", None)) else "—"
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]], radius=4, weight=1, fill=True,
                popup=folium.Popup(
                    f"<b>Data:</b> {pd.to_datetime(r['data_visita']).strftime('%d/%m/%Y')}<br>"
                    f"<b>Hora:</b> {hora_txt}<br><b>ACS:</b> {r.get('ACS','')}<br><b>UBS:</b> {r.get('UBS','')}",
                    max_width=280),
            ).add_to(m)

    ret = st_folium(m, width=None, height=540)

    st.caption("9.4 — Clique no mapa para identificar a visita mais próxima (≤100 m).")
    if ret and ret.get("last_clicked") and not df_dia.empty:
        lat_c = ret["last_clicked"]["lat"]
        lon_c = ret["last_clicked"]["lng"]

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371000.0
            p1, p2 = np.radians(lat1), np.radians(lat2)
            dphi = np.radians(lat2 - lat1)
            dl   = np.radians(lon2 - lon1)
            a = np.sin(dphi/2)**2 + np.cos(p1)*np.cos(p2)*np.sin(dl/2)**2
            return 2*R*np.arcsin(np.sqrt(a))

        df_dia = df_dia.copy()
        df_dia["dist_m"] = haversine(lat_c, lon_c, df_dia["latitude"].values, df_dia["longitude"].values)
        nearest = df_dia.sort_values("dist_m").head(1)
        if not nearest.empty and nearest.iloc[0]["dist_m"] <= 100:
            r = nearest.iloc[0]
            hora_txt = r["hora"].strftime("%H:%M") if pd.notnull(r.get("hora", None)) else "—"
            st.success(f"Visita a {r['dist_m']:.0f} m — {pd.to_datetime(r['data_visita']):%d/%m/%Y} às {hora_txt} | ACS: {r['ACS']} | UBS: {r['UBS']}")
            st.dataframe(nearest.drop(columns=["dist_m"]))
        else:
            st.info("Nenhuma visita dentro de 100 m.")

    st.markdown("**9.1.2 — Agregação (contagens no dia/turno)**")
    st.dataframe(_group_counts(df_dia, nivel), use_container_width=True)
