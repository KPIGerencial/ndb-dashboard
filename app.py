"""
app.py — Visão Executiva do Dashboard NDB.
Une a antiga Home com o antigo "Colheita Analítico Geral" numa única página,
no estilo dos modelos de referência (cartões de KPI + gráficos + acesso rápido às demais páginas).

Rodar com:  streamlit run app.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st
import plotly.express as px
import pandas as pd

from src.data_loader import get_data, kpi_card, milhar_config

st.set_page_config(
    page_title="NDB | Visão Executiva",
    page_icon="🌾",
    layout="wide",
)

# ---------- CSS dos cartões (compacto, para caber em tela 27" sem rolagem) ----------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    h1 { font-size: 1.5rem !important; margin-bottom: 0.1rem !important; }
    h3 { font-size: 0.95rem !important; margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; }
    .stCaption, [data-testid="stCaptionContainer"] { margin-bottom: 0.3rem !important; }
    hr { margin: 0.5rem 0 !important; }
    .kpi-card {
        background: #1B2333;
        border-radius: 10px;
        padding: 8px 12px;
        margin-bottom: 6px;
        border: 1px solid rgba(255,255,255,0.06);
        height: 64px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-card.highlight {
        background: linear-gradient(135deg, #4F7DF3 0%, #6C5CE7 100%);
    }
    .kpi-label {
        font-size: 10.5px;
        opacity: 0.75;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-value {
        font-size: 17px;
        font-weight: 700;
        line-height: 1.1;
    }
    .kpi-delta {
        font-size: 9.5px;
        margin-top: 2px;
        opacity: 0.85;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_kpi(col, label, value, delta=None, highlight=False):
    cls = "kpi-card highlight" if highlight else "kpi-card"
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    with col:
        st.markdown(
            f'<div class="{cls}"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>{delta_html}</div>',
            unsafe_allow_html=True,
        )


# ---------- Barra lateral: fonte de dados + filtros ----------
st.sidebar.title("🌾 NDB Dashboard")
st.sidebar.caption("Visão Executiva — Colheita, Transporte e Logística")

st.sidebar.markdown("### Fonte de dados")
uploaded = st.sidebar.file_uploader(
    "Substituir planilha padrão (opcional)", type=["xlsx"], key="uploader_home"
)
if uploaded is not None:
    st.session_state["uploaded_file"] = uploaded
    st.sidebar.success("Usando arquivo enviado.")
else:
    st.sidebar.info("Usando arquivo padrão em /data/KPIS_NDB.xlsx")

data = get_data()
colheita = data.get("colheita", pd.DataFrame())
estimativa = data.get("estimativa", pd.DataFrame())
transporte = data.get("transporte", pd.DataFrame())
transbordo = data.get("transbordo", pd.DataFrame())
colhedora = data.get("colhedora", pd.DataFrame())
disponibilidade = data.get("disponibilidade", pd.DataFrame())
diesel = data.get("diesel", pd.DataFrame())
prod = data.get("prod", pd.DataFrame())
atr = data.get("atr", pd.DataFrame())

st.sidebar.markdown("### Filtros — Colheita & Estimativa")
safras = sorted(set(colheita.get("Safra", pd.Series(dtype=str)).dropna()) | set(estimativa.get("Safra", pd.Series(dtype=str)).dropna()))
setores = sorted(set(colheita.get("Setor", pd.Series(dtype=str)).dropna()) | set(estimativa.get("Setor", pd.Series(dtype=str)).dropna()))
variedades = sorted(estimativa["Variedade"].dropna().unique().tolist()) if "Variedade" in estimativa.columns else []

f_safra = st.sidebar.multiselect("Safra", safras, default=safras)
f_setor = st.sidebar.multiselect("Setor", setores, default=setores)
f_variedade = st.sidebar.multiselect("Variedade (Estimativa)", variedades, default=variedades)

col_f = colheita[colheita["Safra"].isin(f_safra) & colheita["Setor"].isin(f_setor)] if not colheita.empty else colheita
est_f = estimativa[estimativa["Safra"].isin(f_safra) & estimativa["Setor"].isin(f_setor)] if not estimativa.empty else estimativa
if variedades:
    est_f = est_f[est_f["Variedade"].isin(f_variedade)]

st.title("Visão Executiva da Safra")
st.caption("Colheita Analítico Geral + panorama de Transporte, Transbordo, Colhedoras e Disponibilidade em uma única tela.")

# ==========================================================================
# BLOCO 1 — KPIs principais (Área Estimada/TCH da ESTIMATIVA; Área Colhida/
#            % Variação TCH da COLHEITA — Total Área O.S.), 3 casas decimais.
# ==========================================================================
area_estimada = est_f["Área Estimada"].sum() if not est_f.empty else 0
ton_estimada = prod["Produção (TON)"].sum() if not prod.empty else 0
area_colhida = col_f["Total Área O.S."].sum() if not col_f.empty else 0
pct_colhida = (area_colhida / area_estimada * 100) if area_estimada else 0
tch_estimado_medio = est_f["TCH Estimado"].mean() if not est_f.empty else 0
tch_real_colheita = col_f["TCH Real"].mean() if not col_f.empty else 0
pct_variacao_tch = col_f["% Variação TCH"].mean() if not col_f.empty else 0
ton_transportada = transporte["Toneladas"].sum() if not transporte.empty else 0
atr_medio = atr["ATR"].mean() if not atr.empty and "ATR" in atr.columns else 0

r1 = st.columns(8)
render_kpi(r1[0], "Toneladas Estimadas (t)", f"{ton_estimada:,.0f}", highlight=True)
render_kpi(r1[1], "Área Estimada (ha)", f"{area_estimada:,.3f}")
render_kpi(r1[2], "Área Colhida (ha)", f"{area_colhida:,.3f}")
render_kpi(r1[3], "TCH Estimado", f"{tch_estimado_medio:,.3f}")
render_kpi(r1[4], "% Variação TCH", f"{pct_variacao_tch:,.3f}%")
render_kpi(r1[5], "Ton. Transportadas", f"{ton_transportada:,.0f} t")
render_kpi(r1[6], "TCH Real (Colheita)", f"{tch_real_colheita:,.3f}")
render_kpi(r1[7], "ATR Médio (kg/t)", f"{atr_medio:,.2f}" if atr_medio > 0 else "—")

# ---------- KPIs operacionais (Colhedora, Transbordo, Transporte) ----------
colhedoras_ativas = colhedora[colhedora["FRENTE"] != "BASE"]["Frota"].nunique() if not colhedora.empty else 0
transbordo_ativas = transbordo[transbordo["Frente"] != "BASE"]["Frota"].nunique() if not transbordo.empty else 0
distancia_media = transporte["Distancia Média"].mean() if not transporte.empty else 0
ton_viagem_media = transporte["Toneladas por viagem"].mean() if not transporte.empty else 0
media_carga_colhedora = colhedora["Média Carga"].mean() if not colhedora.empty else 0
media_carga_transbordo = transbordo["Média Carga"].mean() if not transbordo.empty else 0
lt_ton_colhedora = diesel[diesel["TIPO"].str.upper() == "COLHEDORA"]["Lt/ton"].mean() if not diesel.empty else 0
lt_ton_transbordo = diesel[diesel["TIPO"].str.upper() == "TRANSBORDO"]["Lt/ton"].mean() if not diesel.empty else 0

r2 = st.columns(7)
render_kpi(r2[0], "Disponibilidade Média", f"{disponibilidade['Disponibilidade Mecânica'].mean()*100:,.1f}%" if not disponibilidade.empty else "—")
render_kpi(r2[1], "Distância Média (km)", f"{distancia_media:,.2f}")
render_kpi(r2[2], "Ton./Viagem Média", f"{ton_viagem_media:,.2f}")
render_kpi(r2[3], "Colhedoras Ativas", f"{colhedoras_ativas:,}")
render_kpi(r2[4], "Transbordo Ativas", f"{transbordo_ativas:,}")
render_kpi(r2[5], "Lts/Ton. Colhedoras", f"{lt_ton_colhedora:,.3f}" if lt_ton_colhedora > 0 else "—")
render_kpi(r2[6], "Lts/Ton. Transbordos", f"{lt_ton_transbordo:,.3f}" if lt_ton_transbordo > 0 else "—")

CHART_H = 220  # altura padrão de todos os gráficos, para manter tudo harmônico

# ==========================================================================
# BLOCO 2 — Grade compacta 3x2 de gráficos
# ==========================================================================
c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Produção (t): Estimada vs Realizada")
    if not prod.empty and not col_f.empty and "Produção (TON)" in prod.columns:
        prod_estimada = prod["Produção (TON)"].sum()
        prod_realizada = col_f["Prod. Real"].sum()
        comp_df = pd.DataFrame({"Categoria": ["Estimada", "Realizada"], "Toneladas": [prod_estimada, prod_realizada]})
        fig = px.pie(comp_df, names="Categoria", values="Toneladas", hole=0.5, template="plotly_dark")
        fig.update_traces(textinfo="percent+label", textfont_size=12)
        fig.update_layout(height=CHART_H, margin=dict(t=5, b=5, l=5, r=5), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando aba PROD na planilha (ver observação).")

with c2:
    st.subheader("Toneladas Transportadas / Dia")
    if not transporte.empty:
        diario = transporte.groupby("Data", as_index=False)["Toneladas"].sum()
        fig = px.area(diario, x="Data", y="Toneladas", template="plotly_dark")
        fig.update_layout(height=CHART_H, margin=dict(t=5, b=5, l=5, r=5))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de transporte.")

with c3:
    st.subheader("TCH Real x Estimado por Setor")
    if not col_f.empty and not est_f.empty:
        g_col2 = col_f.groupby("Setor", as_index=False)["TCH Real"].mean().rename(columns={"TCH Real": "TCH Real (Colheita)"})
        g_est2 = est_f.groupby("Setor", as_index=False)["TCH Estimado"].mean()
        g_merge = g_col2.merge(g_est2, on="Setor", how="outer")
        fig2 = px.bar(g_merge, x="Setor", y=["TCH Estimado", "TCH Real (Colheita)"], barmode="group", text_auto=".1f", template="plotly_dark")
        fig2.update_traces(textposition="outside")
        fig2.update_layout(height=CHART_H, margin=dict(t=5, b=5, l=5, r=5), legend_title="", legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Dados insuficientes.")

c4, c5, c6 = st.columns(3)

with c4:
    st.subheader("Toneladas (t) por Frente")
    if not colhedora.empty:
        g_colh = colhedora.groupby("FRENTE", as_index=False)["Toneladas"].sum().rename(columns={"FRENTE": "Frente"})
        g_colh = g_colh.sort_values("Toneladas", ascending=False)
        fig4 = px.bar(g_colh, x="Frente", y="Toneladas", text_auto=",.0f", template="plotly_dark")
        fig4.update_traces(textposition="outside")
        fig4.update_layout(height=CHART_H, margin=dict(t=5, b=5, l=5, r=5))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Sem dados de Colhedora.")

with c5:
    st.subheader("Consumo Lts/Ton — Colhedoras")
    if not diesel.empty and "TIPO" in diesel.columns:
        disel_colh = diesel[diesel["TIPO"].str.upper() == "COLHEDORA"].copy()
        if not disel_colh.empty:
            g_colh_diesel = disel_colh.groupby("Equip.", as_index=False)["Lt/ton"].mean()
            g_colh_diesel = g_colh_diesel.sort_values("Lt/ton", ascending=False).head(15)
            fig5 = px.bar(g_colh_diesel, x="Equip.", y="Lt/ton", text="Lt/ton", template="plotly_dark")
            fig5.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig5.update_layout(height=CHART_H, margin=dict(t=5, b=5, l=5, r=5), xaxis_type="category")
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Sem dados de diesel para colhedoras.")
    else:
        st.info("Sem dados de diesel.")

with c6:
    st.subheader("Produção Real por Estágio")
    if not prod.empty and "Estágio da Cultura" in prod.columns and "SETOR" in prod.columns:
        prod_f = prod[prod["SETOR"].isin(f_setor) & prod["Produção Real (TON)"].notna()]
        if not prod_f.empty:
            g_var = prod_f.groupby(["Estágio da Cultura", "SETOR"], as_index=False)["Produção Real (TON)"].sum()
            g_real_var = g_var.pivot_table(index="Estágio da Cultura", columns="SETOR", values="Produção Real (TON)").reset_index()
            fig_var = px.line(g_real_var, x="Estágio da Cultura", y=g_real_var.columns.difference(["Estágio da Cultura"]), markers=True, template="plotly_dark")
            fig_var.update_layout(height=CHART_H, margin=dict(t=5, b=5, l=5, r=5), legend_title="", legend=dict(orientation="h", y=1.15))
            st.plotly_chart(fig_var, use_container_width=True)
        else:
            st.info("Dados insuficientes para este gráfico.")
    else:
        st.info("Aguardando aba PROD na planilha (ver observação).")

# ==========================================================================
# BLOCO 3 — Top 10 Fazendas + Acesso Rápido, lado a lado
# ==========================================================================
t1, t2 = st.columns([1.3, 1])

with t1:
    st.subheader("Top 10 Fazendas — Melhor TCH Real (Estimativa)")
    if not est_f.empty:
        top10 = est_f.groupby("Fazenda", as_index=False)["TCH Real"].mean()
        top10 = top10.sort_values("TCH Real", ascending=False).head(10)
        st.dataframe(
            top10, use_container_width=True, hide_index=True, height=280,
            column_config=milhar_config(["TCH Real"], decimals=3),
        )
    else:
        st.info("Sem dados de estimativa.")

