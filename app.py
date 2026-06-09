"""
app.py
======
Interface principal do Dashboard de Ingestão Multifonte & Persistência.
Combina inserção manual, upload de arquivos e visualização de KPIs financeiros.
"""

import logging
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    carregar_todos_os_gastos,
    inicializar_banco,
    salvar_dataframe,
    salvar_registro,
)
from parsers import processar_arquivo

# ---------------------------------------------------------------------------
# Configuração global
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CATEGORIAS: list[str] = ["Infraestrutura", "Marketing", "Logística", "Operações"]

st.set_page_config(
    page_title="Dashboard Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Inicialização do estado da sessão
# ---------------------------------------------------------------------------
def _init_session() -> None:
    """
    Garante que o banco exista e carrega os dados históricos do SQLite
    no estado da sessão. Executado uma única vez por sessão.
    """
    inicializar_banco()
    if "db_financeiro" not in st.session_state:
        st.session_state.db_financeiro = carregar_todos_os_gastos()


def _recarregar_dados() -> None:
    """Força a releitura completa dos dados do SQLite para a sessão."""
    st.session_state.db_financeiro = carregar_todos_os_gastos()


# ---------------------------------------------------------------------------
# Sidebar — Inserção Manual
# ---------------------------------------------------------------------------
def _render_sidebar() -> None:
    """
    Renderiza o formulário lateral de inserção manual.
    Persiste no SQLite e atualiza o estado da sessão ao submeter.
    """
    st.sidebar.header("✏️ Inserção Manual")

    with st.sidebar.form(key="form_manual", clear_on_submit=True):
        data_input: date = st.date_input(
            "Data da despesa",
            value=date.today(),
            format="DD/MM/YYYY",
        )
        categoria_input: str = st.selectbox(
            "Categoria",
            options=CATEGORIAS,
        )
        valor_input: float = st.number_input(
            "Valor (R$)",
            min_value=0.01,
            step=0.01,
            format="%.2f",
        )
        submitted = st.form_submit_button("💾 Salvar registro", use_container_width=True)

    if submitted:
        try:
            salvar_registro(
                data=data_input,
                categoria=categoria_input,
                valor=valor_input,
                origem="manual",
            )
            _recarregar_dados()
            st.sidebar.success(
                f"✅ Registro salvo: **{categoria_input}** — R$ {valor_input:,.2f} em {data_input.strftime('%d/%m/%Y')}"
            )
        except Exception as exc:
            logger.error("Erro ao salvar registro manual: %s", exc)
            st.sidebar.error(f"❌ Falha ao salvar: {exc}")

    st.sidebar.divider()
    st.sidebar.caption(f"📦 {len(st.session_state.db_financeiro)} registros no banco.")


# ---------------------------------------------------------------------------
# Área central — Upload Multifonte
# ---------------------------------------------------------------------------
def _render_upload() -> None:
    """
    Renderiza a área de upload de arquivos.
    Chama o parser adequado por extensão, salva no SQLite e recarrega.
    """
    st.subheader("📂 Upload Multifonte")
    st.caption("Formatos aceitos: **XLSX**, **CSV**, **PDF**, **PPTX**")

    arquivos = st.file_uploader(
        label="Selecione um ou mais arquivos",
        type=["xlsx", "csv", "pdf", "pptx"],
        accept_multiple_files=True,
        help="Cada arquivo será processado pelo parser correspondente à extensão.",
    )

    if not arquivos:
        return

    for arquivo in arquivos:
        with st.expander(f"📄 {arquivo.name}", expanded=True):
            try:
                df_extraido, origem = processar_arquivo(arquivo)

                if df_extraido.empty:
                    st.warning(
                        f"⚠️ Nenhum dado estruturado encontrado em **{arquivo.name}**. "
                        "Verifique se o arquivo contém as colunas: data, categoria, valor."
                    )
                    continue

                # Preview dos dados extraídos
                st.write(f"**{len(df_extraido)} registros detectados — pré-visualização:**")
                st.dataframe(
                    df_extraido.head(10),
                    use_container_width=True,
                    hide_index=True,
                )

                col_confirm, col_cancel = st.columns([1, 3])
                confirmar = col_confirm.button(
                    "✅ Importar dados",
                    key=f"confirm_{arquivo.name}",
                    type="primary",
                )

                if confirmar:
                    salvos = salvar_dataframe(df_extraido, origem=origem)
                    _recarregar_dados()
                    st.success(
                        f"✅ **{salvos}/{len(df_extraido)}** registros importados de *{arquivo.name}*."
                    )

            except ValueError as exc:
                # Extensão não suportada
                st.error(
                    f"❌ **Formato não suportado:** {exc}\n\n"
                    "Use apenas: `.xlsx`, `.csv`, `.pdf`, `.pptx`."
                )
            except Exception as exc:
                logger.error("Erro inesperado ao processar '%s': %s", arquivo.name, exc)
                st.error(
                    f"❌ **Erro ao processar `{arquivo.name}`:**\n\n"
                    f"```\n{type(exc).__name__}: {exc}\n```\n\n"
                    "Verifique os logs para mais detalhes."
                )


# ---------------------------------------------------------------------------
# Área central — KPIs e visualizações
# ---------------------------------------------------------------------------
def _render_metricas(df: pd.DataFrame) -> None:
    """
    Renderiza as métricas financeiras globais e os gráficos por categoria.

    Args:
        df: DataFrame com todos os registros históricos.
    """
    if df.empty:
        st.info("📭 Nenhum dado registrado ainda. Use a inserção manual ou o upload de arquivos.")
        return

    st.subheader("📊 Visão Geral Financeira")

    # --- KPIs globais ---
    total_gasto = df["valor"].sum()
    maior_gasto = df["valor"].max()
    media_gasto = df["valor"].mean()
    total_registros = len(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Total Gasto", f"R$ {total_gasto:,.2f}")
    col2.metric("📈 Maior Despesa", f"R$ {maior_gasto:,.2f}")
    col3.metric("📉 Média por Registro", f"R$ {media_gasto:,.2f}")
    col4.metric("🗂️ Total de Registros", total_registros)

    st.divider()

    # --- Totalizadores por categoria ---
    st.subheader("📂 Totais por Categoria")
    df_cat = (
        df.groupby("categoria", as_index=False)["valor"]
        .sum()
        .sort_values("valor", ascending=False)
    )

    # Métricas em linha
    cols = st.columns(len(df_cat))
    for col, (_, row) in zip(cols, df_cat.iterrows()):
        col.metric(row["categoria"], f"R$ {row['valor']:,.2f}")

    # Gráfico de barras por categoria
    fig_bar = px.bar(
        df_cat,
        x="categoria",
        y="valor",
        color="categoria",
        text_auto=".2f",
        title="Distribuição de Gastos por Categoria",
        labels={"valor": "Valor (R$)", "categoria": "Categoria"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_bar.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # --- Evolução temporal ---
    st.subheader("📅 Evolução Temporal")
    df_tempo = df.copy()
    df_tempo["data"] = pd.to_datetime(df_tempo["data"], errors="coerce")
    df_tempo = df_tempo.dropna(subset=["data"])

    if not df_tempo.empty:
        df_mes = (
            df_tempo.groupby([pd.Grouper(key="data", freq="ME"), "categoria"], as_index=False)["valor"]
            .sum()
        )
        df_mes["data"] = df_mes["data"].dt.strftime("%Y-%m")
        fig_line = px.line(
            df_mes,
            x="data",
            y="valor",
            color="categoria",
            markers=True,
            title="Gastos Mensais por Categoria",
            labels={"valor": "Valor (R$)", "data": "Mês"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_line, use_container_width=True)


# ---------------------------------------------------------------------------
# Área central — Tabela de dados brutos
# ---------------------------------------------------------------------------
def _render_tabela(df: pd.DataFrame) -> None:
    """
    Exibe a tabela completa de registros com filtro por categoria.

    Args:
        df: DataFrame com todos os registros históricos.
    """
    if df.empty:
        return

    st.subheader("🗃️ Dados Brutos")

    categorias_disponiveis = ["Todas"] + sorted(df["categoria"].unique().tolist())
    filtro_cat = st.selectbox("Filtrar por categoria:", categorias_disponiveis)

    df_filtrado = df if filtro_cat == "Todas" else df[df["categoria"] == filtro_cat]

    st.dataframe(
        df_filtrado.rename(columns={
            "id": "ID",
            "data": "Data",
            "categoria": "Categoria",
            "valor": "Valor (R$)",
            "origem": "Origem",
            "criado_em": "Registrado em",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
    )
    st.caption(f"Exibindo {len(df_filtrado)} de {len(df)} registros.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Ponto de entrada principal do aplicativo Streamlit."""
    _init_session()

    st.title("💰 Dashboard de Ingestão Multifonte & Persistência")
    st.caption("Dados financeiros unificados · Persistência em SQLite · Deploy Hugging Face Spaces")

    _render_sidebar()

    tab_upload, tab_dados, tab_analise = st.tabs(["📂 Upload", "🗃️ Dados", "📊 Análise"])

    with tab_upload:
        _render_upload()

    df_atual = st.session_state.db_financeiro

    with tab_dados:
        _render_tabela(df_atual)

    with tab_analise:
        _render_metricas(df_atual)


if __name__ == "__main__":
    main()
