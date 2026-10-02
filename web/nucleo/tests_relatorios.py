from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase

from contaview.logic.relatorios import (
    calcular_balancete_com_saldos,
    calcular_dre_classificada,
    exportar_pdf_relatorio,
    exportar_planilha_relatorio,
)

from .models import ClassificacaoDre, GeracaoRelatorio
from .servicos import relatorios
from .servicos.contexto import ContextoTrabalho


class CalculosRelatoriosTest(TestCase):
    def test_balancete_separa_saldo_anterior_movimento_e_saldo_final(self):
        anterior = pd.DataFrame([
            {"conta_contabil": "1.1", "valor": Decimal("80.00"), "tipo": "D"},
            {"conta_contabil": "1.1", "valor": Decimal("20.00"), "tipo": "C"},
        ])
        atual = pd.DataFrame([
            {"conta_contabil": "1.1", "valor": Decimal("30.00"), "tipo": "D"},
            {"conta_contabil": "1.1", "valor": Decimal("10.00"), "tipo": "C"},
        ])
        resultado = calcular_balancete_com_saldos(atual, anterior).iloc[0]
        self.assertEqual(resultado["Saldo anterior"], Decimal("60.00"))
        self.assertEqual(resultado["Débitos"], Decimal("30.00"))
        self.assertEqual(resultado["Créditos"], Decimal("10.00"))
        self.assertEqual(resultado["Saldo final"], Decimal("80.00"))

    def test_dre_usa_plano_confirmado_e_mostra_conta_nao_classificada(self):
        quadro = pd.DataFrame([
            {"conta_contabil": "3.1", "valor": Decimal("100.00"), "tipo": "C"},
            {"conta_contabil": "4.1", "valor": Decimal("40.00"), "tipo": "D"},
            {"conta_contabil": "1.1", "valor": Decimal("5.00"), "tipo": "D"},
        ])
        resultado, subtotal = calcular_dre_classificada(quadro, [
            {"prefixo_conta": "3", "grupo": "Receita operacional", "categoria": "receita", "ordem": 10},
            {"prefixo_conta": "4", "grupo": "Despesas operacionais", "categoria": "despesa", "ordem": 20},
        ])
        self.assertEqual(subtotal, Decimal("60.00"))
        self.assertIn("Não classificado", resultado["Grupo"].tolist())
        self.assertEqual(resultado.loc[resultado["Grupo"] == "Despesas operacionais", "Valor"].iloc[0], Decimal("40.00"))

    def test_exportacoes_nao_incluem_colunas_tecnicas(self):
        quadro = pd.DataFrame([{"Conta": "1.1", "Valor": "R$ 10,00", "empresa_id": 7}])
        excel = exportar_planilha_relatorio(quadro, "Teste")
        pdf = exportar_pdf_relatorio(quadro, "Teste", "Empresa", "2026-05")
        self.assertTrue(excel.startswith(b"PK"))
        self.assertTrue(pdf.startswith(b"%PDF"))


class EntregasServicoTest(TestCase):
    contexto = ContextoTrabalho(7, "Empresa teste", "2026-05")

    def setUp(self):
        self.usuario = get_user_model().objects.create_user("contadora", password="senha-segura")
        self.lancamentos = pd.DataFrame([
            {"id": 1, "empresa_id": 7, "data": date(2026, 4, 30), "conta_contabil": "1.1", "valor": Decimal("60.00"), "tipo": "D", "historico": "Saldo", "filial": "Matriz", "periodo": "2026-04"},
            {"id": 2, "empresa_id": 7, "data": date(2026, 5, 2), "conta_contabil": "3.1", "valor": Decimal("100.00"), "tipo": "C", "historico": "Receita", "filial": "Matriz", "periodo": "2026-05"},
            {"id": 3, "empresa_id": 7, "data": date(2026, 5, 3), "conta_contabil": "4.1", "valor": Decimal("40.00"), "tipo": "D", "historico": "Despesa", "filial": "Matriz", "periodo": "2026-05"},
        ])

    def test_geracao_registra_parametros_e_versao(self):
        with patch.object(relatorios, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(relatorios.database, "carregar_lancamentos", return_value=self.lancamentos):
            conteudo, nome, tipo_conteudo = relatorios.gerar(
                self.contexto, self.usuario, "balancete", "xlsx"
            )
        registro = GeracaoRelatorio.objects.get()
        self.assertTrue(conteudo.startswith(b"PK"))
        self.assertEqual(nome, "balancete_2026-05.xlsx")
        self.assertIn("spreadsheetml", tipo_conteudo)
        self.assertEqual(registro.empresa_id, 7)
        self.assertEqual(registro.parametros["competencia"], "2026-05")
        self.assertTrue(registro.versao_calculo)

    def test_classificacao_e_perfil_sao_limitados_a_empresa_do_contexto(self):
        with patch.object(relatorios, "obter_empresa_ativa", return_value={"id": 7}):
            classificacao = relatorios.salvar_classificacao(
                self.contexto, "3", "Receita operacional", "receita", 10
            )
            perfil = relatorios.criar_perfil(
                self.contexto, self.usuario, "Sistema da empresa", "data, valor, historico"
            )
        self.assertEqual(ClassificacaoDre.objects.get(), classificacao)
        self.assertEqual(perfil.campos, ["data", "valor", "historico"])
