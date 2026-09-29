import unittest
from decimal import Decimal

import pandas as pd

from contaview.logic.relatorios import calcular_balancete, calcular_dre


class RelatoriosContabeisTest(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            {"conta_contabil": "3.1.1", "valor": Decimal("100.00"), "tipo": "C"},
            {"conta_contabil": "4.1.1", "valor": Decimal("40.00"), "tipo": "D"},
            {"conta_contabil": "1.1.1", "valor": Decimal("60.00"), "tipo": "D"},
        ])

    def test_balancete_soma_debitos_creditos_e_saldo(self):
        resultado = calcular_balancete(self.df)
        receita = resultado[resultado["Conta contábil"] == "3.1.1"].iloc[0]
        despesa = resultado[resultado["Conta contábil"] == "4.1.1"].iloc[0]

        self.assertEqual(receita["Créditos"], Decimal("100.00"))
        self.assertEqual(receita["Saldo"], Decimal("-100.00"))
        self.assertEqual(despesa["Débitos"], Decimal("40.00"))

    def test_dre_classifica_prefixos_e_preserva_nao_classificadas(self):
        resultado = calcular_dre(self.df)
        receita = resultado[resultado["Conta contábil"] == "3.1.1"].iloc[0]
        despesa = resultado[resultado["Conta contábil"] == "4.1.1"].iloc[0]
        outras = resultado[resultado["Conta contábil"] == "1.1.1"].iloc[0]

        self.assertEqual(receita["Natureza"], "Receita")
        self.assertEqual(receita["Resultado"], Decimal("100.00"))
        self.assertEqual(despesa["Natureza"], "Despesa")
        self.assertEqual(despesa["Resultado"], Decimal("40.00"))
        self.assertEqual(outras["Natureza"], "Não classificada")


if __name__ == "__main__":
    unittest.main()
