"""
app.py
======
Interface principal do Dashboard de Ingestão Multifonte & Persistência.
Combina inserção manual, upload de arquivos e visualização de KPIs financeiros.
"""

import logging
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from database import (
    carregar_todos_os_gastos,
    inicializar_banco,
    salvar_dataframe_otimizado,  # Atualizado para a versão em lote refatorada
    salvar_registro,
)
from parsers import processar_arquivo, extrair_dados_comprovante_imagem

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
    Garante que o banco exista e carrega os dados históricos
    no estado da sessão. Executado uma única vez por sessão.
    """
    try:
        inicializar_banco()
    except Exception as exc:
        st.error("🚨 **Erro de Conexão com o Banco de Dados!**")
        st.markdown(
            "O aplicativo não conseguiu se conectar ao PostgreSQL (Supabase). "
            "Isso geralmente acontece se o banco de dados estiver pausado ou se a variável `DATABASE_URL` não estiver configurada corretamente nas Secrets do Streamlit."
        )
        st.stop()

    if "db_financeiro" not in st.session_state:
        st.session_state.db_financeiro = carregar_todos_os_gastos()


def _atualizar_dados_sessao() -> None:
    """Sincroniza o estado da sessão com os dados mais recentes do banco."""
    st.session_state.db_financeiro = carregar_todos_os_gastos()


# ---------------------------------------------------------------------------
# Componente: Sidebar (Inserção Manual)
# ---------------------------------------------------------------------------
def _render_sidebar() -> None:
    """Renderiza o formulário de inserção manual de registros na barra lateral."""
    with st.sidebar:
        st.header("📝 Lançamento Manual")
        st.markdown("Insira despesas avulsas diretamente na base de dados.")
        
        st.divider()
        st.subheader("🎨 Tema Visual")
        tema = st.radio("Escolha o tema:", ["🌙 Escuro", "☀️ Claro"], horizontal=True)
        if tema == "☀️ Claro":
            st.markdown("""
                <style>
                [data-testid="stAppViewContainer"] { background-color: #FFFFFF; color: #000000; }
                [data-testid="stSidebar"] { background-color: #F0F2F6; }
                </style>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <style>
                [data-testid="stAppViewContainer"] { background-color: #0E1117; color: #FAFAFA; }
                [data-testid="stSidebar"] { background-color: #262730; }
                </style>
            """, unsafe_allow_html=True)
        
        st.divider()

        with st.form("form_registro_manual", clear_on_submit=True):
            campo_data = st.date_input("Data do Gasto", value=date.today())
            campo_categoria = st.selectbox("Categoria", options=CATEGORIAS)
            campo_valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")

            botao_submeter = st.form_submit_button("Gravar Registro")

            if botao_submeter:
                if campo_valor <= 0:
                    st.error("O valor do gasto deve ser maior que R$ 0,00.")
                    return

                sucesso = salvar_registro(
                    data_val=campo_data,
                    categoria=campo_categoria,
                    valor_val=campo_valor,
                    origem="manual",
                )

                if sucesso:
                    st.success("Registro manual salvo com sucesso!")
                    _atualizar_dados_sessao()
                else:
                    st.error("Erro crítico ao tentar persistir o registro no banco.")


# ---------------------------------------------------------------------------
# Aba 1: Ingestão e Upload de Arquivos
# ---------------------------------------------------------------------------
def _render_upload() -> None:
    """Renderiza a área de arrastar arquivos e gerencia o pipeline de parsing/bulk insert."""
    st.header("📂 Upload Multifonte")
    st.markdown(
        "Suporta arquivos desestruturados ou tabulares: **Excel (.xlsx), CSV, PDF e PowerPoint (.pptx)**. "
        "O sistema irá aplicar as estratégias em cascata automaticamente."
    )

    arquivos_enviados = st.file_uploader(
        "Selecione um ou mais arquivos para processamento",
        type=["xlsx", "xls", "csv", "pdf", "pptx"],
        accept_multiple_files=True,
    )

    if not arquivos_enviados:
        st.info("Aguardando upload de arquivos para iniciar o motor de parsing.")
        return

    st.subheader("⚙️ Status do Processamento em Lote")

    for arquivo in arquivos_enviados:
        with st.expander(f"📄 Arquivo: {arquivo.name}", expanded=True):
            try:
                # 1. Aciona o dispatcher estratégico em parsers.py
                df_processado, tipo_origem = processar_arquivo(arquivo)

                if df_processado.empty:
                    st.warning("O arquivo foi lido, mas nenhuma linha válida foi estruturada pelo motor.")
                    continue

                st.markdown(f"**Estratégia aplicada:** Ingestor nativo para `{tipo_origem.upper()}`")
                st.dataframe(df_processado.head(5), use_container_width=True)

                # Colunas para ações de confirmação
                col_info, col_acao = st.columns([3, 1])
                col_info.caption(f"Total de linhas identificadas para ingestão: {len(df_processado)}")

                # Botão único por arquivo para disparar o Bulk Insert seguro
                if col_acao.button("Confirmar Carga no Banco", key=f"btn_{arquivo.name}"):
                    with st.spinner("Persistindo lote de dados de forma atômica..."):
                        # Chamada da nova função vetorizada e otimizada
                        linhas_salvas = salvar_dataframe_otimizado(df_processado, origem=tipo_origem)

                    if linhas_salvas > 0:
                        st.success(f"Sucesso! {linhas_salvas} registros foram gravados em lote.")
                        _atualizar_dados_sessao()
                    else:
                        st.error("A carga falhou. Verifique se o formato dos campos está correto nos logs.")

            except Exception as exc:
                logger.error(f"Falha de processamento no arquivo {arquivo.name}: {exc}", exc_info=True)
                st.error(f"Erro ao processar arquivo: {type(exc).__name__} - {str(exc)}")


# ---------------------------------------------------------------------------
# Aba 1.5: Comprovante por Foto (OCR)
# ---------------------------------------------------------------------------
def _render_comprovante_foto() -> None:
    """Renderiza a interface para upload ou captura de foto de comprovante usando OCR."""
    st.header("📷 Leitura de Comprovante (IA)")
    st.markdown("Envie ou tire uma foto do seu comprovante fiscal para extração automática de dados contábeis.")

    opcao = st.radio("Como deseja enviar o comprovante?", ["Fazer Upload de Arquivo", "Tirar Foto na Hora"], horizontal=True)
    imagem_bytes = None

    if opcao == "Fazer Upload de Arquivo":
        arquivo = st.file_uploader("Selecione a imagem do comprovante", type=["png", "jpg", "jpeg"])
        if arquivo:
            imagem_bytes = arquivo.read()
            st.image(imagem_bytes, caption="Pré-visualização do Comprovante", width=350)
    else:
        foto = st.camera_input("Tire uma foto do comprovante usando a câmera")
        if foto:
            imagem_bytes = foto.read()

    if imagem_bytes:
        if st.button("Escanear Comprovante com IA", type="primary"):
            with st.spinner("Processando imagem via OCR (pode levar alguns segundos)..."):
                resultado = extrair_dados_comprovante_imagem(imagem_bytes)
            
            if resultado:
                st.success("Leitura concluída! Revise os dados abaixo antes de salvar.")
                
                with st.form("form_comprovante_ocr", clear_on_submit=True):
                    try:
                        data_padrao = datetime.strptime(resultado.get("data", ""), "%Y-%m-%d").date() if resultado.get("data") else date.today()
                    except ValueError:
                        try:
                            data_padrao = datetime.strptime(resultado.get("data", ""), "%d/%m/%Y").date() if resultado.get("data") else date.today()
                        except ValueError:
                            data_padrao = date.today()

                    campo_data = st.date_input("Data do Gasto", value=data_padrao)
                    
                    valor_ext = resultado.get("valor") or 0.0
                    campo_valor = st.number_input("Valor Total (R$)", min_value=0.0, value=float(valor_ext), step=10.0, format="%.2f")
                    
                    hora_ext = resultado.get("hora") or ""
                    if hora_ext:
                        st.info(f"Hora identificada no comprovante: {hora_ext}")

                    st.text_area("Texto Bruto Extraído (Referência OCR)", value=resultado.get("texto_extraido", ""), disabled=True, height=100)
                    
                    if st.form_submit_button("Confirmar e Salvar no Banco"):
                        if campo_valor <= 0:
                            st.error("O valor do gasto deve ser maior que R$ 0,00.")
                        else:
                            sucesso = salvar_registro(
                                data_val=campo_data,
                                categoria="Comprovante (OCR Foto)",
                                valor_val=campo_valor,
                                origem="ocr_camera"
                            )
                            if sucesso:
                                st.success("Comprovante salvo com sucesso!")
                                _atualizar_dados_sessao()
                            else:
                                st.error("Erro crítico ao gravar no banco de dados.")
            else:
                st.warning("A IA não conseguiu identificar os dados financeiros. Tente uma foto mais nítida.")


# ---------------------------------------------------------------------------
# Aba 2: Exibição de Dados (Tabelas)
# ---------------------------------------------------------------------------
def _render_dados(df: pd.DataFrame) -> None:
    """Exibe os dados históricos do banco com filtros interativos em tempo real."""
    st.header("🗃️ Registro Histórico Unificado")

    if df.empty:
        st.info("Nenhum dado encontrado no banco de dados. Use a barra lateral ou faça um upload.")
        return

    # Filtro dinâmico por categoria na interface
    categorias_disponiveis = ["Todas"] + sorted(df["categoria"].unique().tolist())
    filtro_cat = st.selectbox("Filtrar visualização por Categoria:", categorias_disponiveis)

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
    st.caption(f"Exibindo {len(df_filtrado)} de {len(df)} registros encontrados no SQLite.")


# ---------------------------------------------------------------------------
# Aba 3: Inteligência de Negócio (Gráficos e KPIs)
# ---------------------------------------------------------------------------
def _render_analise(df: pd.DataFrame) -> None:
    """Gera blocos de métricas e gráficos analíticos interativos usando Plotly."""
    st.header("📊 Métricas Consolidadas")

    if df.empty:
        st.info("Insira dados para habilitar os painéis de inteligência gráfica.")
        return

    # 1. Cálculo de cartões de KPI básicos
    total_gasto = df["valor"].sum()
    total_registros = len(df)
    media_gasto = df["valor"].mean()
    maior_gasto = df["valor"].max()

    kpi_tot, kpi_qtd, kpi_med, kpi_max = st.columns(4)
    kpi_tot.metric("Gasto Acumulado Total", f"R$ {total_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    kpi_qtd.metric("Volume de Registros", f"{total_registros} itens")
    kpi_med.metric("Ticket Médio por Linha", f"R$ {media_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    kpi_max.metric("Maior Despesa Isolada", f"R$ {maior_gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.markdown("---")

    # 2. Geração de Gráficos de Distribuição
    graf_col1, graf_col2 = st.columns(2)

    with graf_col1:
        st.subheader("Despesas por Categoria")
        df_cat = df.groupby("categoria", as_index=False)["valor"].sum()
        fig_pizza = px.pie(
            df_cat,
            names="categoria",
            values="valor",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_pizza.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pizza, use_container_width=True)

    with graf_col2:
        st.subheader("Evolução Cronológica dos Gastos")
        # Agrupa por data para montar o gráfico de linha de tendência temporal
        df_tempo = df.groupby("data", as_index=False)["valor"].sum().sort_values("data")
        fig_linha = px.line(
            df_tempo,
            x="data",
            y="valor",
            labels={"data": "Linha do Tempo", "valor": "Montante Diário (R$)"},
            markers=True,
            color_discrete_sequence=["#2E7D32"],
        )
        st.plotly_chart(fig_linha, use_container_width=True)


# ---------------------------------------------------------------------------
# Entry point da aplicação
# ---------------------------------------------------------------------------
def main() -> None:
    """Ponto de entrada principal da arquitetura do aplicativo Streamlit."""
    _init_session()

    st.title("💰 Dashboard de Ingestão Multifonte & Persistência")
    st.caption("Pipeline de Dados Unificado · Persistência Segura SQLite · Otimização em Lote")

    # Renderiza o painel de gravação manual à esquerda
    _render_sidebar()

    # Cria as abas de navegação da interface de usuário
    tab_upload, tab_foto, tab_dados, tab_analise = st.tabs([
        "📂 Upload em Lote", 
        "📷 Comprovante (Foto)", 
        "🗃️ Dados Cadastrados", 
        "📊 Análise de Performance"
    ])

    # Captura o estado atualizado da memória para distribuir nas views
    df_atual = st.session_state.db_financeiro

    with tab_upload:
        _render_upload()

    with tab_foto:
        _render_comprovante_foto()

    with tab_dados:
        _render_dados(df_atual)

    with tab_analise:
        _render_analise(df_atual)


if __name__ == "__main__":
    main()
