from decimal import Decimal
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from contaview.logic import assistente as logica_assistente

from .models import CompetenciaTrabalho, ItemChecklistTrabalho, RegistroConsultaAssistente, TarefaAutomacao
from .servicos import assistente
from .servicos.contexto import ContextoTrabalho


class Sessao(dict):
    modified = False


class RequisicaoFake:
    def __init__(self, usuario=None):
        self.session = Sessao()
        self.user = usuario


class AssistenteServicoTest(SimpleTestCase):
    contexto = ContextoTrabalho(7, "Empresa", "2026-05")

    def test_conversa_fica_limitada_a_sessao(self):
        requisicao = RequisicaoFake()
        with patch.object(assistente.database, "criar_conversa", return_value=12):
            self.assertEqual(assistente.nova_conversa(requisicao), 12)
        with patch.object(assistente.database, "carregar_mensagens", return_value=[]):
            self.assertEqual(assistente.obter_mensagens(requisicao, 12), [])
            with self.assertRaises(assistente.ErroAssistente):
                assistente.obter_mensagens(requisicao, 99)

    @patch("contaview.logic.assistente.perguntar_ao_assistente", return_value="Resposta segura")
    def test_enviar_persiste_usuario_e_resposta_com_contexto_agregado(self, resposta):
        requisicao = RequisicaoFake()
        requisicao.session[assistente.CHAVE_CONVERSAS] = [12]
        resumo = {"dados_ia": {"fontes": {"lancamentos_aprovados": {"quantidade": 2}}}, "fontes": [], "ha_dados_contabeis": True}
        with patch.object(assistente, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(assistente, "consultar_resumo_autorizado", return_value=resumo), \
             patch.object(assistente.database, "conversa_existe", return_value=True), \
             patch.object(assistente.database, "carregar_mensagens", return_value=[]), \
             patch.object(assistente.database, "salvar_mensagem") as salvar:
            self.assertEqual(assistente.enviar(requisicao, self.contexto, 12, "Qual é o saldo?"), 12)
        self.assertEqual(salvar.call_count, 2)
        self.assertEqual(salvar.call_args_list[0].args[1], "user")
        self.assertEqual(salvar.call_args_list[1].args[1], "assistant")
        self.assertEqual(resposta.call_args.kwargs["dados_consulta"], resumo["dados_ia"])

    @patch("contaview.logic.assistente.perguntar_ao_assistente")
    def test_consulta_sem_dados_nao_chama_modelo_nem_inventa_valor(self, perguntar):
        requisicao = RequisicaoFake()
        requisicao.session[assistente.CHAVE_CONVERSAS] = [12]
        resumo = {"dados_ia": {"fontes": {}}, "fontes": [], "ha_dados_contabeis": False}
        with patch.object(assistente, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(assistente, "consultar_resumo_autorizado", return_value=resumo), \
             patch.object(assistente.database, "conversa_existe", return_value=True), \
             patch.object(assistente.database, "carregar_mensagens", return_value=[]), \
             patch.object(assistente.database, "salvar_mensagem") as salvar:
            assistente.enviar(requisicao, self.contexto, 12, "Qual é o saldo da competência?")
        perguntar.assert_not_called()
        self.assertIn("Não há lançamentos", salvar.call_args_list[1].args[2])

    def test_sanitizacao_oculta_documentos_e_terceiro(self):
        texto = logica_assistente.sanitizar_texto_assistente(
            "Fornecedor Ana Silva informou CPF 123.456.789-09 e e-mail ana@exemplo.com. Ana Silva aguarda retorno."
        )
        self.assertNotIn("Ana Silva", texto)
        self.assertNotIn("123.456.789-09", texto)
        self.assertNotIn("ana@exemplo.com", texto)


class AssistenteConsultaTest(TestCase):
    contexto = ContextoTrabalho(7, "Empresa", "2026-05")

    def setUp(self):
        self.usuario = get_user_model().objects.create_user("contadora", password="senha-segura")
        self.competencia = CompetenciaTrabalho.objects.create(empresa_id=7, competencia="2026-05")
        ItemChecklistTrabalho.objects.create(
            competencia_trabalho=self.competencia,
            titulo="Conferir extrato",
            categoria="conferencia",
            rota_destino="nucleo:conferencia",
        )
        TarefaAutomacao.objects.create(
            empresa_id=7,
            competencia="2026-05",
            tipo="verificar_pendencias",
            estado="concluida",
        )

    def test_resumo_usa_apenas_agregados_e_fontes(self):
        lancamentos = pd.DataFrame([
            {"tipo": "D", "valor": Decimal("100.00"), "historico": "Fornecedor Ana Silva", "cnpj": "12.345.678/0001-90"},
            {"tipo": "C", "valor": Decimal("160.00"), "historico": "Receita", "cnpj": "12.345.678/0001-90"},
        ])
        conciliacoes = pd.DataFrame([{"pares_ok": 1, "pares_com_erro": 0, "status": "concluido"}])
        ocorrencias = pd.DataFrame([{"severidade": "alta"}])
        with patch.object(assistente, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(assistente.database, "carregar_lancamentos", return_value=lancamentos), \
             patch.object(assistente.database, "carregar_conciliacao", return_value=conciliacoes), \
             patch.object(assistente.database, "carregar_ocorrencias", return_value=ocorrencias):
            resumo = assistente.consultar_resumo_autorizado(self.contexto)
        conteudo = repr(resumo["dados_ia"])
        self.assertTrue(resumo["ha_dados_contabeis"])
        self.assertIn("R$ 160,00", conteudo)
        self.assertIn("R$ 60,00", conteudo)
        self.assertNotIn("Ana Silva", conteudo)
        self.assertNotIn("12.345.678/0001-90", conteudo)
        self.assertGreaterEqual(len(resumo["fontes"]), 4)

    @patch("contaview.logic.assistente.perguntar_ao_assistente", return_value="O saldo é R$ 60,00.")
    def test_registro_persiste_pergunta_filtros_resposta_e_fontes(self, perguntar):
        requisicao = RequisicaoFake(self.usuario)
        requisicao.session[assistente.CHAVE_CONVERSAS] = [12]
        resumo = {
            "dados_ia": {"fontes": {"lancamentos_aprovados": {"quantidade": 2}}},
            "fontes": [{"nome": "Lançamentos aprovados", "descricao": "2 lançamento(s)."}],
            "ha_dados_contabeis": True,
        }
        with patch.object(assistente, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(assistente, "consultar_resumo_autorizado", return_value=resumo), \
             patch.object(assistente.database, "conversa_existe", return_value=True), \
             patch.object(assistente.database, "carregar_mensagens", return_value=[]), \
             patch.object(assistente.database, "salvar_mensagem"):
            assistente.enviar(requisicao, self.contexto, 12, "Qual é o saldo?")
        registro = RegistroConsultaAssistente.objects.get()
        self.assertEqual(registro.usuario, self.usuario)
        self.assertEqual(registro.filtros, {"empresa_id": 7, "competencia": "2026-05"})
        self.assertEqual(registro.resposta, "O saldo é R$ 60,00.")
        self.assertEqual(registro.fontes, resumo["fontes"])

    def test_fontes_sao_associadas_a_resposta_persistida(self):
        RegistroConsultaAssistente.objects.create(
            usuario=self.usuario,
            conversa_id=12,
            empresa_id=7,
            competencia="2026-05",
            pergunta="Qual é o saldo?",
            resposta="O saldo é R$ 60,00.",
            fontes=[{"nome": "Lançamentos aprovados", "descricao": "2 lançamento(s)."}],
        )
        requisicao = RequisicaoFake(self.usuario)
        requisicao.session[assistente.CHAVE_CONVERSAS] = [12]
        with patch.object(assistente.database, "carregar_mensagens", return_value=[
            {"role": "user", "content": "Qual é o saldo?"},
            {"role": "assistant", "content": "O saldo é R$ 60,00."},
        ]):
            mensagens = assistente.obter_mensagens(requisicao, 12)
        self.assertEqual(mensagens[1]["fontes"][0]["nome"], "Lançamentos aprovados")
