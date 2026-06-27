# ContaView — Prompts de Migração para Reflex

Guia de construção da nova interface em Reflex.
Use este documento junto com o AGENTS.md e o DESIGN_SYSTEM.md.

---

## Como usar este documento

1. Antes de qualquer etapa, mande sempre esta instrução ao agente:
   ```
   carregue as skills reflex-docs, setup-python-env e reflex-process-management
   depois leia AGENTS.md e docs/DESIGN_SYSTEM.md
   ```
2. Cole o prompt da etapa em seguida.
3. Valide a checklist antes de avançar — nunca pule etapas.
4. Os módulos em `logic/` são reaproveitados — o agente não deve reescrevê-los,
   apenas copiá-los da versão anterior do projeto.

---

## ETAPA 1 — Estrutura base e ambiente

**Objetivo:** Inicializar o projeto Reflex, copiar os módulos de lógica e
configurar a conexão com o Supabase.

**Prompt:**

```
Inicialize o projeto ContaView em Reflex seguindo estas instruções:

1. Use a skill setup-python-env para criar o ambiente virtual Python
   e instalar as dependências corretamente.

2. Rode reflex init para criar a estrutura base do projeto.

3. Crie a estrutura de pastas conforme o AGENTS.md:
   contaview/
   ├── contaview/
   │   ├── contaview.py
   │   ├── styles.py
   │   ├── state/
   │   ├── components/
   │   ├── pages/
   │   └── logic/
   ├── assets/
   │   └── styles.css
   ├── rxconfig.py
   └── requirements.txt

4. Copie os seguintes arquivos da pasta logic/ do projeto anterior
   para contaview/logic/ sem nenhuma alteração de conteúdo:
   database.py, parsers.py, importacao.py, conciliacao.py,
   auditoria.py, relatorios.py, assistente.py

5. No rxconfig.py, configure:
   config = rx.Config(
       app_name="contaview",
       db_url=os.getenv("DATABASE_URL"),
   )

6. Crie o arquivo styles.py com os dois dicionários de tokens de cor
   exatamente como definido no DESIGN_SYSTEM.md:
   MINERAL = { ... }
   ECLIPSE = { ... }
   E a função cor(tema_escuro: bool, token: str) -> str

7. Crie o arquivo assets/styles.css com as regras de hover:
   .conversa-item:hover { background-color: #161920; }
   .conversa-item:hover .conversa-delete { opacity: 1; transition: opacity .15s; }
   .nav-item:hover { background-color: #161B22; }

8. Crie o requirements.txt com as versões fixas definidas no AGENTS.md.

9. Crie o .env.example com as quatro variáveis:
   DATABASE_URL, APP_USUARIO, APP_SENHA, OPENAI_API_KEY

10. Confirme que o .gitignore inclui: .env, __pycache__/, *.pyc,
    .web/, venv/, .streamlit/

Não crie nenhuma página ou componente ainda — apenas a estrutura.
```

**Checklist de validação:**
- [ ] `reflex run` inicia sem erro e abre no navegador na porta 3000
- [ ] A pasta `logic/` contém os 7 arquivos copiados
- [ ] `styles.py` tem os dicionários MINERAL e ECLIPSE com todos os tokens
- [ ] `assets/styles.css` existe com as regras de hover
- [ ] `.env.example` tem as 4 variáveis
- [ ] `.env` está no `.gitignore`

---

## ETAPA 2 — Classes de State

**Objetivo:** Criar as 4 classes de state que gerenciam todo o
comportamento dinâmico da aplicação.

**Prompt:**

```
Crie os 4 arquivos de state do projeto ContaView em Reflex,
conforme a especificação do DESIGN_SYSTEM.md:

STATE/AUTH_STATE.PY:
class AuthState(rx.State):
   autenticado: bool = False
   usuario: str = ""

   def fazer_login(self, usuario: str, senha: str):
      - Lê APP_USUARIO e APP_SENHA via os.getenv()
      - Se credenciais corretas: seta autenticado=True, usuario=usuario
        e retorna rx.redirect("/painel")
      - Se incorretas: retorna rx.window_alert("Usuário ou senha incorretos.")

   def fazer_logout(self):
      - Seta autenticado=False, usuario=""
      - Retorna rx.redirect("/")

STATE/TEMA_STATE.PY:
class TemaState(rx.State):
   tema_escuro: bool = False

   def alternar_tema(self):
      - Inverte tema_escuro

STATE/DADOS_STATE.PY:
class DadosState(rx.State):
   empresa_selecionada: str = ""
   periodo_selecionado: str = ""
   empresas_disponiveis: list[str] = []
   periodos_disponiveis: list[str] = []
   lancamentos: list[dict] = []
   carregando: bool = False

   def carregar_empresas(self):
      - Chama logic/database.carregar_lancamentos()
      - Extrai lista única de nomes de empresas
      - Popula empresas_disponiveis

   def set_empresa_selecionada(self, empresa: str):
      - Seta empresa_selecionada
      - Chama carregar_periodos()

   def carregar_periodos(self):
      - Busca períodos disponíveis para a empresa selecionada
      - Formata cada período de AAAA-MM para MM/AAAA para exibição
      - Popula periodos_disponiveis

   def set_periodo_selecionado(self, periodo: str):
      - Seta periodo_selecionado
      - Chama carregar_lancamentos()

   def carregar_lancamentos(self):
      - Seta carregando=True
      - Chama logic/database.carregar_lancamentos() com os filtros
      - Converte datas para DD/MM/AAAA antes de salvar em lancamentos
      - Seta carregando=False

STATE/CHAT_STATE.PY:
Implementar exatamente como especificado no DESIGN_SYSTEM.md,
incluindo os métodos: carregar_conversas, selecionar_conversa,
nova_conversa, excluir_conversa, enviar_mensagem.

Na excluir_conversa: usar a proteção de conversa_existe()
do logic/database.py antes de qualquer operação.
Se conversa_ativa for None após exclusão, criar nova conversa
automaticamente.

Regras gerais para todos os states:
- Nenhum state importa reflex além de rx.State
- Toda chamada a logic/ é feita dentro de métodos de state,
  nunca em nível de módulo
- Usar try/except em toda chamada a logic/ e logar erros
  sem expor detalhes técnicos na interface
```

**Checklist de validação:**
- [ ] `reflex run` ainda inicia sem erro após criar os states
- [ ] `AuthState.fazer_login()` lê credenciais via `os.getenv()`
- [ ] `DadosState.carregar_periodos()` formata `AAAA-MM` → `MM/AAAA`
- [ ] `ChatState` tem todos os métodos definidos no DESIGN_SYSTEM.md

---

## ETAPA 3 — Componentes reutilizáveis

**Objetivo:** Construir os componentes visuais da sidebar e os
componentes compartilhados entre páginas.

**Prompt:**

```
Crie os componentes visuais do projeto ContaView em Reflex,
seguindo rigorosamente os tokens de cor e a estrutura do DESIGN_SYSTEM.md.
Use a skill reflex-docs para consultar a sintaxe correta de cada componente.

COMPONENTS/NAV_ITEM.PY:
def nav_item(label: str, rota: str, icone: str) -> rx.Component:
   - rx.hstack com ícone (rx.icon) + texto
   - Padding: 8px 10px, border_radius: 8px
   - Cor padrão: sidebar_text do tema ativo
   - Ao clicar: rx.redirect(rota)
   - Estado ativo (rota atual): fundo sidebar_active_bg, texto sidebar_active
   - Usar rx.cond para detectar rota ativa via rx.State ou router state

COMPONENTS/CONVERSA_ITEM.PY:
def conversa_item(conversa: dict) -> rx.Component:
   - rx.hstack com título + data à esquerda e ícone lixeira à direita
   - class_name="conversa-item" para o hover via CSS
   - Ícone lixeira com class_name="conversa-delete" e opacity=0 (CSS revela no hover)
   - on_click: ChatState.selecionar_conversa(conversa["id"])
   - on_click do ícone lixeira: rx.stop_propagation +
     ChatState.excluir_conversa(conversa["id"])
   - Fundo ativo quando conversa["id"] == ChatState.conversa_ativa

COMPONENTS/SIDEBAR.PY:
def sidebar() -> rx.Component:
   Estrutura conforme DESIGN_SYSTEM.md:
   - Cabeçalho: logo "ContaView" com acento na cor accent + ícone chevron
   - Navegação: rx.foreach sobre PAGINAS usando nav_item()
   - Divisor rx.divider()
   - Botão "Nova conversa": background accent, on_click ChatState.nova_conversa
   - Label "CONVERSAS" uppercase em text_secondary
   - rx.scroll_area com max_height="220px" contendo
     rx.foreach sobre ChatState.conversas usando conversa_item()
   - rx.spacer()
   - Footer: avatar com iniciais + nome do usuário + ícone de tema + ícone logout
   Largura fixa: 252px, height: 100vh, background: sidebar_bg do tema ativo

COMPONENTS/KPI_CARD.PY:
def kpi_card(label: str, valor: str, tipo: str) -> rx.Component:
   - rx.vstack com label uppercase (10px, text_secondary) + valor (24px, bold)
   - tipo pode ser "positivo", "negativo" ou "neutro"
   - Cor do valor conforme tipo e tema ativo
   - Fundo card_bg, borda border, border_radius 10px, padding 14px 16px

COMPONENTS/FILTROS.PY:
def filtros() -> rx.Component:
   - rx.hstack com dois rx.select:
     empresa: DadosState.empresas_disponiveis, on_change set_empresa_selecionada
     periodo: DadosState.periodos_disponiveis, on_change set_periodo_selecionado
   - Espaçamento spacing="3", margin_bottom="20px"

COMPONENTS/ALERTA.PY:
def alerta_auditoria(ocorrencia: dict) -> rx.Component:
   - rx.callout com texto da ocorrência
   - color_scheme: red (alta), amber (media), blue (baixa)
   - Baseado em ocorrencia["severidade"]

Regras para todos os componentes:
- Sem emojis
- Sem texto em inglês
- Todas as cores via rx.cond(TemaState.tema_escuro, ECLIPSE["token"], MINERAL["token"])
- Usar a skill reflex-docs se houver dúvida sobre sintaxe de qualquer componente
```

**Checklist de validação:**
- [ ] `reflex run` sem erro após criar os componentes
- [ ] Sidebar renderiza sem erro em uma página de teste
- [ ] Hover do `conversa_item` revela o ícone de lixeira via CSS
- [ ] `kpi_card` muda cor do valor conforme o tipo
- [ ] Nenhum componente tem texto em inglês ou emojis

---

## ETAPA 4 — Página de login e proteção de rotas

**Objetivo:** Criar a tela de login e o mecanismo que impede acesso
a qualquer página sem autenticação.

**Prompt:**

```
Crie a página de login e o mecanismo de proteção de rotas do ContaView:

PAGES/LOGIN.PY:
@rx.page(route="/")
def login() -> rx.Component:
   - Tela centralizada na viewport (height: 100vh)
   - Fundo: content_bg do tema ativo
   - Card central com:
     - Título "ContaView" (22px, weight=600) com acento na cor accent
     - Subtítulo "Acesso restrito" (14px, text_secondary)
     - rx.input para usuário (placeholder="Usuário")
     - rx.input para senha (type="password", placeholder="Senha")
     - Botão "Entrar" (background accent, width="100%")
       on_click: AuthState.fazer_login(usuario, senha)
   - Sem sidebar
   - Sem nenhum outro elemento além do card

PROTEÇÃO DE ROTAS:
Criar uma função decorator ou componente de guarda reutilizável:

def pagina_protegida(componente: rx.Component) -> rx.Component:
   return rx.cond(
      AuthState.autenticado,
      componente,
      rx.script("window.location.href = '/'"),
   )

Aplicar esse wrapper em todas as páginas exceto login.

CONTAVIEW.PY — registrar as rotas:
app = rx.App(
   stylesheets=["styles.css"],
)
app.add_page(login, route="/")
app.add_page(painel, route="/painel")
app.add_page(lancamentos, route="/lancamentos")
app.add_page(importar, route="/importar")
app.add_page(conciliacao, route="/conciliacao")
app.add_page(auditoria, route="/auditoria")
app.add_page(relatorios, route="/relatorios")
app.add_page(assistente, route="/assistente")

Por enquanto, as páginas /painel até /assistente podem ser placeholders
que exibem apenas o título da página e a sidebar — o conteúdo real
vem nas próximas etapas.
```

**Checklist de validação:**
- [ ] Acessar `/` exibe apenas a tela de login, sem sidebar
- [ ] Credenciais erradas exibem o alerta de erro
- [ ] Login correto redireciona para `/painel`
- [ ] Acessar `/painel` diretamente sem login redireciona para `/`
- [ ] Botão de logout na sidebar volta para `/`
- [ ] Todas as 8 rotas estão registradas no `contaview.py`

---

## ETAPA 5 — Páginas analíticas (Painel e Lançamentos)

**Objetivo:** Construir as duas primeiras páginas com dados reais do banco.

**Prompt:**

```
Construa as páginas Painel e Lançamentos do ContaView em Reflex.
Use a skill reflex-docs para sintaxe de gráficos e tabelas.

PAGES/PAINEL.PY:
Layout:
- Sidebar à esquerda (componente sidebar())
- Área de conteúdo com:
  1. Título "Painel" (22px) + subtítulo com empresa e período selecionados
  2. Componente filtros() no topo
  3. Linha de 3 kpi_card():
     - Débitos: soma dos lançamentos tipo D (cor negativo)
     - Créditos: soma dos lançamentos tipo C (cor positivo)
     - Saldo: créditos - débitos (positivo se > 0, negativo se < 0)
  4. Gráfico Plotly de barras agrupadas: débitos vs créditos por mês
     - Barras de débito: cor negative do tema ativo
     - Barras de crédito: cor positive do tema ativo
     - Fundo: card_bg, texto: text_primary, grid: border
  5. Gráfico Plotly de barras horizontais: top 10 contas por volume

Os KPIs e gráficos são calculados a partir de DadosState.lancamentos.
Usar rx.cond(DadosState.carregando, rx.spinner(), conteudo_real)
para mostrar loading enquanto os dados chegam.

PAGES/LANCAMENTOS.PY:
Layout:
- Sidebar + filtros() no topo
- rx.data_table com as colunas:
  Data, Conta Contábil, Valor (R$), Tipo, Histórico, Filial
- Coluna Tipo com badge colorido: C em verde (positive), D em vermelho (negative)
- Coluna Valor alinhada à direita, formatada como R$ 0.000,00
- Coluna Data formatada como DD/MM/AAAA
- Paginação nativa do rx.data_table

Regras:
- Nunca exibir colunas técnicas (id, empresa_id, sequencial_lote, etc.)
- Todas as cores via tokens do tema ativo
- Sem texto em inglês nos cabeçalhos da tabela
```

**Checklist de validação:**
- [ ] Painel exibe os 3 KPIs com valores reais do banco
- [ ] Gráficos renderizam sem erro no dark e no light mode
- [ ] Filtrar por empresa atualiza KPIs e gráficos
- [ ] Tabela de Lançamentos exibe dados reais com formatação correta
- [ ] Coluna Tipo mostra badge colorido C/D
- [ ] Nenhuma coluna técnica aparece na tabela

---

## ETAPA 6 — Importação, Conciliação e Auditoria

**Objetivo:** Construir as páginas de operação contábil.

**Prompt:**

```
Construa as páginas Importar, Conciliação e Auditoria do ContaView.

PAGES/IMPORTAR.PY:
Fluxo de UI:
1. Campo texto para nome da empresa (rx.input)
2. Campo texto para CNPJ opcional (rx.input)
3. rx.upload para arquivo .xlsx ou .csv
4. Ao fazer upload: chamar DadosState.executar_importacao()
   que internamente chama logic/importacao.executar_importacao()
5. Se retornar requer_confirmacao=True:
   exibir rx.alert_dialog com:
   - Mensagem: "Já existem lançamentos de [empresa] para [período]."
   - Botão "Substituir": chama DadosState.confirmar_substituicao()
   - Botão "Cancelar": fecha o dialog
6. Se retornar sucesso: rx.callout verde com quantidade de registros salvos
7. Se retornar erro: rx.callout vermelho com lista de problemas
8. Após salvar com sucesso: executar auditoria e conciliação automaticamente
   e exibir resumo de ocorrências encontradas

PAGES/CONCILIACAO.PY:
- filtros() no topo
- 3 kpi_card(): Total de pares, Pares OK, Sem par
- Tabela de pares conciliados (rx.data_table)
- Tabela de lançamentos sem par com destaque visual (fundo negative com opacity 0.1)
- Botão "Exportar relatório (Excel)" usando rx.download
- Botão "Exportar PDF" usando rx.download

PAGES/AUDITORIA.PY:
- filtros() no topo
- 3 kpi_card() com contagem por severidade: Alta, Média, Baixa
- Tabela de ocorrências com colunas: Tipo, Descrição, Severidade, Resolvida
- Coluna Severidade com badge colorido: alta=vermelho, media=âmbar, baixa=azul
- Checkbox na coluna Resolvida que chama DadosState.marcar_ocorrencia_resolvida()
- Botão "Exportar relatório (Excel)" usando rx.download

Regras gerais:
- Toda operação de escrita usa try/except e exibe feedback visual
- Nunca deixar o usuário sem resposta — sempre exibir sucesso ou erro
- Usar rx.spinner() durante operações assíncronas
```

**Checklist de validação:**
- [ ] Upload da planilha real da contadora funciona
- [ ] Segunda importação do mesmo período exibe o dialog de confirmação
- [ ] "Substituir" apaga e reimporta corretamente
- [ ] Auditoria exibe ocorrências após importação
- [ ] Conciliação exibe pares e lançamentos sem par
- [ ] Marcar ocorrência como resolvida persiste no banco
- [ ] Exportações geram arquivos baixáveis

---

## ETAPA 7 — Relatórios e tema dark/light

**Objetivo:** Construir a página de relatórios e garantir que o tema
funciona corretamente em todas as páginas.

**Prompt:**

```
Construa a página Relatórios e finalize o sistema de tema do ContaView.

PAGES/RELATORIOS.PY:
- Página centralizada com cards de relatório disponíveis
- Cada card exibe: nome do relatório, descrição breve, botões de download
- Relatórios disponíveis:
  1. Lançamentos do período — Excel
  2. Relatório de conciliação — Excel e PDF
  3. Relatório de auditoria — Excel
- Filtros de empresa e período no topo
- Todos os downloads via rx.download com o retorno de
  logic/relatorios.exportar_excel() ou logic/relatorios.exportar_pdf()

SISTEMA DE TEMA:
1. Verificar que o toggle no footer da sidebar chama TemaState.alternar_tema()
2. Verificar que TODOS os componentes já criados usam
   rx.cond(TemaState.tema_escuro, ECLIPSE["token"], MINERAL["token"])
   nos seguintes tokens no mínimo:
   - background das páginas: content_bg
   - background da sidebar: sidebar_bg
   - background dos cards: card_bg
   - bordas: border
   - textos: text_primary e text_secondary
   - accent nas seleções e botões
3. Verificar que os gráficos Plotly recebem o tema correto:
   - Light: fundo #FFFFFF, texto #1A1916, grid #E0DDD5
   - Dark: fundo #161920, texto #E8E8E8, grid #1E2128
4. Verificar que os inputs têm as cores corretas no dark mode:
   texto #E8E8E8, fundo #1E2530, borda #3A4150

Usar a skill reflex-docs para verificar a sintaxe correta
de rx.download e de customização de temas no Reflex.
```

**Checklist de validação:**
- [ ] Toggle de tema muda a interface inteira imediatamente
- [ ] Sidebar, cards, gráficos e inputs têm cores corretas em ambos os modos
- [ ] Downloads de Excel e PDF funcionam em ambos os modos
- [ ] Página Relatórios exibe todos os 3 relatórios disponíveis
- [ ] Filtros de empresa e período funcionam na página Relatórios

---

## ETAPA 8 — Assistente de IA

**Objetivo:** Construir a página do chat com histórico persistido.

**Prompt:**

```
Construa a página do Assistente de IA do ContaView em Reflex.
Use a skill reflex-docs para sintaxe de componentes de chat e scroll.

PAGES/ASSISTENTE.PY:
Layout:
- Sidebar à esquerda (com a lista de conversas já renderizada)
- Área de conteúdo do chat à direita:
  1. Se ChatState.conversa_ativa is None:
     mensagem centralizada "Selecione uma conversa ou inicie uma nova."
  2. Se conversa ativa:
     a. Histórico de mensagens: rx.foreach sobre ChatState.mensagens
        - Mensagem "user": alinhada à direita, fundo accent com opacity 0.15
        - Mensagem "assistant": alinhada à esquerda, fundo card_bg
        - Cada mensagem em rx.box com border_radius=12px, padding=12px 16px
     b. O histórico deve ter scroll automático para a última mensagem
        usando rx.scroll_area com height="calc(100vh - 180px)"
     c. Campo de entrada no rodapé:
        - rx.hstack com rx.text_area (flex=1) + botão enviar
        - on_click ou on_key_down (Enter): ChatState.enviar_mensagem()
        - Mostrar rx.spinner() enquanto ChatState aguarda resposta
        - Limpar o campo após enviar

SIDEBAR — adicionar na Etapa 3 o comportamento de conversas:
- Quando página ativa é /assistente:
  exibir a lista de conversas normalmente
- Quando página ativa é qualquer outra:
  ocultar a seção de conversas (rx.cond sobre rota atual)
- Ao entrar na página /assistente pela primeira vez:
  chamar ChatState.carregar_conversas() via on_mount da página

ON_MOUNT da página assistente:
- Chamar ChatState.carregar_conversas()
- Se ChatState.conversa_ativa is None: chamar ChatState.nova_conversa()

Regras:
- Sem filtros de empresa ou período nesta página
- Sem KPIs ou gráficos nesta página
- O assistente responde qualquer dúvida — não limitar os tópicos
- Usar logic/assistente.perguntar_ao_assistente() do módulo existente
- Usar logic/assistente.gerar_titulo_conversa() para nomear a conversa
  automaticamente a partir da primeira mensagem
```

**Checklist de validação:**
- [ ] Página assistente abre com uma conversa nova automaticamente
- [ ] Enviar mensagem salva no banco e exibe resposta da OpenAI
- [ ] Histórico da conversa persiste ao recarregar a página
- [ ] Lista de conversas na sidebar atualiza após nova conversa
- [ ] Deletar conversa da sidebar remove da lista e cria nova automaticamente
- [ ] Campo de entrada limpa após enviar
- [ ] Scroll desce automaticamente para a última mensagem

---

## ETAPA 9 — Deploy no Reflex Cloud

**Objetivo:** Publicar o projeto no Reflex Cloud.

**Prompt:**

```
Prepare o projeto ContaView para deploy no Reflex Cloud.
Use a skill reflex-process-management para os comandos corretos.

1. Verificar que o rxconfig.py está configurado corretamente para produção.

2. Verificar que nenhuma credencial está hardcoded em nenhum arquivo —
   todas lidas via os.getenv().

3. Verificar que o requirements.txt tem todas as dependências com
   versões fixas conforme o AGENTS.md.

4. Rodar reflex export para verificar se o build de produção funciona
   sem erro antes de fazer o deploy.

5. Executar o deploy:
   reflex deploy

6. Após o deploy, configurar as variáveis de ambiente no painel do
   Reflex Cloud:
   DATABASE_URL, APP_USUARIO, APP_SENHA, OPENAI_API_KEY

7. Verificar que o app abre no URL fornecido pelo Reflex Cloud,
   que o login funciona, e que a conexão com o Supabase está ativa.
```

**Checklist de validação:**
- [ ] `reflex export` sem erro
- [ ] `reflex deploy` conclui sem erro
- [ ] App abre no URL do Reflex Cloud
- [ ] Login funciona em produção
- [ ] Importação de planilha funciona em produção
- [ ] Assistente responde em produção
- [ ] Tema dark/light funciona em produção

---

## Notas gerais para o OpenCode

- Sempre carregar as 3 skills antes de qualquer prompt.
- Sempre colar o AGENTS.md e o DESIGN_SYSTEM.md como contexto.
- Uma etapa por vez — nunca pedir duas etapas no mesmo prompt.
- Se o agente gerar sintaxe de Streamlit (st.*, session_state),
  interrompa e peça para usar a skill reflex-docs e corrigir.
- Se o agente tentar reescrever os módulos de logic/, interrompa —
  eles são reaproveitados sem alteração estrutural.
- Ao final de cada etapa: rodar reflex run localmente e validar
  a checklist antes de avançar.
