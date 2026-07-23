"""
app.py — Ponto de entrada do Dashboard NDB.

Router com menu de navegação no TOPO da página (st.navigation position="top"),
em vez do menu automático na sidebar — pedido explícito para deixar o app
mais parecido com dashboards SaaS de referência. A sidebar fica livre para
filtros e o grid de clima.

Rodar com:  streamlit run app.py

Observação (Streamlit 1.52): há um bug conhecido do próprio Streamlit
(issue #13224) em que position="top" duplica o menu no topo E na sidebar.
Se isso acontecer no seu ambiente, é bug da versão instalada, não do nosso
código — atualize o Streamlit ou aguarde a correção oficial.
"""

import streamlit as st

# st.set_page_config() precisa ser o PRIMEIRO comando st.* do script —
# antes de qualquer import que possa, indiretamente, chamar st.*.
st.set_page_config(
    page_title="NDB | Visão Executiva",
    page_icon="🌾",
    layout="wide",
)

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

pages = [
    st.Page("views/visao_geral.py", title="Visão Geral", icon="📊", url_path="visao-geral", default=True),
    st.Page("pages/transporte.py", title="Transporte", icon="🚛", url_path="transporte"),
    st.Page("pages/transbordo.py", title="Transbordo", icon="🔄", url_path="transbordo"),
    st.Page("pages/disponibilidade.py", title="Disponibilidade", icon="⚙️", url_path="disponibilidade"),
    st.Page("pages/diesel.py", title="Diesel", icon="⛽", url_path="diesel"),
    st.Page("pages/colhedoras.py", title="Colhedoras", icon="🚜", url_path="colhedoras"),
    st.Page("views/historico_safras.py", title="Histórico de Safras", icon="📜", url_path="historico-safras"),
]

pg = st.navigation(pages, position="top")
pg.run()
