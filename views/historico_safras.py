"""
views/historico_safras.py — Histórico de Safras.

Fonte: planilha dedicada (data_loader.GOOGLE_SHEET_HISTORICO_ID), com o ATR
cruzado da aba BASEATR da planilha principal por Fazenda (+ Safra, quando
disponível nas duas). Colunas exibidas: Fazenda | Setor | Safra | Toneladas
| TCH | ATR | Área Colhida.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import get_data, get_historico_safras, enrich_historico_com_atr, milhar_config
from src.theme import inject_theme

inject_theme()
st.title("📜 Histórico de Safras")
st.caption(
    "Fonte: planilha dedicada de histórico de safras, cruzada com o ATR da "
    "planilha principal (aba BASEATR) por Fazenda."
)

historico = get_historico_safras()

if historico.empty:
    st.warning(
        "Não foi possível ler a planilha de Histórico de Safras. Verifique se "
        "o link está compartilhado como 'Qualquer pessoa com o link' (leitor), "
        "e se ela tem as colunas Fazenda, Setor, Safra, Toneladas, TCH e Área Colhida."
    )
    st.stop()

atr = get_data().get("atr", pd.DataFrame())
historico = enrich_historico_com_atr(historico, atr)

colunas_esperadas = ["Fazenda", "Setor", "Safra", "Toneladas", "TCH", "ATR", "Área Colhida"]
colunas_presentes = [c for c in colunas_esperadas if c in historico.columns]
faltando = [c for c in colunas_esperadas if c not in historico.columns]
if faltando:
    st.info(
        f"Colunas não encontradas na planilha (verifique o nome exato): {', '.join(faltando)}. "
        "Exibindo as colunas disponíveis."
    )

st.sidebar.markdown("### Filtros — Histórico de Safras")
safras = sorted(historico["Safra"].dropna().unique().tolist()) if "Safra" in historico.columns else []
setores = sorted(historico["Setor"].dropna().unique().tolist()) if "Setor" in historico.columns else []
fazendas = sorted(historico["Fazenda"].dropna().unique().tolist()) if "Fazenda" in historico.columns else []

f_safra = st.sidebar.multiselect("Safra", safras, default=safras) if safras else []
f_setor = st.sidebar.multiselect("Setor", setores, default=setores) if setores else []
f_fazenda = st.sidebar.multiselect("Fazenda", fazendas, default=fazendas) if fazendas else []

filtrado = historico.copy()
if safras:
    filtrado = filtrado[filtrado["Safra"].isin(f_safra)]
if setores:
    filtrado = filtrado[filtrado["Setor"].isin(f_setor)]
if fazendas:
    filtrado = filtrado[filtrado["Fazenda"].isin(f_fazenda)]

c1, c2, c3, c4 = st.columns(4)
if "Toneladas" in filtrado.columns:
    c1.metric("Toneladas Total", f"{filtrado['Toneladas'].sum():,.0f}")
if "TCH" in filtrado.columns:
    c2.metric("TCH Médio", f"{filtrado['TCH'].mean():,.3f}" if not filtrado.empty else "—")
if "ATR" in filtrado.columns:
    c3.metric("ATR Médio", f"{filtrado['ATR'].mean():,.2f}" if filtrado["ATR"].notna().any() else "—")
if "Área Colhida" in filtrado.columns:
    c4.metric("Área Colhida Total (ha)", f"{filtrado['Área Colhida'].sum():,.2f}")

st.divider()

if "Safra" in filtrado.columns and "Toneladas" in filtrado.columns:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Toneladas por Safra")
        g = filtrado.groupby("Safra", as_index=False)["Toneladas"].sum()
        fig = px.bar(g, x="Safra", y="Toneladas", text_auto=",.0f", template="plotly_dark")
        fig.update_traces(textposition="outside")
        fig.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        if "TCH" in filtrado.columns:
            st.subheader("TCH Médio por Safra")
            g2 = filtrado.groupby("Safra", as_index=False)["TCH"].mean()
            fig2 = px.line(g2, x="Safra", y="TCH", markers=True, template="plotly_dark")
            fig2.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Detalhe por Fazenda")
st.dataframe(
    filtrado[colunas_presentes] if colunas_presentes else filtrado,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(
        [c for c in ["Toneladas", "TCH", "ATR", "Área Colhida"] if c in filtrado.columns], decimals=2
    ),
)
