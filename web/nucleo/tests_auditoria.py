from datetime import date
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import EstadoOcorrenciaAuditoria
from .servicos import auditoria
from .servicos.contexto import ContextoTrabalho


class AuditoriaServicoTest(TestCase):
    contexto = ContextoTrabalho(7, "Empresa teste", "2026-05")

    def setUp(self):
        self.usuario = get_user_model().objects.create_user("contadora", password="senha-segura")
        self.quadro_ocorrencias = pd.DataFrame([{
            "id": 31, "empresa_id": 7, "lancamento_id": 11,
            "tipo_ocorrencia": "DUPLICIDADE", "descricao": "Lançamento duplicado",
            "severidade": "alta", "resolvida": False,
            "data": date(2026, 5, 1), "conta_contabil": "1.1", "valor": 100,
        }])

    def test_resolucao_registra_usuario_e_data(self):
        with patch.object(auditoria, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(auditoria.database, "carregar_ocorrencias", return_value=self.quadro_ocorrencias), \
             patch.object(auditoria.database, "carregar_historico_alteracoes", return_value=[]), \
             patch.object(auditoria.database, "atualizar_ocorrencia_resolvida_empresa") as atualizar:
            dados = auditoria.resolver(self.contexto, self.usuario, 31, True, "Conferido no comprovante.")
        estado = EstadoOcorrenciaAuditoria.objects.get(ocorrencia_id=31)
        self.assertTrue(estado.resolvida)
        self.assertEqual(estado.resolvida_por, self.usuario)
        self.assertEqual(dados["resolvidas"], 1)
        self.assertEqual(dados["ocorrencias"][0]["tipo_exibicao"], "Duplicidade")
        self.assertEqual(dados["ocorrencias"][0]["severidade_exibicao"], "Alta")
        atualizar.assert_called_once_with(7, 31, True)

    def test_execucao_relaciona_ocorrencias_ao_lancamento(self):
        lancamentos = pd.DataFrame([
            {"id": 11, "data": date(2026, 5, 1), "conta_contabil": "1.1", "valor": 100, "tipo": "D", "historico": "Pagamento", "sequencial_lote": 1},
            {"id": 12, "data": date(2026, 5, 1), "conta_contabil": "1.1", "valor": 100, "tipo": "D", "historico": "Pagamento", "sequencial_lote": 2},
        ])
        with patch.object(auditoria, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(auditoria.database, "carregar_lancamentos", return_value=lancamentos), \
             patch.object(auditoria, "salvar_ocorrencias", return_value=2) as salvar, \
             patch.object(auditoria, "carregar", return_value={"total": 2}) as carregar:
            dados, novas = auditoria.executar(self.contexto)
        ocorrencias = salvar.call_args.args[0]
        self.assertEqual({item["lancamento_id"] for item in ocorrencias if item["tipo_ocorrencia"] == "DUPLICIDADE"}, {11, 12})
        self.assertEqual((dados, novas), ({"total": 2}, 2))
