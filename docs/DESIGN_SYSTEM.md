# ContaView — Design System

Documento de referência visual para construção da interface.
Cole este arquivo no contexto do OpenCode antes de construir qualquer tela.

---

## Identidade

**Nome do produto:** ContaView
**Público:** Uma contadora que trabalha com grupo de empresas
**Plataforma:** Streamlit — acesso via navegador
**Tom da interface:** Profissional e direto. Sem emojis. Sem linguagem de marketing.
**Idioma de todo o código e interface:** Português (PT-BR)

---

## Paleta de cores

### Light Mode — Mineral

| Nome do token        | Hex       | Uso                                         |
|----------------------|-----------|---------------------------------------------|
| `sidebar-bg`         | `#2C3540` | Fundo da barra lateral                      |
| `sidebar-text`       | `#8FA0AE` | Texto inativo na sidebar                    |
| `sidebar-active`     | `#7EB8C4` | Texto e indicador do item ativo             |
| `sidebar-active-bg`  | `#3D4F5C` | Fundo do item ativo na sidebar              |
| `content-bg`         | `#F2F0EA` | Fundo da área de conteúdo                   |
| `card-bg`            | `#FFFFFF` | Fundo de cards, KPIs e tabelas              |
| `border`             | `#E0DDD5` | Bordas de cards e separadores               |
| `text-primary`       | `#1A1916` | Títulos e valores principais                |
| `text-secondary`     | `#7A7870` | Labels, subtítulos, texto auxiliar          |
| `accent`             | `#7EB8C4` | Acento principal — seleções, links, hover   |
| `positive`           | `#2D8C5E` | Valores positivos, créditos, saldo positivo |
| `negative`           | `#C94B3C` | Valores negativos, débitos, alertas         |
| `warning`            | `#BA7517` | Ocorrências de severidade média             |
| `info`               | `#3A7DBF` | Informações e indicadores neutros           |

### Dark Mode — Eclipse

| Nome do token        | Hex       | Uso                                         |
|----------------------|-----------|---------------------------------------------|
| `sidebar-bg`         | `#090B0F` | Fundo da barra lateral                      |
| `sidebar-text`       | `#4A5260` | Texto inativo na sidebar                    |
| `sidebar-active`     | `#00C9A0` | Texto e indicador do item ativo             |
| `sidebar-active-bg`  | `#0D1F1B` | Fundo do item ativo na sidebar              |
| `content-bg`         | `#0F1117` | Fundo da área de conteúdo                   |
| `card-bg`            | `#161920` | Fundo de cards, KPIs e tabelas              |
| `border`             | `#1E2128` | Bordas de cards e separadores               |
| `text-primary`       | `#E8E8E8` | Títulos e valores principais                |
| `text-secondary`     | `#4A5260` | Labels, subtítulos, texto auxiliar          |
| `accent`             | `#00C9A0` | Acento principal — seleções, links, hover   |
| `positive`           | `#00C9A0` | Valores positivos, créditos, saldo positivo |
| `negative`           | `#FF6B5B` | Valores negativos, débitos, alertas         |
| `warning`            | `#F0A840` | Ocorrências de severidade média             |
| `info`               | `#5BA8E8` | Informações e indicadores neutros           |

---

## Tipografia

Streamlit usa a fonte do sistema por padrão. As regras de hierarquia são aplicadas via `st.markdown` com HTML/CSS injetado no `app.py`.

| Papel            | Tamanho | Peso   | Uso                                  |
|------------------|---------|--------|--------------------------------------|
| Título de página | 22px    | 600    | Nome da aba atual                    |
| Subtítulo        | 14px    | 400    | Contexto abaixo do título (empresa + período) |
| Label de KPI     | 10px    | 600    | Rótulo acima do valor no card        |
| Valor de KPI     | 24px    | 700    | Número principal do card             |
| Título de seção  | 11px    | 600    | Cabeçalho de grupo (uppercase, letter-spacing 0.08em) |
| Corpo de tabela  | 13px    | 400    | Dados nas tabelas                    |
| Texto auxiliar   | 12px    | 400    | Notas, avisos, rodapés               |

---

## Layout

### Estrutura geral

```
┌─────────────────────────────────────────────────────────────┐
│  SIDEBAR (200px fixo)  │  CONTEÚDO (restante da tela)       │
│                        │                                     │
│  Logo: ContaView       │  [ Título da aba ]                  │
│                        │  [ Subtítulo: empresa + período ]   │
│  > Painel              │                                     │
│    Lançamentos         │  [ KPI ]  [ KPI ]  [ KPI ]          │
│    Importar            │                                     │
│    Conciliação         │  [ Gráfico / Tabela principal ]     │
│    Auditoria           │                                     │
│    Relatórios          │  [ Seção secundária ]               │
│    Assistente          │                                     │
│                        │                                     │
│  ─────────────────     │                                     │
│  [ Tema: Claro/Escuro ]│                                     │
│  [ Sair ]              │                                     │
└────────────────────────┴─────────────────────────────────────┘
```

### Grid de KPIs

Sempre 3 colunas no topo de cada aba analítica.
Cards com padding `16px`, border-radius `10px`, borda `1px solid border`.

```
[ Débitos do período ]  [ Créditos do período ]  [ Saldo ]
```

### Cards de conteúdo

Padding interno: `20px 24px`
Border-radius: `10px`
Borda: `1px solid border`
Fundo: `card-bg`
Sem sombras — a separação é feita pela cor de fundo e pela borda.

### Tabelas

Usar `st.dataframe` com configuração de colunas explícita.
Linhas alternadas com opacidade 4% do `text-primary`.
Colunas de valor sempre alinhadas à direita.
Colunas de data formatadas como `DD/MM/AAAA`.
Valores positivos em `positive`, negativos em `negative`.

---

## Componentes

### Sidebar

```python
# Estrutura da sidebar
with st.sidebar:
    st.markdown("## ContaView")          # Logo textual
    st.markdown("---")
    pagina = st.radio("", PAGINAS)       # Navegação principal
    st.markdown("---")
    tema = st.toggle("Modo escuro")      # Toggle de tema
    st.button("Sair", on_click=logout)   # Botão de saída
```

### Cards de KPI

```python
# Padrão de KPI — usar st.metric nativo do Streamlit
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Débitos", value="R$ 84.320", delta=None)
with col2:
    st.metric(label="Créditos", value="R$ 97.540", delta=None)
with col3:
    st.metric(label="Saldo", value="R$ 13.220", delta="+R$ 2.100 vs mês anterior")
```

### Alertas de auditoria

```python
# Severidade alta
st.error("3 lançamentos duplicados encontrados — verifique antes de salvar.")

# Severidade média
st.warning("7 lançamentos sem histórico preenchido.")

# Severidade baixa / informativo
st.info("Conciliação do período concluída. 142 pares conferidos.")

# Sucesso
st.success("Importação concluída. 156 lançamentos salvos.")
```

### Filtros de contexto

Sempre no topo da área de conteúdo, em linha, antes dos KPIs.

```python
col_emp, col_per, col_spacer = st.columns([2, 2, 4])
with col_emp:
    empresa = st.selectbox("Empresa", opcoes_empresas, key="filtro_empresa")
with col_per:
    periodo = st.selectbox("Período", opcoes_periodos, key="filtro_periodo")
```

### Botões de ação

```python
# Ação principal (salvar, importar, executar)
st.button("Importar lançamentos", type="primary")

# Ação secundária (exportar, limpar)
st.button("Exportar relatório")

# Ação destrutiva (sobrescrever período)
st.button("Substituir período", type="secondary")
```

---

## Injeção de CSS global

Adicionar no início do `app.py`, após definir o tema ativo.

```python
def aplicar_tema(escuro: bool):
    if escuro:
        sidebar_bg      = "#090B0F"
        sidebar_text    = "#4A5260"
        sidebar_active  = "#00C9A0"
        content_bg      = "#0F1117"
        card_bg         = "#161920"
        border          = "#1E2128"
        text_primary    = "#E8E8E8"
        text_secondary  = "#4A5260"
        accent          = "#00C9A0"
    else:
        sidebar_bg      = "#2C3540"
        sidebar_text    = "#8FA0AE"
        sidebar_active  = "#7EB8C4"
        content_bg      = "#F2F0EA"
        card_bg         = "#FFFFFF"
        border          = "#E0DDD5"
        text_primary    = "#1A1916"
        text_secondary  = "#7A7870"
        accent          = "#7EB8C4"

    st.markdown(f"""
    <style>
        /* Fundo geral */
        .stApp {{ background-color: {content_bg}; }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {sidebar_bg};
        }}
        [data-testid="stSidebar"] * {{
            color: {sidebar_text} !important;
        }}
        [data-testid="stSidebar"] .stRadio [aria-checked="true"] + label {{
            color: {sidebar_active} !important;
            font-weight: 600;
        }}

        /* Cards e métricas */
        [data-testid="stMetric"] {{
            background-color: {card_bg};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 16px;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {text_secondary} !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 24px;
            font-weight: 700;
            color: {text_primary} !important;
        }}

        /* Textos gerais */
        .stMarkdown, p, span, label {{
            color: {text_primary};
        }}

        /* Inputs e selects */
        .stSelectbox > div, .stTextInput > div {{
            border-color: {border} !important;
            background-color: {card_bg} !important;
        }}

        /* Botão primário */
        .stButton [data-baseweb="button"][kind="primary"] {{
            background-color: {accent};
            border-color: {accent};
        }}

        /* Divisor */
        hr {{
            border-color: {border};
            opacity: 1;
        }}
    </style>
    """, unsafe_allow_html=True)
```

---

## Nomes padronizados (PT-BR)

Usar estes nomes em todo o código — variáveis, funções, colunas e labels da interface.

### Módulos e arquivos
- `app.py` — entrada principal
- `auth.py` — autenticação
- `database.py` — banco de dados
- `parsers.py` — leitura de arquivos
- `importacao.py` — fluxo de importação
- `conciliacao.py` — conciliação de partidas
- `auditoria.py` — detecção de anomalias
- `relatorios.py` — exportação
- `assistente.py` — IA

### Colunas do DataFrame e banco
- `empresa_id` — chave da empresa
- `data` — data do lançamento (date)
- `conta_contabil` — código da conta
- `valor` — valor numérico (Decimal)
- `tipo` — `'C'` para crédito, `'D'` para débito
- `historico` — descrição do lançamento
- `filial` — código ou nome da filial
- `periodo` — string `'AAAA-MM'`
- `sequencial_lote` — ordem de entrada no arquivo (int)
- `origem` — `'arquivo'` ou `'manual'`
- `arquivo_origem` — nome do arquivo importado

### Variáveis de sessão (st.session_state)
- `st.session_state.autenticado` — bool
- `st.session_state.usuario` — str
- `st.session_state.tema_escuro` — bool
- `st.session_state.empresa_selecionada` — str
- `st.session_state.periodo_selecionado` — str

### Páginas da sidebar
```python
PAGINAS = [
    "Painel",
    "Lançamentos",
    "Importar",
    "Conciliação",
    "Auditoria",
    "Relatórios",
    "Assistente",
]
```

### Funções principais por módulo
- `auth.py` → `verificar_login()`, `logout()`, `exibir_tela_login()`
- `database.py` → `inicializar_banco()`, `obter_ou_criar_empresa()`, `salvar_lancamentos()`, `verificar_periodo_existente()`, `carregar_lancamentos()`
- `parsers.py` → `ler_arquivo()`, `normalizar_colunas()`, `limpar_dataframe()`
- `importacao.py` → `executar_importacao()`, `validar_pre_import()`, `injetar_sequencial_lote()`
- `conciliacao.py` → `conciliar_partidas()`, `gerar_relatorio_conciliacao()`
- `auditoria.py` → `auditar_lancamentos()`, `classificar_ocorrencias()`
- `relatorios.py` → `exportar_excel()`, `exportar_pdf()`
- `assistente.py` → `montar_contexto_resumido()`, `perguntar_ao_assistente()`

---

## Regras de comportamento da interface

1. **Nenhuma tela é acessível sem login.** O `app.py` verifica `st.session_state.autenticado` na primeira linha após os imports. Se falso, exibe apenas `exibir_tela_login()` e para.

2. **Toda importação passa pelo fluxo completo do `importacao.py`.** Nunca chamar `to_sql` diretamente no `app.py`.

3. **Antes de salvar qualquer lote, o sistema verifica duplicidade de período.** Se `verificar_periodo_existente()` retornar `True`, exibir confirmação com as opções "Substituir" e "Cancelar". Não existe opção "Mesclar".

4. **O assistente nunca recebe dados brutos.** A função `montar_contexto_resumido()` sempre agrega os dados antes de enviar para a API (totais por conta, por período — nunca linhas individuais com valores nominais).

5. **Alertas de auditoria aparecem imediatamente após o upload**, antes da confirmação de salvar. A contadora vê os problemas antes de persistir os dados.

6. **O toggle de tema salva o estado em `st.session_state.tema_escuro`** e chama `aplicar_tema()` a cada rerun.

7. **Datas sempre formatadas como `DD/MM/AAAA`** na interface. Internamente armazenadas como `date` no banco.

8. **Valores monetários sempre formatados como `R$ 0.000,00`** na interface. Internamente como `NUMERIC(14,2)` no banco.
