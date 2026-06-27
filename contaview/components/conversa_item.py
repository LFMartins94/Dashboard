import reflex as rx
from contaview.state.tema_state import TemaState
from contaview.state.chat_state import ChatState
from contaview.styles import MINERAL, ECLIPSE


def conversa_item(conversa: dict) -> rx.Component:
    ativo = ChatState.conversa_ativa == conversa["id"]
    return rx.hstack(
        rx.vstack(
            rx.text(conversa["titulo"], size="2",
                    color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"])),
            rx.text(conversa["atualizado_em"], size="1",
                    color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"])),
            spacing="0",
            align="start",
        ),
        rx.icon(
            "trash",
            size=14,
            color=rx.cond(TemaState.tema_escuro, ECLIPSE["text_secondary"], MINERAL["text_secondary"]),
            opacity="0",
            class_name="conversa-delete",
            on_click=[
                rx.stop_propagation,
                lambda: ChatState.excluir_conversa(conversa["id"]),
            ],
        ),
        on_click=lambda: ChatState.selecionar_conversa(conversa["id"]),
        justify="between",
        width="100%",
        padding="8px 10px",
        border_radius="8px",
        cursor="pointer",
        class_name="conversa-item",
        background=rx.cond(
            ativo,
            rx.cond(TemaState.tema_escuro, ECLIPSE["card_bg"], MINERAL["card_bg"]),
            "transparent",
        ),
    )
