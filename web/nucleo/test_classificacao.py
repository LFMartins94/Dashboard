from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import HistoricoRegraClassificacao, RegraClassificacaoContabil
from .servicos.classificacao import (
    ErroClassificacao,
    definir_situacao,
    registrar_amostra,
    salvar_regra,
    sugerir_para_linha,
)
from .servicos.contexto import CHAVE_CONTEXTO, ContextoTrabalho


class ClassificacaoContabilTestes(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="contadora-classificacao", password="Senha-Segura-2026"
        )
        self.contexto = ContextoTrabalho(7, "Empresa Sete", "2026-05")

    def criar_regra(self, **sobrescritos):
        dados = {
            "nome": "Tarifas bancarias",
            "conta_bancaria": "1234",
            "criterios": {"descricao_contem": "tarifa", "tipo": "D"},
            "prioridade": 100,
            "conta_contabil_sugerida": "310101001",
            "historico_sugerido": "Tarifa bancaria",
        }
        dados.update(sobrescritos)
        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7}):
            return salvar_regra(self.contexto, self.usuario, **dados)

    def test_regra_confirmada_sugere_sem_alterar_linha(self):
        regra = self.criar_regra()

        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7}):
            resultado = sugerir_para_linha(
                self.contexto,
                {"descricao": "Tarifa mensal da conta", "tipo": "D", "valor": "45,10", "data": "03/05/2026"},
                conta_bancaria="1234",
            )

        self.assertEqual(resultado.situacao, "sugerida")
        self.assertEqual(resultado.origem, "regra_confirmada")
        self.assertEqual(resultado.regra_id, regra.id)
        self.assertEqual(resultado.conta_contabil, "310101001")
        regra.refresh_from_db()
        self.assertEqual(regra.vezes_utilizada, 0)
        self.assertEqual(HistoricoRegraClassificacao.objects.count(), 1)

    def test_pix_sozinho_e_recusado(self):
        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7}):
            with self.assertRaisesRegex(ErroClassificacao, "apenas em PIX"):
                salvar_regra(
                    self.contexto,
                    self.usuario,
                    nome="PIX amplo",
                    criterios={"descricao_contem": "PIX"},
                    conta_contabil_sugerida="1101",
                )

    def test_conflito_nao_escolhe_regra_por_conta_propria(self):
        self.criar_regra(
            nome="Pagamento fornecedor",
            conta_bancaria="",
            criterios={"descricao_contem": "pagamento"},
        )
        self.criar_regra(
            nome="Fornecedor hotel",
            conta_bancaria="",
            criterios={"favorecido_contem": "hotel"},
            conta_contabil_sugerida="2101",
        )

        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7}):
            resultado = sugerir_para_linha(
                self.contexto,
                {"descricao": "Pagamento mensal", "favorecido": "Hotel Privé", "valor": "100.00"},
                referencia=date(2026, 5, 10),
            )

        self.assertEqual(resultado.situacao, "conflito")
        self.assertEqual(len(resultado.candidatos), 2)

    def test_regra_em_revisao_nao_e_sugerida(self):
        regra = self.criar_regra()
        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7}):
            definir_situacao(self.contexto, self.usuario, regra.id, "em_revisao")
            resultado = sugerir_para_linha(
                self.contexto,
                {"descricao": "Tarifa mensal", "tipo": "D", "valor": "12,00"},
                conta_bancaria="1234",
                referencia=date(2026, 5, 10),
            )

        self.assertEqual(resultado.situacao, "sem_regra")
        regra.refresh_from_db()
        self.assertEqual(regra.situacao, "em_revisao")


    def test_edicao_nao_reativa_regra_desativada(self):
        regra = self.criar_regra()
        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7}):
            definir_situacao(self.contexto, self.usuario, regra.id, "desativada")
            salvar_regra(
                self.contexto,
                self.usuario,
                regra_id=regra.id,
                nome="Tarifa revisada",
                conta_bancaria="1234",
                criterios={"descricao_contem": "tarifa", "tipo": "D"},
                prioridade=100,
                conta_contabil_sugerida="310101001",
                historico_sugerido="Tarifa bancária revisada",
            )

        regra.refresh_from_db()
        self.assertEqual(regra.situacao, "desativada")
        self.assertEqual(regra.nome, "Tarifa revisada")


    def test_situacao_e_amostragem_ficam_rastreaveis(self):
        regra = self.criar_regra()
        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7}):
            definir_situacao(self.contexto, self.usuario, regra.id, "desativada")
            registrar_amostra(self.contexto, regra.id, houve_erro=True)

        regra.refresh_from_db()
        self.assertEqual(regra.situacao, "desativada")
        self.assertEqual(regra.amostras_conferidas, 1)
        self.assertEqual(regra.erros_amostragem, 1)
        self.assertEqual(regra.vezes_utilizada, 1)
        self.assertEqual(HistoricoRegraClassificacao.objects.count(), 2)

    def test_regra_de_outra_empresa_nao_pode_ser_alterada(self):
        regra = self.criar_regra()
        outro = ContextoTrabalho(8, "Empresa Oito", "2026-05")
        with patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 8}):
            with self.assertRaisesRegex(ErroClassificacao, "não pertence"):
                definir_situacao(outro, self.usuario, regra.id, "desativada")


class ClassificacoesNavegadorTestes(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="contadora-tela-classificacao", password="Senha-Segura-2026"
        )
        self.client.force_login(self.usuario)
        sessao = self.client.session
        sessao[CHAVE_CONTEXTO] = {
            "empresa_id": 7,
            "empresa_nome": "Empresa Sete",
            "competencia": "2026-05",
        }
        sessao.save()

    @patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7})
    def test_tela_cria_regra_e_exibe_controles(self, _empresa):
        resposta = self.client.post(reverse("nucleo:classificacoes"), {
            "acao": "salvar",
            "nome": "Tarifa confirmada",
            "prioridade": "50",
            "descricao_contem": "tarifa",
            "tipo": "D",
            "conta_contabil_sugerida": "310101001",
            "historico_sugerido": "Tarifa bancaria",
        }, follow=True)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Tarifa confirmada")
        self.assertContains(resposta, "Desativar")
        self.assertEqual(RegraClassificacaoContabil.objects.count(), 1)

    @patch("nucleo.servicos.classificacao.obter_empresa_ativa", return_value={"id": 7})
    def test_tela_recusa_regra_pix_generica(self, _empresa):
        resposta = self.client.post(reverse("nucleo:classificacoes"), {
            "acao": "salvar",
            "nome": "PIX generico",
            "prioridade": "100",
            "descricao_contem": "PIX",
            "conta_contabil_sugerida": "110101001",
        }, follow=True)

        self.assertContains(resposta, "apenas em PIX")
        self.assertEqual(RegraClassificacaoContabil.objects.count(), 0)
