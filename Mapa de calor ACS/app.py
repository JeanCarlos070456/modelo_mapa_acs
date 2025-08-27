# app.py — Painel de Visitas dos ACS (estável p/ Streamlit Cloud)
import os
from datetime import timedelta
import numpy as np
import pandas as pd
import streamlit as st
import folium
from folium.plugins import HeatMap, HeatMapWithTime, LocateControl, Fullscreen, MousePosition
from streamlit_folium import st_folium

# =========================
# ======= CONFIG ==========
# =========================
st.set_page_config(page_title="Painel de Visitas – ACS", layout="wide")
st.markdown("<h1 style='margin-bottom:0.2rem;'>Mapa de Calor das Visitas — ACS (DF)</h1>", unsafe_allow_html=True)
st.caption("Monitoramento diário, territorial e temporal das visitas dos ACS no DF.")

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
CSV_PATH  = os.path.join(DATA_DIR, "visitas_acs.csv")
STYLE_CSS = os.path.join(BASE_DIR, "styles", "style.css")

def local_css(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
local_css(STYLE_CSS)

# =========================
# ======= LOADERS =========
# =========================
@st.cache_data(show_spinner=True)
def load_csv_visitas(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        st.error("CSV não encontrado em data/visitas_acs.csv")
        st.stop()
    df = pd.read_csv(path)

    # Normalização de nomes
    rename_map = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl in ["data_visita", "data", "dt_visita", "dia", "date"]:
            rename_map[c] = "data_visita"
        elif cl in ["hora", "horario", "time"]:
            rename_map[c] = "hora"
        elif cl in ["latitude", "lat", "y"]:
            rename_map[c] = "latitude"
        elif cl in ["longitude", "lon", "long", "x"]:
            rename_map[c] = "longitude"
        elif cl in ["ubs", "unidade", "estabelecimento"]:
            rename_map[c] = "UBS"
        elif cl in ["acs", "agente", "agente_comunitario"]:
            rename_map[c] = "ACS"
        elif cl in ["equipe", "equipe_saude", "eqp"]:
            rename_map[c] = "Equipe"
        elif cl in ["profissional", "servidor", "colaborador"]:
            rename_map[c] = "Profissional"
        elif cl in ["regiaosaude", "regiao_saude", "rs"]:
            rename_map[c] = "RegiaoSaude"
        elif cl in ["ra", "regiaoadm", "regiao_administrativa"]:
            rename_map[c] = "RA"
    df = df.rename(columns=rename_map)

    # Campos essenciais
    required = ["data_visita", "latitude", "longitude", "UBS", "ACS"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Colunas obrigatórias ausentes no CSV: {missing}")
        st.stop()

    # Tipos
    df["data_visita"] = pd.to_datetime(df["data_visita"], errors="coerce")
    df["latitude"]  = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    if "hora" in df.columns:
        try:
            df["hora"] = pd.to_datetime(df["hora"], errors="coerce").dt.time
        except Exception:
            df["hora"] = pd.to_datetime(df["hora"], errors="coerce", format="%H:%M").dt.time

    df = df.dropna(subset=["data_visita", "latitude", "longitude"]).copy()

    # Turno
    def infer_turno(row):
        if pd.notnull(row.get("hora", None)):
            h = row["hora"].hour
        else:
            return "integral"
        if 5 <= h <= 11:  return "manhã"
        if 12 <= h <= 17: return "tarde"
        return "integral"

    df["turno"] = df.apply(infer_turno, axis=1)

    # Chaves temporais
    df["data"] = df["data_visita"].dt.date
    iso = df["data_visita"].dt.isocalendar()
    df["ano"] = iso.year
    df["semana_epi"] = iso.week
    df["mes"] = df["data_visita"].dt.to_period("M").astype(str)

    return df.sort_values("data_visita").reset_index(drop=True)

@st.cache_data(show_spinner=False)
def load_geojson(path: str):
    import json
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

visitas = load_csv_visitas(CSV_PATH)

# Camadas territoriais (opcional)
territorio_df = load_geojson(os.path.join(DATA_DIR, "territorio_df.geojson"))
regioes_saude = load_geojson(os.path.join(DATA_DIR, "regioes_saude.geojson"))   # campo: RegiaoSaude
regioes_adm   = load_geojson(os.path.join(DATA_DIR, "regioes_adm.geojson"))     # campo: RA

# =========================
# ======= SIDEBAR =========
# =========================
with st.sidebar:
    st.subheader("Filtros")
    dias_disponiveis = sorted(visitas["data"].unique())
    # defaults seguros
    dia_default = dias_disponiveis[-1] if dias_disponiveis else None
    dia_especifico = st.date_input("Dia específico", value=dia_default,
                                   min_value=dias_disponiveis[0] if dias_disponiveis else None,
                                   max_value=dias_disponiveis[-1] if dias_disponiveis else None)
    turno = st.selectbox("Turno", ["integral", "manhã", "tarde"], index=0)

    st.markdown("---")
    data_max = visitas["data_visita"].max().date()
    data_min = visitas["data_visita"].min().date()
    default_ini = max(data_min, data_max - timedelta(days=30))
    periodo = st.slider("Período (séries & animação)", min_value=data_min, max_value=data_max,
                        value=(default_ini, data_max))

    st.markdown("---")
    nivel = st.selectbox("Agregação", ["Distrito Federal", "Região de Saúde", "Região Administrativa", "UBS", "Equipe", "Profissional"])

    st.markdown("---")
    tiles_claros = st.checkbox("Tiles CartoDB Positron", value=True)
    overlay_df   = st.checkbox("Sobrepor DF", value=False, disabled=(territorio_df is None))
    overlay_rs   = st.checkbox("Sobrepor Regiões de Saúde", value=(regioes_saude is not None))
    overlay_ra   = st.checkbox("Sobrepor Regiões Administrativas", value=False, disabled=(regioes_adm is None))
    mostrar_pontos = st.checkbox("Marcadores individuais", value=False)

    st.markdown("---")
    dias_lookup = {"30 dias": 30, "90 dias": 90, "180 dias": 180, "365 dias": 365}
    janela_alerta_label = st.selectbox("Áreas sem visita nos últimos…", list(dias_lookup.keys()), index=0)
    limiar_baixo_mov = st.number_input("Baixo volume por ACS (visitas)", min_value=0, value=5, step=1)

# =========================
# ======= KPI HEADER ======
# =========================
mask_dia = visitas["data"] == pd.to_datetime(dia_especifico).date() if dia_especifico else False
mask_turno = (visitas["turno"] == turno) if turno != "integral" else visitas["turno"].isin(["manhã", "tarde", "integral"])
df_dia = visitas.loc[mask_dia & mask_turno].copy() if dia_especifico else visitas.head(0).copy()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Visitas no dia/turno", f"{len(df_dia):,}".replace(",", "."))
k2.metric("ACS únicos", f"{df_dia['ACS'].nunique():,}".replace(",", "."))
k3.metric("UBS únicas", f"{df_dia['UBS'].nunique():,}".replace(",", "."))
k4.metric("Agregação", nivel)

# =========================
# ======= MAPA PRINC. =====
# =========================
def mapa_base():
    center = [-15.80, -47.90]  # DF
    tiles = "CartoDB positron" if tiles_claros else "OpenStreetMap"
    m = folium.Map(location=center, zoom_start=11, tiles=tiles, control_scale=True)
    Fullscreen().add_to(m)
    LocateControl(auto_start=False).add_to(m)
    MousePosition(position="bottomright", separator=" | ", empty_string="", lng_first=True, num_digits=5,
                  prefix="Coordenadas:").add_to(m)
    return m

def add_geojson(m, data, name, style):
    if not data:
        return
    gj = folium.GeoJson(data=data, name=name, style_function=lambda _ : style)
    gj.add_to(m)

def group_counts(df, nivel: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[nivel, "visitas"])
    chave = {
        "Distrito Federal": None,
        "Região de Saúde": "RegiaoSaude",
        "Região Administrativa": "RA",
        "UBS": "UBS",
        "Equipe": "Equipe",
        "Profissional": "Profissional"
    }[nivel]
    if chave is None:
        return pd.DataFrame({nivel: ["DF"], "visitas": [len(df)]})
    if chave not in df.columns:
        return pd.DataFrame({nivel: ["(sem dado)"], "visitas": [len(df)]})
    tmp = df.groupby(chave).size().reset_index(name="visitas").rename(columns={chave: nivel})
    return tmp.sort_values("visitas", ascending=False)

st.subheader("9.1 — Visualização espacial")
m = mapa_base()

# Sobreposições (sempre nomes distintos)
if overlay_df and territorio_df:
    add_geojson(m, territorio_df, "DF", {"fill": False, "color": "#111", "weight": 2})
if overlay_rs and regioes_saude:
    add_geojson(m, regioes_saude, "Regiões de Saúde", {"fill": False, "color": "#d62728", "weight": 2})
if overlay_ra and regioes_adm:
    add_geojson(m, regioes_adm, "Regiões Administrativas", {"fill": False, "color": "#1f77b4", "weight": 1.5})

# Heatmap do dia/turno
pts = df_dia[["latitude", "longitude"]].dropna()
if not pts.empty:
    HeatMap(pts.values.tolist(), radius=12, blur=16, max_zoom=13).add_to(m)

# Marcadores (opcional)
if mostrar_pontos and not df_dia.empty:
    for _, r in df_dia.iterrows():
        dt = pd.to_datetime(r["data_visita"])
        hora_txt = r["hora"].strftime("%H:%M") if pd.notnull(r.get("hora", None)) else "—"
        popup = folium.Popup(
            f"<b>Data:</b> {dt:%d/%m/%Y}<br>"
            f"<b>Hora:</b> {hora_txt}<br>"
            f"<b>ACS:</b> {r.get('ACS','')}<br>"
            f"<b>UBS:</b> {r.get('UBS','')}",
            max_width=280
        )
        folium.CircleMarker(location=[r["latitude"], r["longitude"]], radius=4, weight=1, fill=True, popup=popup).add_to(m)

# ----- RENDER ESTÁVEL (sempre mapa; key fixa) -----
map_main_placeholder = st.empty()
with map_main_placeholder.container():
    ret = st_folium(m, width=None, height=540, key="map_main")

# 9.1.2 — Agregação
st.markdown("**9.1.2 — Agregação (contagens no dia/turno)**")
st.dataframe(group_counts(df_dia, nivel), use_container_width=True)

# 9.4 — Clique no mapa (≤100 m)
st.caption("9.4 — Clique no mapa para identificar a visita mais próxima (até 100 m).")
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

    df_tmp = df_dia.copy()
    df_tmp["dist_m"] = haversine(lat_c, lon_c, df_tmp["latitude"].values, df_tmp["longitude"].values)
    nearest = df_tmp.sort_values("dist_m").head(1)
    if not nearest.empty and nearest.iloc[0]["dist_m"] <= 100:
        r = nearest.iloc[0]
        dt = pd.to_datetime(r["data_visita"])
        hora_txt = r["hora"].strftime("%H:%M") if pd.notnull(r.get("hora", None)) else "—"
        st.success(f"Visita mais próxima a {r['dist_m']:.0f} m — {dt:%d/%m/%Y} às {hora_txt} | ACS: {r['ACS']} | UBS: {r['UBS']}")
        st.dataframe(nearest.drop(columns=["dist_m"]))
    else:
        st.info("Nenhuma visita dentro de 100 m do clique.")

# =========================
# ======= SÉRIES ==========
# =========================
st.subheader("9.2 — Visualização temporal")

mask_periodo = (visitas["data_visita"].dt.date >= periodo[0]) & (visitas["data_visita"].dt.date <= periodo[1])
visitas_periodo = visitas.loc[mask_periodo].copy()

colA, colB = st.columns(2)
with colA:
    st.markdown("**9.2.2 — Série por mês**")
    if not visitas_periodo.empty:
        mens = visitas_periodo.groupby("mes").size().reset_index(name="visitas").sort_values("mes")
        st.line_chart(mens.set_index("mes"))
    else:
        st.info("Sem dados no período.")

with colB:
    st.markdown("**9.2.3 — Série por semana epidemiológica (SE)**")
    if not visitas_periodo.empty:
        se = visitas_periodo.groupby(["ano", "semana_epi"]).size().reset_index(name="visitas")
        se["SE"] = se["ano"].astype(str) + "-SE" + se["semana_epi"].astype(str)
        st.line_chart(se.set_index("SE")["visitas"])
    else:
        st.info("Sem dados no período.")

# 9.2.4 — Animação temporal (sempre renderiza um mapa; key fixa)
with st.expander("9.2.4 — Ver animação do mapa de calor (linha do tempo)"):
    m_anim = mapa_base()
    df_tmp = visitas_periodo.copy()
    if not df_tmp.empty:
        df_tmp["dia"] = df_tmp["data_visita"].dt.date
        dados, idx = [], []
        for dia, g in sorted(df_tmp.groupby("dia"), key=lambda x: x[0]):
            pts2 = g[["latitude", "longitude"]].dropna().values.tolist()
            if pts2:
                dados.append(pts2)
                idx.append(pd.to_datetime(dia).strftime("%d/%m/%Y"))
        if dados:
            HeatMapWithTime(data=dados, index=idx, radius=10, auto_play=True, max_opacity=0.8,
                            use_local_extrema=False, name="Mapa Temporal").add_to(m_anim)
            folium.LayerControl(collapsed=True).add_to(m_anim)

    # ----- RENDER ESTÁVEL (sempre mapa; key fixa) -----
    st_folium(m_anim, width=None, height=520, key="map_time")

# =========================
# ======= ALERTAS =========
# =========================
st.subheader("9.3 — Alertas inteligentes")

def areas_sem_visita(df: pd.DataFrame, corte: pd.Timestamp):
    """
    Retorna (faltantes, chave) — chave: 'RA', 'RegiaoSaude' ou None
    """
    chave = "RA" if "RA" in df.columns else ("RegiaoSaude" if "RegiaoSaude" in df.columns else None)
    if chave is None:
        return [], None
    universo = df[chave].dropna().astype(str).str.strip().unique().tolist()
    if not universo:
        return [], chave
    recentes = df[df["data_visita"] >= corte]
    com_visita = recentes[chave].dropna().astype(str).str.strip().unique().tolist()
    faltantes = [a for a in universo if a not in com_visita]
    return faltantes, chave

dias_lookup = {"30 dias": 30, "90 dias": 90, "180 dias": 180, "365 dias": 365}
dias_sem = dias_lookup[janela_alerta_label]
corte = visitas["data_visita"].max() - timedelta(days=dias_sem)

faltantes, chave_area = areas_sem_visita(visitas, corte)
if chave_area is None:
    st.info("Para os alertas por área, inclua uma coluna 'RA' ou 'RegiaoSaude' no CSV.")
elif faltantes:
    st.warning(f"Áreas sem visita nos últimos {dias_sem} dias ({chave_area}):")
    st.write(", ".join(faltantes))
else:
    st.success(f"Todas as áreas ({chave_area}) tiveram ao menos uma visita nos últimos {dias_sem} dias.")

# 9.3.5 — ACS com baixo volume no período
vol = visitas_periodo.groupby("ACS").size().reset_index(name="visitas")
baixo = vol[vol["visitas"] <= limiar_baixo_mov]
if not baixo.empty:
    st.warning(f"ACS com baixo volume (≤ {limiar_baixo_mov} visitas no período):")
    st.dataframe(baixo.sort_values("visitas"))
else:
    st.success("Nenhum ACS com baixo volume no período.")

# ====== FIM ======

