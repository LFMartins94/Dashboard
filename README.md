---
title: Dashboard Financeiro Multifonte
emoji: 💰
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.35.0"
app_file: app.py
pinned: false
---

# 💰 Dashboard de Ingestão Multifonte & Persistência

Dashboard financeiro unificado que ingere dados de múltiplas fontes (digitação manual, Excel, CSV, PDF e PowerPoint), persiste tudo em SQLite local e exibe análises interativas.

---

## 🏗️ Arquitetura

```
dashboard_financeiro/
├── app.py            # Interface Streamlit (entry point)
├── database.py       # Módulo SQLite: schema, leitura e escrita
├── parsers.py        # Parsers: Excel/CSV, PDF, PPTX
├── requirements.txt  # Dependências pinadas
└── README.md         # Este arquivo
```

| Módulo         | Responsabilidade                                      |
|----------------|-------------------------------------------------------|
| `database.py`  | Cria `financeiro.db`, funções de CRUD e retry policy  |
| `parsers.py`   | Extrai DataFrames de `.xlsx`, `.csv`, `.pdf`, `.pptx` |
| `app.py`       | Interface Streamlit: sidebar, upload, KPIs, tabelas   |

---

## ⚙️ Pré-requisitos

- Python **3.11+**
- Git instalado localmente
- Conta no [Hugging Face](https://huggingface.co) com acesso ao Spaces

---

## 🚀 Deploy no Hugging Face Spaces

### 1. Clonar e preparar o repositório local

```bash
# Clone seu Space vazio (substitua <usuario> e <nome-do-space>)
git clone https://huggingface.co/spaces/<usuario>/<nome-do-space>
cd <nome-do-space>

# Copie os arquivos do projeto
cp /caminho/do/projeto/* .
```

### 2. Commit e push

```bash
git add app.py database.py parsers.py requirements.txt README.md
git commit -m "feat: dashboard financeiro multifonte v1.0"
git push
```

O Hugging Face detecta o `sdk: streamlit` no frontmatter do README e faz o deploy automaticamente. O build instala as dependências do `requirements.txt` e executa `streamlit run app.py`.

### 3. Verificar o deploy

Acesse: `https://huggingface.co/spaces/<usuario>/<nome-do-space>`

O Space ficará disponível publicamente em ~2 minutos após o push.

---

## 🖥️ Execução local

```bash
# Instalar dependências
pip install -r requirements.txt

# Iniciar o app
streamlit run app.py
```

Acesse em: `http://localhost:8501`

---

## 📁 Formatos de arquivo suportados

| Formato  | Parser usado   | Colunas esperadas             |
|----------|----------------|-------------------------------|
| `.xlsx`  | pandas/openpyxl| `data`, `categoria`, `valor`  |
| `.csv`   | pandas         | `data`, `categoria`, `valor`  |
| `.pdf`   | pdfplumber     | Tabelas nativas ou texto livre|
| `.pptx`  | python-pptx    | Tabelas nativas ou texto livre|

> **Colunas ausentes** são marcadas como `NÃO ENCONTRADO` e salvas no banco sem interromper o fluxo.

---

## 🛡️ Guardrails implementados

- **Sem perda de dados:** toda escrita vai direto ao SQLite — nada fica apenas em `session_state`.
- **Retry policy:** conexões SQLite com até 5 tentativas e intervalo de 0.3s para evitar `SQLITE_BUSY`.
- **Resiliência de parsing:** erros por linha/slide são logados e ignorados; o app nunca trava.
- **Diagnóstico visual:** falhas de upload exibem `st.error()` com tipo de exceção e mensagem.
- **Precisão financeira:** valores armazenados com exatamente 2 casas decimais (`round(v, 2)`).

---

## 📊 Funcionalidades

- **Inserção manual** via sidebar: data, categoria (4 opções fixas), valor
- **Upload multifonte** com pré-visualização antes de importar
- **KPIs automáticos:** total, maior despesa, média, total de registros
- **Totalizadores por categoria** com gráfico de barras interativo (Plotly)
- **Evolução mensal** por categoria (gráfico de linha)
- **Tabela filtrável** com todas as colunas do banco

---

## 📄 Licença

MIT
