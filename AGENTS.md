# AGENTS.md — ContaView (Reflex)

Instruções obrigatórias para agentes de IA que trabalham neste projeto.
Leia este arquivo inteiro antes de modificar qualquer código.

---

## Início obrigatório de toda sessão

Antes de qualquer tarefa, carregar sempre:

```
carregue as skills reflex-docs, setup-python-env e reflex-process-management
depois leia AGENTS.md e docs/DESIGN_SYSTEM.md
```

---

## O que é este projeto

ContaView é uma ferramenta contábil full-stack construída em Reflex (Python).
É usada por uma única contadora que acessa via navegador.
Não é um sistema multi-tenant. Não é uma API pública. Não é um SaaS.

**Stack:**
- Frontend + Backend: Reflex (Python → compila para React + FastAPI internamente)
- Banco de dados: Supabase (PostgreSQL)
- Hospedagem: Reflex Cloud (plano gratuito)
- Assistente de IA: OpenAI GPT-4o-mini

---

## Linguagem e convenções

- Todo o código é escrito em **português PT-BR**: variáveis, funções, classes,
  comentários e mensagens da interface.
- Nomes de arquivos: snake_case em português (`importacao.py`, não `import_module.py`).
- Nomes de colunas do banco: snake_case em português (`conta_contabil`, `sequencial_lote`).
- Mensagens de erro e sucesso: português formal, sem emojis, sem gírias.
- Datas exibidas sempre como `DD/MM/AAAA`. Armazenadas como `DATE` no banco.
- Períodos exibidos sempre como `MM/AAAA`. Armazenados como `AAAA-MM` no banco.
- Valores monetários exibidos sempre como `R$ 0.000,00`. Armazenados como `NUMERIC(14,2)`.

---

## Estrutura de arquivos — responsabilidades fixas

Não mova lógica entre arquivos sem justificativa explícita.

```
contaview/
├── contaview/
│   ├── contaview.py          # Entry point — registra rx.App e as páginas
│   ├── styles.py             # Tokens de cor MINERAL e ECLIPSE
│   ├── state/
│   │   ├── auth_state.py     # Login, logout, sessão
│   │   ├── tema_state.py     # Alternância dark/light
│   │   ├── dados_state.py    # Filtros de empresa/período, cache de lançamentos
│   │   └── chat_state.py     # Conversas, mensagens, conversa ativa
│   ├── components/
│   │   ├── sidebar.py        # Sidebar completa
│   │   ├── nav_item.py       # Item de navegação reutilizável
│   │   ├── conversa_item.py  # Item de conversa com hover e exclusão
│   │   ├── kpi_card.py       # Card de métrica
│   │   ├── alerta.py         # Alertas de auditoria por severidade
│   │   └── filtros.py        # Seletores de empresa e período
│   ├── pages/
│   │   ├── login.py
│   │   ├── painel.py
│   │   ├── lancamentos.py
│   │   ├── importar.py
│   │   ├── conciliacao.py
│   │   ├── auditoria.py
│   │   ├── relatorios.py
│   │   └── assistente.py
│   └── logic/                # Reaproveitado do projeto anterior — não reescrever
│       ├── database.py
│       ├── parsers.py
│       ├── importacao.py
│       ├── conciliacao.py
│       ├── auditoria.py
│       ├── relatorios.py
│       └── assistente.py
├── assets/
│   └── styles.css            # CSS global para hover e transições
├── rxconfig.py
├── requirements.txt
├── .env.example
├── .gitignore
├── AGENTS.md                 # este arquivo
└── docs/
    ├── DESIGN_SYSTEM.md
    └── PROMPTS_ETAPAS.md
```

| Arquivo/pasta | Responsabilidade | Pode alterar? |
|---|---|---|
| `contaview.py` | Registra o app e as rotas | Sim |
| `styles.py` | Tokens de cor dos dois temas | Sim |
| `state/auth_state.py` | Login, logout, sessão | Sim — com cuidado |
| `state/tema_state.py` | Toggle dark/light | Sim |
| `state/dados_state.py` | Filtros e cache de dados | Sim |
| `state/chat_state.py` | Conversas e mensagens | Sim |
| `components/` | Componentes visuais reutilizáveis | Sim |
| `pages/` | Páginas da aplicação | Sim |
| `logic/` | Lógica de negócio reaproveitada | Sim — sem mudar assinaturas |
| `assets/styles.css` | Hover e transições CSS | Sim |
| `docs/DESIGN_SYSTEM.md` | Tokens e regras visuais | Não alterar sem instrução |
| `docs/PROMPTS_ETAPAS.md` | Guia de construção por etapas | Não alterar |

---

## Regras de arquitetura — nunca violar

### 1. Estado gerenciado exclusivamente via classes rx.State
Nunca usar variáveis globais Python, variáveis de módulo ou qualquer outra
forma de estado compartilhado entre requisições.
Cada classe de state tem responsabilidade única — não misturar domínios.

```
AuthState   → autenticação
TemaState   → tema visual
DadosState  → dados contábeis e filtros
ChatState   → conversas e mensagens do assistente
```

### 2. Toda importação passa pelo `logic/importacao.py`
Nenhum manipulador de evento em `state/dados_state.py` ou em qualquer
`page/` chama `database.salvar_lancamentos()` diretamente.
O fluxo obrigatório é:

```
page/importar.py → DadosState.executar_importacao()
                 → logic/importacao.executar_importacao()
                 → logic/database.salvar_lancamentos()
```

### 3. Verificar empresa antes de qualquer insert de lançamentos
Antes de salvar lançamentos, sempre chamar `logic/database.obter_ou_criar_empresa()`
para garantir que o `empresa_id` existe. Nunca inserir lançamento com
`empresa_id` que não foi verificado previamente.

### 4. Verificar duplicidade de período antes de salvar
Antes de qualquer bulk insert, chamar `logic/database.verificar_periodo_existente()`.
Se retornar `True`, exibir `rx.alert_dialog` com as opções "Substituir" e "Cancelar".
**Não existe opção de mesclar períodos.**

### 5. O campo `sequencial_lote` é obrigatório antes do insert
Sempre chamar `logic/importacao.injetar_sequencial_lote(df)` antes de
`logic/database.salvar_lancamentos()`.

### 6. Autenticação é verificada em toda página
Cada página verifica `AuthState.autenticado` e redireciona para `/`
se o usuário não estiver logado. Usar um decorator de proteção de rota
compartilhado ou `rx.cond` no topo de cada componente de página.

### 7. Credenciais nunca no código-fonte
Toda chave, senha ou URL de banco é lida via `rx.config` ou variáveis
de ambiente. Nunca hardcoded em nenhum arquivo.

### 8. Os módulos `logic/` não são reescritos — são chamados
Os arquivos em `logic/` são reaproveitados do projeto Streamlit anterior.
Eles não usam nenhuma API do Reflex — são Python puro com Pandas e SQLAlchemy.
Nunca importar `reflex` dentro de `logic/`.
Nunca importar `streamlit` dentro de `logic/` (remover se ainda existir).

### 9. Hover e transições são CSS — não lógica de state
Não usar `rx.State` para controlar opacidade de hover, cor de fundo
ao passar o mouse ou qualquer efeito visual de interação.
Esses efeitos ficam em `assets/styles.css` usando `:hover` nativo.

```css
/* Exemplo correto em assets/styles.css */
.conversa-item:hover { background-color: var(--card-bg); }
.conversa-item:hover .conversa-delete { opacity: 1; transition: opacity .15s; }
```

### 10. Tema é global e reativo
`TemaState.tema_escuro` é lido por todos os componentes.
Nenhuma página define estado de tema local.
Usar `rx.cond(TemaState.tema_escuro, ECLIPSE["token"], MINERAL["token"])`
diretamente nas props de estilo de cada componente.

### 11. O assistente nunca recebe dados brutos sensíveis
O chat do assistente é livre (responde qualquer dúvida contábil ou geral),
mas nenhuma função de `logic/` deve vazar CPFs, CNPJs individuais ou dados
nominais de terceiros para o contexto enviado à OpenAI.

### 12. Estilos ReportLab sempre definidos manualmente
Nunca usar `styles['small']` ou qualquer estilo que não seja dos nativos
do `getSampleStyleSheet()`: `Normal`, `Heading1`, `Heading2`, `Title`, `BodyText`.
Estilos customizados (rodapé, legenda) sempre via `ParagraphStyle`.

---

## Banco de dados — tabelas e colunas

### Tabelas existentes (não renomear, não remover colunas)

```
empresas          → id, nome, cnpj, ativa, criado_em

lancamentos       → id, empresa_id, data, conta_contabil, valor, tipo,
                    historico, filial, periodo, sequencial_lote, origem,
                    arquivo_origem, criado_em

conciliacoes      → id, empresa_id, periodo, total_pares, pares_ok,
                    pares_com_erro, status, executado_em

ocorrencias_auditoria → id, empresa_id, lancamento_id, tipo_ocorrencia,
                        descricao, severidade, resolvida, criado_em

conversas         → id, titulo, criado_em, atualizado_em

mensagens         → id, conversa_id, role, conteudo, criado_em
```

### Tipos obrigatórios

- `tipo` em `lancamentos`: sempre `'C'` ou `'D'`
- `periodo` em `lancamentos`: sempre `'AAAA-MM'`
- `severidade` em `ocorrencias_auditoria`: sempre `'alta'`, `'media'` ou `'baixa'`
- `role` em `mensagens`: sempre `'user'` ou `'assistant'`

---

## Interface — regras visuais

O design system completo está em `docs/DESIGN_SYSTEM.md`.
Leia esse arquivo antes de modificar qualquer componente ou página.

Resumo inegociável:

- Sem emojis em nenhuma parte da interface
- Sem texto em inglês na interface (labels, botões, mensagens, placeholders)
- Sidebar com largura fixa de 252px — navegação no topo, conversas roláveis no meio, footer no rodapé
- Ícone de excluir conversa aparece apenas no hover via CSS — nunca via state
- Filtros de empresa e período sempre no topo de páginas analíticas
- A página Assistente não exibe filtros de empresa ou período
- Toggle de tema fica no footer da sidebar, ao lado do botão de logout
- Gráficos Plotly respeitam os tokens de cor do tema ativo
- Inputs no dark mode: texto `#E8E8E8`, fundo `#1E2530`, borda `#3A4150`
- Exportações nunca incluem colunas técnicas (`id`, `empresa_id`,
  `sequencial_lote`, `origem`, `arquivo_origem`, `criado_em`)

---

## Secrets e variáveis de ambiente

### Local — arquivo `.env` na raiz

```bash
DATABASE_URL=postgresql://usuario:senha@host:6543/postgres?sslmode=require
APP_USUARIO=nome_da_contadora
APP_SENHA=senha_de_acesso
OPENAI_API_KEY=sk-proj-...
```

### Produção — Reflex Cloud

Configurar no painel do Reflex Cloud em Environment Variables:

```
DATABASE_URL
APP_USUARIO
APP_SENHA
OPENAI_API_KEY
```

---

## Dependências — o que pode e não pode adicionar

### Já presentes — não trocar de versão sem teste
```
reflex
pandas==2.2.2
plotly==5.22.0
openpyxl==3.1.5
python-pptx==1.0.2
pdfplumber==0.11.4
psycopg2-binary==2.9.9
SQLAlchemy==2.0.36
Pillow==10.4.0
xlsxwriter==3.2.0
reportlab==4.2.5
python-dotenv==1.0.1
openai==1.51.2
```

### Permitido adicionar
- Utilitários de formatação (`babel`, `python-dateutil`)

### Não adicionar sem aprovação explícita
- Nenhum cliente de LLM além do `openai` já configurado
- Nenhum ORM além do SQLAlchemy (`SQLModel`, `tortoise-orm`)
- Nenhuma biblioteca de autenticação externa
- Nenhum framework de testes sem instrução de integração

### Regra para novas dependências
Sempre adicionar ao `requirements.txt` na mesma alteração em que
o import é adicionado ao código. Nunca deixar um import sem correspondente.

---

## Como rodar localmente

```bash
# 1. Criar e ativar ambiente virtual
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# preencher as variáveis no .env

# 4. Inicializar o projeto Reflex (primeira vez)
reflex init

# 5. Rodar em desenvolvimento
reflex run
```

Porta local padrão: `3000` (frontend) e `8000` (backend interno do Reflex)

---

## Deploy

Hospedagem: Reflex Cloud
Comando de deploy: `reflex deploy`
Documentação: `reflex.dev/docs/hosting/deploy-quick-start/`

---

## O que fazer quando não tiver certeza

1. Carregar a skill `reflex-docs` para consultar sintaxe atualizada do Reflex
2. Ler `docs/DESIGN_SYSTEM.md` para dúvidas de interface
3. Ler `docs/PROMPTS_ETAPAS.md` para entender em qual etapa o projeto está
4. Perguntar antes de criar um novo arquivo — pode já existir um módulo responsável
5. Perguntar antes de alterar o schema do banco — mudanças de DDL afetam dados em produção
6. Nunca remover tabela ou coluna do banco sem instrução explícita
