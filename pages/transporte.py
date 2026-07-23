import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.express as px

from src.data_loader import get_data, kpi_card, frota_summary, milhar_config, add_pct_entrega, build_grouped_table
from src.theme import inject_theme

inject_theme()
st.title("🚛 Transporte")

data = get_data()
df = data.get("transporte")

if df is None or df.empty:
    st.warning("Aba BASETRANSPORTE não encontrada ou vazia na planilha.")
    st.stop()

st.sidebar.header("Filtros — Transporte")
meses = sorted(df["Mês"].dropna().unique().tolist())
empresas = sorted(df["Empresa"].dropna().unique().tolist())

f_mes = st.sidebar.multiselect("Mês", meses, default=meses)
f_empresa = st.sidebar.multiselect("Empresa/Frota", empresas, default=empresas)
date_min, date_max = df["Data"].min(), df["Data"].max()
f_periodo = st.sidebar.date_input("Período", value=(date_min, date_max))

filtrado = df[df["Mês"].isin(f_mes) & df["Empresa"].isin(f_empresa)]
if isinstance(f_periodo, tuple) and len(f_periodo) == 2:
    filtrado = filtrado[
        (filtrado["Data"].dt.date >= f_periodo[0]) & (filtrado["Data"].dt.date <= f_periodo[1])
    ]

c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "Toneladas Total", f"{filtrado['Toneladas'].sum():,.0f}")
kpi_card(c2, "Total Viagens", f"{filtrado['Total Viagens'].sum():,.0f}")
kpi_card(c3, "Ton./Viagem Média", f"{filtrado['Toneladas por viagem'].mean():,.2f}")
kpi_card(c4, "Distância Média (km)", f"{filtrado['Distancia Média'].mean():,.1f}")

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Toneladas por Empresa (Top 15)")
    g = filtrado.groupby("Empresa", as_index=False)["Toneladas"].sum()
    g = g.sort_values("Toneladas", ascending=False).head(15)
    fig = px.bar(g, x="Toneladas", y="Empresa", orientation="h", text="Toneladas")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Evolução Diária de Toneladas")
    g2 = filtrado.groupby("Data", as_index=False)["Toneladas"].sum()
    fig2 = px.area(g2, x="Data", y="Toneladas")
    fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Entrega de Cana por Empresa")
detalhe_empresa = frota_summary(
    filtrado,
    group_cols=["Empresa"],
    extra_agg={"Distância Média (km)": ("Distancia Média", "mean")},
)
detalhe_empresa = add_pct_entrega(detalhe_empresa)
detalhe_empresa = detalhe_empresa[
    ["Empresa", "Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega", "Distância Média (km)"]
]
st.dataframe(
    detalhe_empresa,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(["Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega", "Distância Média (km)"], decimals=2),
)

st.subheader("Entrega de Cana por Empresa e Frota")
detalhe_empresa_frota = frota_summary(filtrado, group_cols=["Empresa", "Frota"])
detalhe_empresa_frota = add_pct_entrega(detalhe_empresa_frota)
agrupada = build_grouped_table(
    detalhe_empresa_frota,
    group_col="Empresa",
    sub_col="Frota",
    value_cols=["Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega"],
    label_col_name="Empresa / Frota",
    sort_value_col="Acumulado (t)",
)
st.dataframe(
    agrupada,
    use_container_width=True,
    hide_index=True,
    column_config=milhar_config(["Ton dia", "Ton dia Anterior", "Acumulado (t)", "% Entrega"], decimals=2),
)
