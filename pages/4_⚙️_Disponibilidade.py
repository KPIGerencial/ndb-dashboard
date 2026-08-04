import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.express as px

from src.data_loader import get_data, kpi_card, require_columns
from src.theme import inject_theme

inject_theme()
st.title("⚙️ Disponibilidade Mecânica")

data = get_data()
df = data.get("disponibilidade")

if df is None or df.empty:
    st.warning("Aba Disponibilidade não encontrada ou vazia na planilha.")
    st.stop()

if not require_columns(df, ["Equipamento", "Tipo Equipamento", "Frente", "Disponibilidade Mecânica"], "Disponibilidade"):
    st.stop()

st.sidebar.header("Filtros — Disponibilidade")
tipos = sorted(df["Tipo Equipamento"].dropna().unique().tolist())
frentes = sorted(df["Frente"].dropna().unique().tolist())

f_tipo = st.sidebar.multiselect("Tipo de Equipamento", tipos, default=tipos)
f_frente = st.sidebar.multiselect("Frente", frentes, default=frentes)

filtrado = df[df["Tipo Equipamento"].isin(f_tipo) & df["Frente"].isin(f_frente)]

c1, c2 = st.columns(2)
kpi_card(c1, "Disp. Mecânica Média", f"{filtrado['Disponibilidade Mecânica'].mean()*100:,.1f}%")
kpi_card(c2, "Equipamentos", f"{filtrado['Equipamento'].nunique():,}")

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Disponibilidade Média por Tipo de Equipamento")
    g = filtrado.groupby("Tipo Equipamento", as_index=False)["Disponibilidade Mecânica"].mean()
    g["Disponibilidade Mecânica"] = (g["Disponibilidade Mecânica"] * 100).round(1)
    fig = px.bar(g, x="Tipo Equipamento", y="Disponibilidade Mecânica", text="Disponibilidade Mecânica")
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, width='stretch')

with col_b:
    st.subheader("Disponibilidade Média por Frente")
    g2 = filtrado.groupby("Frente", as_index=False)["Disponibilidade Mecânica"].mean()
    g2["Disponibilidade Mecânica"] = (g2["Disponibilidade Mecânica"] * 100).round(1)
    g2 = g2.sort_values("Disponibilidade Mecânica", ascending=False)
    fig2 = px.bar(g2, x="Frente", y="Disponibilidade Mecânica", text="Disponibilidade Mecânica")
    fig2.update_traces(texttemplate="%{text}%", textposition="outside")
    fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig2, width='stretch')

st.divider()
st.subheader("Detalhe por Equipamento")
st.dataframe(
    filtrado[["Equipamento", "Tipo Equipamento", "Frente", "Disponibilidade Mecânica"]],
        width='stretch',
    hide_index=True,
)
