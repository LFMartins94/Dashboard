import reflex as rx
from contaview.state.tema_state import TemaState
from contaview.state.chat_state import ChatState
from contaview.styles import MINERAL, ECLIPSE


def conversa_item(conversa: dict) -> rx.Component:
    ativo = ChatState.conversa_ativa == conversa["id"]
    renomeando = ChatState.renomeando_id == conversa["id"]
    favorito = conversa.get("favorito", False)

    return rx.hstack(
        rx.cond(
            renomeando,
            rx.input(
                value=ChatState.renomear_titulo_temp,
                on_change=ChatState.set_renomear_titulo_temp,
                on_blur=ChatState.confirmar_renomear_conversa,
                on_key_down=ChatState.handle_rename_key,
                size="1",
                width="100%",
                style={
                    "color": rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["text_primary"],
                        MINERAL["text_primary"],
                    ),
                    "background": "transparent",
                    "border": rx.cond(
                        TemaState.tema_escuro,
                        "1px solid #3A4150",
                        "1px solid #E0DDD5",
                    ),
                },
                auto_focus=True,
            ),
            rx.text(
                conversa["titulo"],
                size="2",
                color=rx.cond(
                    TemaState.tema_escuro,
                    ECLIPSE["text_primary"],
                    MINERAL["text_primary"],
                ),
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            ),
        ),
        rx.menu.root(
            rx.menu.trigger(
                rx.icon(
                    "ellipsis-vertical",
                    size=14,
                    color=rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["text_secondary"],
                        MINERAL["text_secondary"],
                    ),
                    opacity="0",
                    class_name="conversa-kebab",
                ),
            ),
            rx.menu.content(
                rx.menu.item(
                    "Renomear",
                    on_select=ChatState.iniciar_renomear_conversa(conversa["id"]),
                ),
                rx.menu.item(
                    rx.cond(
                        favorito,
                        "Desfavoritar",
                        "Favoritar",
                    ),
                    on_select=ChatState.alternar_favorito(conversa["id"]),
                ),
                rx.menu.separator(),
                rx.menu.item(
                    "Excluir",
                    on_select=ChatState.excluir_conversa(conversa["id"]),
                    color_scheme="red",
                ),
                size="1",
                align="start",
            ),
        ),
        on_click=lambda: ChatState.selecionar_conversa(conversa["id"]),
        justify="between",
        align="center",
        width="100%",
        padding="8px 10px",
        border_radius="8px",
        cursor="pointer",
        class_name="conversa-item",
        background=rx.cond(
            ativo,
            rx.cond(
                TemaState.tema_escuro,
                ECLIPSE["card_bg"],
                MINERAL["card_bg"],
            ),
            "transparent",
        ),
    )
