# 💰 Dashboard de Ingestão Multifonte & Persistência

Dashboard financeiro unificado que ingere dados de múltiplas fontes (digitação manual, comprovantes por foto/câmera, Excel, CSV, PDF e PowerPoint), persiste tudo em PostgreSQL (Supabase) e exibe análises interativas.

---

## 🏗️ Arquitetura

```
dashboard_financeiro/
├── app.py            # Interface Streamlit (entry point)
├── database.py       # Módulo PostgreSQL/Supabase via SQLAlchemy
├── parsers.py        # Parsers: Imagens(OCR), Excel/CSV, PDF, PPTX
├── requirements.txt  # Dependências do projeto
└── README.md         # Este arquivo
```

| Módulo         | Responsabilidade                                      |
|----------------|-------------------------------------------------------|
| `database.py`  | Conexão com Supabase, DDL nativo e inserções otimizadas em lote |
| `parsers.py`   | Extrai DataFrames e dicionários de `.png/.jpg`, `.xlsx`, `.csv`, `.pdf`, `.pptx` |
| `app.py`       | Interface Streamlit: temas, sidebar, upload de arquivos, OCR de imagens, KPIs, tabelas   |

---

## ⚙️ Pré-requisitos

- Python **3.11+**
- Git instalado localmente
- Conta no [GitHub](https://github.com)
- Conta no [Streamlit Community Cloud](https://streamlit.io/cloud)
- Projeto criado no [Supabase](https://supabase.com) com um banco de dados PostgreSQL

---

## 🚀 Deploy no Streamlit Community Cloud

### 1. Preparar o Repositório no GitHub

Suba todo o código deste projeto para um repositório público ou privado no GitHub.

### 2. Configurar o Streamlit Cloud

1. Acesse o painel do Streamlit Community Cloud.
2. Clique em **New app** e conecte seu repositório GitHub.
3. Selecione o branch (ex: `main`) e o arquivo principal `app.py`.
4. Antes de clicar em *Deploy*, clique em **Advanced settings**.
5. Na seção **Secrets**, adicione a string de conexão do seu Supabase:
   ```toml
   DATABASE_URL = "postgresql://<user>:<password>@<host>:5432/<dbname>"
   ```
6. Clique em **Deploy**.

O Streamlit instalará as dependências do `requirements.txt` automaticamente.

---

## 🖥️ Execução Local

### 1. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto (ou configure no seu terminal) com a URL do seu Supabase:

```bash
export DATABASE_URL="postgresql://usuario:senha@host:5432/postgres"
```

### 2. Rodar a aplicação

```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar o app
streamlit run app.py
```

Acesse em: `http://localhost:8501`

---

## 📁 Formatos de Arquivo Suportados

| Formato  | Parser usado   | Colunas / Dados Esperados             |
|----------|----------------|-------------------------------|
| `.png, .jpg, .jpeg` | easyocr | Escaneia e extrai: `Valor`, `Data`, `Hora` |
| `.xlsx`  | pandas/openpyxl| `data`, `categoria`, `valor`  |
| `.csv`   | pandas         | `data`, `categoria`, `valor`  |
| `.pdf`   | pdfplumber     | Tabelas nativas ou texto livre|
| `.pptx`  | python-pptx    | Tabelas nativas ou texto livre|

> **Colunas ausentes** são marcadas como `NÃO ENCONTRADO` e salvas no banco sem interromper o fluxo.

---

## 🛡️ Segurança e Resiliência

- **Direct Connection PostgreSQL:** Usa parâmetros no SQLAlchemy (`pool_size`, `pool_pre_ping`) otimizados para Supabase.
- **OCR Fallback:** O módulo `easyocr` carrega sob demanda, impedindo crashes se houver erro de carregamento inicial.
- **Bulk Insert Atômico:** Dados enviados em lote com método `to_sql(method="multi")` do pandas.
- **Segurança de Credentials:** Não salva senhas no código, lendo estritamente via `os.getenv`.

---

## 📊 Funcionalidades

- **Múltiplos Temas (Dark/Light):** Alternância instantânea via barra lateral.
- **Leitura de Comprovantes (Foto/Câmera):** OCR para extrair valor e data de notas fiscais.
- **Inserção Manual** via sidebar rápida.
- **Upload Multifonte** em lote.
- **KPIs Automáticos e Dashboards** utilizando Plotly.

---

## 📄 Licença

MIT
