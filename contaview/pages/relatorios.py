import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.components.filtros import filtros
from contaview.state.tema_state import TemaState
from contaview.state.dados_state import DadosState
from contaview.utils.auth import pagina_protegida
from contaview.styles import MINERAL, ECLIPSE


def _card_relatorio(
    icone: str,
    titulo: str,
    descricao: str,
    botoes: list[rx.Component],
) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon(icone, size=20, color=rx.cond(
                TemaState.tema_escuro, ECLIPSE["accent"], MINERAL["accent"],
            )),
            rx.text(
                titulo,
                font_size="16px",
                font_weight="600",
                color=rx.cond(
                    TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"],
                ),
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.text(
            descricao,
            font_size="13px",
            color=rx.cond(
                TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"],
            ),
            width="100%",
        ),
        rx.hstack(
            *botoes,
            spacing="3",
            width="100%",
        ),
        background=rx.cond(
            TemaState.tema_escuro, ECLIPSE["card_bg"], MINERAL["card_bg"],
        ),
        border=rx.cond(TemaState.tema_escuro, f"1px solid {ECLIPSE['border']}", f"1px solid {MINERAL['border']}"),
        border_radius="10px",
        padding="20px",
        spacing="3",
        width="100%",
        max_width="600px",
    )


def relatorios() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.text(
                    "Relatórios",
                    font_size="22px",
                    font_weight="600",
                    color=rx.cond(
                        TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"],
                    ),
                ),
                rx.text(
                    DadosState.subtitulo_painel,
                    font_size="14px",
                    color=rx.cond(
                        TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"],
                    ),
                ),
                filtros(),
                rx.cond(
                    DadosState.lancamentos,
                    rx.vstack(
                        _card_relatorio(
                            "list",
                            "Lançamentos do período",
                            "Exporte todos os lançamentos contábeis do período "
                            "selecionado em formato Excel ou PDF.",
                            [
                                rx.button(
                                    "Exportar Excel",
                                    variant="outline",
                                    on_click=DadosState.exportar_excel_lancamentos,
                                ),
                                rx.button(
                                    "Exportar PDF",
                                    variant="outline",
                                    on_click=DadosState.exportar_pdf_lancamentos,
                                ),
                            ],
                        ),
                        _card_relatorio(
                            "arrow-left-right",
                            "Relatório de conciliação",
                            "Exporte o relatório de conciliação com pares "
                            "conciliados e lançamentos sem par.",
                            [
                                rx.button(
                                    "Exportar Excel",
                                    variant="outline",
                                    on_click=DadosState.exportar_excel_conciliacao,
                                ),
                                rx.button(
                                    "Exportar PDF",
                                    variant="outline",
                                    on_click=DadosState.exportar_pdf_conciliacao,
                                ),
                            ],
                        ),
                        _card_relatorio(
                            "search",
                            "Relatorio de auditoria",
                            "Exporte as ocorrências de auditoria do período "
                            "selecionado em formato Excel.",
                            [
                                rx.button(
                                    "Exportar Excel",
                                    variant="outline",
                                    on_click=DadosState.exportar_excel_auditoria,
                                ),
                            ],
                        ),
                        spacing="4",
                        width="100%",
                        align="center",
                    ),
                    rx.text(
                        "Selecione uma empresa e período para gerar relatórios.",
                        font_size="14px",
                        color=rx.cond(
                            TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"],
                        ),
                    ),
                ),
                width="100%",
                height="100vh",
                padding="24px",
                background=rx.cond(
                    TemaState.tema_escuro, ECLIPSE["content_bg"], MINERAL["content_bg"],
                ),
                overflow_y="auto",
            ),
            spacing="0",
        ),
    )
