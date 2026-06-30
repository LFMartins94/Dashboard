import reflex as rx
from contaview.state.auth_state import AuthState
from contaview.state.tema_state import TemaState
from contaview.state.chat_state import ChatState
from contaview.components.nav_item import nav_item
from contaview.components.conversa_item import conversa_item
from contaview.styles import MINERAL, ECLIPSE


PAGINAS = [
    {"label": "Painel", "rota": "/painel", "icone": "layout-dashboard"},
    {"label": "Lançamentos", "rota": "/lancamentos", "icone": "list"},
    {"label": "Importar", "rota": "/importar", "icone": "upload"},
    {"label": "Conciliação", "rota": "/conciliacao", "icone": "arrow-left-right"},
    {"label": "Auditoria", "rota": "/auditoria", "icone": "search"},
    {"label": "Relatórios", "rota": "/relatorios", "icone": "file-text"},
    {"label": "Assistente", "rota": "/assistente", "icone": "message-square"},
]


def sidebar() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                "Conta",
                rx.text.span(
                    "View",
                    color=rx.cond(TemaState.tema_escuro, ECLIPSE["accent"], MINERAL["accent"]),
                ),
                size="4",
                weight="medium",
                color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
            ),
            rx.icon(
                "chevron-left",
                size=16,
                color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
            ),
            justify="between",
            width="100%",
            padding="4px 8px 16px",
        ),
        rx.foreach(
            PAGINAS,
            lambda pagina: nav_item(pagina["label"], pagina["rota"], pagina["icone"]),
        ),
        rx.divider(margin_y="14px"),
        rx.cond(
            rx.State.router.page.path == "/assistente",
            rx.vstack(
                rx.button(
                    rx.icon("plus", size=14),
                    "Nova conversa",
                    on_click=ChatState.nova_conversa,
                    width="100%",
                    background=rx.cond(TemaState.tema_escuro, ECLIPSE["accent"], MINERAL["accent"]),
                    color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_bg"], MINERAL["sidebar_bg"]),
                ),
                rx.hstack(
                    rx.text(
                        "CONVERSAS",
                        size="1",
                        color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
                        letter_spacing="0.06em",
                    ),
                    rx.icon(
                        "arrow-up-down",
                        size=13,
                        color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
                    ),
                    justify="between",
                    width="100%",
                    padding="12px 10px 6px",
                ),
                rx.scroll_area(
                    rx.vstack(
                        rx.cond(
                            ChatState.tem_favoritas,
                            rx.foreach(
                                ChatState.conversas_favoritas,
                                conversa_item,
                            ),
                        ),
                        rx.cond(
                            ChatState.tem_favoritas,
                            rx.divider(margin_y="4px"),
                        ),
                        rx.foreach(ChatState.conversas, conversa_item),
                        spacing="1",
                    ),
                    max_height="220px",
                    width="100%",
                ),
                width="100%",
            ),
        ),
        rx.spacer(),
        rx.divider(),
        rx.hstack(
            rx.avatar(fallback="CT", size="2"),
            rx.text(
                AuthState.usuario,
                size="2",
                flex="1",
                color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
            ),
            rx.icon(
                rx.cond(TemaState.tema_escuro, "sun", "moon"),
                size=15,
                cursor="pointer",
                on_click=TemaState.alternar_tema,
                color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
            ),
            rx.icon(
                "log-out",
                size=15,
                cursor="pointer",
                on_click=AuthState.fazer_logout,
                color=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_text"], MINERAL["sidebar_text"]),
            ),
            width="100%",
            padding_top="12px",
        ),
        background=rx.cond(TemaState.tema_escuro, ECLIPSE["sidebar_bg"], MINERAL["sidebar_bg"]),
        height="100vh",
        width="252px",
        padding="16px 10px",
        spacing="2",
    )
