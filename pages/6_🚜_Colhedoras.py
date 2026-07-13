import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.express as px
import pandas as pd

from src.data_loader import get_data, kpi_card, frota_summary, milhar_config, add_pct_entrega, join_disponibilidade_diesel

st.set_page_config(page_title="Colhedoras | NDB", page_icon="🚜", layout="wide")
st.title("🚜 Colhedoras")

data = get_data()
df = data.get("colhedora")
disponibilidade = data.get("disponibilidade")
diesel = data.get("diesel")
transporte = data.get("transporte", pd.DataFrame())

if df is None or df.empty:
    st.warning("Aba BASECOLHEDORA não encontrada ou vazia na planilha.")
    st.stop()

st.sidebar.header("Filtros — Colhedoras")
meses = sorted(df["Mês"].dropna().unique().tolist())
frentes = sorted(df["FRENTE"].dropna().unique().tolist())
proprietarios = sorted(df["PROPRIETARIO"].dropna().unique().tolist())

f_mes = st.sidebar.multiselect("Mês", meses, default=meses)
f_frente = st.sidebar.multiselect("Frente", frentes, default=frentes)
f_prop = st.sidebar.multiselect("Proprietário", proprietarios, default=proprietarios)

filtrado = df[
    df["Mês"].isin(f_mes) & df["FRENTE"].isin(f_frente) & df["PROPRIETARIO"].isin(f_prop)
]

c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "Toneladas Total", f"{filtrado['Toneladas'].sum():,.0f}")
kpi_card(c2, "Total Cargas", f"{filtrado['Total Cargas'].sum():,.0f}")
kpi_card(c3, "Média Carga (t)", f"{filtrado['Média Carga'].mean():,.2f}")
kpi_card(c4, "Colhedoras Ativas", f"{filtrado['Frota'].nunique():,}")

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Toneladas por Frente")
    g = filtrado.groupby("FRENTE", as_index=False)["Toneladas"].sum().sort_values("Toneladas", ascending=False)
    fig = px.bar(g, x="FRENTE", y="Toneladas", text="Toneladas")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Evolução Diária de Toneladas")
    g2 = filtrado.groupby("Data", as_index=False)["Toneladas"].sum()
    fig2 = px.line(g2, x="Data", y="Toneladas", markers=True)
    fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Ranking por Proprietário")
rank_prop = filtrado.groupby("PROPRIETARIO", as_index=False)[["Toneladas", "Total Cargas"]].sum()
rank_prop = rank_prop.sort_values("Toneladas", ascending=False)
st.dataframe(
    rank_prop,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(["Toneladas", "Total Cargas"]),
)

st.subheader("Entrega de Cana (ton) por Frente")
st.caption("Linha TOTAL usa a soma da planilha de Transporte (tonelagem efetivamente entregue/pesada).")
frente_resumo = frota_summary(filtrado, group_cols=["FRENTE"]).rename(columns={"FRENTE": "Frente"})
frente_resumo = add_pct_entrega(frente_resumo)
frente_resumo = frente_resumo[["Frente", "Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega"]]

if not transporte.empty:
    transp_mes = transporte[transporte["Mês"].isin(f_mes)] if "Mês" in transporte.columns else transporte
    ton_dia_total = transp_mes[transp_mes["Data"] == transp_mes["Data"].max()]["Toneladas"].sum() if not transp_mes.empty else 0
    datas_transp = sorted(transp_mes["Data"].dropna().unique()) if not transp_mes.empty else []
    ton_dia_ant_total = (
        transp_mes[transp_mes["Data"] == datas_transp[-2]]["Toneladas"].sum() if len(datas_transp) >= 2 else 0
    )
    acumulado_total = transp_mes["Toneladas"].sum() if not transp_mes.empty else 0
    linha_total = pd.DataFrame(
        [{"Frente": "TOTAL (Transporte)", "Ton dia": ton_dia_total, "Ton dia Anterior": ton_dia_ant_total,
          "Acumulado (t)": acumulado_total, "% Entrega": 100.0}]
    )
    frente_resumo = pd.concat([frente_resumo, linha_total], ignore_index=True)

st.dataframe(
    frente_resumo,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(["Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega"], decimals=2),
)

st.subheader("Entrega de Cana por Colhedora (ton)")
st.caption("Disponibilidade Mecânica e Lt/ton cruzados das abas DISPONIBILIDADE e BASEDIESEL pelo código da frota.")
detalhe = frota_summary(filtrado, group_cols=["Frota", "FRENTE"]).rename(columns={"FRENTE": "Frente"})
detalhe = join_disponibilidade_diesel(detalhe, "Frota", disponibilidade, diesel, tipo_diesel="Colhedora")
detalhe = detalhe[["Frota", "Frente", "Ton dia", "Acumulado (t)", "Disponibilidade Mecânica", "Lt/ton"]]
st.dataframe(
    detalhe,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(["Ton dia", "Acumulado (t)", "Disponibilidade Mecânica", "Lt/ton"], decimals=2),
)
