"""
weather.py — Previsão do tempo via Open-Meteo (API gratuita, sem chave —
https://open-meteo.com/). Suporta uma cidade fixa (compatibilidade) e
múltiplas cidades, resolvidas dinamicamente a partir da aba PROD. da
planilha (uma unidade produtora pode ter fazendas em municípios diferentes).
"""

import requests
import streamlit as st

# Coordenadas de Conceição da Barra - ES (cidade padrão / fallback)
LAT, LON = -18.5928, -39.7325
DEFAULT_CITY = "Conceição da Barra"
DEFAULT_UF = "ES"

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Mapeamento simplificado dos weather_code do Open-Meteo (WMO) para texto/ícone
WEATHER_CODES = {
    0: ("Céu limpo", "☀️"),
    1: ("Poucas nuvens", "🌤️"),
    2: ("Parcialmente nublado", "⛅"),
    3: ("Nublado", "☁️"),
    45: ("Neblina", "🌫️"),
    48: ("Neblina com geada", "🌫️"),
    51: ("Garoa leve", "🌦️"),
    53: ("Garoa moderada", "🌦️"),
    55: ("Garoa forte", "🌧️"),
    61: ("Chuva leve", "🌧️"),
    63: ("Chuva moderada", "🌧️"),
    65: ("Chuva forte", "🌧️"),
    80: ("Pancadas de chuva", "🌧️"),
    81: ("Pancadas moderadas", "🌧️"),
    82: ("Pancadas fortes", "⛈️"),
    95: ("Trovoadas", "⛈️"),
}


@st.cache_data(ttl=1800)  # atualiza a cada 30 min
def get_weather():
    """Busca condição atual + previsão diária para Conceição da Barra."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 5,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return None


@st.cache_data(ttl=86400)  # coordenadas de uma cidade não mudam; cache de 24h
def geocode_city(nome_cidade: str, uf: str = DEFAULT_UF, pais: str = "BR"):
    """Resolve nome da cidade -> (lat, lon) via geocoding gratuito do Open-Meteo.
    Prioriza resultado no Brasil / mesma UF quando há mais de um município
    homônimo; devolve None se a cidade não for encontrada."""
    params = {"name": nome_cidade, "count": 5, "language": "pt", "format": "json"}
    try:
        resp = requests.get(GEOCODE_URL, params=params, timeout=10)
        resp.raise_for_status()
        resultados = resp.json().get("results", [])
    except requests.exceptions.RequestException:
        return None
    if not resultados:
        return None
    for r in resultados:
        if r.get("country_code") == pais and uf.upper() in str(r.get("admin1", "")).upper():
            return r["latitude"], r["longitude"]
    for r in resultados:
        if r.get("country_code") == pais:
            return r["latitude"], r["longitude"]
    return resultados[0]["latitude"], resultados[0]["longitude"]


@st.cache_data(ttl=1800)  # atualiza a cada 30 min
def get_weather_by_coords(lat: float, lon: float):
    """Busca condição atual + previsão diária para um par de coordenadas."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 5,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return None


def get_weather_for_city(nome_cidade: str, uf: str = DEFAULT_UF):
    """Geocodifica a cidade e devolve os dados de clima (ou None se indisponível)."""
    coords = geocode_city(nome_cidade, uf)
    if coords is None:
        return None
    lat, lon = coords
    return get_weather_by_coords(lat, lon)


def _weather_card_html(titulo: str, dados: dict) -> str:
    atual = dados["current"]
    desc, icone = WEATHER_CODES.get(atual["weather_code"], ("—", "🌡️"))
    return f"""
    <div style="background:#1B2333;border-radius:10px;padding:10px 12px;
                border:1px solid rgba(255,255,255,0.06);margin-bottom:8px;min-height:96px;">
        <div style="font-size:11px;opacity:0.7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{titulo}</div>
        <div style="font-size:13px;opacity:0.8;">{desc} {icone}</div>
        <div style="font-size:22px;font-weight:700;">{atual['temperature_2m']:.0f}°C</div>
        <div style="font-size:11px;opacity:0.7;">
            Umidade: {atual['relative_humidity_2m']}% • Vento: {atual['wind_speed_10m']:.0f} km/h
        </div>
    </div>
    """


def _city_card_html(cidade: str, dados: dict | None) -> str:
    if dados is None:
        return f"""
        <div style="background:#1B2333;border-radius:12px;padding:10px;
                    border:1px solid rgba(255,80,80,0.35);margin-bottom:10px;min-height:92px;">
            <div style="font-size:11px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{cidade}</div>
            <div style="font-size:11px;opacity:0.7;margin-top:6px;">Sem dados</div>
        </div>
        """
    atual = dados["current"]
    desc, icone = WEATHER_CODES.get(atual["weather_code"], ("—", "🌡️"))
    return f"""
    <div style="background:linear-gradient(135deg, rgba(109,92,224,0.22), rgba(62,198,224,0.12));
                border-radius:12px;padding:10px;border:1px solid rgba(109,92,224,0.4);
                margin-bottom:10px;min-height:110px;box-shadow:0 4px 14px rgba(0,0,0,0.25);">
        <div style="font-size:11px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{cidade}</div>
        <div style="font-size:26px;font-weight:800;margin-top:2px;">{atual['temperature_2m']:.0f}°</div>
        <div style="font-size:11px;opacity:0.85;">{icone} {desc}</div>
        <div style="font-size:10px;opacity:0.7;margin-top:2px;">💧{atual['relative_humidity_2m']}% • 🍃{atual['wind_speed_10m']:.0f}km/h</div>
    </div>
    """


def render_weather_sidebar(cidades: list | None = None, uf: str = DEFAULT_UF):
    """Grid de previsão do tempo BEM destacado na sidebar — 2 colunas de
    cards, um por cidade das unidades produtoras (aba ESTIMATIVA). Cada card
    tem um expander logo abaixo com a previsão de 5 dias. Cai para a cidade
    padrão (Conceição da Barra) se nenhuma cidade for identificada."""
    cidades = cidades or [DEFAULT_CITY]
    st.sidebar.markdown("### 🌦️ Clima — Unidades")

    col_a, col_b = st.sidebar.columns(2)
    cols = [col_a, col_b]
    resultados = {}
    for i, cidade in enumerate(cidades):
        dados = get_weather_for_city(cidade, uf)
        resultados[cidade] = dados
        with cols[i % 2]:
            st.markdown(_city_card_html(cidade, dados), unsafe_allow_html=True)

    with st.sidebar.expander("Previsão detalhada (5 dias) por cidade"):
        for cidade, dados in resultados.items():
            if dados is None:
                st.caption(f"**{cidade}** — sem dados.")
                continue
            st.markdown(f"**{cidade}**")
            diario = dados["daily"]
            for i, data in enumerate(diario["time"]):
                desc_d, icone_d = WEATHER_CODES.get(diario["weather_code"][i], ("—", "🌡️"))
                st.caption(
                    f"{data[5:]} {icone_d} {desc_d} — "
                    f"{diario['temperature_2m_min'][i]:.0f}°/{diario['temperature_2m_max'][i]:.0f}°C "
                    f"(chuva: {diario['precipitation_probability_max'][i]}%)"
                )
