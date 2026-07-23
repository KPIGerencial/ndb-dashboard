"""
map_view.py — Dois níveis de mapa, o dashboard usa o primeiro que tiver dados:

1) render_mapa_estado(): choropleth por ESTADO (UF), usando a malha oficial
   do IBGE — é o mapa priorizado, a partir do cruzamento da aba CIDADE (Cidade
   -> UF) com a ESTIMATIVA (Fazenda -> Cidade -> Toneladas/Área).
2) render_mapa_colheita(): mapa de bolhas por FAZENDA/CIDADE (fallback),
   usado enquanto a aba CIDADE não existir ou o cruzamento não achar UF.

Reaproveita a geocodificação do módulo de clima (mesma API gratuita, sem
chave — Open-Meteo) para o mapa de bolhas.
"""

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

from src.weather import geocode_city, DEFAULT_UF

# Código IBGE de cada UF — necessário para casar com a malha geográfica
# (a malha identifica os estados pelo código, não pela sigla).
UF_TO_IBGE = {
    "AC": 12, "AL": 27, "AP": 16, "AM": 13, "BA": 29, "CE": 23, "DF": 53,
    "ES": 32, "GO": 52, "MA": 21, "MT": 51, "MS": 50, "MG": 31, "PA": 15,
    "PB": 25, "PR": 41, "PE": 26, "PI": 22, "RJ": 33, "RN": 24, "RS": 43,
    "RO": 11, "RR": 14, "SC": 42, "SP": 35, "SE": 28, "TO": 17,
}

IBGE_MALHA_UF_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/BR?formato=application/vnd.geo+json&resolucao=2"


@st.cache_data(ttl=86400, show_spinner=False)  # malha dos estados não muda; cache de 24h
def _get_geojson_estados():
    try:
        resp = requests.get(IBGE_MALHA_UF_URL, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return None


def render_mapa_estado(estado_df: pd.DataFrame):
    """Choropleth do Brasil por UF — tamanho/cor da região = Toneladas
    Colhidas (uma UF por área colorida), com Área Estimada no hover.
    Prioridade do mapa, conforme cruzamento da aba CIDADE x ESTIMATIVA."""
    st.subheader("🗺️ Mapa por Estado — Toneladas Colhidas x Área Estimada")

    geojson = _get_geojson_estados()
    if geojson is None:
        st.info("Não foi possível carregar a malha de estados do IBGE agora.")
        return

    df = estado_df.copy()
    df["codarea"] = df["UF"].map(UF_TO_IBGE)
    df = df.dropna(subset=["codarea"])
    df["codarea"] = df["codarea"].astype(int).astype(str)

    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="codarea",
        featureidkey="properties.codarea",
        color="Toneladas Colhidas",
        hover_name="UF",
        hover_data={"Área Estimada (ha)": ":,.2f", "Toneladas Colhidas": ":,.0f", "codarea": False},
        color_continuous_scale="Viridis",
        scope="south america",
    )
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        height=420,
        margin=dict(t=5, b=5, l=5, r=5),
        paper_bgcolor="rgba(0,0,0,0)",
        geo_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(ttl=86400, show_spinner=False)
def _geocode_cidades(cidades: tuple, uf: str) -> dict:
    """Geocodifica um conjunto de cidades de uma vez (cacheado por 24h) e
    devolve {cidade: (lat, lon)} — evita repetir chamadas para a mesma
    cidade quando várias fazendas ficam no mesmo município. Cidades que o
    geocoder não encontra viram (None, None) em vez de None puro, para não
    quebrar o [0]/[1] em _add_coords."""
    return {cidade: (geocode_city(cidade, uf) or (None, None)) for cidade in cidades}


def _add_coords(df: pd.DataFrame, uf: str = DEFAULT_UF) -> pd.DataFrame:
    coords_por_cidade = _geocode_cidades(tuple(sorted(df["Cidade"].unique())), uf)
    out = df.copy()
    out["lat"] = out["Cidade"].map(lambda c: coords_por_cidade.get(c, (None, None))[0])
    out["lon"] = out["Cidade"].map(lambda c: coords_por_cidade.get(c, (None, None))[1])
    return out.dropna(subset=["lat", "lon"])


def render_mapa_colheita(mapa_df: pd.DataFrame, uf: str = DEFAULT_UF):
    """Renderiza o mapa de bolhas: tamanho = Toneladas Colhidas, cor = Área
    Estimada (ha), uma bolha por Fazenda posicionada pela cidade. Usado como
    fallback do mapa por estado, enquanto a aba CIDADE (Cidade x UF) não
    existir na planilha."""
    st.subheader("🗺️ Mapa por Fazenda — Toneladas Colhidas x Área Estimada")
    st.caption("Exibindo por fazenda/cidade porque a aba CIDADE (Cidade x UF) ainda não foi encontrada na planilha.")

    if mapa_df is None or mapa_df.empty:
        st.info(
            "Mapa aguardando a coluna de Cidade/Município por Fazenda na "
            "planilha (ainda não preenchida — assim que existir, o mapa "
            "aparece automaticamente)."
        )
        return

    geo_df = _add_coords(mapa_df, uf)
    if geo_df.empty:
        st.info("Não foi possível geolocalizar as cidades informadas na planilha.")
        return

    fig = px.scatter_mapbox(
        geo_df,
        lat="lat",
        lon="lon",
        size="Toneladas Colhidas",
        color="Área Estimada (ha)",
        hover_name="Fazenda",
        hover_data={
            "Cidade": True,
            "Toneladas Colhidas": ":,.0f",
            "Área Estimada (ha)": ":,.2f",
            "lat": False,
            "lon": False,
        },
        color_continuous_scale="Viridis",
        size_max=40,
        zoom=7,
        mapbox_style="carto-darkmatter",  # gratuito, sem token do Mapbox
    )
    fig.update_layout(
        height=420,
        margin=dict(t=5, b=5, l=5, r=5),
        paper_bgcolor="rgba(0,0,0,0)",
        legend_title="",
    )
    st.plotly_chart(fig, use_container_width=True)
