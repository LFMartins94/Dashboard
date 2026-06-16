# ContaView — Prompts por Etapa (OpenCode)

Use este documento como guia de construção.
Antes de cada etapa: abra o OpenCode, cole o contexto indicado e então cole o prompt.
Valide o resultado antes de avançar para a próxima etapa.

---

## Como usar este documento

1. Cada etapa tem um **contexto** (o que colar antes) e um **prompt** (o que pedir).
2. Cole o contexto primeiro — isso ancora o LLM na estrutura do projeto.
3. Cole o prompt em seguida — seja específico, não parafraseie.
4. Ao final de cada etapa, há uma **checklist de validação** — só avance quando todos os itens estiverem marcados.

---

## ETAPA 1 — Banco de dados

**Objetivo:** Criar o DDL final no Supabase e atualizar o `database.py`.

**Contexto para colar antes do prompt:**
```
Projeto: ContaView — ferramenta contábil em Python/Streamlit com banco PostgreSQL no Supabase.
Arquivo atual: database.py (já existe, usa SQLAlchemy + to_sql).
Convenção de nomes: português PT-BR em todo o código.
```

**Prompt:**

```
Atualize o arquivo `database.py` do projeto ContaView com as seguintes instruções:

1. Substituir o DDL atual (que cria apenas a tabela `gastos`) pelo DDL completo abaixo,
   mantendo toda a configuração de engine, pool e SSL que já existe no arquivo.

2. DDL a implementar — criar as 4 tabelas nesta ordem (respeitar dependências de FK):

   TABELA empresas:
   - id SERIAL PRIMARY KEY
   - nome VARCHAR(200) NOT NULL
   - cnpj VARCHAR(18)
   - ativa BOOLEAN NOT NULL DEFAULT TRUE
   - criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

   TABELA lancamentos:
   - id SERIAL PRIMARY KEY
   - empresa_id INTEGER NOT NULL REFERENCES empresas(id)
   - data DATE NOT NULL
   - conta_contabil VARCHAR(50) NOT NULL
   - valor NUMERIC(14, 2) NOT NULL
   - tipo CHAR(1) NOT NULL CHECK (tipo IN ('C', 'D'))
   - historico TEXT
   - filial VARCHAR(20)
   - periodo VARCHAR(7)   -- formato AAAA-MM
   - sequencial_lote INTEGER
   - origem VARCHAR(50) NOT NULL DEFAULT 'arquivo'
   - arquivo_origem VARCHAR(255)
   - criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

   TABELA conciliacoes:
   - id SERIAL PRIMARY KEY
   - empresa_id INTEGER NOT NULL REFERENCES empresas(id)
   - periodo VARCHAR(7) NOT NULL
   - total_pares INTEGER NOT NULL DEFAULT 0
   - pares_ok INTEGER NOT NULL DEFAULT 0
   - pares_com_erro INTEGER NOT NULL DEFAULT 0
   - status VARCHAR(20) NOT NULL DEFAULT 'pendente'
   - executado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

   TABELA ocorrencias_auditoria:
   - id SERIAL PRIMARY KEY
   - empresa_id INTEGER NOT NULL REFERENCES empresas(id)
   - lancamento_id INTEGER REFERENCES lancamentos(id)
   - tipo_ocorrencia VARCHAR(50) NOT NULL
   - descricao TEXT NOT NULL
   - severidade VARCHAR(10) NOT NULL DEFAULT 'media'
   - resolvida BOOLEAN NOT NULL DEFAULT FALSE
   - criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

3. Criar os seguintes índices após as tabelas:
   - idx_lancamentos_empresa em lancamentos(empresa_id)
   - idx_lancamentos_data em lancamentos(data)
   - idx_lancamentos_conta em lancamentos(conta_contabil)
   - idx_lancamentos_periodo em lancamentos(periodo)
   - idx_lancamentos_tipo em lancamentos(tipo)

4. Implementar as funções abaixo (substituindo as funções antigas de `gastos`):

   obter_ou_criar_empresa(nome: str, cnpj: str = None) -> int
   - Faz SELECT por nome. Se existir, retorna o id. Se não existir, faz INSERT e retorna o novo id.
   - Nunca lança exceção se a empresa já existir.

   verificar_periodo_existente(empresa_id: int, periodo: str) -> bool
   - Faz SELECT EXISTS verificando se há lançamentos daquela empresa naquele período.
   - Retorna True se existir, False se não existir.

   deletar_lancamentos_do_periodo(empresa_id: int, periodo: str) -> int
   - Deleta todos os lançamentos daquela empresa naquele período.
   - Retorna a quantidade de registros deletados.
   - Também deleta as ocorrencias_auditoria e conciliacoes do mesmo período e empresa.

   salvar_lancamentos(df: pd.DataFrame, empresa_id: int, origem: str = 'arquivo') -> int
   - Recebe um DataFrame já higienizado com as colunas:
     data, conta_contabil, valor, tipo, historico, filial, periodo, sequencial_lote, arquivo_origem
   - Injeta empresa_id e origem no DataFrame antes do to_sql.
   - Usa to_sql(method='multi', chunksize=1000) como já existe no código.
   - Retorna a quantidade de registros salvos.

   carregar_lancamentos(empresa_id: int = None, periodo: str = None) -> pd.DataFrame
   - Carrega lançamentos com filtros opcionais de empresa e período.
   - Retorna DataFrame com todas as colunas da tabela lancamentos.

5. Manter a função inicializar_banco() existente, apenas substituindo o DDL interno.
6. Manter toda a configuração de logging existente.
7. Não remover a função get_database_url() existente.
```

**Checklist de validação:**
- [ ] `inicializar_banco()` roda sem erros no Supabase e cria as 4 tabelas
- [ ] Os 5 índices aparecem no painel do Supabase
- [ ] `obter_ou_criar_empresa("Teste")` retorna um id e não duplica ao chamar duas vezes
- [ ] `verificar_periodo_existente(1, "2026-06")` retorna False em banco vazio
- [ ] `salvar_lancamentos()` com DataFrame de teste insere registros corretamente

---

## ETAPA 2 — Autenticação e shell do app

**Objetivo:** Criar o `auth.py` e o shell inicial do `app.py` com login funcionando.

**Contexto para colar antes do prompt:**
```
Projeto: ContaView — Streamlit + Supabase.
Etapa 1 concluída: database.py com as 4 tabelas e funções de banco prontas.
Convenção: português PT-BR, sem emojis na interface, sem bibliotecas externas de auth.
Credenciais lidas via st.secrets — nunca hardcoded.
```

**Prompt:**

```
Crie o arquivo `auth.py` e atualize o `app.py` do projeto ContaView:

AUTH.PY — implementar:

1. verificar_login(usuario: str, senha: str) -> bool
   - Lê APP_USUARIO e APP_SENHA de st.secrets.
   - Compara com os parâmetros recebidos (comparação case-sensitive para senha).
   - Retorna True se ambos baterem, False caso contrário.

2. logout() -> None
   - Limpa st.session_state.autenticado, st.session_state.usuario.
   - Faz st.rerun().

3. exibir_tela_login() -> None
   - Exibe uma tela centralizada com:
     - Título "ContaView" em destaque
     - Subtítulo "Acesso restrito"
     - Campo de texto para usuário (st.text_input)
     - Campo de senha (st.text_input com type="password")
     - Botão "Entrar"
   - Ao clicar em "Entrar": chama verificar_login(). Se True, seta
     st.session_state.autenticado = True e st.session_state.usuario = usuario,
     então st.rerun(). Se False, exibe st.error("Usuário ou senha incorretos.").
   - Não exibe sidebar, não exibe nenhum outro elemento.

APP.PY — atualizar para:

1. Primeira ação após imports: verificar st.session_state.get("autenticado", False).
   Se False: chamar exibir_tela_login() e st.stop(). Nada mais executa.

2. Se autenticado, montar a sidebar com:
   - Texto "ContaView" como logo
   - Separador
   - st.radio com as páginas: ["Painel", "Lançamentos", "Importar",
     "Conciliação", "Auditoria", "Relatórios", "Assistente"]
   - Separador
   - st.toggle "Modo escuro" — salva em st.session_state.tema_escuro
   - Botão "Sair" que chama logout()

3. Área de conteúdo: por enquanto exibir apenas o nome da página selecionada
   com st.title() e st.info("Módulo em construção.") — placeholder para as
   próximas etapas.

4. Chamar inicializar_banco() do database.py uma única vez usando
   st.cache_resource para não reconectar a cada rerun.

5. Configuração da página:
   st.set_page_config(
       page_title="ContaView",
       layout="wide",
       initial_sidebar_state="expanded"
   )

Não implementar ainda nenhum CSS de tema — isso vem na Etapa 5B.
Não implementar nenhum módulo de análise — apenas a navegação funcional.
```

**Checklist de validação:**
- [ ] Acessar a URL sem login exibe apenas a tela de login, sem sidebar
- [ ] Credenciais erradas exibem mensagem de erro
- [ ] Login correto exibe a sidebar com as 7 páginas
- [ ] Botão "Sair" volta para a tela de login
- [ ] Trocar de página na sidebar muda o título na área de conteúdo
- [ ] Toggle "Modo escuro" não quebra a aplicação (mesmo sem CSS aplicado ainda)

---

## ETAPA 3 — Fluxo de importação

**Objetivo:** Criar o `importacao.py` e atualizar o `parsers.py` para ler os campos contábeis reais.

**Contexto para colar antes do prompt:**
```
Projeto: ContaView — Streamlit + Supabase.
Etapas 1 e 2 concluídas.
Planilha real da contadora: arquivo .xlsx com as colunas separadas por ponto-e-vírgula
numa única célula por linha. Colunas: Data, Conta Contábil, Valor, Tipo (C ou D),
Histórico, Filial.
O parsers.py atual tem 3 estratégias em cascata — manter a estrutura, apenas adaptar
o mapeamento de colunas.
```

**Prompt:**

```
Atualize o `parsers.py` e crie o `importacao.py` do projeto ContaView:

PARSERS.PY — atualizar:

1. Manter as 3 estratégias em cascata existentes.

2. Após qualquer estratégia detectar as colunas, aplicar a função normalizar_colunas(df)
   que mapeia variações de nome para os nomes padronizados:
   - Variações de "data" → coluna "data"
   - Variações de "conta", "conta contábil", "conta_contabil" → "conta_contabil"
   - Variações de "valor", "vl", "vlr" → "valor"
   - Variações de "tipo", "tp", "c/d" → "tipo"
   - Variações de "histórico", "historico", "hist", "descricao" → "historico"
   - Variações de "filial", "fil", "unidade" → "filial"

3. Após normalizar colunas, aplicar limpar_dataframe(df) que:
   - Converte "data" para datetime, descarta linhas onde a conversão falhar
   - Converte "valor" para float: remove "R$", ".", troca "," por "." — descarta linhas inválidas
   - Garante que "tipo" seja exatamente "C" ou "D" (uppercase, strip) — descarta linhas inválidas
   - Preenche "historico" vazio com string vazia (não null)
   - Preenche "filial" vazio com "SEM FILIAL"
   - Deriva a coluna "periodo" a partir de "data" no formato "AAAA-MM"

4. A função principal ler_arquivo(arquivo) deve retornar um dict:
   {
     "sucesso": bool,
     "df": DataFrame ou None,
     "linhas_lidas": int,
     "linhas_descartadas": int,
     "motivo_falha": str ou None
   }

IMPORTACAO.PY — criar:

1. validar_pre_import(df: pd.DataFrame) -> dict
   - Verifica se todas as colunas obrigatórias existem: data, conta_contabil, valor, tipo
   - Retorna {"valido": bool, "erros": list[str]}

2. injetar_sequencial_lote(df: pd.DataFrame) -> pd.DataFrame
   - Adiciona coluna "sequencial_lote" com valores 1, 2, 3... na ordem original do DataFrame
   - Não reordena o DataFrame

3. executar_importacao(arquivo, nome_empresa: str, cnpj_empresa: str = None) -> dict
   Fluxo completo em ordem:
   a. Chama ler_arquivo(arquivo) — se falhar, retorna erro imediatamente
   b. Chama validar_pre_import(df) — se inválido, retorna lista de erros
   c. Chama injetar_sequencial_lote(df)
   d. Determina o período (primeiro período único encontrado no df)
   e. Chama obter_ou_criar_empresa(nome_empresa, cnpj_empresa) → empresa_id
   f. Chama verificar_periodo_existente(empresa_id, periodo) → se True, retorna
      {"requer_confirmacao": True, "empresa_id": empresa_id, "periodo": periodo, "df": df}
   g. Se não existe conflito: chama salvar_lancamentos(df, empresa_id, origem=arquivo.name)
   h. Retorna {"sucesso": True, "registros_salvos": int, "empresa_id": int, "periodo": str}

4. confirmar_substituicao(empresa_id: int, periodo: str, df: pd.DataFrame) -> dict
   - Chama deletar_lancamentos_do_periodo(empresa_id, periodo)
   - Chama salvar_lancamentos(df, empresa_id)
   - Retorna {"sucesso": True, "registros_salvos": int}

Na aba "Importar" do app.py, implementar o seguinte fluxo de UI:
- Campo para nome da empresa (st.text_input)
- Campo para CNPJ opcional (st.text_input)
- st.file_uploader aceitando .xlsx e .csv
- Ao fazer upload: chamar executar_importacao() imediatamente
- Se retornar requer_confirmacao=True: exibir st.warning com os dados do conflito
  e dois botões: "Substituir período" e "Cancelar"
- Se retornar sucesso: exibir st.success com quantidade de registros salvos
- Se retornar erro: exibir st.error com a lista de problemas encontrados
```

**Checklist de validação:**
- [ ] Upload da planilha real da contadora (CAP_ILHAS_DO_LAGO_CONCILIADO.xlsx) funciona
- [ ] Colunas são detectadas e normalizadas corretamente
- [ ] Registros com tipo inválido são descartados com contagem informada
- [ ] Segunda importação do mesmo arquivo exibe o alerta de conflito de período
- [ ] "Substituir período" apaga e reimporta corretamente
- [ ] "Cancelar" não salva nada e limpa o estado

---

## ETAPA 4 — Conciliação e auditoria

**Objetivo:** Criar `conciliacao.py` e `auditoria.py` integrados ao fluxo de importação.

**Contexto para colar antes do prompt:**
```
Projeto: ContaView — Streamlit + Supabase.
Etapas 1, 2 e 3 concluídas.
Os lançamentos têm o campo sequencial_lote que preserva a ordem original do arquivo.
O tipo é sempre 'C' (crédito) ou 'D' (débito).
Partidas dobradas: cada C deve ter um D correspondente de mesmo valor e data (±1 no sequencial).
```

**Prompt:**

```
Crie os arquivos `conciliacao.py` e `auditoria.py` do projeto ContaView:

CONCILIACAO.PY:

1. conciliar_partidas(df: pd.DataFrame) -> dict
   Recebe o DataFrame de lançamentos (já importado).
   Algoritmo:
   a. Ordenar por sequencial_lote
   b. Para cada lançamento C, procurar o D mais próximo com mesmo valor e mesma data
      (usando sequencial_lote adjacente como critério de desempate)
   c. Marcar pares encontrados como "conciliado"
   d. Lançamentos sem par: classificar como "sem_par"
   e. Retornar:
      {
        "pares_ok": int,
        "sem_par": int,
        "df_pares": DataFrame com colunas [seq_c, seq_d, data, valor, status],
        "df_sem_par": DataFrame com lançamentos sem correspondência
      }

2. salvar_resultado_conciliacao(empresa_id: int, periodo: str, resultado: dict) -> None
   - Insere um registro na tabela conciliacoes com os totais do resultado.

3. gerar_relatorio_conciliacao(resultado: dict) -> pd.DataFrame
   - Retorna um DataFrame formatado para exibição e exportação.

AUDITORIA.PY:

1. auditar_lancamentos(df: pd.DataFrame) -> list[dict]
   Executa todas as verificações abaixo e retorna lista de ocorrências.
   Cada ocorrência é um dict:
   { "lancamento_id": int ou None, "tipo_ocorrencia": str,
     "descricao": str, "severidade": str }

   Verificações obrigatórias:
   a. DUPLICIDADE (severidade: "alta")
      - Mesmo conjunto de (data + conta_contabil + valor + tipo) aparece mais de uma vez
      - descricao: "Lançamento duplicado: [conta] R$ [valor] em [data]"

   b. SEM_PAR (severidade: "alta")
      - Lançamentos C ou D sem correspondência após rodar conciliar_partidas()
      - descricao: "Lançamento sem par: [tipo] R$ [valor] em [data]"

   c. HISTORICO_VAZIO (severidade: "media")
      - Campo historico vazio ou com menos de 3 caracteres
      - descricao: "Histórico não preenchido na conta [conta] em [data]"

   d. VALOR_ANOMALO (severidade: "media")
      - Valor acima de média + 3 desvios padrão do conjunto
      - descricao: "Valor atípico: R$ [valor] na conta [conta] (média do período: R$ [media])"

   e. CONTA_FORMATO_INVALIDO (severidade: "baixa")
      - conta_contabil com menos de 3 caracteres ou contendo apenas letras
      - descricao: "Código de conta fora do padrão: [conta]"

2. salvar_ocorrencias(ocorrencias: list[dict], empresa_id: int) -> int
   - Insere as ocorrências na tabela ocorrencias_auditoria.
   - Retorna quantidade salva.

3. resumo_auditoria(ocorrencias: list[dict]) -> dict
   - Retorna contagens por severidade: {"alta": int, "media": int, "baixa": int, "total": int}

INTEGRAÇÃO NO APP.PY:

Na aba "Importar", após salvar os lançamentos com sucesso:
- Executar auditar_lancamentos(df) automaticamente
- Executar conciliar_partidas(df) automaticamente
- Exibir resumo_auditoria() com st.error para ocorrências altas, st.warning para médias
- Salvar ocorrências no banco via salvar_ocorrencias()
- Exibir tabela expandível com detalhes de cada ocorrência encontrada

Na aba "Auditoria" do app.py:
- Filtros de empresa e período no topo
- Tabela com todas as ocorrências do período, com colunas:
  Tipo, Descrição, Severidade, Resolvida
- Checkbox para marcar ocorrência como resolvida (atualiza campo no banco)
- Contadores de ocorrências por severidade no topo (usando st.metric)

Na aba "Conciliação" do app.py:
- Filtros de empresa e período no topo
- st.metric com: Total de pares, Pares OK, Sem par
- Tabela de pares conciliados
- Tabela de lançamentos sem par em destaque (st.dataframe com cor de fundo)
```

**Checklist de validação:**
- [ ] Importar o arquivo da contadora e ver as ocorrências aparecerem automaticamente
- [ ] Duplicidades são detectadas corretamente
- [ ] Aba Auditoria mostra as ocorrências salvas no banco
- [ ] Aba Conciliação mostra os pares e os lançamentos sem par
- [ ] Marcar ocorrência como resolvida persiste no banco

---

## ETAPA 5A — Navegação e filtros

**Objetivo:** Estruturar a navegação final do `app.py` com filtros funcionais de empresa e período.

**Contexto para colar antes do prompt:**
```
Projeto: ContaView — Streamlit + Supabase.
Etapas 1 a 4 concluídas.
As abas Importar, Auditoria e Conciliação já têm conteúdo real.
As abas Painel, Lançamentos, Relatórios e Assistente ainda têm placeholder.
```

**Prompt:**

```
Atualize o `app.py` do projeto ContaView para estruturar a navegação completa:

1. Filtros globais de contexto:
   - Carregar lista de empresas do banco via carregar_lancamentos() e extrair empresas únicas
   - Exibir no topo da área de conteúdo (exceto na aba Importar e Assistente):
     col_empresa, col_periodo, _ = st.columns([2, 2, 4])
     - selectbox "Empresa" com as empresas cadastradas + opção "Todas"
     - selectbox "Período" com os períodos disponíveis para a empresa selecionada
   - Salvar seleção em st.session_state.empresa_selecionada e st.session_state.periodo_selecionado

2. Aba "Painel":
   - Carregar lançamentos filtrados por empresa e período
   - Exibir 3 KPIs: total débitos, total créditos, saldo (créditos - débitos)
   - Exibir gráfico Plotly de barras: evolução mensal de débitos vs créditos
     (mesmo que o período selecionado seja único, o gráfico agrupa por mês)
   - Exibir gráfico Plotly de barras horizontais: top 10 contas por volume movimentado
   - Placeholder para os demais gráficos com st.info("Em desenvolvimento")

3. Aba "Lançamentos":
   - Carregar lançamentos filtrados
   - Exibir st.dataframe com todas as colunas, paginado (use st.dataframe nativo)
   - Colunas exibidas: Data, Conta Contábil, Valor, Tipo, Histórico, Filial
   - Coluna Valor formatada como moeda brasileira
   - Coluna Tipo colorida: C em verde, D em vermelho (via st.dataframe column_config)

4. Não alterar o conteúdo das abas Importar, Conciliação e Auditoria já construídas.
   Apenas garantir que os filtros globais não aparecem nessas abas.

5. As abas Relatórios e Assistente permanecem como placeholder.
```

**Checklist de validação:**
- [ ] Filtro de empresa popula corretamente a partir do banco
- [ ] Trocar empresa atualiza o filtro de período disponível
- [ ] Aba Painel exibe os 3 KPIs com valores reais do banco
- [ ] Gráfico de evolução mensal renderiza sem erros
- [ ] Aba Lançamentos exibe a tabela com os dados reais
- [ ] Coluna Tipo mostra C/D com cores distintas

---

## ETAPA 5B — Design system e tema

**Objetivo:** Aplicar o design system completo com dark/light mode funcional.

**Contexto para colar antes do prompt:**
Cole o arquivo `DESIGN_SYSTEM.md` completo aqui antes do prompt abaixo.

**Prompt:**

```
Aplique o design system do ContaView no `app.py` conforme a especificação do
DESIGN_SYSTEM.md colado acima.

1. Implementar a função aplicar_tema(escuro: bool) exatamente como especificada
   no design system, com todos os tokens de cor para light mode (Mineral) e
   dark mode (Eclipse).

2. Chamar aplicar_tema(st.session_state.get("tema_escuro", False)) no início
   do app.py, logo após verificar autenticação.

3. O toggle "Modo escuro" na sidebar deve atualizar st.session_state.tema_escuro
   e acionar st.rerun() para reaplicar o tema imediatamente.

4. Aplicar formatação consistente em todas as abas já construídas:
   - Títulos de seção em uppercase com letter-spacing (usar st.markdown com HTML)
   - Separadores entre seções com st.divider()
   - Labels de KPI em uppercase pequeno acima dos valores

5. Garantir que os gráficos Plotly respeitam o tema:
   - Em light mode: fundo #FFFFFF, texto #1A1916, grid #E0DDD5
   - Em dark mode: fundo #161920, texto #E8E8E8, grid #1E2128
   - Barras de débito: negative (#C94B3C light / #FF6B5B dark)
   - Barras de crédito: positive (#2D8C5E light / #00C9A0 dark)

6. Não alterar nenhuma lógica de negócio — apenas aparência.
```

**Checklist de validação:**
- [ ] Alternar tema muda as cores imediatamente sem erro
- [ ] Sidebar tem a cor correta em cada modo
- [ ] Gráficos Plotly respeitam as cores do tema ativo
- [ ] KPIs têm o visual correto (label pequeno + valor grande)
- [ ] Tabelas legíveis nos dois modos

---

## ETAPA 6A — Exportação de relatórios

**Objetivo:** Criar o `relatorios.py` com exportação em Excel e PDF.

**Contexto para colar antes do prompt:**
```
Projeto: ContaView — Streamlit + Supabase.
Etapas 1 a 5B concluídas.
Bibliotecas disponíveis: xlsxwriter (Excel), reportlab (PDF).
Convenção: todos os nomes em PT-BR.
```

**Prompt:**

```
Crie o arquivo `relatorios.py` e adicione botões de exportação no `app.py`:

RELATORIOS.PY:

1. exportar_excel(df: pd.DataFrame, nome_arquivo: str, titulo: str) -> bytes
   - Gera um arquivo .xlsx em memória (io.BytesIO) usando xlsxwriter
   - Primeira linha: título em negrito, fonte 14
   - Segunda linha: vazia
   - A partir da terceira linha: cabeçalho da tabela em negrito com fundo cinza claro
   - Dados a partir da quarta linha
   - Colunas de valor formatadas como moeda: R$ #.##0,00
   - Colunas de data formatadas como DD/MM/AAAA
   - Largura das colunas ajustada automaticamente pelo conteúdo
   - Retorna bytes do arquivo para uso com st.download_button

2. exportar_pdf(dados: dict, tipo_relatorio: str) -> bytes
   - tipos suportados: "conciliacao", "auditoria", "lancamentos"
   - Gera PDF em memória usando reportlab
   - Cabeçalho: "ContaView — [tipo]" + empresa + período
   - Tabela com os dados
   - Rodapé: data de geração
   - Retorna bytes do arquivo

NO APP.PY — adicionar botões de exportação:

- Aba "Lançamentos": botão "Exportar Excel" abaixo da tabela
- Aba "Conciliação": botão "Exportar relatório de conciliação (Excel)" e "Exportar PDF"
- Aba "Auditoria": botão "Exportar relatório de auditoria (Excel)"
- Aba "Relatórios": exibir os mesmos botões de exportação de todas as abas em um único lugar
  com descrição de cada relatório disponível

Todos os botões devem usar st.download_button com mime type correto:
- Excel: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
- PDF: "application/pdf"
```

**Checklist de validação:**
- [ ] Download de Excel abre corretamente no Excel/LibreOffice
- [ ] Valores monetários formatados como R$ no Excel
- [ ] Datas no formato DD/MM/AAAA no Excel
- [ ] Download de PDF abre corretamente e exibe os dados
- [ ] Botões aparecem corretamente nas abas

---

## ETAPA 6B — Assistente de IA

**Objetivo:** Criar o `assistente.py` integrado à aba Assistente do app.

**Contexto para colar antes do prompt:**
```
Projeto: ContaView — Streamlit + Supabase.
Todas as etapas anteriores concluídas.
LLM escolhido: Gemini (google-generativeai).
REGRA DE SEGURANÇA: o assistente nunca recebe dados brutos, apenas resumos agregados.
Chave da API lida via st.secrets["LLM_API_KEY"].
```

**Prompt:**

```
Crie o arquivo `assistente.py` e implemente a aba "Assistente" no `app.py`:

ASSISTENTE.PY:

1. montar_contexto_resumido(empresa_id: int, periodo: str) -> str
   Monta um texto de contexto para enviar à IA. NUNCA enviar dados brutos.
   O texto deve conter apenas:
   - Nome da empresa e período
   - Total de lançamentos no período
   - Total de débitos e créditos (valores agregados)
   - Top 5 contas por volume movimentado (conta + total)
   - Quantidade de ocorrências de auditoria por severidade
   - Status da conciliação do período (pares OK vs sem par)
   Exemplo de saída:
   "Empresa: Ilhas do Lago | Período: 2026-05
    Total de lançamentos: 156
    Total débitos: R$ 84.320,00 | Total créditos: R$ 97.540,00
    Top contas: 110401001 (R$ 22.400), 210301002 (R$ 18.900)...
    Auditoria: 2 ocorrências altas, 7 médias
    Conciliação: 74 pares OK, 4 sem par"

2. perguntar_ao_assistente(pergunta: str, contexto: str, historico: list) -> str
   - Monta o payload para a API do Gemini
   - System prompt fixo:
     "Você é um assistente contábil especializado. Responda em português brasileiro.
      Seja objetivo e preciso. Baseie suas respostas apenas nos dados fornecidos.
      Não invente valores ou informações que não estejam no contexto."
   - Inclui o contexto resumido como parte do prompt do usuário
   - Inclui o histórico da conversa atual
   - Retorna apenas o texto da resposta

NO APP.PY — aba "Assistente":

1. Exibir os filtros de empresa e período (mesmo padrão das outras abas)
2. Exibir uma caixa com o resumo do contexto que será enviado à IA
   (para a contadora entender o que o assistente "sabe")
3. Histórico da conversa exibido acima do campo de entrada
   (usar st.session_state.historico_chat para persistir na sessão)
4. Campo de entrada: st.chat_input("Pergunte sobre os dados...")
5. Ao enviar: chamar perguntar_ao_assistente() e exibir resposta com st.chat_message
6. Botão "Limpar conversa" que reseta st.session_state.historico_chat
```

**Checklist de validação:**
- [ ] Aba Assistente abre sem erro
- [ ] O resumo de contexto exibido não contém dados individuais, apenas agregados
- [ ] Pergunta simples ("qual o saldo do período?") retorna resposta coerente
- [ ] Histórico da conversa persiste enquanto a sessão está ativa
- [ ] "Limpar conversa" reseta o chat corretamente
- [ ] Chave da API não aparece em nenhum log ou mensagem de erro visível

---

## Notas gerais para o OpenCode

- **Sempre** cole o `DESIGN_SYSTEM.md` antes de qualquer prompt que envolva interface.
- **Nunca** peça duas etapas no mesmo prompt — o agente perde o foco.
- Se o agente gerar código que contradiz o design system, corrija apontando o token exato.
- Ao final do projeto, rode `streamlit run app.py` localmente para validação final antes do deploy.
- Para deploy no Hugging Face Spaces: o `Dockerfile` deve expor a porta `7860` e usar
  `CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]`
