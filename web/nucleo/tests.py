import io
import json
import logging
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import (
    Client,
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.urls import reverse

from .logs import FormatadorJson
from .models import (
    CategoriaChecklist,
    CompetenciaTrabalho,
    EstadoOperacional,
    ItemChecklistTrabalho,
    TentativaLogin,
)
from .servicos.contexto import CHAVE_CONTEXTO, ContextoTrabalho, obter_empresa_ativa
from .servicos.trabalho import (
    MetricasTrabalho,
    PainelTrabalho,
    _consultar_metricas_existentes,
    _listar_lotes_pendentes,
    atualizar_item_checklist,
    iniciar_competencia,
    montar_painel_trabalho,
)


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

        self.assertRedirects(
            resposta, reverse("nucleo:trabalho"), fetch_redirect_response=False
        )
        self.assertEqual(self.client.session[CHAVE_CONTEXTO]["empresa_id"], 7)
        self.assertEqual(self.client.session[CHAVE_CONTEXTO]["competencia"], "2026-09")
        obter.assert_called_once_with(7)

    def test_contextos_de_duas_sessoes_nao_se_misturam(self):
        outro_cliente = Client()
        outro_cliente.force_login(self.usuario)
        definir_contexto(self.client, 1, "Empresa Um", "2026-08")
        definir_contexto(outro_cliente, 2, "Empresa Dois", "2026-09")

        with mock.patch(
            "nucleo.views.montar_painel_trabalho", return_value=PainelTrabalho()
        ):
            primeira = self.client.get(reverse("nucleo:trabalho"))
            segunda = outro_cliente.get(reverse("nucleo:trabalho"))

        self.assertContains(primeira, "Empresa Um")
        self.assertNotContains(primeira, "Empresa Dois")
        self.assertContains(segunda, "Empresa Dois")
        self.assertNotContains(segunda, "Empresa Um")

    @mock.patch("nucleo.views.listar_lotes_contexto", return_value=[])
    def test_rota_direta_funciona_quando_contexto_existe(self, _listar):
        definir_contexto(self.client)

        resposta = self.client.get(reverse("nucleo:entradas"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Receba primeiro. Decida o destino depois.")

    @mock.patch("nucleo.servicos.contexto.connection.cursor")
    def test_validacao_de_empresa_usa_parametro_no_servidor(self, cursor):
        gerenciador = cursor.return_value.__enter__.return_value
        gerenciador.fetchone.return_value = (12, "Empresa Doze")

        empresa = obter_empresa_ativa(12)

        self.assertEqual(empresa, {"id": 12, "nome": "Empresa Doze"})
        sql, parametros = gerenciador.execute.call_args.args
        self.assertIn("id = %s", sql)
        self.assertEqual(parametros, [12])


class TrabalhoOperacionalTestes(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="contadora-trabalho", password="Senha-Segura-2026"
        )
        self.contexto = ContextoTrabalho(7, "Empresa Sete", "2026-09")
        self.client.force_login(self.usuario)
        definir_contexto(self.client, 7, "Empresa Sete", "2026-09")

    def _iniciar(self, contexto=None):
        with mock.patch(
            "nucleo.servicos.trabalho.obter_empresa_ativa",
            return_value={"id": (contexto or self.contexto).empresa_id, "nome": "Empresa"},
        ):
            return iniciar_competencia(contexto or self.contexto, self.usuario)

    def test_inicio_cria_checklist_recorrente_sem_duplicar(self):
        primeira = self._iniciar()
        segunda = self._iniciar()

        self.assertEqual(primeira.pk, segunda.pk)
        self.assertEqual(CompetenciaTrabalho.objects.count(), 1)
        self.assertEqual(ItemChecklistTrabalho.objects.count(), 4)
        self.assertSetEqual(
            set(ItemChecklistTrabalho.objects.values_list("categoria", flat=True)),
            set(CategoriaChecklist.values),
        )

    def test_banco_recusa_competencia_fora_do_padrao(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CompetenciaTrabalho.objects.create(
                    empresa_id=7,
                    competencia="2026-13",
                    iniciado_por=self.usuario,
                )

    @mock.patch(
        "nucleo.servicos.trabalho.listar_empresas_ativas",
        return_value=[
            {"id": 7, "nome": "Empresa Sete"},
            {"id": 8, "nome": "Empresa Oito"},
        ],
    )
    @mock.patch("nucleo.servicos.trabalho._listar_lotes_pendentes", return_value=[])
    @mock.patch(
        "nucleo.servicos.trabalho._consultar_metricas_existentes",
        return_value=(3, 1, 5, 2),
    )
    def test_painel_reune_metricas_e_isola_contexto(self, metricas, lotes, empresas):
        competencia = self._iniciar()
        outro_contexto = ContextoTrabalho(8, "Empresa Oito", "2026-09")
        outra = self._iniciar(outro_contexto)
        outra.itens.update(estado=EstadoOperacional.ENTREGUE)

        painel = montar_painel_trabalho(self.contexto)

        self.assertEqual(painel.competencia.pk, competencia.pk)
        self.assertTrue(all(item.competencia_trabalho_id == competencia.pk for item in painel.itens))
        self.assertEqual(painel.metricas.arquivos_recebidos, 3)
        self.assertEqual(painel.metricas.linhas_pendentes, 5)
        self.assertEqual(painel.metricas.divergencias, 2)
        self.assertEqual(painel.proxima_acao.titulo, "Revisar o lote pendente")
        self.assertTrue(painel.competencias_abertas[0]["selecionada"])

    def test_item_de_outro_contexto_nao_pode_ser_atualizado(self):
        self._iniciar()
        outro_contexto = ContextoTrabalho(8, "Empresa Oito", "2026-09")
        outra = self._iniciar(outro_contexto)
        item_alheio = outra.itens.first()

        with self.assertRaisesMessage(ValueError, "contexto selecionado"):
            atualizar_item_checklist(
                self.contexto,
                item_alheio.pk,
                EstadoOperacional.RECEBIDO,
                self.usuario,
            )

        item_alheio.refresh_from_db()
        self.assertEqual(item_alheio.estado, EstadoOperacional.AGUARDANDO)

    def test_estado_da_competencia_e_recalculado_a_partir_do_checklist(self):
        competencia = self._iniciar()
        itens = list(competencia.itens.order_by("id"))

        for item in itens:
            atualizar_item_checklist(
                self.contexto, item.pk, EstadoOperacional.REVISADO, self.usuario
            )
        competencia.refresh_from_db()
        self.assertEqual(competencia.estado, EstadoOperacional.REVISADO)

        for item in itens:
            atualizar_item_checklist(
                self.contexto, item.pk, EstadoOperacional.ENTREGUE, self.usuario
            )
        competencia.refresh_from_db()
        self.assertEqual(competencia.estado, EstadoOperacional.ENTREGUE)

    @mock.patch(
        "nucleo.servicos.trabalho.listar_empresas_ativas",
        return_value=[{"id": 7, "nome": "Empresa Sete"}],
    )
    @mock.patch("nucleo.servicos.trabalho._listar_lotes_pendentes", return_value=[])
    @mock.patch(
        "nucleo.servicos.trabalho._consultar_metricas_existentes",
        return_value=(2, 0, 0, 0),
    )
    def test_tela_exibe_fila_e_acoes_diretas(self, metricas, lotes, empresas):
        self._iniciar()

        resposta = self.client.get(reverse("nucleo:trabalho"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Checklist da competência")
        self.assertContains(resposta, "Receber documentos da competência")
        self.assertContains(resposta, "Próxima ação")
        self.assertContains(resposta, reverse("nucleo:entradas"))
        self.assertContains(resposta, "2")

    @mock.patch("nucleo.views.montar_painel_trabalho")
    def test_falha_de_banco_nao_expoe_erro_nem_oferece_gravacao(self, montar):
        montar.side_effect = DatabaseError("detalhe interno sensível")

        resposta = self.client.get(reverse("nucleo:trabalho"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Fila indisponível")
        self.assertNotContains(resposta, "detalhe interno sensível")
        self.assertNotContains(resposta, "Iniciar competência")

    @mock.patch(
        "nucleo.servicos.trabalho.obter_empresa_ativa",
        return_value={"id": 7, "nome": "Empresa Sete"},
    )
    def test_endpoint_de_inicio_e_idempotente(self, empresa):
        for _ in range(2):
            resposta = self.client.post(reverse("nucleo:iniciar_trabalho"))
            self.assertRedirects(resposta, reverse("nucleo:trabalho"), fetch_redirect_response=False)

        self.assertEqual(CompetenciaTrabalho.objects.count(), 1)
        self.assertEqual(ItemChecklistTrabalho.objects.count(), 4)

    def test_endpoints_de_escrita_recusam_get(self):
        for rota in (
            "nucleo:iniciar_trabalho",
            "nucleo:atualizar_item_trabalho",
            "nucleo:alternar_competencia_trabalho",
        ):
            self.assertEqual(self.client.get(reverse(rota)).status_code, 405)

    @mock.patch(
        "nucleo.views.obter_competencia_para_alternar"
    )
    def test_alternancia_revalida_competencia_no_servidor(self, obter):
        competencia = CompetenciaTrabalho.objects.create(
            empresa_id=8,
            competencia="2026-10",
            iniciado_por=self.usuario,
        )
        obter.return_value = (competencia, {"id": 8, "nome": "Empresa Oito"})

        resposta = self.client.post(
            reverse("nucleo:alternar_competencia_trabalho"),
            {"competencia_id": competencia.pk},
        )

        self.assertRedirects(resposta, reverse("nucleo:trabalho"), fetch_redirect_response=False)
        obter.assert_called_once_with(competencia.pk)
        self.assertEqual(self.client.session[CHAVE_CONTEXTO]["empresa_id"], 8)
        self.assertEqual(self.client.session[CHAVE_CONTEXTO]["competencia"], "2026-10")


class ConsultasTrabalhoLegadoTestes(TransactionTestCase):
    """Exercita as consultas da fila contra o formato real das tabelas legadas."""

    tabelas = (
        "linhas_preparadas",
        "lotes_importacao",
        "ocorrencias_auditoria",
        "conciliacoes",
        "lancamentos",
    )

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE lotes_importacao (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER, periodo VARCHAR(7),
                    status VARCHAR(20), nome_arquivo VARCHAR(255),
                    total_linhas INTEGER, criado_em DATETIME
                )"""
            )
            cursor.execute(
                """CREATE TABLE linhas_preparadas (
                    id INTEGER PRIMARY KEY, lote_id INTEGER, empresa_id INTEGER,
                    status VARCHAR(20)
                )"""
            )
            cursor.execute(
                """CREATE TABLE conciliacoes (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER, periodo VARCHAR(7),
                    pares_com_erro INTEGER, executado_em DATETIME
                )"""
            )
            cursor.execute(
                """CREATE TABLE lancamentos (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER, periodo VARCHAR(7)
                )"""
            )
            cursor.execute(
                """CREATE TABLE ocorrencias_auditoria (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER,
                    lancamento_id INTEGER, resolvida BOOLEAN
                )"""
            )
            cursor.executemany(
                "INSERT INTO lotes_importacao VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    (1, 7, "2026-09", "em_revisao", "extrato.xlsx", 3, "2026-09-10"),
                    (2, 7, "2026-09", "concluido", "folha.xlsx", 8, "2026-09-11"),
                    (3, 7, "2026-09", "cancelado", "repetido.xlsx", 3, "2026-09-12"),
                    (4, 8, "2026-09", "em_revisao", "outra.xlsx", 9, "2026-09-13"),
                ],
            )
            cursor.executemany(
                "INSERT INTO linhas_preparadas VALUES (%s, %s, %s, %s)",
                [(1, 1, 7, "pendente"), (2, 1, 7, "pendente"), (3, 1, 7, "validado")],
            )
            cursor.executemany(
                "INSERT INTO conciliacoes VALUES (%s, %s, %s, %s, %s)",
                [
                    (1, 7, "2026-09", 6, "2026-09-12"),
                    (2, 7, "2026-09", 3, "2026-09-13"),
                    (3, 8, "2026-09", 9, "2026-09-14"),
                ],
            )
            cursor.executemany(
                "INSERT INTO lancamentos VALUES (%s, %s, %s)",
                [(11, 7, "2026-09"), (12, 7, "2026-08"), (13, 8, "2026-09")],
            )
            cursor.executemany(
                "INSERT INTO ocorrencias_auditoria VALUES (%s, %s, %s, %s)",
                [(21, 7, 11, False), (22, 7, 11, True), (23, 7, 12, False), (24, 8, 13, False)],
            )

    def tearDown(self):
        with connection.cursor() as cursor:
            for tabela in self.tabelas:
                cursor.execute(f'DROP TABLE IF EXISTS "{tabela}"')

    def test_metricas_e_alertas_respeitam_empresa_e_competencia(self):
        contexto = ContextoTrabalho(7, "Empresa Sete", "2026-09")

        metricas = _consultar_metricas_existentes(contexto)
        alertas = _listar_lotes_pendentes(contexto)

        self.assertEqual(metricas, (2, 1, 2, 4))
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0].titulo, "extrato.xlsx")
        self.assertIn("lote=1", alertas[0].url)
        self.assertIn("2 de 3 linhas", alertas[0].descricao)


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
