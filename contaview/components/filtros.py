import reflex as rx
from contaview.state.dados_state import DadosState
from contaview.state.tema_state import TemaState
from contaview.styles import MINERAL, ECLIPSE


def filtros() -> rx.Component:
    return rx.hstack(
        rx.select(
            DadosState.empresas_disponiveis,
            placeholder="Empresa",
            on_change=DadosState.set_empresa_selecionada,
            background=rx.cond(TemaState.tema_escuro, ECLIPSE["card_bg"], MINERAL["card_bg"]),
            border=rx.cond(TemaState.tema_escuro, f"1px solid {ECLIPSE['border']}", f"1px solid {MINERAL['border']}"),
            color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"]),
            border_radius="8px",
        ),
        rx.select(
            DadosState.periodos_disponiveis,
            placeholder="Período",
            on_change=DadosState.set_periodo_selecionado,
            background=rx.cond(TemaState.tema_escuro, ECLIPSE["card_bg"], MINERAL["card_bg"]),
            border=rx.cond(TemaState.tema_escuro, f"1px solid {ECLIPSE['border']}", f"1px solid {MINERAL['border']}"),
            color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"]),
            border_radius="8px",
        ),
        spacing="3",
        margin_bottom="20px",
    )
