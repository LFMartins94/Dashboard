import reflex as rx
from contaview.state.auth_state import AuthState
from contaview.state.tema_state import TemaState
from contaview.styles import MINERAL, ECLIPSE


def _input_style() -> dict:
    return {
        "color": rx.cond(TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"]),
        "background_color": rx.cond(
            TemaState.tema_escuro,
            "#1E2530",
            "#FFFFFF",
        ),
        "border": rx.cond(
            TemaState.tema_escuro,
            "1px solid #3A4150",
            "1px solid #E0DDD5",
        ),
        "placeholder_color": rx.cond(
            TemaState.tema_escuro,
            ECLIPSE["text_secondary"],
            MINERAL["text_secondary"],
        ),
    }


def login() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.vstack(
                rx.text(
                    "Conta",
                    rx.text.span(
                        "View",
                        color=rx.cond(TemaState.tema_escuro, ECLIPSE["accent"], MINERAL["accent"]),
                    ),
                    size="5",
                    weight="bold",
                    color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"]),
                ),
                rx.text(
                    "Acesso restrito",
                    size="2",
                    color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"]),
                ),
                spacing="1",
                align="center",
                width="100%",
                margin_bottom="24px",
            ),
            rx.input(
                placeholder="Usuário",
                on_change=AuthState.set_usuario_input,
                width="100%",
                style=_input_style(),
            ),
            rx.input(
                placeholder="Senha",
                type="password",
                on_change=AuthState.set_senha_input,
                width="100%",
                style=_input_style(),
            ),
            rx.button(
                "Entrar",
                on_click=AuthState.fazer_login(AuthState.usuario_input, AuthState.senha_input),
                width="100%",
                background=rx.cond(TemaState.tema_escuro, ECLIPSE["accent"], MINERAL["accent"]),
                color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_bg"], MINERAL["sidebar_bg"]),
            ),
            spacing="3",
            width="320px",
            background=rx.cond(TemaState.tema_escuro, ECLIPSE["card_bg"], MINERAL["card_bg"]),
            border=rx.cond(TemaState.tema_escuro, f"1px solid {ECLIPSE['border']}", f"1px solid {MINERAL['border']}"),
            border_radius="10px",
            padding="32px",
            box_shadow="0 4px 12px rgba(0,0,0,0.1)",
        ),
        height="100vh",
        width="100%",
        background=rx.cond(TemaState.tema_escuro, ECLIPSE["content_bg"], MINERAL["content_bg"]),
    )
