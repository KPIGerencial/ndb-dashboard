# Dashboard NDB — Colheita, Transporte, Transbordo e Estimativas

Dashboard interativo (estilo Power BI) construído em **Python + Streamlit**, com menu de
navegação no topo. Os dados vêm **exclusivamente do Google Sheets** (dois links — planilha
principal + histórico de safras) — não há nenhuma planilha `.xlsx` embutida no projeto.

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
│   ├── data_loader.py         # Camada única de leitura/cache do Google Sheets + helpers
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

O app NÃO tem nenhum `.xlsx` embutido. Os dados vêm de dois links do Google Sheets, fixos
em `src/data_loader.py`:

- `GOOGLE_SHEET_ID` — planilha principal (Transporte, Colhedoras, Transbordo, Disponibilidade,
  Diesel, Colheita, Estimativa, ATR, Cidades).
- `GOOGLE_SHEET_HISTORICO_ID` — histórico de safras (uma aba por ano, ex: 2026, 2025, 2024, 2023).

**Os dois precisam estar compartilhados como "Qualquer pessoa com o link" (Leitor)** —
Compartilhar → Acesso geral, no Google Sheets. Sem isso, o app para com uma mensagem de erro
em vez de mostrar dado desatualizado (não há mais fallback silencioso para arquivo local).

Se precisar testar com um arquivo pontual sem mexer no Sheets, ainda dá pra enviar um `.xlsx`
pelo uploader na barra lateral da Visão Geral — vale só para aquela sessão, não fica salvo
no projeto.

Para trocar de planilha, edite `GOOGLE_SHEET_ID`/`GOOGLE_SHEET_HISTORICO_ID` em
`src/data_loader.py` com o ID novo (a parte do link entre `/d/` e `/edit`).

As abas lidas hoje (nomes com variações de caixa já são reconhecidos automaticamente — ver
dicionário `SHEETS` em `src/data_loader.py`): `BaseTransporte`, `BaseColhedoras`,
`BaseTransbordo`, `Disponibilidade`, `BASEDIESEL`, `COLHEITA`, `ESTIMATIVA`, `Mes`,
`BASEEMPRESA`, `AGR500` (produção), `BASEART`/`BASEATR` (ATR), `CIDADES` (Cidade x UF).
Se a planilha ganhar novas abas ou colunas, ajuste em `src/data_loader.py` — o resto do app
não precisa mudar.

## Próximos passos sugeridos

- Autenticação simples (`streamlit-authenticator`) se o dashboard for para vários usuários.
- Publicar internamente via Streamlit Community Cloud, ou em servidor próprio com
  `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`.
