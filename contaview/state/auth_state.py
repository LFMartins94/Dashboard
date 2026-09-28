import os
import logging
import secrets
from datetime import datetime, timezone
import reflex as rx

logger = logging.getLogger(__name__)


def credenciais_configuradas() -> bool:
    """Retorna se o ambiente possui credenciais de acesso completas."""
    return bool(
        os.getenv("APP_USUARIO", "").strip()
        and os.getenv("APP_SENHA", "").strip()
    )


def credenciais_conferem(
    usuario_input: str,
    senha_input: str,
    usuario_correto: str,
    senha_correta: str,
) -> bool:
    """Compara credenciais sem aceitar configuração vazia."""
    if not usuario_correto or not senha_correta:
        return False
    return secrets.compare_digest(
        usuario_input.casefold(), usuario_correto.casefold()
    ) and secrets.compare_digest(senha_input, senha_correta)


class AuthState(rx.State):
    autenticado: bool = False
    usuario: str = ""
    carregando_login: bool = False

    async def fazer_login_submit(self, form_data: dict):
        self.carregando_login = True
        yield
        try:
            usuario_input = (form_data.get("usuario") or "").strip()
            senha_input = (form_data.get("senha") or "").strip()
            usuario_correto = os.getenv("APP_USUARIO", "").strip()
            senha_correta = os.getenv("APP_SENHA", "").strip()

            if not credenciais_configuradas():
                self.autenticado = False
                self.usuario = ""
                logger.critical(
                    "Login bloqueado: APP_USUARIO e APP_SENHA precisam estar configurados."
                )
                yield rx.window_alert(
                    "O acesso está indisponível porque as credenciais não foram configuradas."
                )
                return

            usuario_correto_normalizado = usuario_correto.casefold()
            usuario_input_normalizado = usuario_input.casefold()

            logger.info(
                "LOGIN: hora=%s input_user_len=%d input_pass_len=%d "
                "env_user_len=%d env_pass_len=%d "
                "user_match=%s pass_match=%s",
                datetime.now(timezone.utc).isoformat(),
                len(usuario_input), len(senha_input),
                len(usuario_correto), len(senha_correta),
                secrets.compare_digest(usuario_input_normalizado, usuario_correto_normalizado),
                secrets.compare_digest(senha_input, senha_correta),
            )

            if credenciais_conferem(
                usuario_input, senha_input, usuario_correto, senha_correta
            ):
                self.autenticado = True
                self.usuario = usuario_correto or usuario_input
                from contaview.state.chat_state import ChatState
                from contaview.state.dados_state import DadosState

                (await self.get_state(DadosState)).sessao_autorizada = True
                (await self.get_state(ChatState)).sessao_autorizada = True
                yield rx.redirect("/painel")
                return
            yield rx.window_alert("Usu\u00e1rio ou senha incorretos.")
        except Exception as exc:
            logger.error("Erro no login: %s", exc)
            yield rx.window_alert("Erro interno. Tente novamente.")
        finally:
            self.carregando_login = False

    async def fazer_logout(self):
        self.autenticado = False
        self.usuario = ""
        from contaview.state.chat_state import ChatState
        from contaview.state.dados_state import DadosState

        dados_state = await self.get_state(DadosState)
        dados_state.sessao_autorizada = False
        dados_state._limpar_dados_protegidos()
        chat_state = await self.get_state(ChatState)
        chat_state.sessao_autorizada = False
        chat_state.conversas = []
        chat_state.mensagens = []
        chat_state.conversa_ativa = None
        return rx.redirect("/")
