# ContaView — Ferramenta Contabil Inteligente

Sistema web full-stack para analise, conciliacao e auditoria de dados
contabeis. Construido em [Reflex (Python)](https://reflex.dev) com
banco de dados Supabase (PostgreSQL).

---

## Arquitetura do projeto

```
contaview/
└── contaview/
    ├── contaview.py          # Entry point — registra rx.App e as paginas
    ├── styles.py             # Tokens de cor MINERAL e ECLIPSE
    ├── state/
    │   ├── auth_state.py     # Login, logout, sessao
    │   ├── tema_state.py     # Alternancia dark/light
    │   ├── dados_state.py    # Filtros de empresa/periodo, cache de lancamentos
    │   └── chat_state.py     # Conversas, mensagens, conversa ativa
    ├── components/
    │   ├── sidebar.py        # Sidebar completa
    │   ├── nav_item.py       # Item de navegacao reutilizavel
    │   ├── conversa_item.py  # Item de conversa com hover e exclusao
    │   ├── kpi_card.py       # Card de metrica
    │   ├── alerta.py         # Alertas de auditoria por severidade
    │   └── filtros.py        # Seletores de empresa e periodo
    ├── pages/
    │   ├── login.py
    │   ├── painel.py
    │   ├── lancamentos.py
    │   ├── importar.py
    │   ├── conciliacao.py
    │   ├── auditoria.py
    │   ├── relatorios.py
    │   └── assistente.py
    └── logic/                # Logica de negocio (Python puro, sem Reflex)
        ├── database.py       # Conexao Supabase/PostgreSQL via SQLAlchemy
        ├── parsers.py        # 4 estrategias em cascata para ler planilhas
        ├── importacao.py     # Fluxo completo de importacao com validacoes
        ├── conciliacao.py    # Conciliacao de partidas dobradas C/D
        ├── auditoria.py      # Deteccao de anomalias, duplicidades e erros
        ├── relatorios.py     # Exportacao de relatorios em PDF e Excel
        ├── assistente.py     # Chat com IA via OpenAI
        ├── leitor_xml_legado.py      # Leitor de XML SpreadsheetML (.xls)
        ├── mapeamento_colunas.py     # Fallback fuzzy via rapidfuzz
        └── assistente_ferramentas.py # Ferramentas de consulta para o assistente
├── assets/
│   └── styles.css            # CSS global para hover e transicoes
├── rxconfig.py
├── requirements.txt
├── .env.example
├── .gitignore
├── AGENTS.md
└── docs/
    ├── DESIGN_SYSTEM.md
    └── PROMPTS_ETAPAS.md
```

| Modulo | Responsabilidade |
|---|---|
| `contaview.py` | Entry point Reflex: registra app e rotas |
| `pages/` | 8 paginas: login, painel, lancamentos, importar, conciliacao, auditoria, relatorios, assistente |
| `state/` | 4 classes de estado: AuthState, TemaState, DadosState, ChatState |
| `logic/` | Logica de negocio reaproveitada (Python puro, sem dependencia Reflex) |

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
    tipo            CHAR(1) CHECK (tipo IS NULL OR tipo IN ('C', 'D')),
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

## Pre-requisitos

- Python **3.11+**
- Conta no [Supabase](https://supabase.com) — plano gratuito suficiente
- Conta na [Reflex Cloud](https://reflex.dev) (opcional para producao)
- Repositorio no [GitHub](https://github.com) (privado recomendado)
- Chave de API da [OpenAI](https://platform.openai.com)

---

## Execucao local

### 1. Criar ambiente virtual e instalar dependencias

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### 2. Configurar variaveis de ambiente

```bash
cp .env.example .env
# preencher DATABASE_URL, APP_USUARIO, APP_SENHA, OPENAI_API_KEY
```

### 3. Inicializar e rodar

```bash
reflex init
reflex run
```

Acesse em: `http://localhost:3000`

---

## Deploy na Reflex Cloud

```bash
reflex deploy
```

Documentacao oficial: [reflex.dev/docs/hosting/deploy-quick-start/](https://reflex.dev/docs/hosting/deploy-quick-start/)

Configurar variaveis de ambiente no painel da Reflex Cloud:
```
DATABASE_URL
APP_USUARIO
APP_SENHA
OPENAI_API_KEY
```

---

## Formatos de planilha suportados

| Formato | Estrategia | Colunas detectadas |
|---|---|---|
| `.xlsx` / `.xls` (binario) | 3 estrategias em cascata | `data`, `conta_contabil`, `valor`, `tipo`, `historico`, `filial` |
| `.xls` (XML SpreadsheetML) | Deteccao por cabecalho XML | Idem |
| `.csv` | Deteccao automatica de separador | Idem |
| `.pdf` | Extracao de tabelas nativas | Idem |
| `.png` / `.jpg` | OCR via EasyOCR | `valor`, `data` |

O parser usa 4 estrategias em cascata:
- **Estrategia 1** — Semicolon-delimited: linha unica com campos separados por `;`
- **Estrategia 2** — Named header: varre o arquivo procurando cabecalho com palavras-chave contabeis
- **Estrategia 3** — Headerless positional: detecta colunas por padrao de conteudo (regex)
- **Estrategia 4** — Fallback fuzzy via rapidfuzz: mapeia colunas com `debito`/`credito`

---

## Modulos funcionais

### Importacao
- Upload de `.xlsx`, `.csv`, `.pdf`, imagem, `.xls` XML legado
- Deteccao automatica do formato da planilha (4 estrategias)
- Fallback fuzzy com mapeamento de colunas debito/credito
- Verificacao de empresa antes do insert (cria se nao existir)
- Bloqueio de importacao duplicada por periodo com opcao Substituir ou Cancelar
- Sequencial de lote injetado automaticamente

### Dashboard
- KPIs: total de debitos, creditos e saldo do periodo
- Grafico de evolucao mensal de lancamentos
- Distribuicao por conta contabil e por filial
- Filtros por empresa e periodo

### Conciliacao de partidas dobradas
- Verifica se cada lancamento C tem seu D correspondente
- Usa `sequencial_lote` para desempatar lancamentos com mesmo valor e data
- Relatorio de pares conciliados e lancamentos sem par
- Exportacao do relatorio em Excel e PDF

### Auditoria inteligente
- Duplicidades: mesmo conjunto de data + conta + valor + tipo
- Lancamentos sem par C/D
- Anomalias de valor: acima de media + 3 desvios padrao
- Campos obrigatorios em branco
- Contas com formato invalido
- Classificacao por severidade: alta, media, baixa
- Marcacao de ocorrencias como resolvidas

### Exportacao de relatorios
- Excel com formatacao profissional (datas DD/MM/AAAA, valores R$)
- PDF com cabecalho, tabela e rodape
- Disponivel para: lancamentos, conciliacao e auditoria

### Assistente de IA
- Chat livre integrado — funciona como o ChatGPT
- Responde qualquer duvida contabil, fiscal, tributaria ou geral
- Ferramentas de consulta a dados contabeis (saldo, debitos, creditos, conciliacao, auditoria)
- Historico de conversas salvo no banco entre sessoes
- Lista de conversas anteriores na sidebar com opcao de retomar ou deletar
- Titulo gerado automaticamente pela IA a partir da primeira mensagem
- Powered by OpenAI GPT-4o-mini

---

## Seguranca

| Camada | Implementacao |
|---|---|
| Credenciais | Nunca no codigo. Sempre via `os.getenv()` / variaveis de ambiente |
| Autenticacao | Login por senha antes de qualquer tela, com bloqueio total sem login |
| Banco de dados | Conexao SSL obrigatoria, SQLAlchemy com pool |
| Git | `.gitignore` protege `.env`, `venv/`, `__pycache__/` |
| Backup | Supabase realiza backup automatico diario no plano gratuito |

---

## Dependencias (`requirements.txt`)

```
reflex
pandas
plotly
openpyxl
python-pptx
pdfplumber
psycopg2-binary
SQLAlchemy
Pillow
xlsxwriter
reportlab
python-dotenv
openai
rapidfuzz
```

---

## Licenca

MIT — uso livre para fins pessoais e profissionais.
