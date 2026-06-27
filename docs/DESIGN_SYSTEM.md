# ContaView — Design System (Reflex)

Documento de referência visual e estrutural para construção da interface em Reflex.
Cole este arquivo no contexto do OpenCode antes de construir qualquer tela ou componente.

> Nota de versão: a sintaxe exata de algumas props do Reflex pode variar entre versões
> do framework. Os conceitos, tokens e arquitetura abaixo são estáveis — se algum nome
> de prop específico (`_hover`, `class_name`, etc.) tiver mudado na versão instalada,
> consulte a documentação oficial do Reflex e adapte mantendo o mesmo comportamento.

---

## Identidade

**Nome do produto:** ContaView
**Público:** Uma contadora que trabalha com grupo de empresas
**Stack de interface:** Reflex (Python → compila para React + FastAPI)
**Backend de dados:** Os módulos `database.py`, `parsers.py`, `importacao.py`,
`conciliacao.py`, `auditoria.py` e `relatorios.py` são reaproveitados sem alteração
estrutural — apenas chamados a partir dos manipuladores de evento do Reflex.
**Tom da interface:** Profissional e direto. Sem emojis. Sem linguagem de marketing.
**Idioma de todo o código e interface:** Português (PT-BR)

---

## Paleta de cores

### Light Mode — Mineral

| Nome do token        | Hex       | Uso                                         |
|-----------------------|-----------|---------------------------------------------|
| `sidebar_bg`          | `#2C3540` | Fundo da barra lateral                      |
| `sidebar_text`        | `#8FA0AE` | Texto inativo na sidebar                    |
| `sidebar_active`      | `#7EB8C4` | Texto e ícone do item ativo                 |
| `sidebar_active_bg`   | `#3D4F5C` | Fundo do item ativo na sidebar              |
| `content_bg`          | `#F2F0EA` | Fundo da área de conteúdo                   |
| `card_bg`             | `#FFFFFF` | Fundo de cards, KPIs e tabelas              |
| `border`              | `#E0DDD5` | Bordas de cards e separadores               |
| `text_primary`        | `#1A1916` | Títulos e valores principais                |
| `text_secondary`      | `#7A7870` | Labels, subtítulos, texto auxiliar          |
| `accent`              | `#7EB8C4` | Acento principal — seleções, links, hover   |
| `positive`            | `#2D8C5E` | Valores positivos, créditos, saldo positivo |
| `negative`            | `#C94B3C` | Valores negativos, débitos, alertas         |
| `warning`             | `#BA7517` | Ocorrências de severidade média             |
| `info`                | `#3A7DBF` | Informações e indicadores neutros           |

### Dark Mode — Eclipse

| Nome do token        | Hex       | Uso                                         |
|-----------------------|-----------|---------------------------------------------|
| `sidebar_bg`          | `#090B0F` | Fundo da barra lateral                      |
| `sidebar_text`        | `#4A5260` | Texto inativo na sidebar                    |
| `sidebar_active`      | `#00C9A0` | Texto e ícone do item ativo                 |
| `sidebar_active_bg`   | `#0D1F1B` | Fundo do item ativo na sidebar              |
| `content_bg`          | `#0F1117` | Fundo da área de conteúdo                   |
| `card_bg`             | `#161920` | Fundo de cards, KPIs e tabelas              |
| `border`              | `#1E2128` | Bordas de cards e separadores               |
| `text_primary`        | `#E8E8E8` | Títulos e valores principais                |
| `text_secondary`      | `#4A5260` | Labels, subtítulos, texto auxiliar          |
| `accent`              | `#00C9A0` | Acento principal — seleções, links, hover   |
| `positive`            | `#00C9A0` | Valores positivos, créditos, saldo positivo |
| `negative`            | `#FF6B5B` | Valores negativos, débitos, alertas         |
| `warning`             | `#F0A840` | Ocorrências de severidade média             |
| `info`                | `#5BA8E8` | Informações e indicadores neutros           |

---

## Tipografia

| Papel            | Tamanho | Peso   | Uso                                  |
|------------------|---------|--------|---------------------------------------|
| Título de página | 22px    | 600    | Nome da página atual                  |
| Subtítulo        | 14px    | 400    | Contexto abaixo do título (empresa + período) |
| Label de KPI     | 10px    | 600    | Rótulo acima do valor no card         |
| Valor de KPI     | 24px    | 700    | Número principal do card              |
| Título de seção  | 11px    | 600    | Cabeçalho de grupo (uppercase, letter-spacing 0.06em) |
| Corpo de tabela  | 13px    | 400    | Dados nas tabelas                     |
| Texto auxiliar   | 12px    | 400    | Notas, avisos, rodapés                |

---

## Arquitetura de pastas do projeto

```
contaview/
├── contaview/
│   ├── contaview.py          # Entry point — registra o rx.App e as páginas
│   ├── styles.py              # Tokens de cor (dicts MINERAL e ECLIPSE)
│   ├── state/
│   │   ├── auth_state.py      # Login, sessão
│   │   ├── tema_state.py      # Tema claro/escuro
│   │   ├── dados_state.py     # Filtros de empresa/período, cache de lançamentos
│   │   └── chat_state.py      # Conversas, mensagens, conversa ativa
│   ├── components/
│   │   ├── sidebar.py         # Sidebar completa (nav + conversas)
│   │   ├── nav_item.py        # Item de navegação reutilizável
│   │   ├── conversa_item.py   # Item de conversa com hover e exclusão
│   │   ├── kpi_card.py         # Card de métrica
│   │   ├── alerta.py           # Alertas de auditoria por severidade
│   │   └── filtros.py          # Seletores de empresa/período
│   ├── pages/
│   │   ├── login.py
│   │   ├── painel.py
│   │   ├── lancamentos.py
│   │   ├── importar.py
│   │   ├── conciliacao.py
│   │   ├── auditoria.py
│   │   ├── relatorios.py
│   │   └── assistente.py
│   └── logic/                  # Reaproveitado quase sem alteração
│       ├── database.py
│       ├── parsers.py
│       ├── importacao.py
│       ├── conciliacao.py
│       ├── auditoria.py
│       ├── relatorios.py
│       └── assistente.py       # Apenas a lógica de chamada à OpenAI — sem UI
├── rxconfig.py
├── requirements.txt
├── .env.example
├── .gitignore
├── AGENTS.md
└── docs/
    └── DESIGN_SYSTEM.md
```

---

## Gerenciamento de estado

O Reflex usa classes de `rx.State` para qualquer dado que muda na tela.
Cada classe abaixo tem uma responsabilidade única — não misturar.

### `AuthState`
```python
class AuthState(rx.State):
    autenticado: bool = False
    usuario: str = ""

    def fazer_login(self, usuario: str, senha: str):
        from contaview.logic import auth
        if auth.verificar_login(usuario, senha):
            self.autenticado = True
            self.usuario = usuario
            return rx.redirect("/painel")
        return rx.window_alert("Usuário ou senha incorretos.")

    def fazer_logout(self):
        self.autenticado = False
        self.usuario = ""
        return rx.redirect("/")
```

### `TemaState`
```python
class TemaState(rx.State):
    tema_escuro: bool = False

    def alternar_tema(self):
        self.tema_escuro = not self.tema_escuro
```

### `DadosState`
```python
class DadosState(rx.State):
    empresa_selecionada: str = ""
    periodo_selecionado: str = ""
    lancamentos: list[dict] = []

    def carregar_lancamentos(self):
        from contaview.logic import database
        self.lancamentos = database.carregar_lancamentos(
            empresa_id=self.empresa_selecionada,
            periodo=self.periodo_selecionado,
        ).to_dict("records")
```

### `ChatState`
```python
class ChatState(rx.State):
    conversas: list[dict] = []
    conversa_ativa: int | None = None
    mensagens: list[dict] = []
    entrada_atual: str = ""

    def carregar_conversas(self):
        from contaview.logic import database
        self.conversas = database.listar_conversas()

    def selecionar_conversa(self, conversa_id: int):
        from contaview.logic import database
        self.conversa_ativa = conversa_id
        self.mensagens = database.carregar_mensagens(conversa_id)

    def nova_conversa(self):
        from contaview.logic import database
        novo_id = database.criar_conversa()
        self.conversa_ativa = novo_id
        self.mensagens = []
        return ChatState.carregar_conversas

    def excluir_conversa(self, conversa_id: int):
        from contaview.logic import database
        database.deletar_conversa(conversa_id)
        if self.conversa_ativa == conversa_id:
            self.conversa_ativa = None
            self.mensagens = []
        return ChatState.carregar_conversas

    async def enviar_mensagem(self):
        from contaview.logic import database, assistente
        if self.conversa_ativa is None:
            self.conversa_ativa = database.criar_conversa()

        texto = self.entrada_atual
        self.entrada_atual = ""
        database.salvar_mensagem(self.conversa_ativa, "user", texto)
        self.mensagens.append({"role": "user", "conteudo": texto})

        if len(self.mensagens) == 1:
            titulo = assistente.gerar_titulo_conversa(texto)
            database.renomear_conversa(self.conversa_ativa, titulo)

        resposta = assistente.perguntar_ao_assistente(self.mensagens)
        database.salvar_mensagem(self.conversa_ativa, "assistant", resposta)
        self.mensagens.append({"role": "assistant", "conteudo": resposta})
```

---

## Layout — estrutura geral

```
┌─────────────────────────────────────────────────────────────┐
│  SIDEBAR (252px fixo)  │  CONTEÚDO (restante da tela)        │
│                         │                                     │
│  ContaView         <   │  [ Título da página ]                │
│  ─────────────────     │  [ Subtítulo: empresa + período ]    │
│  Painel                │                                     │
│  Lançamentos            │  [ KPI ]  [ KPI ]  [ KPI ]           │
│  Importar               │                                     │
│  Conciliação            │  [ Gráfico / Tabela principal ]      │
│  Auditoria               │                                     │
│  Relatórios              │  [ Seção secundária ]                │
│  ─────────────────     │                                     │
│  + Nova conversa        │                                     │
│  CONVERSAS         ↕    │                                     │
│  ┌───────────────────┐ │                                     │
│  │ conversa 1      🗑│ │  (scroll vertical, hover revela     │
│  │ conversa 2      🗑│ │   o ícone de excluir)                │
│  │ conversa 3      🗑│ │                                     │
│  └───────────────────┘ │                                     │
│  ─────────────────     │                                     │
│  [avatar] usuario  ☾ ⎋ │                                     │
└─────────────────────────┴─────────────────────────────────────┘
```

---

## Sidebar — especificação de componente

```python
def sidebar() -> rx.Component:
    return rx.vstack(
        # Cabeçalho
        rx.hstack(
            rx.text("Conta", rx.text.span("View", color=rx.color("teal", 9)),
                     size="4", weight="medium"),
            rx.icon("chevron-left", size=16, color=Cor.text_secondary),
            justify="between",
            width="100%",
            padding="4px 8px 16px",
        ),

        # Navegação principal
        rx.foreach(
            PAGINAS,
            lambda pagina: nav_item(pagina),
        ),

        rx.divider(margin_y="14px"),

        # Botão nova conversa
        rx.button(
            rx.icon("plus", size=14),
            "Nova conversa",
            on_click=ChatState.nova_conversa,
            width="100%",
            background=Cor.accent,
            color=Cor.sidebar_bg,
        ),

        # Cabeçalho da lista de conversas
        rx.hstack(
            rx.text("CONVERSAS", size="1", color=Cor.text_secondary,
                     letter_spacing="0.06em"),
            rx.icon("arrow-up-down", size=13, color=Cor.text_secondary),
            justify="between",
            width="100%",
            padding="12px 10px 6px",
        ),

        # Lista rolável de conversas
        rx.scroll_area(
            rx.vstack(
                rx.foreach(ChatState.conversas, conversa_item),
                spacing="1",
            ),
            max_height="220px",
            width="100%",
        ),

        rx.spacer(),

        # Rodapé
        rx.divider(),
        rx.hstack(
            rx.avatar(fallback="LF", size="2"),
            rx.text(AuthState.usuario, size="2", flex="1"),
            rx.icon(
                rx.cond(TemaState.tema_escuro, "sun", "moon"),
                size=15,
                cursor="pointer",
                on_click=TemaState.alternar_tema,
            ),
            rx.icon("log-out", size=15, cursor="pointer",
                     on_click=AuthState.fazer_logout),
            width="100%",
            padding_top="12px",
        ),

        background=Cor.sidebar_bg,
        height="100vh",
        width="252px",
        padding="16px 10px",
        spacing="2",
    )
```

### Item de conversa com hover de exclusão

```python
def conversa_item(conversa: dict) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(conversa["titulo"], size="2", color=Cor.text_primary),
            rx.text(conversa["atualizado_em"], size="1", color=Cor.text_secondary),
            spacing="0",
            align="start",
        ),
        rx.icon(
            "trash",
            size=14,
            color=Cor.text_secondary,
            opacity="0",
            class_name="conversa-delete",
            on_click=[
                rx.stop_propagation,
                lambda: ChatState.excluir_conversa(conversa["id"]),
            ],
        ),
        on_click=lambda: ChatState.selecionar_conversa(conversa["id"]),
        justify="between",
        width="100%",
        padding="8px 10px",
        border_radius="8px",
        cursor="pointer",
        class_name="conversa-item",
        background=rx.cond(
            ChatState.conversa_ativa == conversa["id"],
            Cor.card_bg,
            "transparent",
        ),
    )
```

CSS global necessário (em `assets/styles.css`, importado no `rxconfig.py`):
```css
.conversa-item:hover { background-color: var(--card-bg); }
.conversa-item:hover .conversa-delete { opacity: 1; transition: opacity .15s; }
```

---

## Componentes

### Card de KPI

```python
def kpi_card(label: str, valor: str, tipo: str = "neutro") -> rx.Component:
    cor_valor = {
        "positivo": Cor.positive,
        "negativo": Cor.negative,
        "neutro": Cor.text_primary,
    }[tipo]
    return rx.vstack(
        rx.text(label.upper(), size="1", color=Cor.text_secondary,
                 letter_spacing="0.08em", weight="bold"),
        rx.text(valor, size="6", weight="bold", color=cor_valor),
        background=Cor.card_bg,
        border=f"1px solid {Cor.border}",
        border_radius="10px",
        padding="14px 16px",
        spacing="1",
    )
```

### Alertas de auditoria

```python
def alerta_auditoria(ocorrencia: dict) -> rx.Component:
    cores = {"alta": Cor.negative, "media": Cor.warning, "baixa": Cor.info}
    return rx.callout(
        ocorrencia["descricao"],
        color_scheme=rx.cond(ocorrencia["severidade"] == "alta", "red",
                     rx.cond(ocorrencia["severidade"] == "media", "amber", "blue")),
        size="2",
    )
```

### Botões — variantes

```python
rx.button("Importar lançamentos", color_scheme="teal")     # ação principal
rx.button("Exportar relatório", variant="outline")          # ação secundária
rx.button("Substituir período", color_scheme="red", variant="soft")  # destrutiva
```

### Filtros de contexto

```python
def filtros() -> rx.Component:
    return rx.hstack(
        rx.select(
            DadosState.empresas_disponiveis,
            placeholder="Empresa",
            on_change=DadosState.set_empresa_selecionada,
        ),
        rx.select(
            DadosState.periodos_disponiveis,
            placeholder="Período",
            on_change=DadosState.set_periodo_selecionado,
        ),
        spacing="3",
        margin_bottom="20px",
    )
```

---

## Tema dinâmico

O arquivo `styles.py` define os dois dicionários de tokens e uma função que escolhe
o conjunto certo conforme `TemaState.tema_escuro`:

```python
MINERAL = {
    "sidebar_bg": "#2C3540", "sidebar_text": "#8FA0AE",
    "sidebar_active": "#7EB8C4", "content_bg": "#F2F0EA",
    "card_bg": "#FFFFFF", "border": "#E0DDD5",
    "text_primary": "#1A1916", "text_secondary": "#7A7870",
    "accent": "#7EB8C4", "positive": "#2D8C5E",
    "negative": "#C94B3C", "warning": "#BA7517", "info": "#3A7DBF",
}

ECLIPSE = {
    "sidebar_bg": "#090B0F", "sidebar_text": "#4A5260",
    "sidebar_active": "#00C9A0", "content_bg": "#0F1117",
    "card_bg": "#161920", "border": "#1E2128",
    "text_primary": "#E8E8E8", "text_secondary": "#4A5260",
    "accent": "#00C9A0", "positive": "#00C9A0",
    "negative": "#FF6B5B", "warning": "#F0A840", "info": "#5BA8E8",
}

def cor(tema_escuro: bool, token: str) -> str:
    return (ECLIPSE if tema_escuro else MINERAL)[token]
```

Cada componente usa `rx.cond(TemaState.tema_escuro, ECLIPSE["x"], MINERAL["x"])`
diretamente nas props de estilo — o Reflex já lida com a reatividade, então a tela
inteira se atualiza sozinha quando o toggle é acionado, sem rerun de página.

---

## Nomes padronizados (PT-BR)

### Classes de State
- `AuthState` — `auth_state.py`
- `TemaState` — `tema_state.py`
- `DadosState` — `dados_state.py`
- `ChatState` — `chat_state.py`

### Páginas (rotas)
```python
PAGINAS = [
    {"label": "Painel",        "rota": "/painel",       "icone": "layout-dashboard"},
    {"label": "Lançamentos",   "rota": "/lancamentos",  "icone": "list"},
    {"label": "Importar",      "rota": "/importar",     "icone": "upload"},
    {"label": "Conciliação",   "rota": "/conciliacao",  "icone": "arrow-left-right"},
    {"label": "Auditoria",     "rota": "/auditoria",    "icone": "search"},
    {"label": "Relatórios",    "rota": "/relatorios",   "icone": "file-text"},
]
```

### Funções de `logic/` — mantidas exatamente como antes
- `database.py` → `inicializar_banco()`, `obter_ou_criar_empresa()`, `salvar_lancamentos()`,
  `verificar_periodo_existente()`, `carregar_lancamentos()`, `criar_conversa()`,
  `salvar_mensagem()`, `carregar_mensagens()`, `listar_conversas()`, `deletar_conversa()`
- `parsers.py` → `ler_arquivo()`, `normalizar_colunas()`, `limpar_dataframe()`
- `importacao.py` → `executar_importacao()`, `validar_pre_import()`, `injetar_sequencial_lote()`
- `conciliacao.py` → `conciliar_partidas()`, `gerar_relatorio_conciliacao()`
- `auditoria.py` → `auditar_lancamentos()`, `classificar_ocorrencias()`
- `relatorios.py` → `exportar_excel()`, `exportar_pdf()`
- `assistente.py` → `perguntar_ao_assistente()`, `gerar_titulo_conversa()`

---

## Regras de comportamento da interface

1. **Nenhuma página é acessível sem login.** Cada página verifica `AuthState.autenticado`
   no topo do componente e redireciona para `/` (login) se falso, usando `rx.cond`
   ou um decorator de proteção de rota compartilhado.

2. **Toda importação passa pelo fluxo completo de `logic/importacao.py`.** Nenhum
   manipulador de evento chama `database.salvar_lancamentos()` diretamente sem passar
   primeiro por `importacao.executar_importacao()`.

3. **Antes de salvar qualquer lote, verificar duplicidade de período.** Se
   `verificar_periodo_existente()` retornar `True`, exibir um `rx.alert_dialog` com as
   opções "Substituir" e "Cancelar". Não existe opção de mesclar.

4. **O assistente nunca recebe dados brutos** quando estiver no modo de análise contextual.
   No modo de chat livre atual, ele responde livremente — mas nenhuma função do
   `logic/` deve vazar dados de outras empresas ou de outras conversas.

5. **Hover e transições são responsabilidade do CSS gerado pelo Reflex**, não de
   lógica de estado. Não usar `rx.State` para controlar opacidade de hover — isso
   é puramente `:hover` em CSS, conforme o exemplo do `conversa_item`.

6. **O toggle de tema é global** — `TemaState.tema_escuro` é lido por todas as páginas
   e componentes. Nenhuma página define seu próprio estado de tema local.

7. **Datas sempre formatadas como `DD/MM/AAAA`** na interface. Internamente armazenadas
   como `date` no banco — a conversão acontece nos componentes, nunca no `logic/`.

8. **Valores monetários sempre formatados como `R$ 0.000,00`** na interface — a
   formatação é feita por uma função utilitária `formatar_moeda()` reutilizada em
   todos os componentes, nunca duplicada inline.
