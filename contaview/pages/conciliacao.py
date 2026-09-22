import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.components.filtros import filtros
from contaview.components.kpi_card import kpi_card
from contaview.state.tema_state import TemaState
from contaview.state.dados_state import DadosState
from contaview.utils.auth import pagina_protegida
from contaview.styles import MINERAL, ECLIPSE


def _tabela_pares() -> rx.Component:
    return rx.cond(
        DadosState.conciliacao_pares,
        rx.data_table(
            data=DadosState.conciliacao_df_pares,
            columns=DadosState.conciliacao_colunas,
            pagination=True,
            sort=True,
        ),
        rx.text(
            "Nenhum par conciliado encontrado.",
            font_size="13px",
            color=rx.cond(
                TemaState.tema_escuro,
                ECLIPSE["text_secondary"],
                MINERAL["text_secondary"],
            ),
        ),
    )


def _tabela_sem_par() -> rx.Component:
    return rx.cond(
        DadosState.conciliacao_qtd_sem_par,
        rx.vstack(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.foreach(
                            DadosState.conciliacao_colunas_sem_par,
                            lambda col: rx.table.column_header_cell(col),
                        ),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        DadosState.conciliacao_df_sem_par,
                        lambda linha: rx.table.row(
                            rx.foreach(
                                linha,
                                lambda cel: rx.table.cell(cel),
                            ),
                            style={
                                "background": "rgba(201, 75, 60, 0.08)",
                            },
                        ),
                    ),
                ),
                width="100%",
            ),
        ),
        rx.text(
            "Nenhum lançamento sem par encontrado.",
            font_size="13px",
            color=rx.cond(
                TemaState.tema_escuro,
                ECLIPSE["text_secondary"],
                MINERAL["text_secondary"],
            ),
        ),
    )


def _acoes_exportacao() -> rx.Component:
    return rx.hstack(
        rx.button(
            "Exportar relatório (Excel)",
            variant="outline",
            on_click=DadosState.exportar_excel_conciliacao,
        ),
        rx.button(
            "Exportar PDF",
            variant="outline",
            on_click=DadosState.exportar_pdf_conciliacao,
        ),
        spacing="3",
        margin_top="16px",
    )


def _cruzamento_fontes() -> rx.Component:
    return rx.vstack(
        rx.text("Cruzar arquivos preparados", font_size="18px", font_weight="600"),
        rx.text(
            "Selecione duas fontes da mesma empresa. Apenas pares únicos com "
            "data, valor e descrição iguais são confirmados automaticamente.",
            font_size="13px",
        ),
        rx.hstack(
            rx.select(
                DadosState.lotes_conciliacao_opcoes,
                placeholder="Primeira fonte",
                value=DadosState.lote_conciliacao_extrato,
                on_change=DadosState.set_lote_conciliacao_extrato,
                width="100%",
            ),
            rx.select(
                DadosState.lotes_conciliacao_opcoes,
                placeholder="Segunda fonte",
                value=DadosState.lote_conciliacao_referencia,
                on_change=DadosState.set_lote_conciliacao_referencia,
                width="100%",
            ),
            width="100%",
            spacing="3",
        ),
        rx.hstack(
            rx.button(
                "Executar cruzamento", on_click=DadosState.executar_conciliacao_fontes
            ),
            rx.button(
                "Exportar cruzamento CSV", variant="outline",
                on_click=DadosState.exportar_conciliacao_fontes,
            ),
        ),
        rx.cond(
            DadosState.conciliacao_cruzada_mensagem != "",
            rx.callout(DadosState.conciliacao_cruzada_mensagem, width="100%"),
        ),
        rx.cond(
            DadosState.conciliacao_cruzada_pares,
            rx.vstack(
                rx.text("Pares exatos", font_weight="600"),
                rx.foreach(
                    DadosState.conciliacao_cruzada_pares,
                    lambda par: rx.hstack(
                        rx.text("Linha da fonte 1:"),
                        rx.text(par["linha_extrato"]),
                        rx.text("Linha da fonte 2:"),
                        rx.text(par["linha_referencia"]),
                        rx.text(par["valor"]),
                    ),
                ),
                width="100%",
            ),
        ),
        rx.cond(
            DadosState.conciliacao_cruzada_candidatos,
            rx.vstack(
                rx.text("Candidatos para revisão", font_weight="600"),
                rx.foreach(
                    DadosState.conciliacao_cruzada_candidatos,
                    lambda par: rx.hstack(
                        rx.text(par["linha_extrato"]),
                        rx.text("↔"),
                        rx.text(par["linha_referencia"]),
                        rx.text(par["valor_extrato"]),
                        rx.text("Diferença de dias:"),
                        rx.text(par["dias_diferenca"]),
                    ),
                ),
                width="100%",
            ),
        ),
        rx.cond(
            DadosState.conciliacao_cruzada_divergencias,
            rx.vstack(
                rx.text("Diferenças de valor", font_weight="600"),
                rx.foreach(
                    DadosState.conciliacao_cruzada_divergencias,
                    lambda par: rx.hstack(
                        rx.text(par["linha_extrato"]),
                        rx.text("↔"),
                        rx.text(par["linha_referencia"]),
                        rx.text(par["valor_extrato"]),
                        rx.text("/"),
                        rx.text(par["valor_referencia"]),
                    ),
                ),
                width="100%",
            ),
        ),
        rx.cond(
            DadosState.conciliacao_cruzada_faltantes_extrato,
            rx.vstack(
                rx.text("Sem correspondência na fonte 2", font_weight="600"),
                rx.foreach(
                    DadosState.conciliacao_cruzada_faltantes_extrato,
                    lambda linha: rx.hstack(
                        rx.text("Linha"), rx.text(linha["numero_linha"]),
                        rx.text(linha["data"]), rx.text(linha["descricao"]),
                        rx.text(linha["valor"]),
                    ),
                ),
                width="100%",
            ),
        ),
        rx.cond(
            DadosState.conciliacao_cruzada_faltantes_referencia,
            rx.vstack(
                rx.text("Sem correspondência na fonte 1", font_weight="600"),
                rx.foreach(
                    DadosState.conciliacao_cruzada_faltantes_referencia,
                    lambda linha: rx.hstack(
                        rx.text("Linha"), rx.text(linha["numero_linha"]),
                        rx.text(linha["data"]), rx.text(linha["descricao"]),
                        rx.text(linha["valor"]),
                    ),
                ),
                width="100%",
            ),
        ),
        width="100%",
        spacing="3",
        padding="16px",
        border="1px solid",
        border_color=rx.cond(
            TemaState.tema_escuro, ECLIPSE["border"], MINERAL["border"]
        ),
        border_radius="10px",
    )


def conciliacao() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.text(
                    "Conciliação",
                    font_size="22px",
                    font_weight="600",
                    color=rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["text_primary"],
                        MINERAL["text_primary"],
                    ),
                ),
                filtros(),
                _cruzamento_fontes(),
                rx.text("Conferência de partidas C/D", font_size="18px", font_weight="600"),
                rx.cond(
                    DadosState.carregando,
                    rx.spinner(),
                    rx.vstack(
                        rx.grid(
                            kpi_card(
                                "Total de pares",
                                DadosState.conciliacao_total_pares,
                                "neutro",
                            ),
                            kpi_card(
                                "Pares OK",
                                DadosState.conciliacao_pares_ok,
                                "positivo",
                            ),
                            kpi_card(
                                "Sem par",
                                DadosState.conciliacao_qtd_sem_par,
                                "negativo",
                            ),
                            columns="3",
                            spacing="4",
                            width="100%",
                        ),
                        rx.text(
                            "PARES CONCILIADOS",
                            size="1",
                            weight="bold",
                            letter_spacing="0.06em",
                            color=rx.cond(
                                TemaState.tema_escuro,
                                ECLIPSE["text_secondary"],
                                MINERAL["text_secondary"],
                            ),
                            margin_top="16px",
                        ),
                        _tabela_pares(),
                        rx.text(
                            "LANCAMENTOS SEM PAR",
                            size="1",
                            weight="bold",
                            letter_spacing="0.06em",
                            color=rx.cond(
                                TemaState.tema_escuro,
                                ECLIPSE["text_secondary"],
                                MINERAL["text_secondary"],
                            ),
                            margin_top="16px",
                        ),
                        _tabela_sem_par(),
                        _acoes_exportacao(),
                        spacing="4",
                        width="100%",
                    ),
                ),
                width="100%",
                height="100vh",
                max_width="100%",
                padding="24px",
                background=rx.cond(
                    TemaState.tema_escuro,
                    ECLIPSE["content_bg"],
                    MINERAL["content_bg"],
                ),
                overflow_x="hidden",
                overflow_y="auto",
            ),
            spacing="0",
        ),
    )
