import reflex as rx
from contaview.state.tema_state import TemaState
from contaview.styles import MINERAL, ECLIPSE


def kpi_card(label: str, valor, tipo: str) -> rx.Component:
    cor_valor = rx.match(
        tipo,
        ("positivo", rx.cond(TemaState.tema_escuro, ECLIPSE["positive"], MINERAL["positive"])),
        ("negativo", rx.cond(TemaState.tema_escuro, ECLIPSE["negative"], MINERAL["negative"])),
        rx.cond(TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"]),
    )
    return rx.vstack(
        rx.text(
            label.upper(),
            size="1",
            color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"]),
            letter_spacing="0.08em",
            weight="bold",
        ),
        rx.text(
            valor,
            size="6",
            weight="bold",
            color=cor_valor,
        ),
        background=rx.cond(TemaState.tema_escuro, ECLIPSE["card_bg"], MINERAL["card_bg"]),
        border=rx.cond(TemaState.tema_escuro, f"1px solid {ECLIPSE['border']}", f"1px solid {MINERAL['border']}"),
        border_radius="10px",
        padding="14px 16px",
        spacing="1",
    )
