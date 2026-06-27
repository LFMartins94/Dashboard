import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.components.filtros import filtros
from contaview.state.tema_state import TemaState
from contaview.state.dados_state import DadosState
from contaview.utils.auth import pagina_protegida
from contaview.styles import MINERAL, ECLIPSE


def lancamentos() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.text(
                    "Lançamentos",
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
                    rx.data_table(
                        data=DadosState.lancamentos_tabela,
                        columns=DadosState.colunas_tabela,
                        pagination=True,
                        sort=True,
                    ),
                ),
                width="100%",
                height="100vh",
                padding="24px",
                background=rx.cond(
                    TemaState.tema_escuro,
                    ECLIPSE["content_bg"],
                    MINERAL["content_bg"],
                ),
                overflow_y="auto",
            ),
            spacing="0",
        ),
    )
