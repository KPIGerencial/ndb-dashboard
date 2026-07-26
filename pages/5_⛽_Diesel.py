import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.express as px

from src.data_loader import get_data, kpi_card
from src.theme import inject_theme

inject_theme()
st.title("⛽ Consumo de Diesel")

data = get_data()
df = data.get("diesel")

if df is None or df.empty:
    st.warning("Aba BASEDIESEL não encontrada ou vazia na planilha.")
    st.stop()

st.sidebar.header("Filtros — Diesel")
tipos = sorted(df["TIPO"].dropna().unique().tolist())
frentes = sorted(df["Frente"].dropna().unique().tolist())
safras = sorted(df["Safra"].dropna().unique().tolist())

f_tipo = st.sidebar.multiselect("Tipo", tipos, default=tipos)
f_frente = st.sidebar.multiselect("Frente", frentes, default=frentes)
f_safra = st.sidebar.multiselect("Safra", safras, default=safras)

filtrado = df[
    df["TIPO"].isin(f_tipo) & df["Frente"].isin(f_frente) & df["Safra"].isin(f_safra)
]

c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "Toneladas de Cana", f"{filtrado['Ton. Cana'].sum():,.0f}")
kpi_card(c2, "Litros Consumidos", f"{filtrado['Lt'].sum():,.0f}")
kpi_card(c3, "Litros/Ton. Médio", f"{filtrado['Lt/ton'].mean():,.3f}")
kpi_card(c4, "Equipamentos", f"{filtrado['Equip.'].nunique():,}")

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Litros/Ton. por Frente")
    g = filtrado.groupby("Frente", as_index=False)["Lt/ton"].mean().sort_values("Lt/ton", ascending=False)
    fig = px.bar(g, x="Frente", y="Lt/ton", text="Lt/ton")
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Litros/Ton. por Tipo de Equipamento")
    g2 = filtrado.groupby("TIPO", as_index=False)["Lt/ton"].mean()
    fig2 = px.bar(g2, x="TIPO", y="Lt/ton", text="Lt/ton")
    fig2.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Consumo por Equipamento")
rank = filtrado.sort_values("Lt/ton", ascending=False)
st.dataframe(rank, use_container_width=True, hide_index=True)
