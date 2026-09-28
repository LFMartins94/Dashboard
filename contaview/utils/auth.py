import logging
import reflex as rx
from contaview.state.auth_state import AuthState


logger = logging.getLogger(__name__)


def estado_autenticado(estado: rx.State) -> bool:
    """Consulta a autorização espelhada no estado do domínio.

    Os handlers de domínio são síncronos em vários pontos do Reflex. Por isso
    cada estado protegido mantém uma cópia booleana da sessão, atualizada pelo
    AuthState no mesmo websocket. Ausência dessa cópia significa acesso negado.
    """
    try:
        return bool(getattr(estado, "sessao_autorizada", False))
    except Exception as exc:
        logger.warning("Não foi possível validar a sessão: %s", type(exc).__name__)
        return False


def pagina_protegida(componente: rx.Component) -> rx.Component:
    return rx.cond(
        AuthState.autenticado,
        componente,
        rx.script("window.location.href = '/'"),
    )
