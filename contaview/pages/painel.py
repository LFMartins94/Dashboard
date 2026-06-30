import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.components.filtros import filtros
from contaview.components.kpi_card import kpi_card
from contaview.state.tema_state import TemaState
from contaview.state.dados_state import DadosState
from contaview.utils.auth import pagina_protegida
from contaview.utils.formatacao import formatar_moeda
from contaview.styles import MINERAL, ECLIPSE


def painel() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            "Painel",
                            font_size="22px",
                            font_weight="600",
                            color=rx.cond(
                                TemaState.tema_escuro,
                                ECLIPSE["text_primary"],
                                MINERAL["text_primary"],
                            ),
                        ),
                        rx.text(
                            DadosState.subtitulo_painel,
                            font_size="14px",
                            color=rx.cond(
                                TemaState.tema_escuro,
                                ECLIPSE["text_secondary"],
                                MINERAL["text_secondary"],
                            ),
                        ),
                        align="start",
                        spacing="0",
                    ),
                    width="100%",
                ),
                filtros(),
                rx.cond(
                    DadosState.empresa_selecionada != "",
                    rx.hstack(
                        rx.button(
                            "Renomear empresa",
                            variant="ghost",
                            size="1",
                            on_click=DadosState.abrir_renomear_empresa,
                        ),
                        width="100%",
                    ),
                ),
                rx.alert_dialog.root(
                    rx.alert_dialog.content(
                        rx.alert_dialog.title("Renomear empresa"),
                        rx.alert_dialog.description(
                            "Altere o nome da empresa selecionada."
                        ),
                        rx.input(
                            value=DadosState.renomear_empresa_nome,
                            on_change=DadosState.set_renomear_empresa_nome,
                            width="100%",
                        ),
                        rx.flex(
                            rx.alert_dialog.cancel(
                                rx.button(
                                    "Cancelar",
                                    variant="soft",
                                    on_click=DadosState.cancelar_renomear_empresa,
                                ),
                            ),
                            rx.alert_dialog.action(
                                rx.button(
                                    "Salvar",
                                    on_click=DadosState.confirmar_renomear_empresa,
                                ),
                            ),
                            spacing="3",
                            justify="end",
                            margin_top="16px",
                        ),
                    ),
                    open=DadosState.dialog_renomear_aberto,
                ),
                rx.cond(
                    DadosState.carregando,
                    rx.spinner(),
                    rx.vstack(
                        rx.grid(
                            kpi_card(
                                "Débitos",
                                rx.cond(
                                    DadosState.lancamentos,
                                    formatar_moeda(DadosState.total_debitos),
                                    "R$ 0,00",
                                ),
                                "negativo",
                            ),
                            kpi_card(
                                "Créditos",
                                rx.cond(
                                    DadosState.lancamentos,
                                    formatar_moeda(DadosState.total_creditos),
                                    "R$ 0,00",
                                ),
                                "positivo",
                            ),
                            kpi_card(
                                "Saldo",
                                rx.cond(
                                    DadosState.lancamentos,
                                    formatar_moeda(abs(DadosState.saldo)),
                                    "R$ 0,00",
                                ),
                                rx.cond(
                                    DadosState.saldo > 0,
                                    "positivo",
                                    rx.cond(
                                        DadosState.saldo < 0,
                                        "negativo",
                                        "neutro",
                                    ),
                                ),
                            ),
                            columns="3",
                            spacing="4",
                            width="100%",
                        ),
                        rx.grid(
                            rx.card(
                                rx.plotly(data=DadosState.fig_mensal),
                                width="100%",
                                background=rx.cond(
                                    TemaState.tema_escuro,
                                    ECLIPSE["card_bg"],
                                    MINERAL["card_bg"],
                                ),
                            ),
                            rx.card(
                                rx.plotly(data=DadosState.fig_top_contas),
                                width="100%",
                                background=rx.cond(
                                    TemaState.tema_escuro,
                                    ECLIPSE["card_bg"],
                                    MINERAL["card_bg"],
                                ),
                            ),
                            columns="2",
                            spacing="4",
                            width="100%",
                        ),
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
