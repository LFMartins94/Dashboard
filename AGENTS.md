# AGENTS.md — ContaView

Instruções obrigatórias para agentes de IA que trabalham neste projeto.
Leia este arquivo inteiro antes de modificar qualquer código.

---

## O que é este projeto

ContaView é uma ferramenta contábil em Python/Streamlit com banco PostgreSQL no Supabase.
É construída para uso individual pora uma contadora que acessa via navegador.
Não é um sistema multi-tenant. Não é uma API. Não é um SaaS.

---

## Linguagem e convenções

- Todo o código é escrito em **português PT-BR**: variáveis, funções, classes, comentários e mensagens da interface.
- Nomes de arquivos: snake_case em português (`importacao.py`, não `import_module.py`).
- Nomes de colunas do banco: snake_case em português (`conta_contabil`, `sequencial_lote`).
- Mensagens de erro e sucesso exibidas na interface: português formal, sem emojis, sem gírias.
- Datas exibidas sempre como `DD/MM/AAAA`. Armazenadas como `DATE` no banco.
- Valores monetários exibidos sempre como `R$ 0.000,00`. Armazenados como `NUMERIC(14,2)`.

---

## Estrutura de arquivos — responsabilidades fixas

Cada arquivo tem uma responsabilidade única. Não mova lógica entre arquivos sem justificativa explícita.

| Arquivo | Responsabilidade | Pode ser alterado? |
|---|---|---|
| `app.py` | Interface Streamlit — navegação, layout, chamada dos módulos | Sim |
| `database.py` | Conexão com Supabase, DDL, funções de leitura e escrita | Sim |
| `parsers.py` | Leitura de arquivos — Excel, CSV, PDF, imagem | Sim |
| `importacao.py` | Fluxo completo de importação — orquestra parsers + banco | Sim |
| `conciliacao.py` | Verificação de partidas dobradas C/D | Sim |
| `auditoria.py` | Detecção de anomalias, duplicidades e erros contábeis | Sim |
| `relatorios.py` | Exportação de PDF e Excel | Sim |
| `assistente.py` | Integração com LLM — perguntas sobre os dados | Sim |
| `auth.py` | Autenticação e controle de sessão | Sim — com cuidado |
| `docs/DESIGN_SYSTEM.md` | Tokens de cor, layout e regras visuais | Não alterar sem instrução explícita |
| `docs/PROMPTS_ETAPAS.md` | Guia de construção por etapas | Não alterar |

---

## Regras de arquitetura — nunca violar

### 1. Toda importação passa pelo `importacao.py`
Nunca chamar `to_sql`, `salvar_lancamentos()` ou qualquer função de escrita no banco
diretamente do `app.py`. O fluxo obrigatório é:

```
app.py → importacao.executar_importacao() → database.salvar_lancamentos()
```

### 2. Verificar empresa antes de qualquer insert de lançamentos
Antes de salvar lançamentos, sempre chamar `database.obter_ou_criar_empresa()` para
garantir que o `empresa_id` existe. Nunca inserir um lançamento com `empresa_id` que
não foi verificado previamente.

### 3. Verificar duplicidade de período antes de salvar
Antes de qualquer bulk insert, chamar `database.verificar_periodo_existente()`.
Se retornar `True`, interromper o fluxo e perguntar à usuária: "Substituir" ou "Cancelar".
**Não existe opção de mesclar períodos.**

### 4. O campo `sequencial_lote` é obrigatório em todo DataFrame antes do insert
Sempre chamar `importacao.injetar_sequencial_lote(df)` antes de `salvar_lancamentos()`.
Esse campo preserva a ordem original do arquivo e é usado pela conciliação de partidas.

### 5. O assistente nunca recebe dados brutos
A função `assistente.montar_contexto_resumido()` deve sempre agregar os dados antes
de enviá-los à API do LLM. Nunca passar linhas individuais de lançamentos, valores
nominais por CPF/CNPJ ou qualquer dado sensível não agregado.

### 6. Autenticação é a primeira verificação do `app.py`
A primeira instrução executável do `app.py`, após os imports, deve ser:
```python
if not st.session_state.get("autenticado", False):
    auth.exibir_tela_login()
    st.stop()
```
Nenhum dado, gráfico ou módulo é carregado antes dessa verificação.

### 7. Credenciais nunca no código-fonte
Toda chave, senha ou URL de banco é lida via `st.secrets` (produção) ou `os.getenv` (local).
Se encontrar uma string de conexão, senha ou chave de API hardcoded em qualquer arquivo,
remova imediatamente e substitua pela leitura via secrets.

---

## Banco de dados — tabelas e colunas

### Tabelas existentes (não renomear, não remover colunas)

```
empresas          → id, nome, cnpj, ativa, criado_em
lancamentos       → id, empresa_id, data, conta_contabil, valor, tipo, historico,
                    filial, periodo, sequencial_lote, origem, arquivo_origem, criado_em
conciliacoes      → id, empresa_id, periodo, total_pares, pares_ok, pares_com_erro,
                    status, executado_em
ocorrencias_auditoria → id, empresa_id, lancamento_id, tipo_ocorrencia, descricao,
                        severidade, resolvida, criado_em
```

### Tipos obrigatórios

- `tipo` em `lancamentos`: sempre `'C'` ou `'D'` — nunca outro valor
- `periodo`: sempre formato `'AAAA-MM'` — nunca `'MM/AAAA'` ou outro formato
- `severidade` em `ocorrencias_auditoria`: sempre `'alta'`, `'media'` ou `'baixa'`

---

## Interface — regras visuais

O design system completo está em `docs/DESIGN_SYSTEM.md`.
Leia esse arquivo antes de modificar qualquer tela.

Resumo das regras inegociáveis:

- Sem emojis em nenhuma parte da interface
- Sem texto em inglês na interface (labels, botões, mensagens)
- Filtros de empresa e período sempre no topo de abas analíticas
- Alertas de auditoria aparecem antes da confirmação de salvar — nunca depois
- O toggle de tema fica na sidebar, abaixo da navegação, acima do botão "Sair"
- Gráficos Plotly sempre respeitam os tokens de cor do tema ativo (light/dark)

---

## Dependências — o que pode e o que não pode adicionar

### Permitido adicionar
- Bibliotecas para formatação de dados (`babel`, `python-dateutil`)
- Clientes de LLM (`google-generativeai`, `openai`, `anthropic`)
- Utilitários de exportação (`xlsxwriter`, `reportlab`)

### Não adicionar sem aprovação explícita
- Nenhuma biblioteca de autenticação externa (`streamlit-authenticator`, `authlib`)
- Nenhum ORM além do SQLAlchemy já configurado (`SQLModel`, `tortoise-orm`)
- Nenhuma biblioteca de cache externo (`redis`, `memcached`)
- Nenhum framework de testes sem instrução de como integrá-lo ao fluxo

### Como instalar dependências
Sempre adicionar ao `requirements.txt` na mesma alteração em que o import é adicionado ao código.
Nunca deixar um import sem o correspondente no `requirements.txt`.

---

## Como rodar localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# preencher DATABASE_URL, APP_USUARIO, APP_SENHA, LLM_API_KEY no .env

# Rodar
streamlit run app.py
```

Porta local padrão: `8501`

---

## Deploy

Hospedagem: Hugging Face Spaces com Dockerfile.
Porta de produção: `7860`

```dockerfile
CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
```

Secrets de produção configurados no painel do Hugging Face Space:
- `DATABASE_URL`
- `APP_USUARIO`
- `APP_SENHA`
- `LLM_API_KEY`

---

## O que fazer quando não tiver certeza

1. Leia `docs/DESIGN_SYSTEM.md` para dúvidas de interface
2. Leia `docs/PROMPTS_ETAPAS.md` para entender em qual etapa o projeto está
3. Pergunte antes de criar um novo arquivo — pode já existir um módulo responsável por isso
4. Pergunte antes de alterar o schema do banco — mudanças de DDL afetam dados existentes
