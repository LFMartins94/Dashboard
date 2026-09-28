import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine, text

from contaview.logic import database
from contaview.logic.auditoria import auditar_lancamentos
from contaview.logic.conciliacao import conciliar_partidas


class AuditoriaConciliacaoTest(unittest.TestCase):
    def test_auditoria_relaciona_ocorrencia_ao_lancamento(self):
        df = pd.DataFrame([
            {
                "id": 11, "data": date(2026, 5, 1), "conta_contabil": "1.1.1",
                "valor": 100, "tipo": "D", "historico": "Pagamento",
                "sequencial_lote": 1,
            },
            {
                "id": 12, "data": date(2026, 5, 1), "conta_contabil": "1.1.1",
                "valor": 100, "tipo": "D", "historico": "Pagamento",
                "sequencial_lote": 2,
            },
        ])

        ocorrencias = auditar_lancamentos(df)

        duplicidades = [
            item for item in ocorrencias if item["tipo_ocorrencia"] == "DUPLICIDADE"
        ]
        self.assertEqual({item["lancamento_id"] for item in duplicidades}, {11, 12})

    def test_conciliacao_nao_parea_contas_diferentes(self):
        base = {
            "data": date(2026, 5, 1), "valor": 100,
            "historico": "Movimento", "sequencial_lote": 1,
        }
        df = pd.DataFrame([
            {**base, "conta_contabil": "1.1.1", "tipo": "C"},
            {**base, "conta_contabil": "2.2.2", "tipo": "D", "sequencial_lote": 2},
        ])

        resultado = conciliar_partidas(df)

        self.assertEqual(resultado["pares_ok"], 0)
        self.assertEqual(resultado["sem_par"], 2)

    def test_insercao_de_ocorrencia_e_idempotente(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE ocorrencias_auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id INTEGER, lancamento_id INTEGER,
                    tipo_ocorrencia TEXT, descricao TEXT, severidade TEXT
                )
            """))
        ocorrencia = [{
            "empresa_id": 7, "lancamento_id": 11,
            "tipo_ocorrencia": "DUPLICIDADE",
            "descricao": "Lançamento duplicado",
            "severidade": "alta",
        }]

        with patch.object(database, "_get_engine", return_value=engine):
            primeira = database.inserir_ocorrencias(ocorrencia)
            segunda = database.inserir_ocorrencias(ocorrencia)

        self.assertEqual(primeira, 1)
        self.assertEqual(segunda, 0)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
