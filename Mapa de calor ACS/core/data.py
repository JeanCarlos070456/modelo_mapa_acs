import json, os
import pandas as pd
import streamlit as st
from dataclasses import dataclass
from typing import Optional
from .config import Settings

@st.cache_data(show_spinner=True)
def load_visitas(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        st.error("CSV não encontrado em data/visitas_acs.csv")
        st.stop()
    df = pd.read_csv(csv_path)

    # normalização de nomes
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

    # campos essenciais
    required = ["data_visita", "latitude", "longitude", "UBS", "ACS"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Colunas obrigatórias ausentes: {missing}")
        st.stop()

    # tipos + derivados
    df["data_visita"] = pd.to_datetime(df["data_visita"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    if "hora" in df.columns:
        try:
            df["hora"] = pd.to_datetime(df["hora"], errors="coerce").dt.time
        except Exception:
            df["hora"] = pd.to_datetime(df["hora"], format="%H:%M", errors="coerce").dt.time

    df = df.dropna(subset=["data_visita", "latitude", "longitude"]).copy()

    def infer_turno(row):
        if pd.notnull(row.get("hora", None)):
            h = row["hora"].hour
        else:
            return "integral"
        if 5 <= h <= 11: return "manhã"
        if 12 <= h <= 17: return "tarde"
        return "integral"

    df["turno"] = df.apply(infer_turno, axis=1)
    df["data"] = df["data_visita"].dt.date
    iso = df["data_visita"].dt.isocalendar()
    df["ano"] = iso.year
    df["semana_epi"] = iso.week
    df["mes"] = df["data_visita"].dt.to_period("M").astype(str)
    return df.sort_values("data_visita").reset_index(drop=True)

@dataclass
class Layers:
    df: Optional[dict]
    rs: Optional[dict]
    ra: Optional[dict]

@st.cache_data(show_spinner=False)
def _load_geojson(path: str):
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_geojson_layers(settings: Settings) -> Layers:
    return Layers(
        df=_load_geojson(settings.territorio_df),
        rs=_load_geojson(settings.regioes_saude),
        ra=_load_geojson(settings.regioes_adm),
    )
