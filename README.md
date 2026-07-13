# Dashboard NDB — Colheita, Transporte, Transbordo e Estimativas

Dashboard interativo (estilo Power BI) construído em **Python + Streamlit**, que lê a planilha
`KPIS_-_NDB.xlsx` diretamente como fonte de dados — sem necessidade de banco de dados externo.

## Estrutura do projeto

```
ndb_dashboard/
├── app.py                          # Visão Executiva (Home + Colheita Analítico Geral unificados)
├── pages/
│   ├── 2_🚛_Transporte.py
│   ├── 3_🔄_Transbordo.py
│   ├── 4_⚙️_Disponibilidade.py
│   ├── 5_⛽_Diesel.py
│   └── 6_🚜_Colhedoras.py
├── src/
│   └── data_loader.py         # Camada única de leitura/cache do Excel + helpers de resumo por frota
├── data/
│   └── KPIS_NDB.xlsx          # Planilha usada como "banco de dados"
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

## Atualizando os dados

- Para usar uma planilha mais recente sem mexer no código, basta enviar o novo arquivo `.xlsx`
  pelo uploader na barra lateral — o dashboard recarrega tudo automaticamente.
- Para trocar o arquivo padrão, substitua `data/KPIS_NDB.xlsx` mantendo o mesmo nome (ou
  ajuste `DEFAULT_PATH` em `src/data_loader.py`).
- As abas lidas hoje são: `BASETRANSPORTE`, `BASECOLHEDORA`, `BASETRANSBORDO`,
  `DISPONIBILIDADE`, `BASEDIESEL`, `COLHEITA`, `ESTIMATIVA`, `Mes`, `BASEEMPRESA`.
  Se a planilha ganhar novas abas ou colunas, adicione/ajuste em `src/data_loader.py`
  (dicionário `SHEETS`) — o resto do app não precisa mudar.

## Próximos passos sugeridos

- Autenticação simples (`streamlit-authenticator`) se o dashboard for para vários usuários.
- Agendar atualização automática do arquivo Excel (ex: sincronizar com OneDrive/SharePoint).
- Publicar internamente via Streamlit Community Cloud, ou em servidor próprio com
  `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`.
