# Mentor Agro ERP — Colheita, Transporte, Transbordo e Estimativas

Dashboard interativo (estilo Power BI) construído em **Python + Streamlit**, com menu de
navegação no topo. Os dados vêm **exclusivamente do Dropbox** (vários links, um `.xlsx` por
tabela/grupo de tabelas) — não há nenhuma planilha embutida no projeto.

## Estrutura do projeto

```
ndb_dashboard/
├── app.py                        # Router: menu no topo (st.navigation position="top")
├── views/
│   ├── visao_geral.py             # Visão Executiva (página padrão)
│   └── historico_safras.py        # Histórico de Safras (planilha separada, uma aba por ano)
├── pages/
│   ├── transporte.py
│   ├── transbordo.py
│   ├── disponibilidade.py
│   ├── diesel.py
│   └── colhedoras.py
├── src/
│   ├── data_loader.py         # Camada única de leitura/cache do Dropbox + helpers
│   ├── weather.py             # Previsão do tempo (Open-Meteo) — grid na sidebar
│   ├── map_view.py            # Mapa por estado (IBGE) com fallback por fazenda
│   └── theme.py               # CSS compartilhado (visual profissional consistente)
├── .streamlit/config.toml     # Tema visual (dark, inspirado nos modelos de referência)
└── requirements.txt
```

## Como rodar no VS Code

1. Abra a pasta `ndb_dashboard` no VS Code.
2. Crie um ambiente virtual (recomendado) e ative:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Rode o app (terminal integrado do VS Code):
   ```bash
   streamlit run app.py
   ```
5. O navegador abrirá automaticamente em `http://localhost:8501`.

## Fonte de dados — só pelo link

O app NÃO tem nenhum `.xlsx` embutido. Os dados vêm de vários links do Dropbox, fixos em
`src/data_loader.py` (dicionário `DROPBOX_URLS` + `DROPBOX_HISTORICO_URL`):

- `KPIS-COLHEITA-TRANSPORTE-OK.xlsx` — planilha principal (Transporte, Colhedoras,
  Transbordo, Disponibilidade, Diesel, Colheita, Meses, Empresas).
- `AGR500.xlsx` — produção (aba AGR500).
- `BASE-ART.xlsx` — ATR (aba BASEATR/BASEART).
- `CIDADES.xlsx` — cruzamento Cidade x Estado (UF).
- `BASE-ESTIMATIVAS.xlsx` — estimativas de safra.
- `SAFRAS-COLHEITA.xlsx` — histórico de safras (uma aba por ano, ex: 2026, 2025, 2024, 2023).

**Todos os links precisam continuar compartilhados publicamente** (o link "com acesso
geral" do Dropbox, o parâmetro `?dl=0` na URL) — o app converte automaticamente para
download direto (`dl=1`). Sem isso, o app para com uma mensagem de erro em vez de mostrar
dado desatualizado (não há fallback silencioso para arquivo local).

Se precisar testar com um arquivo pontual sem mexer no Dropbox, ainda dá pra enviar um
`.xlsx` pelo uploader na barra lateral da Visão Geral — vale só para aquela sessão, não
fica salvo no projeto.

Para trocar algum link, edite `DROPBOX_URLS`/`DROPBOX_HISTORICO_URL` em
`src/data_loader.py` com a URL nova (o `rlkey` muda quando o arquivo é recompartilhado).

As abas lidas hoje (nomes com variações de caixa já são reconhecidos automaticamente — ver
dicionário `SHEETS` em `src/data_loader.py`): `BaseTransporte`, `BaseColhedoras`,
`BaseTransbordo`, `Disponibilidade`, `BASEDIESEL`, `COLHEITA`, `ESTIMATIVA`, `Mes`,
`BASEEMPRESA`, `AGR500` (produção), `BASEART`/`BASEATR` (ATR — a coluna de Fazenda nessa
aba pode vir como `Fundo Agrícola`, tratada como equivalente), `CIDADES` (Cidade x UF).
Se a planilha ganhar novas abas ou colunas, ajuste em `src/data_loader.py` — o resto do app
não precisa mudar.
