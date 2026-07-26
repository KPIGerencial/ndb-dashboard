"""
views/historico_safras.py — Histórico de Safras.

Fonte: planilha dedicada (GOOGLE_SHEET_HISTORICO_ID), uma aba por safra
(2026, 2025, 2024, 2023...). O ATR é cruzado da aba BASEATR/BASEART da
planilha principal por Fazenda + Safra (ano da Data Produção) — nunca
misturando leituras de anos diferentes na mesma média.

Duas visões:
- Padrão (nenhuma fazenda buscada): agrupado por Fazenda, somando/mediando
  todas as safras selecionadas no filtro.
- Fazenda específica (buscada no campo de busca): quebra ano a ano
  (Safra | Toneladas | TCH | Área Colhida), ignorando o filtro de Safra —
  sempre mostra o histórico completo da fazenda escolhida.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import (
    get_data,
    get_historico_safras,
    enrich_historico_com_atr,
    agrupar_historico_por_fazenda,
    agrupar_historico_por_safra,
    milhar_config,
)
from src.theme import inject_theme

inject_theme()
st.title("📜 Histórico de Safras")
st.caption(
    "Fonte: planilha dedicada de histórico de safras (uma aba por ano), cruzada com "
    "o ATR da planilha principal (aba BASEATR/BASEART) por Fazenda + Safra."
)

historico = get_historico_safras()

if historico.empty:
    st.warning(
        "Não foi possível ler a planilha de Histórico de Safras — ou nenhuma aba com "
        "nome de ano (ex: 2026, 2025...) tem as colunas Fazenda, Toneladas, TCH e "
        "Área Colhida preenchidas. Verifique se o link está compartilhado como "
        "'Qualquer pessoa com o link' (leitor)."
    )
    st.stop()

atr = get_data().get("atr", pd.DataFrame())
historico = enrich_historico_com_atr(historico, atr)

# --------------------------------------------------------------------------
# Filtros
# --------------------------------------------------------------------------
st.sidebar.markdown("### Filtros — Histórico de Safras")

safras = sorted(historico["Safra"].dropna().unique().tolist(), reverse=True) if "Safra" in historico.columns else []
f_safra = st.sidebar.multiselect("Safra", safras, default=safras) if safras else []

setores = sorted(historico["Setor"].dropna().unique().tolist()) if "Setor" in historico.columns else []
f_setor = st.sidebar.multiselect("Setor", setores, default=setores) if setores else []

# Campo de busca por Fazenda — digitar filtra a lista (comportamento nativo
# do selectbox do Streamlit). Padrão "Todas": não restringe nada.
fazendas = sorted(historico["Fazenda"].dropna().unique().tolist()) if "Fazenda" in historico.columns else []
fazenda_escolhida = st.sidebar.selectbox("Buscar Fazenda", ["Todas as Fazendas"] + fazendas, index=0)

base = historico.copy()
if setores:
    base = base[base["Setor"].isin(f_setor)]

# --------------------------------------------------------------------------
# Visão 1: uma Fazenda específica — quebra ano a ano, TODAS as safras
# (ignora o filtro de Safra de propósito: "mostrar dados de todas as safras
# da fazenda específica").
# --------------------------------------------------------------------------
if fazenda_escolhida != "Todas as Fazendas":
    st.subheader(f"🌾 {fazenda_escolhida} — histórico por safra")

    dados_fazenda = base[base["Fazenda"] == fazenda_escolhida]
    por_safra = agrupar_historico_por_safra(dados_fazenda)

    if por_safra.empty:
        st.info("Sem dados para esta fazenda.")
        st.stop()

    colunas_kpi = st.columns(4)
    colunas_kpi[0].metric("Toneladas Total (todas as safras)", f"{por_safra['Toneladas'].sum():,.0f}")
    if "TCH" in por_safra.columns:
        colunas_kpi[1].metric("TCH Médio (todas as safras)", f"{por_safra['TCH'].mean():,.2f}")
    if "Área Colhida" in por_safra.columns:
        colunas_kpi[2].metric("Área Colhida Média/Safra (ha)", f"{por_safra['Área Colhida'].mean():,.2f}")
    if "ATR" in por_safra.columns and por_safra["ATR"].notna().any():
        colunas_kpi[3].metric("ATR Médio (todas as safras)", f"{por_safra['ATR'].mean():,.2f}")

    # Δ da safra mais recente vs a anterior — leitura rápida de tendência.
    if len(por_safra) >= 2:
        atual, anterior = por_safra.iloc[0], por_safra.iloc[1]
        delta_ton = ((atual["Toneladas"] - anterior["Toneladas"]) / anterior["Toneladas"] * 100) if anterior["Toneladas"] else None
        if delta_ton is not None:
            st.caption(
                f"Safra {int(atual['Safra'])} vs {int(anterior['Safra'])}: "
                f"{'+' if delta_ton >= 0 else ''}{delta_ton:,.1f}% em Toneladas."
            )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Toneladas por Safra")
        g = por_safra.sort_values("Safra")
        fig = px.bar(g, x="Safra", y="Toneladas", text_auto=",.0f", template="plotly_dark")
        fig.update_traces(textposition="outside")
        fig.update_xaxes(type="category")
        fig.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("TCH Médio por Safra")
        g2 = por_safra.sort_values("Safra")
        fig2 = px.line(g2, x="Safra", y="TCH", markers=True, template="plotly_dark")
        fig2.update_xaxes(type="category")
        fig2.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Toneladas | TCH | Área Colhida por Safra")
    colunas_tabela = ["Safra", "Toneladas", "TCH", "Área Colhida"] + (["ATR"] if "ATR" in por_safra.columns else [])
    st.dataframe(
        por_safra[colunas_tabela],
        use_container_width=True,
        hide_index=True,
        column_config=milhar_config(["Toneladas", "TCH", "Área Colhida", "ATR"], decimals=2),
    )

    with st.expander("Detalhe por Setor, dentro desta Fazenda"):
        st.dataframe(
            dados_fazenda.sort_values("Safra", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config=milhar_config(["Toneladas", "TCH", "Área Colhida", "ATR"], decimals=2),
        )

# --------------------------------------------------------------------------
# Visão 2: todas as Fazendas, agrupado — respeita o filtro de Safra.
# --------------------------------------------------------------------------
else:
    filtrado = base[base["Safra"].isin(f_safra)] if f_safra else base
    agrupado = agrupar_historico_por_fazenda(filtrado)

    if agrupado.empty:
        st.info("Sem dados para os filtros selecionados.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toneladas Total", f"{agrupado['Toneladas'].sum():,.0f}")
    if "TCH" in agrupado.columns:
        c2.metric("TCH Médio", f"{agrupado['TCH'].mean():,.2f}")
    if "Área Colhida" in agrupado.columns:
        c3.metric("Área Colhida Total (ha)", f"{agrupado['Área Colhida'].sum():,.2f}")
    if "ATR" in agrupado.columns and agrupado["ATR"].notna().any():
        c4.metric("ATR Médio", f"{agrupado['ATR'].mean():,.2f}")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Top 10 Fazendas por Toneladas")
        top10 = agrupado.head(10)
        fig = px.bar(top10, x="Fazenda", y="Toneladas", text_auto=",.0f", template="plotly_dark")
        fig.update_traces(textposition="outside")
        fig.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Toneladas Total por Safra")
        if "Safra" in filtrado.columns:
            por_ano = agrupar_historico_por_safra(filtrado)
            fig2 = px.bar(por_ano.sort_values("Safra"), x="Safra", y="Toneladas", text_auto=",.0f", template="plotly_dark")
            fig2.update_traces(textposition="outside")
            fig2.update_xaxes(type="category")
            fig2.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Todas as Fazendas — agrupado pelas safras selecionadas")
    st.caption("Use o campo \"Buscar Fazenda\" na barra lateral para ver o histórico ano a ano de uma fazenda específica.")
    colunas_tabela = ["Fazenda", "Toneladas", "TCH", "Área Colhida"] + (["ATR"] if "ATR" in agrupado.columns else [])
    st.dataframe(
        agrupado[colunas_tabela],
        use_container_width=True,
        hide_index=True,
        column_config=milhar_config(["Toneladas", "TCH", "Área Colhida", "ATR"], decimals=2),
    )
