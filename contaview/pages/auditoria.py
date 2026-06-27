import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.components.filtros import filtros
from contaview.components.kpi_card import kpi_card
from contaview.state.tema_state import TemaState
from contaview.state.dados_state import DadosState
from contaview.utils.auth import pagina_protegida
from contaview.styles import MINERAL, ECLIPSE


def _badge_severidade(severidade: str) -> rx.Component:
    return rx.badge(
        rx.text(severidade, text_transform="uppercase"),
        color_scheme=rx.match(
            severidade,
            ("alta", "red"),
            ("media", "amber"),
            ("baixa", "blue"),
            "blue",
        ),
        size="1",
    )


def _tabela_ocorrencias() -> rx.Component:
    return rx.cond(
        DadosState.ocorrencias,
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Tipo"),
                    rx.table.column_header_cell("Descrição"),
                    rx.table.column_header_cell("Severidade"),
                    rx.table.column_header_cell("Resolvida"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    DadosState.ocorrencias,
                    lambda o: rx.table.row(
                        rx.table.cell(
                            rx.text(
                                o.get("tipo_ocorrencia", ""),
                                font_size="13px",
                                font_weight="600",
                            ),
                        ),
                        rx.table.cell(
                            rx.text(
                                o.get("descricao", ""),
                                font_size="13px",
                            ),
                        ),
                        rx.table.cell(
                            _badge_severidade(o.get("severidade", "baixa")),
                        ),
                        rx.table.cell(
                            rx.checkbox(
                                default_checked=o.get("resolvida", False),
                                on_change=lambda checked, oid=o.get("id"):
                                    DadosState.marcar_ocorrencia_resolvida(oid, checked),
                            ),
                        ),
                    ),
                ),
            ),
            width="100%",
        ),
        rx.text(
            "Nenhuma ocorrência de auditoria encontrada.",
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
            on_click=DadosState.exportar_excel_auditoria,
        ),
        spacing="3",
        margin_top="16px",
    )


def auditoria() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.text(
                    "Auditoria",
                    font_size="22px",
                    font_weight="600",
                    color=rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["text_primary"],
                        MINERAL["text_primary"],
                    ),
                ),
                filtros(),
                rx.cond(
                    DadosState.carregando,
                    rx.spinner(),
                    rx.vstack(
                        rx.grid(
                            kpi_card(
                                "Alta",
                                DadosState.ocorrencias_total_alta,
                                "negativo",
                            ),
                            kpi_card(
                                "Media",
                                DadosState.ocorrencias_total_media,
                                "neutro",
                            ),
                            kpi_card(
                                "Baixa",
                                DadosState.ocorrencias_total_baixa,
                                "neutro",
                            ),
                            columns="3",
                            spacing="4",
                            width="100%",
                        ),
                        _tabela_ocorrencias(),
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
