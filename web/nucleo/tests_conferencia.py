from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from .servicos.contexto import ContextoTrabalho
from .servicos import conferencia


class ConferenciaServicoTest(SimpleTestCase):
    contexto = ContextoTrabalho(7, "Empresa teste", "2026-05")

    def dados(self, status="em_revisao"):
        return {
            "lotes": [{"id": 10, "total_linhas": 1, "status": status}],
            "lote": {"id": 10, "empresa_id": 7, "periodo": "2026-05", "status": status, "tipo_documento": "lancamentos"},
            "linhas": [{"id": 101, "data": date(2026, 5, 2), "descricao": "Recebimento", "valor": 100, "tipo": "C", "conta_contabil": "1.1", "filial": "Matriz", "status": "validado", "pendencias": []}],
            "validas": 1, "pendentes": 0, "total_debito": 0, "total_credito": 100, "saldo": -100,
        }

    def test_edicao_valida_linha(self):
        with patch.object(conferencia, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(conferencia, "carregar_conferencia", return_value=self.dados()), \
             patch.object(conferencia.database, "atualizar_linha_preparada") as atualizar:
            conferencia.editar_linha(self.contexto, 10, 101, {"data": "02/05/2026", "descricao": "Novo", "valor": "100,00", "tipo": "C", "conta_contabil": "1.1", "filial": "Matriz"})
            atualizar.assert_called_once()
            self.assertEqual(atualizar.call_args.args[1], 101)

    @patch("web.nucleo.servicos.conferencia.obter_empresa_ativa", return_value={"id": 7})
    def test_lote_cancelado_nao_pode_ser_editado(self, _empresa):
        with patch.object(conferencia, "carregar_conferencia", return_value=self.dados("cancelado")):
            with self.assertRaises(conferencia.ErroConferencia):
                conferencia.editar_linha(self.contexto, 10, 101, {})
