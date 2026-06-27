import reflex as rx
from contaview.state.auth_state import AuthState


def pagina_protegida(componente: rx.Component) -> rx.Component:
    return rx.cond(
        AuthState.autenticado,
        componente,
        rx.script("window.location.href = '/'"),
    )
