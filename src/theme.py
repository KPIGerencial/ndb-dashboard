"""
theme.py — CSS compartilhado por todas as páginas do dashboard, chamado uma
vez no início de cada página (inject_theme()). Mantém a identidade visual
consistente (cores, cards, tipografia) em vez de cada página estilizar do
seu jeito — inspirado nos dois exemplos de referência (fundo escuro,
cards arredondados com destaque em roxo/azul).
"""

import streamlit as st

# Paleta central — mude aqui para afetar o app inteiro.
BG = "#0B0F1C"
BG_CARD = "#151B2E"
BORDER = "rgba(255,255,255,0.07)"
ACCENT_1 = "#6D5CE0"   # roxo
ACCENT_2 = "#3EC6E0"   # azul-ciano
TEXT_MUTED = "rgba(255,255,255,0.65)"

CSS = f"""
<style>
    .stApp {{
        background: radial-gradient(1200px 600px at 10% -10%, #1A2140 0%, {BG} 55%);
    }}

    /* Top navigation (st.navigation position="top") com acabamento em gradiente */
    div[data-testid="stTopNav"] {{
        background: linear-gradient(90deg, #141A30 0%, #1B2244 100%);
        border-bottom: 1px solid {BORDER};
    }}
    div[data-testid="stTopNav"] button[aria-selected="true"] {{
        background: linear-gradient(90deg, {ACCENT_1}, {ACCENT_2}) !important;
        border-radius: 8px !important;
        color: white !important;
    }}

    /* Cards genéricos usados via .ndb-card */
    .ndb-card {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.25);
    }}
    .ndb-card-accent {{
        background: linear-gradient(135deg, rgba(109,92,224,0.18), rgba(62,198,224,0.10));
        border: 1px solid rgba(109,92,224,0.35);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.25);
    }}

    .ndb-eyebrow {{
        font-size: 11px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: {TEXT_MUTED};
        margin-bottom: 2px;
    }}

    /* Métricas nativas do Streamlit com acabamento mais "premium" */
    div[data-testid="stMetric"] {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.25);
    }}

    section[data-testid="stSidebar"] {{
        background: #0E1425;
        border-right: 1px solid {BORDER};
    }}

    h1, h2, h3 {{
        letter-spacing: -0.01em;
    }}
</style>
"""


def inject_theme():
    """Injeta o CSS compartilhado — chamar uma vez no topo de cada página."""
    st.markdown(CSS, unsafe_allow_html=True)


def card(titulo: str, valor: str, subtitulo: str = "", accent: bool = False) -> str:
    """Monta o HTML de um card de métrica no estilo do dashboard (usado fora
    do st.metric nativo quando queremos mais controle visual, como nos cards
    de clima e no cabeçalho)."""
    classe = "ndb-card-accent" if accent else "ndb-card"
    sub_html = f'<div style="font-size:11px;color:{TEXT_MUTED};margin-top:4px;">{subtitulo}</div>' if subtitulo else ""
    return f"""
    <div class="{classe}">
        <div class="ndb-eyebrow">{titulo}</div>
        <div style="font-size:24px;font-weight:700;">{valor}</div>
        {sub_html}
    </div>
    """
