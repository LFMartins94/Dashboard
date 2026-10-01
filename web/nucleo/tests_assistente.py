from unittest.mock import patch

from django.test import SimpleTestCase

from .servicos import assistente
from .servicos.contexto import ContextoTrabalho


class Sessao(dict):
    modified = False


class RequisicaoFake:
    def __init__(self):
        self.session = Sessao()


class AssistenteServicoTest(SimpleTestCase):
    def test_conversa_fica_limitada_a_sessao(self):
        requisicao = RequisicaoFake()
        with patch.object(assistente.database, "criar_conversa", return_value=12):
            self.assertEqual(assistente.nova_conversa(requisicao), 12)
        with patch.object(assistente.database, "carregar_mensagens", return_value=[]):
            self.assertEqual(assistente.obter_mensagens(requisicao, 12), [])
            with self.assertRaises(assistente.ErroAssistente):
                assistente.obter_mensagens(requisicao, 99)

    @patch("contaview.logic.assistente.perguntar_ao_assistente", return_value="Resposta segura")
    def test_enviar_persiste_usuario_e_resposta(self, resposta):
        requisicao = RequisicaoFake()
        requisicao.session[assistente.CHAVE_CONVERSAS] = [12]
        with patch.object(assistente.database, "conversa_existe", return_value=True), \
             patch.object(assistente.database, "carregar_mensagens", return_value=[]), \
             patch.object(assistente.database, "salvar_mensagem") as salvar:
            self.assertEqual(assistente.enviar(requisicao, ContextoTrabalho(7, "Empresa", "2026-05"), 12, "Qual é o saldo?"), 12)
        self.assertEqual(salvar.call_count, 2)
        self.assertEqual(salvar.call_args_list[0].args[1], "user")
        self.assertEqual(salvar.call_args_list[1].args[1], "assistant")
