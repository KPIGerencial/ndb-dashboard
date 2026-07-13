"""
data_loader.py
==============
Camada única de acesso aos dados. Toda a aplicação lê a planilha Excel
através deste módulo — se a estrutura da planilha mudar (novas colunas,
nova aba), o ajuste é feito aqui, não em cada página.

A planilha é tratada como "banco de dados": cada aba = uma tabela.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

# Caminho padrão do arquivo. Pode ser sobrescrito pela variável de
# ambiente NDB_EXCEL_PATH, ou pelo upload feito na barra lateral.
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "KPIS_NDB.xlsx"

SHEETS = {
    "transporte": "BASETRANSPORTE",
    "colhedora": "BASECOLHEDORA",
    "transbordo": "BASETRANSBORDO",
    "disponibilidade": "DISPONIBILIDADE",
    "diesel": "BASEDIESEL",
    "colheita": "COLHEITA",
    "estimativa": "ESTIMATIVA",
    "meses": "Mes",
    "empresas": "BASEEMPRESA",
    "prod": "PROD.",   # nome real da aba, com ponto no final
    "atr": "BASEATR",  # Fazenda -> ATR
}


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


@st.cache_data(show_spinner="Lendo planilha...")
def load_excel(file_bytes_or_path) -> dict:
    """Lê todas as abas relevantes e devolve um dict {nome_logico: DataFrame}."""
    xls = pd.ExcelFile(file_bytes_or_path)
    data = {}
    for key, sheet_name in SHEETS.items():
        if sheet_name not in xls.sheet_names:
            continue
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = _clean_columns(df)
        df = df.dropna(how="all")
        data[key] = df

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

    return data


def get_data() -> dict:
    """
    Ponto único usado pelas páginas.
    Prioridade: arquivo enviado pelo usuário na sessão > arquivo padrão em /data.
    """
    uploaded = st.session_state.get("uploaded_file")
    if uploaded is not None:
        return load_excel(uploaded)
    return load_excel(str(DEFAULT_PATH))


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
