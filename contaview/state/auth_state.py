import os
import logging
from datetime import datetime, timezone
import reflex as rx

logger = logging.getLogger(__name__)


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

            logger.info(
                "LOGIN: hora=%s input_user_len=%d input_pass_len=%d "
                "env_user_len=%d env_pass_len=%d "
                "user_match=%s pass_match=%s",
                datetime.now(timezone.utc).isoformat(),
                len(usuario_input), len(senha_input),
                len(usuario_correto), len(senha_correta),
                usuario_input == usuario_correto,
                senha_input == senha_correta,
            )

            if usuario_input == usuario_correto and senha_input == senha_correta:
                self.autenticado = True
                self.usuario = usuario_input
                yield rx.redirect("/painel")
                return
            yield rx.window_alert("Usuario ou senha incorretos.")
        except Exception as exc:
            logger.error("Erro no login: %s", exc)
            yield rx.window_alert("Erro interno. Tente novamente.")
        finally:
            self.carregando_login = False

    def fazer_logout(self):
        self.autenticado = False
        self.usuario = ""
        return rx.redirect("/")
