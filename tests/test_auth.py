import os
import unittest
from unittest.mock import patch

from contaview.state.auth_state import credenciais_conferem, credenciais_configuradas
from contaview.utils.auth import estado_autenticado


class AutenticacaoTest(unittest.TestCase):
    def test_ambiente_incompleto_nao_e_considerado_configurado(self):
        with patch.dict(os.environ, {"APP_USUARIO": "", "APP_SENHA": ""}, clear=False):
            self.assertFalse(credenciais_configuradas())

    def test_credenciais_vazias_nunca_sao_aceitas(self):
        self.assertFalse(credenciais_conferem("", "", "", ""))
        self.assertFalse(credenciais_conferem("contadora", "", "contadora", ""))

    def test_usuario_ignora_maiusculas_mas_senha_e_exata(self):
        self.assertTrue(
            credenciais_conferem("CONTADORA", "Segredo123", "contadora", "Segredo123")
        )
        self.assertFalse(
            credenciais_conferem("contadora", "segredo123", "contadora", "Segredo123")
        )

    def test_estado_de_dominio_sem_sessao_e_negado(self):
        class Estado:
            sessao_autorizada = False

        class EstadoAutorizado:
            sessao_autorizada = True

        self.assertFalse(estado_autenticado(Estado()))
        self.assertTrue(estado_autenticado(EstadoAutorizado()))


if __name__ == "__main__":
    unittest.main()
