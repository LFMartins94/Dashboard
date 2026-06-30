import unittest
from unittest.mock import patch

import pandas as pd

from contaview.logic import importacao


def _df_lancamentos() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "data": pd.Timestamp("2026-05-01"),
                "conta_contabil": "1.1.1",
                "valor": 100.00,
                "tipo": "C",
                "historico": "Recebimento",
                "filial": "Matriz",
            },
            {
                "data": pd.Timestamp("2026-05-01"),
                "conta_contabil": "2.1.1",
                "valor": 100.00,
                "tipo": "D",
                "historico": "Pagamento",
                "filial": "Matriz",
            },
        ]
    )


class ImportacaoDataFrameTest(unittest.TestCase):
    def test_reenvio_mesma_planilha_requer_confirmacao_de_substituicao(self):
        df = _df_lancamentos()

        with (
            patch.object(importacao, "obter_ou_criar_empresa", return_value=7),
            patch.object(
                importacao,
                "verificar_periodo_existente",
                side_effect=[False, True],
            ),
            patch.object(importacao, "salvar_lancamentos", return_value=2) as salvar,
        ):
            primeira = importacao.executar_importacao_dataframe(
                df, "Empresa Teste", "00.000.000/0001-00", "maio_2026.xlsx"
            )
            segunda = importacao.executar_importacao_dataframe(
                df, "Empresa Teste", "00.000.000/0001-00", "maio_2026.xlsx"
            )

        self.assertTrue(primeira.get("sucesso"))
        self.assertEqual(primeira["periodo"], "2026-05")

        self.assertTrue(segunda.get("requer_confirmacao"))
        self.assertEqual(segunda["empresa_id"], 7)
        self.assertEqual(segunda["periodo"], "2026-05")
        self.assertIn("sequencial_lote", segunda["df"].columns)

        self.assertEqual(salvar.call_count, 1)
        df_salvo = salvar.call_args.args[0]
        self.assertEqual(df_salvo["arquivo_origem"].iloc[0], "maio_2026.xlsx")


if __name__ == "__main__":
    unittest.main()
