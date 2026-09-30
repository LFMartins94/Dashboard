import json
import logging
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .logs import FormatadorJson


class RotasBasicasTestes(TestCase):
    def test_tela_inicial_abre(self):
        resposta = self.client.get(reverse("nucleo:trabalho"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Uma rotina contábil mais clara.")
        self.assertContains(resposta, "Modo escuro")

    def test_modulo_abre_em_acesso_direto(self):
        resposta = self.client.get(reverse("nucleo:entradas"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Recebimento, leitura e preparação")

    def test_rota_inexistente_usa_erro_do_sistema(self):
        resposta = self.client.get("/rota-que-nao-existe/")

        self.assertEqual(resposta.status_code, 404)
        self.assertContains(resposta, "Página não encontrada", status_code=404)
        self.assertContains(resposta, "Referência:", status_code=404)

    def test_segredo_de_sessao_nao_aparece_no_html(self):
        from django.conf import settings

        resposta = self.client.get(reverse("nucleo:trabalho"))

        self.assertNotContains(resposta, settings.SECRET_KEY)

    def test_identificador_recebido_volta_no_cabecalho(self):
        resposta = self.client.get(
            reverse("nucleo:trabalho"), headers={"X-Request-ID": "teste-123"}
        )

        self.assertEqual(resposta.headers["X-Request-ID"], "teste-123")

    def test_identificador_invalido_e_substituido(self):
        resposta = self.client.get(
            reverse("nucleo:trabalho"), headers={"X-Request-ID": "valor inválido"}
        )

        self.assertNotEqual(resposta.headers["X-Request-ID"], "valor inválido")


class DiagnosticoTestes(TestCase):
    def test_diagnostico_da_aplicacao_independe_do_banco(self):
        resposta = self.client.get(reverse("nucleo:saude_aplicacao"))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["aplicacao"], "disponivel")

    def test_diagnostico_indica_banco_disponivel(self):
        resposta = self.client.get(reverse("nucleo:saude"))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["banco"], "disponivel")

    @mock.patch("nucleo.views.connection.cursor")
    def test_diagnostico_diferencia_banco_indisponivel(self, cursor):
        cursor.side_effect = RuntimeError("falha simulada")

        resposta = self.client.get(reverse("nucleo:saude"))

        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(
            resposta.json(),
            {
                "status": "degradado",
                "aplicacao": "disponivel",
                "banco": "indisponivel",
            },
        )
        self.assertNotContains(resposta, "falha simulada", status_code=503)


class LogsTestes(SimpleTestCase):
    def test_formatador_gera_json_com_identificador(self):
        registro = logging.LogRecord(
            name="contaview.teste",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Teste concluído",
            args=(),
            exc_info=None,
        )
        registro.requisicao_id = "req-456"

        conteudo = json.loads(FormatadorJson().format(registro))

        self.assertEqual(conteudo["requisicao_id"], "req-456")
        self.assertEqual(conteudo["mensagem"], "Teste concluído")
