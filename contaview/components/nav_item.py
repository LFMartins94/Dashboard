import reflex as rx
from contaview.state.tema_state import TemaState
from contaview.styles import MINERAL, ECLIPSE


def nav_item(label: str, rota: str, icone: str) -> rx.Component:
    ativo = rx.State.router.page.path == rota
    return rx.link(
        rx.hstack(
            rx.icon(
                icone,
                size=16,
                color=rx.cond(
                    ativo,
                    rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_active"], MINERAL["sidebar_active"]),
                    rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
                ),
            ),
            rx.text(
                label,
                size="2",
                color=rx.cond(
                    ativo,
                    rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_active"], MINERAL["sidebar_active"]),
                    rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
                ),
            ),
            background=rx.cond(
                ativo,
                rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_active_bg"], MINERAL["sidebar_active_bg"]),
                "transparent",
            ),
            padding="8px 10px",
            border_radius="8px",
            width="100%",
            class_name="nav-item",
        ),
        href=rota,
        text_decoration="none",
    )
