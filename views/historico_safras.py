"""
views/historico_safras.py — Histórico de Safras.

Fonte: planilha dedicada no Dropbox (DROPBOX_HISTORICO_URL), uma aba por safra
(2026, 2025, 2024, 2023...). O ATR é cruzado da aba BASEATR/BASEART da
planilha principal por Fazenda + Safra (ano da Data Produção) — nunca
misturando leituras de anos diferentes na mesma média. A partir do ATR e do
TCH, calcula o TAH = TCH × ATR ÷ 100 (Toneladas de Açúcar por Hectare).

Duas visões:
- Padrão (nenhuma fazenda buscada): agrupado por Fazenda, somando/mediando
  todas as safras selecionadas no filtro.
- Fazenda específica (buscada no campo de busca): quebra ano a ano
  (Safra | Área Colhida | Toneladas | TCH | TAH), ignorando o filtro de
  Safra — sempre mostra o histórico completo da fazenda escolhida.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import (
    get_data,
    get_historico_safras,
    enrich_historico_com_atr,
    diagnostico_atr,
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
motivo_atr_indisponivel = diagnostico_atr(atr)
historico = enrich_historico_com_atr(historico, atr)

if "ATR" not in historico.columns:
    st.warning(f"TAH e ATR não calculados: {motivo_atr_indisponivel or 'motivo desconhecido.'}")
else:
    total_linhas = len(historico)
    com_atr = int(historico["ATR"].notna().sum())
    if com_atr == 0:
        st.warning(
            "Nenhuma Fazenda do histórico casou com a aba BASEATR/BASEART da planilha "
            "principal — TAH e ATR vão ficar em branco. Confira se o nome da Fazenda "
            "está escrito igual nas duas planilhas."
        )
    elif com_atr < total_linhas:
        st.caption(f"ATR encontrado para {com_atr} de {total_linhas} linhas (o restante fica sem TAH/ATR).")

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

    colunas_kpi = st.columns(7)
    colunas_kpi[0].metric("Toneladas Total (todas as safras)", f"{por_safra['Toneladas'].sum():,.0f}")
    if "TCH" in por_safra.columns:
        colunas_kpi[1].metric("TCH Médio (todas as safras)", f"{por_safra['TCH'].mean():,.2f}")
    if "Área Colhida" in por_safra.columns:
        colunas_kpi[2].metric("Área Colhida Média/Safra (ha)", f"{por_safra['Área Colhida'].mean():,.2f}")
    if "ATR" in por_safra.columns and por_safra["ATR"].notna().any():
        colunas_kpi[3].metric("ATR Médio (todas as safras)", f"{por_safra['ATR'].mean():,.2f}")
    if "TAH" in por_safra.columns and por_safra["TAH"].notna().any():
        colunas_kpi[4].metric("TAH Médio (todas as safras)", f"{por_safra['TAH'].mean():,.2f}")
    # "MAX ANO": o melhor ano (safra) da fazenda em Área Colhida, não a soma.
    if "Área Colhida" in por_safra.columns:
        colunas_kpi[5].metric("Área Colhida Máx. (ha) — melhor safra", f"{por_safra['Área Colhida'].max():,.2f}")
    # % Variação TCH: safra mais recente vs a anterior (por_safra já vem
    # ordenado por Safra decrescente — ver agrupar_historico_por_safra).
    pct_var_tch_fazenda = None
    if "TCH" in por_safra.columns and len(por_safra) >= 2:
        tch_atual, tch_anterior = por_safra.iloc[0]["TCH"], por_safra.iloc[1]["TCH"]
        if tch_anterior:
            pct_var_tch_fazenda = (tch_atual - tch_anterior) / tch_anterior * 100
    colunas_kpi[6].metric(
        "% Variação TCH (safra atual vs anterior)",
        f"{pct_var_tch_fazenda:+.1f}%" if pct_var_tch_fazenda is not None else "—",
    )

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

    col_a, col_b, col_c = st.columns(3)
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

    with col_c:
        st.subheader("TAH por Safra")
        st.caption("TCH × ATR ÷ 100")
        if "TAH" in por_safra.columns:
            g3 = por_safra.sort_values("Safra")
            fig3 = px.bar(g3, x="Safra", y="TAH", text_auto=".2f", template="plotly_dark")
            fig3.update_traces(textposition="outside")
            fig3.update_xaxes(type="category")
            fig3.update_layout(height=280, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sem ATR cruzado para calcular o TAH.")

    st.divider()
    st.subheader("Safra | Área Colhida | Toneladas | TCH | TAH")
    colunas_tabela = ["Safra", "Área Colhida", "Toneladas", "TCH"] + (["TAH"] if "TAH" in por_safra.columns else [])
    st.dataframe(
        por_safra[colunas_tabela],
        use_container_width=True,
        hide_index=True,
        column_config=milhar_config(["Área Colhida", "Toneladas", "TCH", "TAH"], decimals=2),
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

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Toneladas Total", f"{agrupado['Toneladas'].sum():,.0f}")
    if "TCH" in agrupado.columns:
        c2.metric("TCH Médio", f"{agrupado['TCH'].mean():,.2f}")
    if "Área Colhida" in agrupado.columns:
        c3.metric("Área Colhida Total (ha)", f"{agrupado['Área Colhida'].sum():,.2f}")
    if "ATR" in agrupado.columns and agrupado["ATR"].notna().any():
        c4.metric("ATR Médio", f"{agrupado['ATR'].mean():,.2f}")
    if "TAH" in agrupado.columns and agrupado["TAH"].notna().any():
        c5.metric("TAH Médio", f"{agrupado['TAH'].mean():,.2f}")

    # por_ano_geral (uma linha por Safra, entre todas as fazendas filtradas) —
    # usado tanto pelos dois cards abaixo (MAX ANO / % Variação TCH) quanto
    # pelo gráfico "Toneladas Total por Safra" logo adiante.
    por_ano_geral = agrupar_historico_por_safra(filtrado) if "Safra" in filtrado.columns else pd.DataFrame()

    # "MAX ANO": a melhor safra (ano) em Área Colhida somada, entre todas as
    # fazendas filtradas — não o total acumulado de todas as safras juntas.
    if "Área Colhida" in por_ano_geral.columns and not por_ano_geral.empty:
        c6.metric("Área Colhida Máx. (ha) — melhor safra", f"{por_ano_geral['Área Colhida'].max():,.2f}")

    # % Variação TCH: safra mais recente vs a anterior, entre todas as
    # fazendas filtradas (por_ano_geral já vem ordenado por Safra decrescente
    # — ver agrupar_historico_por_safra).
    pct_var_tch_geral = None
    if "TCH" in por_ano_geral.columns and len(por_ano_geral) >= 2:
        tch_atual, tch_anterior = por_ano_geral.iloc[0]["TCH"], por_ano_geral.iloc[1]["TCH"]
        if tch_anterior:
            pct_var_tch_geral = (tch_atual - tch_anterior) / tch_anterior * 100
    c7.metric(
        "% Variação TCH (safra atual vs anterior)",
        f"{pct_var_tch_geral:+.1f}%" if pct_var_tch_geral is not None else "—",
    )

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
        if not por_ano_geral.empty:
            fig2 = px.bar(por_ano_geral.sort_values("Safra"), x="Safra", y="Toneladas", text_auto=",.0f", template="plotly_dark")
            fig2.update_traces(textposition="outside")
            fig2.update_xaxes(type="category")
            fig2.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Todas as Fazendas — agrupado pelas safras selecionadas")
    st.caption("Use o campo \"Buscar Fazenda\" na barra lateral para ver o histórico ano a ano de uma fazenda específica.")
    colunas_tabela = ["Fazenda", "Área Colhida", "Toneladas", "TCH"] + (["TAH"] if "TAH" in agrupado.columns else [])
    st.dataframe(
        agrupado[colunas_tabela],
        use_container_width=True,
        hide_index=True,
        column_config=milhar_config(["Área Colhida", "Toneladas", "TCH", "TAH"], decimals=2),
    )
