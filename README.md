# 📊 ContaView — Ferramenta Contábil Inteligente

Sistema web para análise, conciliação e auditoria de dados contábeis, construído especificamente para uso individual por contadora. Acesso via navegador, sem instalação, sem dependência de TI.

---

## 🏗️ Arquitetura do projeto

```
contaview/
├── app.py              # Interface Streamlit — entry point principal
├── database.py         # Conexão Supabase/PostgreSQL via SQLAlchemy
├── parsers.py          # Ingestão multifonte: Excel, CSV, PDF, PPTX, Imagem (OCR)
├── auth.py             # Controle de autenticação e sessão
├── conciliacao.py      # Módulo de conciliação de partidas dobradas
├── auditoria.py        # Módulo de detecção de anomalias, duplicidades e erros
├── relatorios.py       # Exportação de relatórios em PDF e Excel
├── assistente.py       # Assistente de IA (perguntas em linguagem natural)
├── requirements.txt    # Dependências Python
├── .env.example        # Modelo de variáveis de ambiente (nunca suba o .env real)
├── .gitignore          # Protege credenciais e arquivos sensíveis
└── README.md           # Este arquivo
```

| Módulo           | Responsabilidade                                                                 |
|------------------|---------------------------------------------------------------------------------|
| `app.py`         | Interface Streamlit: navegação por abas, sidebar, autenticação, upload de arquivos |
| `database.py`    | DDL, conexão segura com Supabase, bulk insert otimizado, leitura histórica       |
| `parsers.py`     | 3 estratégias em cascata para ler planilhas de qualquer formato estrutural       |
| `auth.py`        | Login por senha via `st.secrets`, controle de sessão com token JWT               |
| `conciliacao.py` | Verificação de partidas C/D, identificação de pares sem correspondência          |
| `auditoria.py`   | Duplicidades, anomalias estatísticas, campos inválidos, contas fora do plano     |
| `relatorios.py`  | Geração de PDF e Excel exportável para qualquer visão do sistema                 |
| `assistente.py`  | Integração com LLM (Gemini/Claude/OpenAI/DeepSeek) para perguntas sobre os dados |

---

## 🗄️ Modelo de dados (Supabase / PostgreSQL)

### Tabela `empresas`
Cada empresa do grupo contábil é registrada aqui.

```sql
CREATE TABLE empresas (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(200) NOT NULL,
    cnpj        VARCHAR(18),
    ativa       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Tabela `lancamentos`
Coração do sistema — espelha o formato real das planilhas contábeis (partidas dobradas).

```sql
CREATE TABLE lancamentos (
    id              SERIAL PRIMARY KEY,
    empresa_id      INTEGER NOT NULL REFERENCES empresas(id),
    data            DATE NOT NULL,
    conta_contabil  VARCHAR(50) NOT NULL,
    valor           NUMERIC(14, 2) NOT NULL,
    tipo            CHAR(1) NOT NULL CHECK (tipo IN ('C', 'D')),
    historico       TEXT,
    filial          VARCHAR(20),
    periodo         VARCHAR(7),           -- formato: YYYY-MM
    origem          VARCHAR(50) NOT NULL DEFAULT 'arquivo',
    arquivo_origem  VARCHAR(255),
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lancamentos_empresa   ON lancamentos(empresa_id);
CREATE INDEX idx_lancamentos_data      ON lancamentos(data);
CREATE INDEX idx_lancamentos_conta     ON lancamentos(conta_contabil);
CREATE INDEX idx_lancamentos_periodo   ON lancamentos(periodo);
CREATE INDEX idx_lancamentos_tipo      ON lancamentos(tipo);
```

### Tabela `conciliacoes`
Registra o resultado de cada processo de conciliação executado.

```sql
CREATE TABLE conciliacoes (
    id              SERIAL PRIMARY KEY,
    empresa_id      INTEGER NOT NULL REFERENCES empresas(id),
    periodo         VARCHAR(7) NOT NULL,
    total_pares     INTEGER NOT NULL DEFAULT 0,
    pares_ok        INTEGER NOT NULL DEFAULT 0,
    pares_com_erro  INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'pendente',
    executado_em    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Tabela `ocorrencias_auditoria`
Cada anomalia, duplicidade ou erro encontrado pelo módulo de auditoria.

```sql
CREATE TABLE ocorrencias_auditoria (
    id              SERIAL PRIMARY KEY,
    empresa_id      INTEGER NOT NULL REFERENCES empresas(id),
    lancamento_id   INTEGER REFERENCES lancamentos(id),
    tipo_ocorrencia VARCHAR(50) NOT NULL,   -- ex: 'duplicidade', 'sem_par', 'anomalia_valor'
    descricao       TEXT NOT NULL,
    severidade      VARCHAR(10) NOT NULL DEFAULT 'media',  -- 'baixa', 'media', 'alta'
    resolvida       BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## ⚙️ Pré-requisitos

- Python **3.11+**
- Conta no [Supabase](https://supabase.com) — plano gratuito suficiente para uso individual
- Conta no [Hugging Face](https://huggingface.co) ou [Streamlit Community Cloud](https://streamlit.io/cloud) para hospedagem gratuita
- Repositório no [GitHub](https://github.com) (privado recomendado)

---

## 🚀 Deploy no Hugging Face Spaces

### 1. Preparar o repositório

```bash
git clone https://github.com/seu-usuario/contaview.git
cd contaview
```

### 2. Criar o arquivo `Dockerfile` (necessário no Hugging Face)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
```

### 3. Configurar os Secrets no Hugging Face

No painel do Space, vá em **Settings → Repository secrets** e adicione:

```
DATABASE_URL = postgresql://usuario:senha@host:6543/postgres?sslmode=require
APP_PASSWORD  = sua_senha_de_acesso
LLM_API_KEY   = sua_chave_do_gemini_ou_outro
```

### 4. Subir o código e fazer o deploy

```bash
git add .
git commit -m "deploy inicial"
git push origin main
```

O Hugging Face detecta o `Dockerfile` e faz o build automaticamente.

---

## 🖥️ Execução local

### 1. Clonar e instalar dependências

```bash
git clone https://github.com/seu-usuario/contaview.git
cd contaview
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o arquivo de exemplo e preencha com suas credenciais reais:

```bash
cp .env.example .env
```

Conteúdo do `.env`:
```bash
DATABASE_URL=postgresql://usuario:senha@host:6543/postgres?sslmode=require
APP_PASSWORD=sua_senha_local
LLM_API_KEY=sua_chave_de_api
```

### 3. Iniciar a aplicação

```bash
streamlit run app.py
```

Acesse em: `http://localhost:8501`

---

## 📁 Formatos de planilha suportados

| Formato | Estratégia de leitura | Campos detectados |
|---|---|---|
| `.xlsx` / `.xls` | 3 estratégias em cascata | `data`, `conta_contabil`, `valor`, `tipo`, `historico`, `filial` |
| `.csv` | Detecção automática de separador (`;` ou `,`) | Idem acima |
| `.pdf` | Extração de tabelas nativas + texto livre | Idem acima |
| `.pptx` | Extração de tabelas por slide | Idem acima |
| `.png` / `.jpg` | OCR via EasyOCR | `valor`, `data`, `hora` |

> O parser usa **3 estratégias em cascata**:
> - **Estratégia 1** — Semicolon-delimited: detecta quando toda a linha está em uma célula separada por `;` (formato das planilhas do sistema contábil atual)
> - **Estratégia 2** — Named header detection: varre o arquivo procurando uma linha de cabeçalho com palavras-chave contábeis
> - **Estratégia 3** — Headerless positional: detecta colunas por padrão de conteúdo (regex de data, regex de valor monetário)

---

## 🧩 Módulos funcionais

### 📂 Upload e ingestão
Arraste e solte arquivos diretamente na interface. O sistema detecta o formato, aplica o parser correto, exibe preview dos dados e aguarda confirmação antes de salvar.

### 📊 Dashboard contábil
- KPIs por empresa e período: total de débitos, total de créditos, saldo
- Gráfico de evolução mensal de lançamentos
- Distribuição por conta contábil e por filial
- Filtros interativos: empresa, período, conta, tipo (C/D)

### 🔁 Conciliação de partidas dobradas
- Verifica se cada lançamento **C** tem um **D** correspondente (mesma data + mesmo valor)
- Lista os pares encontrados, os pares com diferença de centavos e os lançamentos sem par
- Gera relatório de conciliação exportável

### 🔍 Auditoria inteligente
Ao importar uma planilha, o sistema verifica automaticamente:
- **Duplicidades** — mesmo conjunto de (data + conta + valor + tipo) repetido
- **Sem par** — lançamento C ou D sem contrapartida correspondente
- **Anomalias de valor** — valores estatisticamente fora do padrão (desvio padrão)
- **Campos inválidos** — datas impossíveis, valores zerados, histórico em branco
- **Contas desconhecidas** — código de conta contábil fora do plano cadastrado
Cada ocorrência recebe severidade (baixa / média / alta) e fica registrada para acompanhamento.

### 📋 Histórico de lançamentos
Tabela interativa com todos os lançamentos salvos, filtros por empresa, período, conta e tipo, com busca por histórico.

### 📤 Exportação de relatórios
Qualquer visão do sistema pode ser exportada com um clique:
- **Excel** (`.xlsx`) — formatação profissional com `xlsxwriter`
- **PDF** — layout limpo com `reportlab`

### 🤖 Assistente de IA
Chat integrado onde a contadora pergunta sobre os dados em português:
> *"Quais contas tiveram mais lançamentos em maio?"*
> *"Tem algum lançamento duplicado no período atual?"*
> *"Qual o saldo da conta 110401001?"*

O assistente recebe apenas **resumos agregados** dos dados — nunca dados brutos, CPFs ou informações sensíveis. Compatível com qualquer LLM via troca de uma linha no código: **Gemini** (gratuito para começar), **Claude**, **GPT-4o** ou **DeepSeek**.

---

## 🛡️ Segurança

| Camada | Implementação |
|---|---|
| **Credenciais** | Nunca no código-fonte. Sempre via `st.secrets` (produção) ou `.env` (local) |
| **Autenticação** | Login por senha no `app.py` antes de qualquer tela, com sessão por token |
| **Banco de dados** | Conexão SSL obrigatória (`sslmode=require`), chave `service_role` apenas no backend |
| **Dados na IA** | O assistente recebe apenas resumos agregados, nunca dados brutos |
| **Git** | `.gitignore` protege `.env`, `*.key`, `secrets/` e arquivos de cache |
| **Backup** | O Supabase realiza backup automático diário no plano gratuito |

### `.gitignore` mínimo obrigatório

```
.env
*.key
secrets/
__pycache__/
*.pyc
.streamlit/secrets.toml
```

---

## 📦 Dependências (`requirements.txt`)

```
streamlit
pandas
plotly
openpyxl
python-pptx
pdfplumber
psycopg2-binary
SQLAlchemy
easyocr
Pillow
xlsxwriter
reportlab
python-dotenv
```

---

## 🗺️ Roadmap de construção

| Etapa | Módulo | Status |
|---|---|---|
| 1 | Schema do banco (`lancamentos`, `empresas`, `conciliacoes`, `ocorrencias_auditoria`) | 🔲 A fazer |
| 2 | `database.py` atualizado para o novo schema | 🔲 A fazer |
| 3 | `auth.py` — login com senha + controle de sessão | 🔲 A fazer |
| 4 | `parsers.py` — extensão para mapear `conta_contabil`, `tipo`, `historico`, `filial` | 🔲 A fazer |
| 5 | `app.py` — estrutura base com autenticação e navegação por abas | 🔲 A fazer |
| 6 | Dashboard contábil com KPIs e gráficos Plotly | 🔲 A fazer |
| 7 | `conciliacao.py` — verificação de partidas dobradas | 🔲 A fazer |
| 8 | `auditoria.py` — detecção de anomalias e duplicidades | 🔲 A fazer |
| 9 | `relatorios.py` — exportação PDF e Excel | 🔲 A fazer |
| 10 | `assistente.py` — chat com LLM sobre os dados | 🔲 A fazer |

---

## 📄 Licença

MIT — uso livre para fins pessoais e profissionais.
