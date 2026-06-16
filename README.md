# ContaView — Ferramenta Contábil Inteligente

Sistema web para análise, conciliação e auditoria de dados contábeis.
Construído para uso individual por contadora, com acesso via navegador,
sem instalação e sem dependência de TI.

---

## Arquitetura do projeto

```
contaview/
├── app.py              # Interface Streamlit — entry point principal
├── auth.py             # Autenticação e controle de sessão
├── database.py         # Conexão Supabase/PostgreSQL via SQLAlchemy
├── parsers.py          # Leitura de arquivos: Excel, CSV, PDF, imagem
├── importacao.py       # Fluxo completo de importação com validações
├── conciliacao.py      # Conciliação de partidas dobradas C/D
├── auditoria.py        # Detecção de anomalias, duplicidades e erros
├── relatorios.py       # Exportação de relatórios em PDF e Excel
├── assistente.py       # Chat com IA via OpenAI — histórico persistido
├── requirements.txt    # Dependências Python
├── .env.example        # Modelo de variáveis de ambiente
├── .gitignore          # Protege credenciais e arquivos sensíveis
├── AGENTS.md           # Instruções para agentes de IA (OpenCode)
├── docs/
│   ├── DESIGN_SYSTEM.md   # Tokens de cor, layout e regras visuais
│   └── PROMPTS_ETAPAS.md  # Guia de construção por etapas
└── README.md           # Este arquivo
```

| Módulo | Responsabilidade |
|---|---|
| `app.py` | Interface Streamlit: navegação, layout, autenticação, tema dark/light |
| `auth.py` | Login por senha via `st.secrets`, controle de sessão |
| `database.py` | DDL, conexão segura com Supabase, bulk insert otimizado |
| `parsers.py` | 3 estratégias em cascata para ler planilhas de qualquer formato |
| `importacao.py` | Orquestra parsers + validações + banco em fluxo seguro |
| `conciliacao.py` | Verifica se cada C tem seu D correspondente (partidas dobradas) |
| `auditoria.py` | Duplicidades, anomalias estatísticas, campos inválidos |
| `relatorios.py` | PDF e Excel exportável com formatação profissional |
| `assistente.py` | Chat livre com OpenAI — responde qualquer dúvida contábil ou geral |

---

## Modelo de dados (Supabase / PostgreSQL)

### `empresas`
```sql
CREATE TABLE empresas (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(200) NOT NULL,
    cnpj        VARCHAR(18),
    ativa       BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `lancamentos`
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
    periodo         VARCHAR(7),
    sequencial_lote INTEGER,
    origem          VARCHAR(50) NOT NULL DEFAULT 'arquivo',
    arquivo_origem  VARCHAR(255),
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `conciliacoes`
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

### `ocorrencias_auditoria`
```sql
CREATE TABLE ocorrencias_auditoria (
    id              SERIAL PRIMARY KEY,
    empresa_id      INTEGER NOT NULL REFERENCES empresas(id),
    lancamento_id   INTEGER REFERENCES lancamentos(id),
    tipo_ocorrencia VARCHAR(50) NOT NULL,
    descricao       TEXT NOT NULL,
    severidade      VARCHAR(10) NOT NULL DEFAULT 'media',
    resolvida       BOOLEAN NOT NULL DEFAULT FALSE,
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `conversas`
```sql
CREATE TABLE conversas (
    id            SERIAL PRIMARY KEY,
    titulo        VARCHAR(200) NOT NULL DEFAULT 'Nova conversa',
    criado_em     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `mensagens`
```sql
CREATE TABLE mensagens (
    id           SERIAL PRIMARY KEY,
    conversa_id  INTEGER NOT NULL REFERENCES conversas(id) ON DELETE CASCADE,
    role         VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    conteudo     TEXT NOT NULL,
    criado_em    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## Pré-requisitos

- Python **3.11+**
- Conta no [Supabase](https://supabase.com) — plano gratuito suficiente
- Conta no [Streamlit Community Cloud](https://streamlit.io/cloud)
- Repositório no [GitHub](https://github.com) (privado recomendado)
- Chave de API da [OpenAI](https://platform.openai.com)

---

## Deploy no Streamlit Community Cloud

### 1. Subir o código para o GitHub

```bash
git add .
git commit -m "deploy inicial"
git push origin main
```

### 2. Conectar no Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io)
2. Clique em **New app**
3. Conecte o repositório GitHub
4. Selecione o arquivo principal: `app.py`
5. Antes de clicar em Deploy, vá em **Advanced settings → Secrets**

### 3. Configurar os Secrets

```toml
DATABASE_URL  = "postgresql://usuario:senha@host:6543/postgres?sslmode=require"
APP_USUARIO   = "nome_da_contadora"
APP_SENHA     = "senha_de_acesso"
OPENAI_API_KEY = "sk-proj-..."
```

### 4. Deploy

Clique em **Deploy** — o Streamlit instala o `requirements.txt` automaticamente.

---

## Execução local

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# preencher DATABASE_URL, APP_USUARIO, APP_SENHA, OPENAI_API_KEY
```

### 3. Rodar

```bash
streamlit run app.py
```

Acesse em: `http://localhost:8501`

---

## Formatos de planilha suportados

| Formato | Estratégia | Colunas detectadas |
|---|---|---|
| `.xlsx` / `.xls` | 3 estratégias em cascata | `data`, `conta_contabil`, `valor`, `tipo`, `historico`, `filial` |
| `.csv` | Detecção automática de separador | Idem |
| `.pdf` | Extração de tabelas nativas | Idem |
| `.png` / `.jpg` | OCR via EasyOCR | `valor`, `data` |

O parser usa 3 estratégias em cascata:
- **Estratégia 1** — Semicolon-delimited: linha única com campos separados por `;`
- **Estratégia 2** — Named header: varre o arquivo procurando cabeçalho com palavras-chave contábeis
- **Estratégia 3** — Headerless positional: detecta colunas por padrão de conteúdo (regex)

---

## Módulos funcionais

### Importação
- Upload de `.xlsx`, `.csv`, `.pdf`, imagem
- Detecção automática do formato da planilha
- Verificação de empresa antes do insert (cria se não existir)
- Bloqueio de importação duplicada por período com opção Substituir ou Cancelar
- Sequencial de lote injetado automaticamente para garantir ordem dos pares C/D

### Dashboard
- KPIs: total de débitos, créditos e saldo do período
- Gráfico de evolução mensal de lançamentos
- Distribuição por conta contábil e por filial
- Filtros por empresa e período

### Conciliação de partidas dobradas
- Verifica se cada lançamento C tem seu D correspondente
- Usa `sequencial_lote` para desempatar lançamentos com mesmo valor e data
- Relatório de pares conciliados e lançamentos sem par
- Exportação do relatório em Excel e PDF

### Auditoria inteligente
- Duplicidades: mesmo conjunto de data + conta + valor + tipo
- Lançamentos sem par C/D
- Anomalias de valor: acima de média + 3 desvios padrão
- Campos obrigatórios em branco
- Contas com formato inválido
- Classificação por severidade: alta, média, baixa
- Marcação de ocorrências como resolvidas

### Exportação de relatórios
- Excel com formatação profissional (datas DD/MM/AAAA, valores R$)
- PDF com cabeçalho, tabela e rodapé
- Disponível para: lançamentos, conciliação e auditoria

### Assistente de IA
- Chat livre integrado — funciona como o ChatGPT
- Responde qualquer dúvida contábil, fiscal, tributária ou geral
- Histórico de conversas salvo no banco entre sessões
- Lista de conversas anteriores na sidebar com opção de retomar ou deletar
- Título gerado automaticamente pela IA a partir da primeira mensagem
- Powered by OpenAI GPT-4o-mini

---

## Segurança

| Camada | Implementação |
|---|---|
| Credenciais | Nunca no código. Sempre via `st.secrets` (produção) ou `.env` (local) |
| Autenticação | Login por senha antes de qualquer tela, com bloqueio total sem login |
| Banco de dados | Conexão SSL obrigatória, chave `service_role` apenas no backend |
| Git | `.gitignore` protege `.env`, `*.key`, `secrets/`, `__pycache__/` |
| Backup | Supabase realiza backup automático diário no plano gratuito |

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

## Dependências (`requirements.txt`)

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
openai
```

---

## Licença

MIT — uso livre para fins pessoais e profissionais.
