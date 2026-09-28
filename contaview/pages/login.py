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
    return rx.flex(
        rx.form.root(
                rx.vstack(
                    rx.vstack(
                        rx.text(
                            "Conta",
                            rx.text.span(
                                "View",
                                color=rx.cond(
                                    TemaState.tema_escuro,
                                    ECLIPSE["accent"],
                                    MINERAL["accent"],
                                ),
                            ),
                            size="5",
                            weight="bold",
                            color=rx.cond(
                                TemaState.tema_escuro,
                                ECLIPSE["text_primary"],
                                MINERAL["text_primary"],
                            ),
                        ),
                        rx.text(
                            "Acesso restrito",
                            size="2",
                            color=rx.cond(
                                TemaState.tema_escuro,
                                ECLIPSE["text_secondary"],
                                MINERAL["text_secondary"],
                            ),
                        ),
                        spacing="1",
                        align="center",
                        width="100%",
                        margin_bottom="24px",
                    ),
                    rx.input(
                        name="usuario",
                        placeholder="Usuario",
                        width="100%",
                        style=_input_style(),
                        disabled=AuthState.carregando_login,
                    ),
                    rx.input(
                        name="senha",
                        placeholder="Senha",
                        type="password",
                        width="100%",
                        style=_input_style(),
                        disabled=AuthState.carregando_login,
                    ),
                    rx.button(
                        rx.cond(
                            AuthState.carregando_login,
                            "Conectando...",
                            "Entrar",
                        ),
                        type="submit",
                        width="100%",
                        disabled=AuthState.carregando_login,
                        background=rx.cond(
                            TemaState.tema_escuro,
                            ECLIPSE["accent"],
                            MINERAL["accent"],
                        ),
                        color=rx.cond(
                            TemaState.tema_escuro,
                            ECLIPSE["sidebar_bg"],
                            MINERAL["sidebar_bg"],
                        ),
                    ),
                    spacing="3",
                    width="320px",
                    background=rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["card_bg"],
                        MINERAL["card_bg"],
                    ),
                    border=rx.cond(
                        TemaState.tema_escuro,
                        f"1px solid {ECLIPSE['border']}",
                        f"1px solid {MINERAL['border']}",
                    ),
                    border_radius="10px",
                    padding="32px",
                    margin_left="auto",
                    margin_right="auto",
                    box_shadow="0 4px 12px rgba(0,0,0,0.1)",
                ),
                on_submit=AuthState.fazer_login_submit,
                reset_on_submit=False,
            ),
        height="100vh",
        width="100%",
        position="fixed",
        top="0",
        right="0",
        bottom="0",
        left="0",
        align_items="center",
        justify_content="center",
        flex_direction="column",
        background=rx.cond(
            TemaState.tema_escuro,
            ECLIPSE["content_bg"],
            MINERAL["content_bg"],
        ),
    )
