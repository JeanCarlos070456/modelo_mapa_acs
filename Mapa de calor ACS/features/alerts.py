import pandas as pd
import streamlit as st
from datetime import timedelta

def _areas_sem_visita(df: pd.DataFrame, corte):
    chave = "RA" if "RA" in df.columns else ("RegiaoSaude" if "RegiaoSaude" in df.columns else None)
    if chave is None: return [], None
    universo = (df[chave].dropna().astype(str).str.strip().unique().tolist())
    if not universo: return [], chave
    recentes = df[df["data_visita"] >= corte]
    com_visita = (recentes[chave].dropna().astype(str).str.strip().unique().tolist())
    faltantes = [a for a in universo if a not in com_visita]
    return faltantes, chave

def render_alerts(visitas: pd.DataFrame, janela_label: str, limiar_baixo_mov: int, periodo):
    st.subheader("9.3 — Alertas inteligentes")
    dias_lookup = {"30 dias":30, "90 dias":90, "180 dias":180, "365 dias":365}
    dias = dias_lookup[janela_label]
    corte = visitas["data_visita"].max() - timedelta(days=dias)

    faltantes, chave_area = _areas_sem_visita(visitas, corte)
    if chave_area is None:
        st.info("Inclua coluna 'RA' ou 'RegiaoSaude' no CSV para alertas por área.")
    elif faltantes:
        st.warning(f"Áreas sem visita nos últimos {dias} dias ({chave_area}):")
        st.write(", ".join(faltantes))
    else:
        st.success(f"Todas as áreas ({chave_area}) tiveram ao menos uma visita nos últimos {dias} dias.")

    mask = (visitas["data_visita"].dt.date >= periodo[0]) & (visitas["data_visita"].dt.date <= periodo[1])
    dfp = visitas.loc[mask]
    vol = dfp.groupby("ACS").size().reset_index(name="visitas")
    baixo = vol[vol["visitas"] <= limiar_baixo_mov]
    if not baixo.empty:
        st.warning(f"ACS com baixo volume (≤ {limiar_baixo_mov} visitas no período):")
        st.dataframe(baixo.sort_values("visitas"))
    else:
        st.success("Nenhum ACS com baixo volume no período.")

