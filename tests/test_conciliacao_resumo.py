import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, text

from contaview.logic import database


class ResumoConciliacaoTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        with self.engine.begin() as conexao:
            conexao.execute(text("""
                CREATE TABLE conciliacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id INTEGER NOT NULL,
                    periodo TEXT NOT NULL,
                    total_pares INTEGER NOT NULL,
                    pares_ok INTEGER NOT NULL,
                    pares_com_erro INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    executado_em TEXT
                )
            """))

    def tearDown(self):
        self.engine.dispose()

    def test_reexecucao_substitui_resumo_do_mes(self):
        with patch.object(database, "_get_engine", return_value=self.engine):
            database.inserir_conciliacao(7, "2026-05", 3, 1, 2)
            database.inserir_conciliacao(7, "2026-05", 4, 3, 1)
        with self.engine.connect() as conexao:
            linhas = conexao.execute(text("SELECT total_pares, pares_ok, pares_com_erro FROM conciliacoes")).all()
        self.assertEqual(linhas, [(4, 3, 1)])


if __name__ == "__main__":
    unittest.main()
