from decimal import Decimal
from pathlib import Path
import unittest

from contaview.logic.parsers import inspecionar_planilha, ler_arquivo


FIXTURES = Path(__file__).parent / "fixtures" / "aceitacao"


class FixturesAceitacaoTest(unittest.TestCase):
    def validar_movimentos(self, caminho: Path) -> None:
        with caminho.open("rb") as arquivo:
            resultado = ler_arquivo(arquivo)

        self.assertTrue(resultado["sucesso"])
        dados = resultado["df"]
        self.assertEqual(len(dados), 42)
        self.assertEqual(int((dados["tipo"] == "D").sum()), 21)
        self.assertEqual(int((dados["tipo"] == "C").sum()), 21)
        totais = dados.groupby("tipo")["valor"].sum().to_dict()
        self.assertEqual(Decimal(str(totais["D"])), Decimal("11243.72"))
        self.assertEqual(Decimal(str(totais["C"])), Decimal("11243.72"))

    def test_cap_anonimizada_delimitada(self) -> None:
        self.validar_movimentos(FIXTURES / "cap_anonimizada_delimitada.xlsx")

    def test_cap_anonimizada_em_csv(self) -> None:
        self.validar_movimentos(FIXTURES / "cap_anonimizada_colunas.csv")

    def test_cap_multiplas_abas_permite_escolha_manual(self) -> None:
        caminho = FIXTURES / "cap_anonimizada_multiplas_abas.xlsx"
        with caminho.open("rb") as arquivo:
            resultado = inspecionar_planilha(
                arquivo,
                linha_cabecalho=1,
                aba_alvo="Movimentos",
            )

        self.assertTrue(resultado["sucesso"])
        movimentos = next(aba for aba in resultado["abas"] if aba["nome"] == "Movimentos")
        self.assertEqual(movimentos["total_linhas"], 42)
        self.assertEqual(
            movimentos["cabecalhos"],
            ["Dia", "Conta", "Montante", "Natureza", "Memo", "Unidade"],
        )


if __name__ == "__main__":
    unittest.main()
