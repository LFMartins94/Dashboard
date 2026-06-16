import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import assistente
import auditoria
import auth
import conciliacao
import importacao
import relatorios
from database import (
    atualizar_ocorrencia_resolvida,
    carregar_lancamentos,
    carregar_mensagens,
    carregar_ocorrencias,
    criar_conversa,
    deletar_conversa,
    inicializar_banco,
    listar_conversas,
    listar_empresas,
    listar_periodos,
    renomear_conversa,
    salvar_mensagem,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ContaView",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 1. Autenticação ──────────────────────────────────────────────
if not st.session_state.get("autenticado", False):
    auth.exibir_tela_login()
    st.stop()

# ── 2. Injeção de CSS (tema) ─────────────────────────────────────
def aplicar_tema(escuro: bool):
    if escuro:
        sidebar_bg      = "#090B0F"
        sidebar_text    = "#4A5260"
        sidebar_active  = "#00C9A0"
        sidebar_active_bg = "#0D1F1B"
        content_bg      = "#0F1117"
        card_bg         = "#161920"
        border          = "#1E2128"
        text_primary    = "#E8E8E8"
        text_secondary  = "#4A5260"
        accent          = "#00C9A0"
        positive        = "#00C9A0"
        negative        = "#FF6B5B"
        warning         = "#F0A840"
        info            = "#5BA8E8"
    else:
        sidebar_bg      = "#2C3540"
        sidebar_text    = "#8FA0AE"
        sidebar_active  = "#7EB8C4"
        sidebar_active_bg = "#3D4F5C"
        content_bg      = "#F2F0EA"
        card_bg         = "#FFFFFF"
        border          = "#E0DDD5"
        text_primary    = "#1A1916"
        text_secondary  = "#7A7870"
        accent          = "#7EB8C4"
        positive        = "#2D8C5E"
        negative        = "#C94B3C"
        warning         = "#BA7517"
        info            = "#3A7DBF"

    st.session_state.theme_tokens = {
        "sidebar_bg": sidebar_bg,
        "sidebar_text": sidebar_text,
        "sidebar_active": sidebar_active,
        "content_bg": content_bg,
        "card_bg": card_bg,
        "border": border,
        "text_primary": text_primary,
        "text_secondary": text_secondary,
        "accent": accent,
        "positive": positive,
        "negative": negative,
        "warning": warning,
        "info": info,
    }

    st.markdown(f"""
    <style>
        .stApp {{ background-color: {content_bg}; }}

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
        [data-testid="stSidebar"] .stRadio [aria-checked="true"] {{
            background-color: {sidebar_active_bg};
        }}

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

        .stMarkdown, p, span, label, .stDataFrame, .stTextInput > div > div > input {{
            color: {text_primary};
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {text_primary};
        }}

        .stSelectbox > div, .stTextInput > div {{
            border-color: {border} !important;
            background-color: {card_bg} !important;
        }}

        .stButton [data-baseweb="button"][kind="primary"] {{
            background-color: {accent};
            border-color: {accent};
        }}

        hr {{ border-color: {border}; opacity: 1; }}

        .st-emotion-cache-1wivap2, .stChatInput {{
            border-color: {border} !important;
        }}
        [data-testid="stChatMessageContent"] {{
            background-color: {card_bg};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 12px 16px;
        }}
        [data-testid="stChatMessageContent"] p {{
            color: {text_primary};
        }}

        {f'''
        /* Dark mode — inputs com contraste garantido */
        input, textarea, [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {{
            color: #E8E8E8 !important;
            background-color: #1E2530 !important;
        }}
        [data-baseweb="select"] > div {{
            color: #E8E8E8 !important;
            background-color: #1E2530 !important;
        }}
        .stTextInput > div, .stSelectbox > div,
        .stTextArea > div {{
            border-color: #3A4150 !important;
            background-color: #1E2530 !important;
        }}
        input::placeholder, textarea::placeholder {{
            color: #6A7280 !important;
        }}
        label, .stSelectbox label, .stTextInput label,
        .stTextArea label, .stRadio label, .stCheckbox label {{
            color: #B0B8C8 !important;
        }}
        ''' if escuro else ''}
    </style>
    """, unsafe_allow_html=True)

# ── 3. Helpers de UI ─────────────────────────────────────────────
def st_secao(titulo: str):
    tokens = st.session_state.theme_tokens
    st.markdown(f"""
    <h3 style="text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px;
               font-weight: 600; color: {tokens['text_secondary']};
               margin-top: 24px; margin-bottom: 8px;">
        {titulo}
    </h3>
    """, unsafe_allow_html=True)

def configurar_grafico_tema(fig: go.Figure) -> go.Figure:
    tokens = st.session_state.theme_tokens
    fig.update_layout(
        plot_bgcolor=tokens["card_bg"],
        paper_bgcolor=tokens["card_bg"],
        font_color=tokens["text_primary"],
        xaxis=dict(gridcolor=tokens["border"]),
        yaxis=dict(gridcolor=tokens["border"]),
        title_font_size=16,
    )
    return fig

def _fmt_brl(valor: float) -> str:
    s = f"R$ {valor:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_periodo(p: str) -> str:
    try:
        partes = p.split("-")
        return f"{partes[1]}/{partes[0]}"
    except Exception:
        return p

def _selectbox_periodo(label: str, periodos: list, key: str) -> None:
    opcoes = ["Todos"]
    mapa = {}
    for p in (periodos or []):
        d = formatar_periodo(p)
        mapa[d] = p
        opcoes.append(d)
    valor_atual = st.session_state.get(key, "Todos")
    display_atual = "Todos" if valor_atual == "Todos" else formatar_periodo(valor_atual)
    if display_atual not in opcoes:
        display_atual = "Todos"
    selecionado = st.selectbox(label, opcoes, index=opcoes.index(display_atual))
    if selecionado == "Todos":
        st.session_state[key] = "Todos"
    else:
        st.session_state[key] = mapa[selecionado]

def _formatar_df_exibicao(df):
    df = df.copy()
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y")
    if "periodo" in df.columns:
        df["periodo"] = df["periodo"].apply(formatar_periodo)
    return df

# ── 4. Inicialização ─────────────────────────────────────────────
@st.cache_resource
def _inicializar():
    inicializar_banco()

_inicializar()

# ── 5. Sidebar ───────────────────────────────────────────────────
PAGINAS = [
    "Painel",
    "Lançamentos",
    "Importar",
    "Conciliação",
    "Auditoria",
    "Relatórios",
    "Assistente",
]

with st.sidebar:
    st.markdown("## ContaView")
    st.divider()
    pagina = st.radio("Navegação", PAGINAS, label_visibility="collapsed")
    st.divider()

    if pagina == "Assistente":
        if st.button("Nova conversa", type="primary", use_container_width=True):
            conv_id = criar_conversa()
            st.session_state.conversa_ativa = conv_id
            st.rerun()

        conversas = listar_conversas()
        for conv in conversas:
            c1, c2 = st.columns([5, 1])
            with c1:
                ativo = st.session_state.get("conversa_ativa") == conv["id"]
                label = conv["titulo"]
                if st.button(
                    label,
                    key=f"conv_{conv['id']}",
                    use_container_width=True,
                    type="primary" if ativo else "secondary",
                ):
                    st.session_state.conversa_ativa = conv["id"]
                    st.rerun()
            with c2:
                if st.button("X", key=f"del_{conv['id']}", use_container_width=True):
                    if st.session_state.get("conversa_ativa") == conv["id"]:
                        st.session_state.conversa_ativa = None
                    deletar_conversa(conv["id"])
                    st.rerun()

        st.divider()

    tema_escuro = st.toggle("Modo escuro", key="tema_escuro")
    st.button("Sair", on_click=auth.logout)

aplicar_tema(st.session_state.get("tema_escuro", False))
st.title(pagina)

# ── 6. Helpers de filtro ─────────────────────────────────────────
def _empresa_id_do_filtro() -> int | None:
    return st.session_state.get("_empresa_id")

def _periodo_do_filtro() -> str | None:
    val = st.session_state.get("periodo_selecionado", "Todos")
    return None if val == "Todos" else val

# ── 7. Filtros globais ───────────────────────────────────────────
exibe_filtros = pagina in ("Painel", "Lançamentos", "Relatórios")
if exibe_filtros:
    empresas_df = listar_empresas()
    if not empresas_df.empty:
        opcoes_emp = ["Todas"] + empresas_df["nome"].tolist()
        col_emp, col_per, _ = st.columns([2, 2, 4])
        with col_emp:
            st.selectbox("Empresa", opcoes_emp, key="empresa_selecionada")
        with col_per:
            emp_atual = st.session_state.empresa_selecionada
            if emp_atual == "Todas":
                periodos = listar_periodos()
                st.session_state._empresa_id = None
            else:
                row = empresas_df.loc[empresas_df["nome"] == emp_atual]
                st.session_state._empresa_id = int(row["id"].iloc[0])
                periodos = listar_periodos(st.session_state._empresa_id)
            _selectbox_periodo("Período", periodos, key="periodo_selecionado")
    else:
        empresas_df = pd.DataFrame()
        st.info("Nenhuma empresa cadastrada.")
else:
    empresas_df = pd.DataFrame()

# ──────────────────────────────────────────────────────────────────
# PÁGINAS
# ──────────────────────────────────────────────────────────────────

# ── Painel ─────────────────────────────────────────────────────
if pagina == "Painel":
    if empresas_df.empty:
        st.info("Nenhum lançamento encontrado.")
    else:
        df = carregar_lancamentos(_empresa_id_do_filtro(), _periodo_do_filtro())
        if df.empty:
            st.info("Nenhum lançamento encontrado para os filtros selecionados.")
        else:
            total_creditos = df[df["tipo"] == "C"]["valor"].sum()
            total_debitos = df[df["tipo"] == "D"]["valor"].sum()
            saldo = total_creditos - total_debitos

            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("TOTAL DÉBITOS", _fmt_brl(total_debitos))
            mc2.metric("TOTAL CRÉDITOS", _fmt_brl(total_creditos))
            mc3.metric("SALDO", _fmt_brl(saldo))

            st.divider()

            df_plot = df.copy()
            df_plot["mes"] = pd.to_datetime(df_plot["data"]).dt.to_period("M").astype(str)
            evol = df_plot.groupby(["mes", "tipo"])["valor"].sum().reset_index()

            tokens = st.session_state.theme_tokens
            fig1 = px.bar(
                evol, x="mes", y="valor", color="tipo", barmode="group",
                title="Evolução Mensal — Débitos vs Créditos",
                color_discrete_map={"C": tokens["positive"], "D": tokens["negative"]},
                labels={"mes": "Mês", "valor": "Valor (R$)", "tipo": "Tipo"},
            )
            fig1.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(configurar_grafico_tema(fig1), use_container_width=True)

            top = (
                df_plot.groupby("conta_contabil")["valor"]
                .agg(lambda s: s.abs().sum())
                .sort_values(ascending=False)
                .head(10)
                .reset_index()
            )
            top.columns = ["conta_contabil", "volume"]

            fig2 = px.bar(
                top, x="volume", y="conta_contabil", orientation="h",
                title="Top 10 Contas por Volume Movimentado",
                labels={"volume": "Volume (R$)", "conta_contabil": "Conta Contábil"},
            ).update_traces(marker_color=tokens["accent"])
            fig2.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(configurar_grafico_tema(fig2), use_container_width=True)

# ── Lançamentos ────────────────────────────────────────────────
elif pagina == "Lançamentos":
    if empresas_df.empty:
        st.info("Nenhum lançamento encontrado.")
    else:
        df = carregar_lancamentos(_empresa_id_do_filtro(), _periodo_do_filtro())
        if df.empty:
            st.info("Nenhum lançamento encontrado para os filtros selecionados.")
        else:
            def _cor_tipo(val):
                tokens = st.session_state.theme_tokens
                if val == "C":
                    return f"color: {tokens['positive']}; font-weight: 600"
                if val == "D":
                    return f"color: {tokens['negative']}; font-weight: 600"
                return ""

            df_exibir = _formatar_df_exibicao(df)
            styled = df_exibir.style.map(_cor_tipo, subset=["tipo"])
            st.dataframe(
                styled,
                column_config={
                    "data": "Data",
                    "conta_contabil": "Conta Contábil",
                    "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ ,.2f"),
                    "tipo": st.column_config.TextColumn("Tipo", help="C = Crédito, D = Débito"),
                    "historico": "Histórico",
                    "filial": "Filial",
                    "periodo": "Período",
                },
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.download_button(
                label="Exportar para Excel",
                data=relatorios.exportar_excel(df, "Relatório de Lançamentos"),
                file_name=f"lancamentos_{st.session_state.get('empresa_selecionada', 'todas')}_{st.session_state.get('periodo_selecionado', 'todos')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ── Importar ─────────────────────────────────────────────────────
elif pagina == "Importar":
    pendente = st.session_state.get("import_pendente")
    import_concluido = st.session_state.get("import_concluido")

    if pendente:
        st.warning(
            f"Já existem lançamentos para esta empresa no período "
            f"**{formatar_periodo(pendente['periodo'])}**. Deseja substituir?"
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Substituir período", type="primary"):
                with st.spinner("Substituindo lançamentos..."):
                    resultado = importacao.confirmar_substituicao(
                        pendente["empresa_id"],
                        pendente["periodo"],
                        pendente["df"],
                    )
                if resultado["sucesso"]:
                    st.success(
                        f"{resultado['registros_salvos']} lançamentos importados "
                        f"com sucesso (período substituído)."
                    )
                else:
                    st.error(resultado.get("erro", "Erro ao substituir período."))
                st.session_state.import_pendente = None
                st.rerun()
        with col2:
            if st.button("Cancelar"):
                st.session_state.import_pendente = None
                st.rerun()

    elif import_concluido:
        dados = st.session_state.import_dados

        st.success(
            f"{dados['registros_salvos']} lançamentos importados com sucesso."
        )

        if dados.get("ocorrencias"):
            resumo = auditoria.resumo_auditoria(dados["ocorrencias"])
            if resumo["alta"] > 0:
                st.error(f"{resumo['alta']} ocorrência(s) de alta severidade.")
            if resumo["media"] > 0:
                st.warning(f"{resumo['media']} ocorrência(s) de média severidade.")

            with st.expander("Detalhes da auditoria"):
                st.dataframe(
                    _formatar_df_exibicao(pd.DataFrame(dados["ocorrencias"])),
                    use_container_width=True,
                    hide_index=True,
                )

        if dados.get("conciliacao"):
            conc = dados["conciliacao"]
            with st.expander("Resultado da conciliação"):
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("TOTAL DE PARES", conc["pares_ok"] + conc["sem_par"])
                mc2.metric("PARES OK", conc["pares_ok"])
                mc3.metric("SEM PAR", conc["sem_par"])

                if not conc["df_pares"].empty:
                    st_secao("PARES CONCILIADOS")
                    st.dataframe(_formatar_df_exibicao(conc["df_pares"]), use_container_width=True, hide_index=True)
                if not conc["df_sem_par"].empty:
                    st_secao("LANÇAMENTOS SEM PAR")
                    st.dataframe(_formatar_df_exibicao(conc["df_sem_par"]), use_container_width=True, hide_index=True)

        if st.button("Nova importação"):
            st.session_state.import_concluido = False
            st.rerun()

    else:
        nome_empresa = st.text_input("Nome da empresa", key="imp_nome")
        cnpj_empresa = st.text_input("CNPJ (opcional)", key="imp_cnpj")

        arquivo = st.file_uploader(
            "Arquivo (.xlsx, .csv)", type=["xlsx", "csv"], key="imp_arquivo"
        )

        if st.button("Importar", type="primary", disabled=not (arquivo and nome_empresa)):
            with st.spinner("Processando arquivo..."):
                resultado = importacao.executar_importacao(
                    arquivo,
                    nome_empresa.strip(),
                    (cnpj_empresa or "").strip() or None,
                )

            if resultado.get("requer_confirmacao"):
                st.session_state.import_pendente = {
                    "empresa_id": resultado["empresa_id"],
                    "periodo": resultado["periodo"],
                    "df": resultado["df"],
                }
                st.rerun()

            elif resultado.get("sucesso"):
                df = resultado["df"]
                empresa_id = resultado["empresa_id"]
                periodo = resultado["periodo"]

                ocorrencias = auditoria.auditar_lancamentos(df)
                if ocorrencias:
                    auditoria.salvar_ocorrencias(ocorrencias, empresa_id)

                conc_result = conciliacao.conciliar_partidas(df)
                conciliacao.salvar_resultado_conciliacao(empresa_id, periodo, conc_result)

                st.session_state.import_dados = {
                    "registros_salvos": resultado["registros_salvos"],
                    "ocorrencias": ocorrencias,
                    "conciliacao": conc_result,
                }
                st.session_state.import_concluido = True
                st.rerun()

            else:
                st.error(resultado.get("erro", "Erro desconhecido."))

# ── Conciliação ──────────────────────────────────────────────────
elif pagina == "Conciliação":
    empresas_df = listar_empresas()
    if empresas_df.empty:
        st.info("Nenhuma empresa cadastrada. Importe lançamentos primeiro.")
    else:
        opcoes_emp = {str(row["nome"]): row["id"] for _, row in empresas_df.iterrows()}
        emp_selecionada = st.selectbox("Empresa", list(opcoes_emp.keys()), key="con_emp")
        empresa_id = opcoes_emp[emp_selecionada]

        periodos = listar_periodos(empresa_id)
        if not periodos:
            st.info("Nenhum período encontrado para esta empresa.")
        else:
            _selectbox_periodo("Período", periodos, key="con_per")
            periodo = st.session_state.get("con_per")

            df_lanc = carregar_lancamentos(empresa_id, periodo)
            if df_lanc.empty:
                st.info("Nenhum lançamento encontrado para este período.")
            else:
                resultado = conciliacao.conciliar_partidas(df_lanc)

                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("TOTAL DE PARES", resultado["pares_ok"] + resultado["sem_par"])
                mc2.metric("PARES OK", resultado["pares_ok"])
                mc3.metric("SEM PAR", resultado["sem_par"])

                st.divider()

                if not resultado["df_pares"].empty:
                    st_secao("PARES CONCILIADOS")
                    st.dataframe(_formatar_df_exibicao(resultado["df_pares"]), use_container_width=True, hide_index=True)
                if not resultado["df_sem_par"].empty:
                    st_secao("LANÇAMENTOS SEM PAR")
                    st.dataframe(_formatar_df_exibicao(resultado["df_sem_par"]), use_container_width=True, hide_index=True)

                st.divider()
                df_relatorio = conciliacao.gerar_relatorio_conciliacao(resultado)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="Exportar para Excel",
                        data=relatorios.exportar_excel(df_relatorio, "Relatório de Conciliação"),
                        file_name=f"conciliacao_{emp_selecionada}_{periodo}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                with col2:
                    st.download_button(
                        label="Exportar para PDF",
                        data=relatorios.exportar_pdf(
                            {"df_relatorio": df_relatorio}, "conciliacao", emp_selecionada, periodo
                        ),
                        file_name=f"conciliacao_{emp_selecionada}_{periodo}.pdf",
                        mime="application/pdf",
                    )

# ── Auditoria ────────────────────────────────────────────────────
elif pagina == "Auditoria":
    empresas_df = listar_empresas()
    if empresas_df.empty:
        st.info("Nenhuma empresa cadastrada. Importe lançamentos primeiro.")
    else:
        opcoes_emp = {str(row["nome"]): row["id"] for _, row in empresas_df.iterrows()}
        emp_selecionada = st.selectbox("Empresa", list(opcoes_emp.keys()), key="aud_emp")
        empresa_id = opcoes_emp[emp_selecionada]

        periodos = listar_periodos(empresa_id)
        if not periodos:
            st.info("Nenhum período encontrado para esta empresa.")
        else:
            _selectbox_periodo("Período", periodos, key="aud_per")
            periodo = st.session_state.get("aud_per")

            df_oc = carregar_ocorrencias(empresa_id, periodo)
            if df_oc.empty:
                st.info("Nenhuma ocorrência de auditoria para este período.")
            else:
                alta = len(df_oc[df_oc["severidade"] == "alta"])
                media = len(df_oc[df_oc["severidade"] == "media"])
                baixa = len(df_oc[df_oc["severidade"] == "baixa"])

                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("ALTA", alta)
                mc2.metric("MÉDIA", media)
                mc3.metric("BAIXA", baixa)

                st.divider()

                cols_exibir = ["tipo_ocorrencia", "descricao", "severidade", "resolvida"]
                cols_exibir = [c for c in cols_exibir if c in df_oc.columns]
                df_exibir = df_oc[cols_exibir].copy()

                edited = st.data_editor(
                    df_exibir,
                    column_config={
                        "resolvida": st.column_config.CheckboxColumn("Resolvida"),
                    },
                    disabled=[c for c in cols_exibir if c != "resolvida"],
                    hide_index=True,
                    use_container_width=True,
                    key="aud_editor",
                )

                if st.button("Salvar alterações"):
                    alteradas = edited[edited["resolvida"] != df_exibir["resolvida"]]
                    for idx in alteradas.index:
                        oc_id = df_oc.iloc[idx]["id"]
                        atualizar_ocorrencia_resolvida(int(oc_id), bool(edited.loc[idx, "resolvida"]))
                    if not alteradas.empty:
                        st.success(f"{len(alteradas)} ocorrência(s) atualizada(s).")
                        st.rerun()
                    else:
                        st.info("Nenhuma alteração detectada.")

                st.divider()
                st.download_button(
                    label="Exportar para Excel",
                    data=relatorios.exportar_excel(df_oc, "Relatório de Auditoria"),
                    file_name=f"auditoria_{emp_selecionada}_{periodo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

# ── Relatórios ───────────────────────────────────────────────────
elif pagina == "Relatórios":
    st.info("Selecione uma empresa e período para gerar os relatórios.")

    empresa_id = _empresa_id_do_filtro()
    periodo = _periodo_do_filtro()
    empresa_nome = st.session_state.get("empresa_selecionada", "Todas")

    if empresa_id and periodo:
        st.divider()
        st_secao("RELATÓRIO DE LANÇAMENTOS")
        st.markdown("Exporta todos os lançamentos do período selecionado em formato Excel.")
        df_lanc = carregar_lancamentos(empresa_id, periodo)
        if not df_lanc.empty:
            st.download_button(
                label="Gerar Excel de Lançamentos",
                data=relatorios.exportar_excel(df_lanc, "Relatório de Lançamentos"),
                file_name=f"lancamentos_{empresa_nome}_{periodo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.warning("Nenhum lançamento encontrado para este período.")

        st.divider()
        st_secao("RELATÓRIO DE CONCILIAÇÃO")
        st.markdown("Gera um relatório detalhado com pares conciliados e lançamentos sem par.")
        resultado_conc = conciliacao.conciliar_partidas(df_lanc)
        df_relatorio_conc = conciliacao.gerar_relatorio_conciliacao(resultado_conc)
        if not df_relatorio_conc.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Gerar Excel de Conciliação",
                    data=relatorios.exportar_excel(df_relatorio_conc, "Relatório de Conciliação"),
                    file_name=f"conciliacao_{empresa_nome}_{periodo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with col2:
                st.download_button(
                    label="Gerar PDF de Conciliação",
                    data=relatorios.exportar_pdf(
                        {"df_relatorio": df_relatorio_conc}, "conciliacao", empresa_nome, periodo
                    ),
                    file_name=f"conciliacao_{empresa_nome}_{periodo}.pdf",
                    mime="application/pdf",
                )

        st.divider()
        st_secao("RELATÓRIO DE AUDITORIA")
        st.markdown("Exporta todas as ocorrências de auditoria encontradas para o período.")
        df_oc = carregar_ocorrencias(empresa_id, periodo)
        if not df_oc.empty:
            st.download_button(
                label="Gerar Excel de Auditoria",
                data=relatorios.exportar_excel(df_oc, "Relatório de Auditoria"),
                file_name=f"auditoria_{empresa_nome}_{periodo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Nenhuma ocorrência de auditoria para este período.")

# ── Assistente ───────────────────────────────────────────────────
elif pagina == "Assistente":
    if "conversa_ativa" not in st.session_state:
        conv_id = criar_conversa()
        st.session_state.conversa_ativa = conv_id
        st.rerun()

    conversa_id = st.session_state.conversa_ativa

    mensagens = carregar_mensagens(conversa_id)

    for msg in mensagens:
        with st.chat_message(msg["role"]):
            st.markdown(msg["conteudo"])

    pergunta = st.chat_input("Digite sua mensagem...")
    if pergunta:
        salvar_mensagem(conversa_id, "user", pergunta)

        primeira_mensagem = len(mensagens) == 0
        if primeira_mensagem:
            titulo = assistente.gerar_titulo_conversa(pergunta)
            renomear_conversa(conversa_id, titulo)

        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                historico = [{"role": m["role"], "content": m["conteudo"]} for m in mensagens]
                historico.append({"role": "user", "content": pergunta})
                resposta = assistente.perguntar_ao_assistente(historico)
            st.markdown(resposta)

        salvar_mensagem(conversa_id, "assistant", resposta)
        st.rerun()

# ── Fallback ─────────────────────────────────────────────────────
else:
    st.info("Módulo em construção.")
