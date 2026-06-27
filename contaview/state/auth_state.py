import os
import logging
import reflex as rx

logger = logging.getLogger(__name__)


class AuthState(rx.State):
    autenticado: bool = False
    usuario: str = ""
    usuario_input: str = ""
    senha_input: str = ""

    def set_usuario_input(self, valor: str):
        self.usuario_input = valor

    def set_senha_input(self, valor: str):
        self.senha_input = valor

    def fazer_login(self, usuario: str, senha: str):
        try:
            usuario_correto = os.getenv("APP_USUARIO", "")
            senha_correta = os.getenv("APP_SENHA", "")
            if usuario == usuario_correto and senha == senha_correta:
                self.autenticado = True
                self.usuario = usuario
                return rx.redirect("/painel")
            return rx.window_alert("Usuário ou senha incorretos.")
        except Exception as exc:
            logger.error("Erro no login: %s", exc)
            return rx.window_alert("Erro interno. Tente novamente.")

    def fazer_logout(self):
        self.autenticado = False
        self.usuario = ""
        return rx.redirect("/")
