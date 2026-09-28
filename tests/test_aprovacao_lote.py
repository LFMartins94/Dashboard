import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine, text

from contaview.logic import database


class AprovacaoLoteTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE empresas (id INTEGER PRIMARY KEY)"))
            conn.execute(text("""
                CREATE TABLE lotes_importacao (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER, nome_arquivo TEXT,
                    periodo TEXT, status TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE linhas_preparadas (
                    id INTEGER PRIMARY KEY, lote_id INTEGER, empresa_id INTEGER,
                    numero_linha INTEGER, data DATE, descricao TEXT, valor NUMERIC,
                    tipo TEXT, conta_contabil TEXT, filial TEXT, status TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE lancamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER,
                    data DATE, conta_contabil TEXT, valor NUMERIC, tipo TEXT,
                    historico TEXT, filial TEXT, periodo TEXT,
                    sequencial_lote INTEGER, origem TEXT, arquivo_origem TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE ocorrencias_auditoria (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER, lancamento_id INTEGER
                )
            """))
            conn.execute(text("""
                CREATE TABLE conciliacoes (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER, periodo TEXT
                )
            """))
            conn.execute(text("INSERT INTO empresas (id) VALUES (7)"))
            conn.execute(text("""
                INSERT INTO lotes_importacao
                    (id, empresa_id, nome_arquivo, periodo, status)
                VALUES (10, 7, 'maio.xlsx', '2026-05', 'em_revisao')
            """))
            conn.execute(text("""
                INSERT INTO linhas_preparadas
                    (id, lote_id, empresa_id, numero_linha, data, descricao,
                     valor, tipo, conta_contabil, filial, status)
                VALUES
                    (101, 10, 7, 2, '2026-05-02', 'Recebimento', 100, 'C',
                     '1.1.1', 'Matriz', 'validado')
            """))

    def tearDown(self):
        self.engine.dispose()

    def test_aprovacao_grava_lancamento_e_conclui_lote(self):
        with patch.object(database, "_get_engine", return_value=self.engine):
            resultado = database.aprovar_lote_preparacao(7, 10)

        self.assertEqual(resultado["registros_salvos"], 1)
        with self.engine.connect() as conn:
            lancamento = conn.execute(text("""
                SELECT empresa_id, periodo, historico, origem
                FROM lancamentos
            """)).one()
            status = conn.execute(
                text("SELECT status FROM lotes_importacao WHERE id = 10")
            ).scalar_one()
        self.assertEqual(tuple(lancamento), (7, "2026-05", "Recebimento", "lote_preparado"))
        self.assertEqual(status, "concluido")

    def test_lote_pendente_nao_grava_nada(self):
        with self.engine.begin() as conn:
            conn.execute(text(
                "UPDATE linhas_preparadas SET status = 'pendente' WHERE id = 101"
            ))

        with patch.object(database, "_get_engine", return_value=self.engine):
            with self.assertRaises(ValueError):
                database.aprovar_lote_preparacao(7, 10)

        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM lancamentos")).scalar_one(), 0)

    def test_periodo_existente_exige_substituicao(self):
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO lancamentos
                    (empresa_id, data, conta_contabil, valor, tipo, periodo)
                VALUES (7, '2026-05-01', '9.9.9', 50, 'D', '2026-05')
            """))

        with patch.object(database, "_get_engine", return_value=self.engine):
            with self.assertRaises(database.PeriodoExistenteError):
                database.aprovar_lote_preparacao(7, 10)
            resultado = database.aprovar_lote_preparacao(7, 10, substituir=True)

        self.assertEqual(resultado["registros_salvos"], 1)
        with self.engine.connect() as conn:
            conta = conn.execute(text("SELECT conta_contabil FROM lancamentos")).scalar_one()
        self.assertEqual(conta, "1.1.1")


if __name__ == "__main__":
    unittest.main()
