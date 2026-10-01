from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import DecisaoConciliacao, RevisaoConciliacao
from .servicos import conciliacao
from .servicos.contexto import ContextoTrabalho


class ConciliacaoServicoTest(TestCase):
    contexto = ContextoTrabalho(7, "Empresa teste", "2026-05")

    def setUp(self):
        self.usuario = get_user_model().objects.create_user("contadora", password="senha-segura")
        self.lotes = [
            {"id": 10, "nome_arquivo": "extrato.xlsx", "tipo_documento": "extrato", "periodo": "2026-05", "total_linhas": 1, "status": "concluido"},
            {"id": 11, "nome_arquivo": "referencia.xlsx", "tipo_documento": "lancamentos", "periodo": "2026-05", "total_linhas": 1, "status": "concluido"},
        ]
        self.extrato = [{"id": 101, "numero_linha": 2, "data": date(2026, 5, 5), "descricao": "Pagamento fornecedor", "valor": Decimal("100.00"), "tipo": "D", "conta_contabil": "1.1", "status": "validado"}]
        self.referencia = [{"id": 201, "numero_linha": 3, "data": date(2026, 5, 5), "descricao": "Pagamento fornecedor", "valor": Decimal("100.00"), "tipo": "D", "conta_contabil": "1.1", "status": "validado"}]

    def _mocks(self):
        return (
            patch.object(conciliacao, "obter_empresa_ativa", return_value={"id": 7}),
            patch.object(conciliacao.database, "listar_lotes_preparacao", return_value=self.lotes),
            patch.object(conciliacao.database, "carregar_linhas_para_exportacao", side_effect=[self.extrato, self.referencia, self.extrato, self.referencia]),
            patch.object(conciliacao.database, "inserir_conciliacao"),
        )

    def test_execucao_confirma_par_exato_e_grava_resumo(self):
        empresa, lotes, linhas, resumo = self._mocks()
        with empresa, lotes, linhas, resumo as resumo_mock:
            dados = conciliacao.executar(self.contexto, 10, 11)
        self.assertEqual(len(dados["resultado"]["pares_confirmados"]), 1)
        resumo_mock.assert_called_once()

    def test_decisao_persiste_apenas_candidato_atual(self):
        self.referencia[0]["data"] = date(2026, 5, 6)
        empresa, lotes, linhas, resumo = self._mocks()
        with empresa, lotes, linhas, resumo:
            dados = conciliacao.decidir(
                self.contexto, self.usuario, 10, 11, 101, 201,
                DecisaoConciliacao.CONFIRMADA, "Conferido com comprovante.",
            )
        self.assertEqual(RevisaoConciliacao.objects.count(), 1)
        self.assertEqual(dados["resultado"]["revisoes_confirmadas"], 1)

    def test_extrato_pode_ser_comparado_a_lancamentos_aprovados(self):
        empresa, lotes, linhas, resumo = self._mocks()
        with empresa, lotes, linhas, resumo, patch.object(
            conciliacao.database, "carregar_lancamentos"
        ) as lancamentos:
            lancamentos.return_value.to_dict.return_value = [{
                "id": 201, "sequencial_lote": 3, "data": date(2026, 5, 5),
                "historico": "Pagamento fornecedor", "valor": Decimal("100.00"),
                "tipo": "D", "conta_contabil": "1.1",
            }]
            dados = conciliacao.executar(self.contexto, 10, 0)
        self.assertEqual(len(dados["resultado"]["pares_confirmados"]), 1)
