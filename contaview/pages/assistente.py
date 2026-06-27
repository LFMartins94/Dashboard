import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.state.tema_state import TemaState
from contaview.state.chat_state import ChatState
from contaview.utils.auth import pagina_protegida
from contaview.styles import MINERAL, ECLIPSE


def _bolha_mensagem(mensagem: dict) -> rx.Component:
    papel = mensagem["role"]
    conteudo = mensagem["content"]
    return rx.box(
        rx.text(
            conteudo,
            font_size="14px",
            color=rx.cond(
                TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"],
            ),
        ),
        align_self=rx.cond(
            papel == "user",
            "flex-end",
            "flex-start",
        ),
        background=rx.cond(
            papel == "user",
            rx.cond(
                TemaState.tema_escuro,
                "rgba(0, 201, 160, 0.15)",
                "rgba(126, 184, 196, 0.15)",
            ),
            rx.cond(
                TemaState.tema_escuro, ECLIPSE["card_bg"], MINERAL["card_bg"],
            ),
        ),
        border_radius="12px",
        padding="12px 16px",
        max_width="75%",
        margin_bottom="12px",
    )


def assistente() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.text(
                    "Assistente",
                    font_size="22px",
                    font_weight="600",
                    color=rx.cond(
                        TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"],
                    ),
                ),
                rx.cond(
                    ChatState.erro_assistente != "",
                    rx.callout(
                        ChatState.erro_assistente,
                        icon="triangle_alert",
                        color_scheme="red",
                        width="100%",
                    ),
                ),
                rx.cond(
                    ChatState.conversa_ativa is None,
                    rx.center(
                        rx.text(
                            "Selecione uma conversa ou inicie uma nova.",
                            font_size="14px",
                            color=rx.cond(
                                TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"],
                            ),
                        ),
                        flex="1",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    ChatState.mensagens,
                                    _bolha_mensagem,
                                ),
                                spacing="0",
                                width="100%",
                            ),
                            style={"height": "calc(100vh - 220px)"},
                            width="100%",
                            padding_right="8px",
                        ),
                        rx.hstack(
                            rx.text_area(
                                value=ChatState.entrada_atual,
                                on_change=ChatState.set_entrada_atual,
                                placeholder="Digite sua mensagem...",
                                size="2",
                                width="100%",
                                style={
                                    "color": rx.cond(
                                        TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"],
                                    ),
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
                                },
                            ),
                            rx.button(
                                rx.cond(
                                    ChatState.carregando_resposta,
                                    rx.spinner(size="2"),
                                    rx.icon("send", size=16),
                                ),
                                on_click=ChatState.enviar_mensagem,
                                is_disabled=ChatState.carregando_resposta,
                                background=rx.cond(
                                    TemaState.tema_escuro, ECLIPSE["accent"], MINERAL["accent"],
                                ),
                                color=rx.cond(
                                    TemaState.tema_escuro, ECLIPSE["sidebar_bg"], MINERAL["sidebar_bg"],
                                ),
                            ),
                            spacing="3",
                            width="100%",
                            padding_top="12px",
                        ),
                        flex="1",
                        width="100%",
                    ),
                ),
                on_mount=ChatState.iniciar_assistente,
                width="100%",
                height="100vh",
                padding="24px",
                background=rx.cond(
                    TemaState.tema_escuro, ECLIPSE["content_bg"], MINERAL["content_bg"],
                ),
                overflow_y="hidden",
            ),
            spacing="0",
        ),
    )
