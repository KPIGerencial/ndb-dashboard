"""
data_loader.py
==============
Camada única de acesso aos dados. Toda a aplicação lê a planilha Excel
através deste módulo — se a estrutura da planilha mudar (novas colunas,
nova aba), o ajuste é feito aqui, não em cada página.

A planilha é tratada como "banco de dados": cada aba = uma tabela.
"""

from io import BytesIO
from pathlib import Path
import pandas as pd
import requests
import streamlit as st

# Planilha oficial agora vive no Google Sheets (não mais em /data). O arquivo
# em /data/KPIS_NDB.xlsx é mantido só como último recurso, caso o Sheets
# fique fora do ar — a fonte principal é sempre o link abaixo.
# IMPORTANTE: a planilha precisa estar compartilhada como
# "Qualquer pessoa com o link" (leitor), senão o download falha.
GOOGLE_SHEET_ID = "1v4Ykj59hGBQmeAsLjF-HB7tg0hewDCeH"
GOOGLE_SHEET_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx"

# Planilha separada com o histórico de safras (página "Histórico de Safras").
GOOGLE_SHEET_HISTORICO_ID = "1Fb764e6s0hXxR_FyXaoleqmO1y6b1T8H"
GOOGLE_SHEET_HISTORICO_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_HISTORICO_ID}/export?format=xlsx"

# Caminho do arquivo local de contingência.
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "KPIS_NDB.xlsx"

# Cada chave lógica lista TODOS os nomes de aba já vistos para ela — a
# planilha nova trocou a caixa de várias abas (ex: "BaseTransporte" em vez de
# "BASETRANSPORTE") e a aba de ATR mudou de "BASEATR" para "BASEART". A
# busca abaixo é sempre case-insensitive, então "BaseTransporte" já bate com
# o candidato "BASETRANSPORTE" — as variações extras aqui cobrem mudanças de
# singular/plural e grafias que a caixa sozinha não resolve.
SHEETS = {
    "transporte": ["BASETRANSPORTE", "BASE TRANSPORTE"],
    "colhedora": ["BASECOLHEDORA", "BASECOLHEDORAS", "BASE COLHEDORA", "BASE COLHEDORAS"],
    "transbordo": ["BASETRANSBORDO", "BASE TRANSBORDO"],
    "disponibilidade": ["DISPONIBILIDADE"],
    "diesel": ["BASEDIESEL", "BASE DIESEL"],
    "colheita": ["COLHEITA"],
    "estimativa": ["ESTIMATIVA"],
    "meses": ["MES", "MESES"],
    "empresas": ["BASEEMPRESA", "BASE EMPRESA"],
    "prod": ["PROD.", "PROD", "PRODUCAO", "PRODUÇÃO", "AGR500"],  # a planilha nova usa "AGR500"
    "atr": ["BASEATR", "BASEART", "BASE ATR", "BASE ART"],  # a planilha nova usa "BASEART"
}

# Nome da aba com o cruzamento Cidade x Estado (UF) — usada para agregar o
# mapa por estado. O nome exato pode variar, por isso a busca abaixo é
# case-insensitive e cobre as variações mais comuns (a planilha nova usa "CIDADES").
CIDADE_SHEET_CANDIDATES = ["CIDADE", "CIDADES", "UF", "Estados", "Cidade x Estado"]


def _find_sheet(sheet_names_lower: dict, candidatos: list) -> str | None:
    """Localiza o nome real de uma aba a partir de uma lista de candidatos,
    ignorando maiúsculas/minúsculas e espaços nas pontas."""
    for candidato in candidatos:
        real = sheet_names_lower.get(candidato.strip().lower())
        if real is not None:
            return real
    return None


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


@st.cache_data(show_spinner="Lendo planilha...")
def load_excel(file_bytes_or_path) -> dict:
    """Lê todas as abas relevantes e devolve um dict {nome_logico: DataFrame}.

    Aceita um caminho (str) ou os bytes brutos do .xlsx. Receber bytes (em vez
    de um objeto de arquivo/BytesIO já aberto) é o que permite ao
    st.cache_data reconhecer quando o conteúdo baixado do Google Sheets não
    mudou e pular o reparsing do workbook inteiro a cada rerun — é o ganho de
    performance real da troca de fonte de dados.
    """
    fonte = BytesIO(file_bytes_or_path) if isinstance(file_bytes_or_path, (bytes, bytearray)) else file_bytes_or_path
    xls = pd.ExcelFile(fonte)
    sheet_names_lower = {s.strip().lower(): s for s in xls.sheet_names}

    data = {}
    for key, candidatos in SHEETS.items():
        sheet_name = _find_sheet(sheet_names_lower, candidatos)
        if sheet_name is None:
            continue
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = _clean_columns(df)
        df = df.dropna(how="all")
        data[key] = df

    # Aba de Cidade x UF (nome pode variar — busca case-insensitive) — usada
    # para agregar o mapa por estado (ver get_cidade_uf_map/build_mapa_estado).
    cidade_sheet = _find_sheet(sheet_names_lower, CIDADE_SHEET_CANDIDATES)
    if cidade_sheet is not None:
        df_cidade = pd.read_excel(xls, sheet_name=cidade_sheet)
        data["cidade_uf"] = _clean_columns(df_cidade).dropna(how="all")

    # --- normalizações pontuais ---
    if "transporte" in data:
        data["transporte"]["Data"] = pd.to_datetime(data["transporte"]["Data"], errors="coerce")
    if "colhedora" in data:
        data["colhedora"]["Data"] = pd.to_datetime(data["colhedora"]["Data"], errors="coerce")
    if "transbordo" in data:
        data["transbordo"]["Data"] = pd.to_datetime(data["transbordo"]["Data"], errors="coerce")
    if "diesel" in data and "DATA" in data["diesel"].columns:
        data["diesel"]["DATA"] = pd.to_datetime(data["diesel"]["DATA"], errors="coerce")
    if "colheita" in data:
        for col in ("Data Ultima Entrega",):
            if col in data["colheita"].columns:
                data["colheita"][col] = pd.to_datetime(
                    data["colheita"][col], errors="coerce", dayfirst=True
                )
    if "estimativa" in data:
        for col in ("Data Colheita/Plantio",):
            if col in data["estimativa"].columns:
                data["estimativa"][col] = pd.to_datetime(
                    data["estimativa"][col], errors="coerce", dayfirst=True
                )
    if "atr" in data and "Data Produção" in data["atr"].columns:
        data["atr"]["Data Produção"] = pd.to_datetime(
            data["atr"]["Data Produção"], errors="coerce", dayfirst=True
        )
    # A aba BASETRANSPORTE traz a coluna de empresa como "EMPRESA" (maiúsculas),
    # mas as páginas do dashboard leem "Empresa" — normaliza aqui, na fonte
    # única dos dados, para não precisar editar cada página que usa esse campo.
    if "transporte" in data and "EMPRESA" in data["transporte"].columns and "Empresa" not in data["transporte"].columns:
        data["transporte"] = data["transporte"].rename(columns={"EMPRESA": "Empresa"})

    return data


@st.cache_data(ttl=600, show_spinner="Baixando planilha do Google Sheets...")
def _download_gsheet_bytes(url: str) -> bytes:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.content


def get_data() -> dict:
    """
    Ponto único usado pelas páginas.
    Prioridade: arquivo enviado pelo usuário na sessão > planilha do Google
    Sheets (fonte oficial) > arquivo local em /data (só como contingência,
    se o Sheets estiver inacessível ou sem permissão de leitura pública).
    """
    uploaded = st.session_state.get("uploaded_file")
    if uploaded is not None:
        return load_excel(uploaded.getvalue())

    try:
        conteudo = _download_gsheet_bytes(GOOGLE_SHEET_EXPORT_URL)
        return load_excel(conteudo)
    except Exception:
        st.sidebar.error(
            "Não foi possível ler a planilha do Google Sheets. Verifique se o "
            "link está compartilhado como 'Qualquer pessoa com o link' (leitor). "
            "Exibindo o arquivo local em /data como contingência."
        )
        return load_excel(str(DEFAULT_PATH))


# Colunas esperadas na página Histórico de Safras (Fazenda | Setor |
# Toneladas | TCH | ATR | Safra | Área Colhida). Cada entrada lista os nomes
# possíveis para aquela coluna na planilha — a busca é case-insensitive.
HISTORICO_COLUMN_CANDIDATES = {
    "Fazenda": ["Fazenda", "Cod. fazenda", "Código Fazenda"],
    "Setor": ["Setor"],
    "Safra": ["Safra"],
    "Toneladas": ["Toneladas", "Tonelada Real", "Prod. Real", "Produção"],
    "TCH": ["TCH", "TCH Real", "TCH Estimado"],
    "Área Colhida": ["Área Colhida", "Area Colhida", "Total Área O.S."],
}


def _find_column(df: pd.DataFrame, candidatos: list) -> str | None:
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for candidato in candidatos:
        real = cols_lower.get(candidato.lower())
        if real is not None:
            return real
    return None


@st.cache_data(ttl=600, show_spinner="Baixando histórico de safras...")
def get_historico_safras() -> pd.DataFrame:
    """Lê a planilha dedicada de Histórico de Safras (link separado) e
    normaliza as colunas para Fazenda | Setor | Safra | Toneladas | TCH |
    Área Colhida. O ATR não costuma estar nessa planilha — é cruzado depois,
    por Fazenda (+ Safra quando disponível), com a aba BASEATR da planilha
    principal (ver enrich_historico_com_atr).

    A escolha da aba correta é feita testando TODAS as abas da planilha e
    escolhendo a que tiver mais colunas esperadas preenchidas com dados —
    não confia em nome de aba nem cai cegamente na primeira aba, porque
    planilhas reais costumam ter abas vazias/auxiliares antes da aba com os
    dados de verdade. Devolve DataFrame vazio (sem lançar exceção) se a
    planilha ainda estiver privada ou nenhuma aba bater com o padrão
    esperado — a página trata isso com uma mensagem em vez de quebrar."""
    try:
        conteudo = _download_gsheet_bytes(GOOGLE_SHEET_HISTORICO_EXPORT_URL)
    except Exception:
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(BytesIO(conteudo))
    except Exception:
        return pd.DataFrame()

    melhor_df = None
    melhor_score = 0
    for nome_aba in xls.sheet_names:
        try:
            candidata = _clean_columns(pd.read_excel(xls, sheet_name=nome_aba)).dropna(how="all")
        except Exception:
            continue
        if candidata.empty:
            continue
        score = sum(1 for candidatos in HISTORICO_COLUMN_CANDIDATES.values() if _find_column(candidata, candidatos) is not None)
        if score > melhor_score:
            melhor_score = score
            melhor_df = candidata

    # Exige pelo menos 2 colunas reconhecidas (ex: Fazenda + Toneladas) para
    # considerar a aba válida — evita pegar uma aba qualquer com dados
    # irrelevantes que por acaso não estava totalmente vazia.
    if melhor_df is None or melhor_score < 2:
        return pd.DataFrame()

    df = melhor_df
    renomeia = {}
    for nome_final, candidatos in HISTORICO_COLUMN_CANDIDATES.items():
        col = _find_column(df, candidatos)
        if col is not None:
            renomeia[col] = nome_final
    df = df.rename(columns=renomeia)
    return df


def enrich_historico_com_atr(historico: pd.DataFrame, atr: pd.DataFrame) -> pd.DataFrame:
    """Cruza o histórico de safras com a aba BASEATR (planilha principal) por
    Fazenda (+ Safra, quando as duas tabelas tiverem essa coluna), trazendo
    o ATR para dentro do histórico. Se BASEATR não tiver Fazenda/ATR
    identificáveis, devolve o histórico sem alterações."""
    if historico is None or historico.empty or atr is None or atr.empty:
        return historico

    col_fazenda_atr = _find_column(atr, ["Fazenda", "Cod. fazenda", "Código Fazenda"])
    col_atr = _find_column(atr, ["ATR", "Atr"])
    if col_fazenda_atr is None or col_atr is None or "Fazenda" not in historico.columns:
        return historico

    chaves = [col_fazenda_atr]
    left_chaves = ["Fazenda"]
    col_safra_atr = _find_column(atr, ["Safra"])
    if col_safra_atr is not None and "Safra" in historico.columns:
        chaves.append(col_safra_atr)
        left_chaves.append("Safra")

    atr_resumo = (
        atr[chaves + [col_atr]]
        .rename(columns={col_fazenda_atr: "Fazenda", col_atr: "ATR"} | ({col_safra_atr: "Safra"} if col_safra_atr else {}))
        .groupby(left_chaves, as_index=False)["ATR"]
        .mean()
    )
    return historico.merge(atr_resumo, on=left_chaves, how="left")


# Nomes possíveis da coluna de cidade/município na aba PROD./COLHEITA/ESTIMATIVA.
# A comparação é case-insensitive (ex: "cidade" minúsculo bate com "Cidade").
CITY_COLUMN_CANDIDATES = ["Cidade", "Município", "Municipio", "City", "Cidade/Município"]


def _find_city_column(df: pd.DataFrame) -> str | None:
    """Localiza a coluna de cidade num DataFrame, ignorando maiúsculas/minúsculas."""
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for candidato in CITY_COLUMN_CANDIDATES:
        real = cols_lower.get(candidato.lower())
        if real is not None:
            return real
    return None


def get_prod_cities(prod: pd.DataFrame) -> list:
    """Localiza a coluna de cidade na aba PROD. (o nome pode variar) e devolve
    a lista de cidades únicas, usada para montar a área de clima por unidade.
    Devolve lista vazia se a coluna ainda não existir na planilha (o chamador
    cai para a cidade padrão nesse caso)."""
    if prod is None or prod.empty:
        return []
    col = _find_city_column(prod)
    if col is None:
        return []
    cidades = sorted(prod[col].dropna().astype(str).str.strip().unique().tolist())
    return [c for c in cidades if c]


def get_fazenda_city_map(*dfs: pd.DataFrame) -> dict:
    """Procura a coluna de cidade/município e a coluna Fazenda em qualquer uma
    das abas passadas (ex: COLHEITA, ESTIMATIVA, PROD.) e monta um mapa
    {Fazenda: Cidade}. Devolve {} se a coluna de cidade ainda não existir em
    nenhuma delas — o mapa fica pendente até a planilha ser atualizada."""
    mapa: dict = {}
    for df in dfs:
        if df is None or df.empty or "Fazenda" not in df.columns:
            continue
        col = _find_city_column(df)
        if col is None:
            continue
        sub = df[["Fazenda", col]].dropna()
        for fazenda, cidade in zip(sub["Fazenda"], sub[col]):
            mapa[str(fazenda).strip()] = str(cidade).strip()
    return mapa


def build_mapa_colheita(colheita: pd.DataFrame, estimativa: pd.DataFrame, fazenda_city_map: dict) -> pd.DataFrame:
    """Agrega Toneladas Colhidas (COLHEITA, coluna 'Prod. Real') e Área
    Estimada (ESTIMATIVA, coluna 'Área Estimada') por Fazenda e junta a
    cidade correspondente — base de dados para o mapa de bolhas em
    map_view.render_mapa_colheita. Fazendas sem cidade mapeada ficam de fora
    do mapa, mas continuam normalmente nos KPIs e gráficos do dashboard."""
    ton = (
        colheita.groupby("Fazenda", as_index=False)["Prod. Real"]
        .sum()
        .rename(columns={"Prod. Real": "Toneladas Colhidas"})
        if not colheita.empty and "Fazenda" in colheita.columns and "Prod. Real" in colheita.columns
        else pd.DataFrame(columns=["Fazenda", "Toneladas Colhidas"])
    )
    area = (
        estimativa.groupby("Fazenda", as_index=False)["Área Estimada"]
        .sum()
        .rename(columns={"Área Estimada": "Área Estimada (ha)"})
        if not estimativa.empty and "Fazenda" in estimativa.columns and "Área Estimada" in estimativa.columns
        else pd.DataFrame(columns=["Fazenda", "Área Estimada (ha)"])
    )

    if ton.empty and area.empty:
        return pd.DataFrame(columns=["Fazenda", "Toneladas Colhidas", "Área Estimada (ha)", "Cidade"])

    out = ton.merge(area, on="Fazenda", how="outer")
    out["Toneladas Colhidas"] = out["Toneladas Colhidas"].fillna(0)
    out["Área Estimada (ha)"] = out["Área Estimada (ha)"].fillna(0)
    out["Cidade"] = out["Fazenda"].astype(str).str.strip().map(fazenda_city_map)
    return out.dropna(subset=["Cidade"])


UF_COLUMN_CANDIDATES = ["UF", "Estado", "Sigla UF", "Sigla"]


def _find_uf_column(df: pd.DataFrame) -> str | None:
    """Localiza a coluna de UF/Estado num DataFrame, ignorando maiúsculas/minúsculas."""
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for candidato in UF_COLUMN_CANDIDATES:
        real = cols_lower.get(candidato.lower())
        if real is not None:
            return real
    return None


def get_cidade_uf_map(cidade_uf_df: pd.DataFrame) -> dict:
    """Lê a aba de Cidade x UF e devolve {cidade: UF}. Devolve {} se a aba
    ainda não existir na planilha ou não tiver as colunas esperadas — nesse
    caso o mapa cai para a visão por fazenda/cidade (bolhas) em vez de estado."""
    if cidade_uf_df is None or cidade_uf_df.empty:
        return {}
    col_cidade = _find_city_column(cidade_uf_df)
    col_uf = _find_uf_column(cidade_uf_df)
    if col_cidade is None or col_uf is None:
        return {}
    sub = cidade_uf_df[[col_cidade, col_uf]].dropna()
    return {str(c).strip(): str(u).strip().upper() for c, u in zip(sub[col_cidade], sub[col_uf])}


def build_mapa_estado(mapa_colheita_df: pd.DataFrame, cidade_uf_map: dict) -> pd.DataFrame:
    """Cruza a aba CIDADE (cidade -> UF) com o resultado de build_mapa_colheita
    (fazenda -> cidade -> toneladas/área, vindo da ESTIMATIVA) para agregar
    Toneladas Colhidas e Área Estimada por ESTADO — a visão que o mapa deve
    priorizar. Devolve DataFrame vazio se faltar a aba CIDADE ou o cruzamento
    não achar nenhuma UF (o chamador cai para o mapa por fazenda nesse caso)."""
    if mapa_colheita_df is None or mapa_colheita_df.empty or not cidade_uf_map:
        return pd.DataFrame(columns=["UF", "Toneladas Colhidas", "Área Estimada (ha)"])
    df = mapa_colheita_df.copy()
    df["UF"] = df["Cidade"].map(cidade_uf_map)
    df = df.dropna(subset=["UF"])
    if df.empty:
        return pd.DataFrame(columns=["UF", "Toneladas Colhidas", "Área Estimada (ha)"])
    return df.groupby("UF", as_index=False)[["Toneladas Colhidas", "Área Estimada (ha)"]].sum()


def frota_summary(df: pd.DataFrame, group_cols: list, date_col: str = "Data",
                   value_col: str = "Toneladas", extra_agg: dict | None = None) -> pd.DataFrame:
    """
    Resume um DataFrame por grupo (ex: Frota, Empresa) com três métricas padrão:
      - "Ton dia": soma de value_col na última data presente no recorte filtrado
      - "Ton dia Anterior": soma de value_col na penúltima data presente
      - "Acumulado (t)": soma total de value_col no período filtrado

    extra_agg: dict opcional {nome_da_coluna_final: (coluna_origem, função_agregação)}
               para métricas adicionais (ex: média de distância).
    """
    base_cols = list(group_cols) + ["Ton dia", "Ton dia Anterior", "Acumulado (t)"]
    if df.empty:
        return pd.DataFrame(columns=base_cols)

    datas = sorted(df[date_col].dropna().unique())
    ultima = datas[-1] if len(datas) >= 1 else None
    penultima = datas[-2] if len(datas) >= 2 else None

    acumulado = (
        df.groupby(group_cols, as_index=False)[value_col]
        .sum()
        .rename(columns={value_col: "Acumulado (t)"})
    )

    if ultima is not None:
        ton_dia = (
            df[df[date_col] == ultima]
            .groupby(group_cols, as_index=False)[value_col]
            .sum()
            .rename(columns={value_col: "Ton dia"})
        )
    else:
        ton_dia = pd.DataFrame(columns=list(group_cols) + ["Ton dia"])

    if penultima is not None:
        ton_dia_ant = (
            df[df[date_col] == penultima]
            .groupby(group_cols, as_index=False)[value_col]
            .sum()
            .rename(columns={value_col: "Ton dia Anterior"})
        )
    else:
        ton_dia_ant = pd.DataFrame(columns=list(group_cols) + ["Ton dia Anterior"])

    out = acumulado.merge(ton_dia, on=group_cols, how="left").merge(ton_dia_ant, on=group_cols, how="left")
    out["Ton dia"] = out["Ton dia"].fillna(0)
    out["Ton dia Anterior"] = out["Ton dia Anterior"].fillna(0)

    if extra_agg:
        for new_name, (col, func) in extra_agg.items():
            extra = df.groupby(group_cols, as_index=False)[col].agg(func).rename(columns={col: new_name})
            out = out.merge(extra, on=group_cols, how="left")

    out = out.sort_values("Acumulado (t)", ascending=False).reset_index(drop=True)
    return out


def milhar_config(cols: list, decimals: int = 0) -> dict:
    """Gera um dict de column_config do Streamlit aplicando separador de milhares às colunas dadas."""
    fmt = f"%,.{decimals}f"
    return {c: st.column_config.NumberColumn(c, format=fmt) for c in cols}


def add_pct_entrega(df: pd.DataFrame, value_col: str = "Acumulado (t)", out_col: str = "% Entrega") -> pd.DataFrame:
    """Adiciona a coluna % Entrega = participação da linha no acumulado total (como nos relatórios KPIs)."""
    out = df.copy()
    total = out[value_col].sum()
    out[out_col] = (out[value_col] / total * 100) if total else 0
    return out


def join_disponibilidade_diesel(
    resumo: pd.DataFrame,
    frota_col: str,
    disponibilidade: pd.DataFrame,
    diesel: pd.DataFrame,
    tipo_diesel: str | None = None,
) -> pd.DataFrame:
    """
    Junta ao resumo por frota:
      - "Disponibilidade Mecânica" (%) — média por Equipamento (a aba tem mais de um registro por equipamento)
      - "Lt/ton" — vindo da aba de diesel, filtrando por TIPO quando informado
    """
    out = resumo.copy()

    if disponibilidade is not None and not disponibilidade.empty and "Equipamento" in disponibilidade.columns:
        disp = (
            disponibilidade.groupby("Equipamento", as_index=False)["Disponibilidade Mecânica"]
            .mean()
        )
        disp["Disponibilidade Mecânica"] = disp["Disponibilidade Mecânica"] * 100
        out = out.merge(disp, left_on=frota_col, right_on="Equipamento", how="left")
        if "Equipamento" in out.columns and "Equipamento" != frota_col:
            out = out.drop(columns=["Equipamento"])

    if diesel is not None and not diesel.empty and "Equip." in diesel.columns:
        d = diesel.copy()
        if tipo_diesel and "TIPO" in d.columns:
            d = d[d["TIPO"] == tipo_diesel]
        d = d.groupby("Equip.", as_index=False)["Lt/ton"].mean()
        out = out.merge(d, left_on=frota_col, right_on="Equip.", how="left")
        if "Equip." in out.columns and "Equip." != frota_col:
            out = out.drop(columns=["Equip."])

    return out


def build_grouped_table(
    df: pd.DataFrame, group_col: str, sub_col: str, value_cols: list,
    label_col_name: str = "Empresa/Frota", sort_value_col: str | None = None,
) -> pd.DataFrame:
    """
    Constrói uma tabela no estilo dos relatórios KPI: uma linha com o nome do grupo
    (ex: Empresa), seguida pelas linhas de detalhe (ex: Frota) indentadas abaixo,
    sem repetir o nome do grupo a cada linha.
    """
    sort_col = sort_value_col or (value_cols[-1] if value_cols else sub_col)
    ordem_grupos = (
        df.groupby(group_col)[sort_col].sum().sort_values(ascending=False).index.tolist()
    )

    rows = []
    for grupo in ordem_grupos:
        sub = df[df[group_col] == grupo]
        header = {label_col_name: grupo}
        for c in value_cols:
            header[c] = None
        rows.append(header)

        sub_sorted = sub.sort_values(sort_col, ascending=False)
        for _, r in sub_sorted.iterrows():
            row = {label_col_name: f"    {r[sub_col]}"}
            for c in value_cols:
                row[c] = r[c]
            rows.append(row)

    return pd.DataFrame(rows)


def kpi_card(col, label: str, value: str, delta: str | None = None):
    """Helper para exibir um cartão de KPI padronizado."""
    with col:
        st.metric(label, value, delta)


def period_delta(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    agg: str = "sum",
    window_days: int = 15,
    fmt: str = "{:+.1f}%",
    mode: str = "pct_change",
) -> str | None:
    """
    Compara os últimos `window_days` dias com os `window_days` anteriores,
    usando a data mais recente disponível na própria coluna como referência
    (não "hoje", já que a planilha é histórica).

    mode="pct_change": variação percentual (padrão, para valores em unidades como t, km, kg/t).
    mode="abs_diff": diferença absoluta em pontos (para métricas que já são % —
                      evita "% de %" instável quando o valor de base oscila perto de zero).

    Retorna string tipo "▲ +8.4% vs período anterior" ou None se não houver
    dado suficiente para os dois períodos.
    """
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return None

    d = df[[date_col, value_col]].dropna()
    if d.empty:
        return None

    ultima_data = d[date_col].max()
    corte_atual = ultima_data - pd.Timedelta(days=window_days)
    corte_anterior = corte_atual - pd.Timedelta(days=window_days)

    atual = d[d[date_col] > corte_atual][value_col]
    anterior = d[(d[date_col] > corte_anterior) & (d[date_col] <= corte_atual)][value_col]

    if atual.empty or anterior.empty:
        return None

    val_atual = atual.sum() if agg == "sum" else atual.mean()
    val_anterior = anterior.sum() if agg == "sum" else anterior.mean()

    if mode == "abs_diff":
        variacao = val_atual - val_anterior
        seta = "▲" if variacao >= 0 else "▼"
        return f"{seta} {fmt.format(variacao)} p.p. ({window_days}d)"

    if not val_anterior:
        return None

    variacao = (val_atual - val_anterior) / val_anterior * 100
    seta = "▲" if variacao >= 0 else "▼"
    return f"{seta} {fmt.format(variacao)} ({window_days}d)"

