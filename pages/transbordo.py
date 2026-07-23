import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.express as px

from src.data_loader import get_data, kpi_card, frota_summary, milhar_config, add_pct_entrega, join_disponibilidade_diesel
from src.theme import inject_theme

inject_theme()
st.title("🔄 Transbordo")

data = get_data()
df = data.get("transbordo")
disponibilidade = data.get("disponibilidade")
diesel = data.get("diesel")

if df is None or df.empty:
    st.warning("Aba BASETRANSBORDO não encontrada ou vazia na planilha.")
    st.stop()

st.sidebar.header("Filtros — Transbordo")
meses = sorted(df["Mês"].dropna().unique().tolist())
frentes = sorted(df["Frente"].dropna().unique().tolist())

f_mes = st.sidebar.multiselect("Mês", meses, default=meses)
f_frente = st.sidebar.multiselect("Frente", frentes, default=frentes)

filtrado = df[df["Mês"].isin(f_mes) & df["Frente"].isin(f_frente)]

c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "Toneladas Total", f"{filtrado['Toneladas'].sum():,.0f}")
kpi_card(c2, "Total Cargas", f"{filtrado['Total Cargas'].sum():,.0f}")
kpi_card(c3, "Média Carga (t)", f"{filtrado['Média Carga'].mean():,.2f}")
kpi_card(c4, "Frotas Ativas", f"{filtrado['Frota'].nunique():,}")

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Toneladas por Frente")
    g = filtrado.groupby("Frente", as_index=False)["Toneladas"].sum().sort_values("Toneladas", ascending=False)
    fig = px.bar(g, x="Frente", y="Toneladas", text="Toneladas")
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
st.subheader("Entrega de Cana (ton) por Frente")
frente_resumo = frota_summary(filtrado, group_cols=["Frente"])
frente_resumo = add_pct_entrega(frente_resumo)
frente_resumo = frente_resumo[["Frente", "Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega"]]
st.dataframe(
    frente_resumo,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(["Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega"], decimals=2),
)

st.subheader("Entrega de Cana por Transbordo (ton)")
st.caption("Disponibilidade Mecânica e Lt/ton cruzados das abas DISPONIBILIDADE e BASEDIESEL pelo código da frota.")
detalhe = frota_summary(filtrado, group_cols=["Frota", "Frente"])
detalhe = join_disponibilidade_diesel(detalhe, "Frota", disponibilidade, diesel, tipo_diesel="TRANSBORDO")
detalhe = detalhe[["Frota", "Frente", "Ton dia", "Acumulado (t)", "Disponibilidade Mecânica", "Lt/ton"]]
st.dataframe(
    detalhe,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(["Ton dia", "Acumulado (t)", "Disponibilidade Mecânica", "Lt/ton"], decimals=2),
)
