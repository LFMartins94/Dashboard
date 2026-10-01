import io
import json
import logging
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .logs import FormatadorJson
from .models import TentativaLogin
from .servicos.contexto import CHAVE_CONTEXTO, obter_empresa_ativa


def definir_contexto(cliente, empresa_id=1, nome="Empresa Alfa", competencia="2026-09"):
    sessao = cliente.session
    sessao[CHAVE_CONTEXTO] = {
        "empresa_id": empresa_id,
        "empresa_nome": nome,
        "competencia": competencia,
    }
    sessao.save()


class AutenticacaoTestes(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="contadora",
            password="Senha-Segura-2026",
            first_name="Ana",
        )

    def test_tela_de_acesso_abre_sem_autenticacao(self):
        resposta = self.client.get(reverse("nucleo:login"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Entre no seu espaço de trabalho")
        self.assertContains(resposta, "csrfmiddlewaretoken")

    def test_rota_operacional_sem_login_redireciona(self):
        resposta = self.client.get(reverse("nucleo:trabalho"))

        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("nucleo:login"), resposta.url)

    def test_login_valido_exige_selecao_de_contexto(self):
        resposta = self.client.post(
            reverse("nucleo:login"),
            {"username": "contadora", "password": "Senha-Segura-2026"},
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("nucleo:selecionar_contexto"), resposta.url)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.usuario.pk))
        self.assertNotIn(CHAVE_CONTEXTO, self.client.session)

    def test_credenciais_incorretas_nao_revelam_se_usuario_existe(self):
        existente = self.client.post(
            reverse("nucleo:login"),
            {"username": "contadora", "password": "incorreta"},
            REMOTE_ADDR="10.0.0.1",
        )
        desconhecido = self.client.post(
            reverse("nucleo:login"),
            {"username": "usuario-inexistente", "password": "incorreta"},
            REMOTE_ADDR="10.0.0.2",
        )

        mensagem = "Usuário ou senha incorretos."
        self.assertContains(existente, mensagem)
        self.assertContains(desconhecido, mensagem)
        self.assertNotContains(desconhecido, "não existe")

    @override_settings(LOGIN_TENTATIVAS_LIMITE=3)
    def test_excesso_de_tentativas_bloqueia_novas_validacoes(self):
        dados = {"username": "contadora", "password": "incorreta"}
        for _ in range(3):
            self.client.post(reverse("nucleo:login"), dados, REMOTE_ADDR="10.1.1.1")

        tentativa_apos_limite = TentativaLogin.objects.get()
        self.assertEqual(tentativa_apos_limite.tentativas, 3)
        self.assertIsNotNone(tentativa_apos_limite.bloqueado_ate)

        resposta = self.client.post(
            reverse("nucleo:login"), dados, REMOTE_ADDR="10.1.1.1"
        )

        self.assertContains(resposta, "Muitas tentativas de acesso")
        tentativa = TentativaLogin.objects.get()
        self.assertEqual(len(tentativa.chave_hash), 64)
        self.assertNotIn("contadora", tentativa.chave_hash)

    def test_login_descarta_redirecionamento_externo(self):
        resposta = self.client.post(
            reverse("nucleo:login"),
            {
                "username": "contadora",
                "password": "Senha-Segura-2026",
                "proximo": "https://exemplo-malicioso.invalid/",
            },
        )

        self.assertNotIn("exemplo-malicioso", resposta.url)

    def test_logout_por_post_invalida_sessao_e_contexto(self):
        self.client.force_login(self.usuario)
        definir_contexto(self.client)

        resposta = self.client.post(reverse("nucleo:logout"))

        self.assertRedirects(resposta, reverse("nucleo:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertNotIn(CHAVE_CONTEXTO, self.client.session)

    def test_logout_por_get_e_recusado(self):
        self.client.force_login(self.usuario)

        resposta = self.client.get(reverse("nucleo:logout"))

        self.assertEqual(resposta.status_code, 405)

    def test_cookie_de_sessao_e_http_only_e_samesite(self):
        resposta = self.client.post(
            reverse("nucleo:login"),
            {"username": "contadora", "password": "Senha-Segura-2026"},
        )

        cookie = resposta.cookies["sessionid"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["expires"], "")

    def test_post_sem_csrf_e_recusado_com_pagina_do_sistema(self):
        cliente = Client(enforce_csrf_checks=True)

        resposta = cliente.post(
            reverse("nucleo:login"),
            {"username": "contadora", "password": "Senha-Segura-2026"},
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertContains(resposta, "Esta solicitação expirou", status_code=403)

    def test_login_com_token_csrf_valido_e_aceito(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.get(reverse("nucleo:login"))
        token = cliente.cookies["csrftoken"].value

        resposta = cliente.post(
            reverse("nucleo:login"),
            {
                "username": "contadora",
                "password": "Senha-Segura-2026",
                "csrfmiddlewaretoken": token,
            },
        )

        self.assertEqual(resposta.status_code, 302)


class ContextoTrabalhoTestes(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="contadora", password="Senha-Segura-2026"
        )
        self.client.force_login(self.usuario)

    def test_usuario_sem_contexto_e_redirecionado_para_selecao(self):
        resposta = self.client.get(reverse("nucleo:entradas"))

        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("nucleo:selecionar_contexto"), resposta.url)

    @mock.patch("nucleo.views.obter_empresa_ativa")
    @mock.patch("nucleo.views.listar_empresas_ativas")
    def test_selecao_valida_fica_na_sessao(self, listar, obter):
        listar.return_value = [{"id": 7, "nome": "Empresa Sete"}]
        obter.return_value = {"id": 7, "nome": "Empresa Sete"}

        resposta = self.client.post(
            reverse("nucleo:selecionar_contexto"),
            {"empresa": "7", "competencia": "2026-09", "proximo": "/"},
        )

        self.assertRedirects(resposta, reverse("nucleo:trabalho"))
        self.assertEqual(self.client.session[CHAVE_CONTEXTO]["empresa_id"], 7)
        self.assertEqual(self.client.session[CHAVE_CONTEXTO]["competencia"], "2026-09")
        obter.assert_called_once_with(7)

    def test_contextos_de_duas_sessoes_nao_se_misturam(self):
        outro_cliente = Client()
        outro_cliente.force_login(self.usuario)
        definir_contexto(self.client, 1, "Empresa Um", "2026-08")
        definir_contexto(outro_cliente, 2, "Empresa Dois", "2026-09")

        primeira = self.client.get(reverse("nucleo:trabalho"))
        segunda = outro_cliente.get(reverse("nucleo:trabalho"))

        self.assertContains(primeira, "Empresa Um")
        self.assertNotContains(primeira, "Empresa Dois")
        self.assertContains(segunda, "Empresa Dois")
        self.assertNotContains(segunda, "Empresa Um")

    def test_rota_direta_funciona_quando_contexto_existe(self):
        definir_contexto(self.client)

        resposta = self.client.get(reverse("nucleo:entradas"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Recebimento, leitura e preparação")

    @mock.patch("nucleo.servicos.contexto.connection.cursor")
    def test_validacao_de_empresa_usa_parametro_no_servidor(self, cursor):
        gerenciador = cursor.return_value.__enter__.return_value
        gerenciador.fetchone.return_value = (12, "Empresa Doze")

        empresa = obter_empresa_ativa(12)

        self.assertEqual(empresa, {"id": 12, "nome": "Empresa Doze"})
        sql, parametros = gerenciador.execute.call_args.args
        self.assertIn("id = %s", sql)
        self.assertEqual(parametros, [12])


class ComandoUsuarioInicialTestes(TestCase):
    @override_settings(AUTH_PASSWORD_VALIDATORS=[])
    def test_comando_cria_superusuario_sem_expor_senha(self):
        saida = io.StringIO()
        with mock.patch.dict(
            os.environ, {"DJANGO_ADMIN_PASSWORD": "Senha-Temporaria-2026"}
        ):
            call_command(
                "criar_usuario_inicial",
                usuario="administradora",
                nome="Ana",
                nao_interativo=True,
                stdout=saida,
            )

        usuario = get_user_model().objects.get(username="administradora")
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.check_password("Senha-Temporaria-2026"))
        self.assertNotIn("Senha-Temporaria-2026", saida.getvalue())

    def test_modo_nao_interativo_exige_senha_temporaria(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CommandError):
                call_command(
                    "criar_usuario_inicial",
                    usuario="administradora",
                    nao_interativo=True,
                )


class RotasErrosEDiagnosticoTestes(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="contadora", password="Senha-Segura-2026"
        )

    def test_rota_inexistente_usa_erro_do_sistema(self):
        self.client.force_login(self.usuario)
        definir_contexto(self.client)

        resposta = self.client.get("/rota-que-nao-existe/")

        self.assertEqual(resposta.status_code, 404)
        self.assertContains(resposta, "Página não encontrada", status_code=404)
        self.assertContains(resposta, "Referência:", status_code=404)

    def test_erro_anonimo_nao_exibe_dados_da_area_interna(self):
        resposta = self.client.get("/rota-publica-inexistente/")

        self.assertEqual(resposta.status_code, 404)
        self.assertNotContains(resposta, "Acesso contábil", status_code=404)
        self.assertNotContains(resposta, "sair/", status_code=404)

    def test_diagnostico_da_aplicacao_e_publico(self):
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
        self.assertEqual(resposta.json()["aplicacao"], "disponivel")
        self.assertEqual(resposta.json()["banco"], "indisponivel")
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
