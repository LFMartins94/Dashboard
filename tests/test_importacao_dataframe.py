import unittest
from io import BytesIO
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
from openpyxl import Workbook
from sqlalchemy import create_engine, text

from contaview.logic import database, importacao
from contaview.logic.assistente_ferramentas import consultar_saldo
from contaview.logic.conciliacao import conciliar_fontes
from contaview.logic.mapeamento_colunas import sugerir_mapeamento
from contaview.logic.parsers import inspecionar_planilha, resolver_datas_para_periodo
from contaview.logic.relatorios import exportar_lote_preparado, exportar_cruzamento_fontes


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

    def test_datas_ambiguas_usam_periodo_sem_alterar_o_dia(self):
        datas = pd.Series(["05/06/2026", "25/05/2026"])
        resolvidas, invalidas = resolver_datas_para_periodo(datas, "2026-05")

        self.assertEqual(invalidas, [])
        self.assertEqual(resolvidas.iloc[0].isoformat(), "2026-05-06")
        self.assertEqual(resolvidas.iloc[1].isoformat(), "2026-05-25")

    def test_periodo_incompativel_nao_inventa_data(self):
        resolvidas, invalidas = resolver_datas_para_periodo(
            pd.Series(["05/06/2026"]), "2026-07"
        )
        self.assertEqual(invalidas, [1])
        self.assertIsNone(resolvidas.iloc[0])


class SubstituicaoAtomicaTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE empresas (id INTEGER PRIMARY KEY)"))
            conn.execute(text("""
                CREATE TABLE lancamentos (
                    id INTEGER PRIMARY KEY, empresa_id INTEGER, data DATE,
                    conta_contabil TEXT, valor NUMERIC, tipo TEXT, historico TEXT,
                    filial TEXT, periodo TEXT, sequencial_lote INTEGER,
                    origem TEXT, arquivo_origem TEXT
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
                INSERT INTO lancamentos (
                    id, empresa_id, data, conta_contabil, valor, tipo, historico,
                    filial, periodo, sequencial_lote, origem, arquivo_origem
                ) VALUES (
                    1, 7, '2026-05-01', '1.1.1', 80, 'C', 'Antigo',
                    'Matriz', '2026-05', 1, 'arquivo', 'antigo.xlsx'
                )
            """))
            conn.execute(text("""
                INSERT INTO ocorrencias_auditoria (id, empresa_id, lancamento_id)
                VALUES (1, 7, 1)
            """))
            conn.execute(text("""
                INSERT INTO conciliacoes (id, empresa_id, periodo)
                VALUES (1, 7, '2026-05')
            """))

        self.novo_df = pd.DataFrame([{
            "data": pd.Timestamp("2026-05-02"),
            "conta_contabil": "2.2.2", "valor": 90.0, "tipo": "D",
            "historico": "Novo", "filial": "Matriz", "periodo": "2026-05",
            "sequencial_lote": 1, "arquivo_origem": "novo.xlsx",
        }])

    def tearDown(self):
        self.engine.dispose()

    def test_falha_ao_inserir_reverte_exclusoes(self):
        with (
            patch.object(database, "_get_engine", return_value=self.engine),
            patch.object(database, "_inserir_lancamentos", side_effect=RuntimeError("falha")),
        ):
            with self.assertRaises(RuntimeError):
                database.substituir_lancamentos_do_periodo(self.novo_df, 7, "2026-05")

        with self.engine.connect() as conn:
            historico = conn.execute(text("SELECT historico FROM lancamentos")).scalar_one()
            ocorrencias = conn.execute(text("SELECT COUNT(*) FROM ocorrencias_auditoria")).scalar_one()
            conciliacoes = conn.execute(text("SELECT COUNT(*) FROM conciliacoes")).scalar_one()
        self.assertEqual(historico, "Antigo")
        self.assertEqual(ocorrencias, 1)
        self.assertEqual(conciliacoes, 1)

    def test_substituicao_concluida_grava_lote_novo(self):
        with patch.object(database, "_get_engine", return_value=self.engine):
            quantidade = database.substituir_lancamentos_do_periodo(
                self.novo_df, 7, "2026-05"
            )

        with self.engine.connect() as conn:
            historico = conn.execute(text("SELECT historico FROM lancamentos")).scalar_one()
            ocorrencias = conn.execute(text("SELECT COUNT(*) FROM ocorrencias_auditoria")).scalar_one()
        self.assertEqual(quantidade, 1)
        self.assertEqual(historico, "Novo")
        self.assertEqual(ocorrencias, 0)


class PreparacaoGenericaTest(unittest.TestCase):
    def test_valor_zero_e_negativo_em_parenteses_sao_preservados(self):
        linhas = [
            {"numero_linha": 2, "valores": {"Valor": 0, "Data": "25/05/2026"}},
            {"numero_linha": 3, "valores": {"Valor": "(1.234,56)", "Data": "25/05/2026"}},
        ]
        preparadas = importacao.preparar_linhas_mapeadas(
            linhas, {"data": "Data", "valor": "Valor"}, "extrato", "2026-05"
        )
        self.assertEqual(
            [linha["valor"] for linha in preparadas],
            [Decimal("0.00"), Decimal("-1234.56")],
        )

    def test_preparacao_registra_cabecalho_e_mapeamento_confirmados(self):
        arquivo = BytesIO(b"Data;Valor\n25/05/2026;10,00\n")
        arquivo.name = "extrato.csv"
        with (
            patch.object(importacao, "obter_ou_criar_empresa", return_value=7),
            patch.object(importacao, "salvar_lote_preparacao", return_value={
                "duplicado": False, "lote_id": 2, "total_linhas": 1,
            }) as salvar,
        ):
            resultado = importacao.executar_preparacao(
                arquivo, "Empresa", None, "Planilha", "extrato", "2026-05",
                {"data": "Data", "valor": "Valor"}, 1,
            )
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(salvar.call_args.args[7], {
            "linha_cabecalho": 1,
            "colunas": {"data": "Data", "valor": "Valor"},
        })

    def test_saldo_do_assistente_subtrai_debitos(self):
        quadro = pd.DataFrame([
            {"tipo": "C", "valor": Decimal("100.00")},
            {"tipo": "D", "valor": Decimal("60.00")},
        ])
        with (
            patch("contaview.logic.assistente_ferramentas.resolver_nome_empresa", return_value=7),
            patch.object(database, "carregar_lancamentos", return_value=quadro),
        ):
            resultado = consultar_saldo("Empresa", "05/2026")
        self.assertEqual(resultado["saldo"], 40.0)

    def test_sem_cabecalho_preserva_primeira_linha_e_permite_escolha_manual(self):
        arquivo = BytesIO(
            "25/05/2026;100,00;Pagamento\n26/05/2026;50,00;Recebimento\n".encode()
        )
        arquivo.name = "sem_cabecalho.csv"
        resultado = inspecionar_planilha(arquivo)
        aba = resultado["abas"][0]
        self.assertEqual(aba["linha_cabecalho"], 0)
        self.assertEqual(aba["total_linhas"], 2)
        self.assertEqual(aba["linhas"][0]["numero_linha"], 1)

        arquivo = BytesIO(b"Identificacao;Total\nA;10\n")
        arquivo.name = "com_cabecalho.csv"
        resultado = inspecionar_planilha(
            arquivo, linha_cabecalho=1, aba_alvo="Planilha"
        )
        aba = resultado["abas"][0]
        self.assertEqual(aba["cabecalhos"], ["Identificacao", "Total"])
        self.assertEqual(aba["total_linhas"], 1)

    def test_planilha_compactada_preserva_linhas_e_valores(self):
        pasta = Workbook()
        aba = pasta.active
        aba.title = "Conferência"
        aba.append(["Data;Conta Contábil;Valor;Tipo;Histórico;Filial"])
        aba.append(["25/05/2026;1.1.1;1.234,56;C;Recebimento;Matriz"])
        aba.append(["25/05/2026;2.2.2;1.234,56;D;Pagamento;Matriz"])
        arquivo = BytesIO()
        pasta.save(arquivo)
        arquivo.seek(0)
        arquivo.name = "exemplo.xlsx"

        resultado = inspecionar_planilha(arquivo)
        self.assertTrue(resultado["sucesso"])
        aba_lida = resultado["abas"][0]
        self.assertEqual(aba_lida["total_linhas"], 2)
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            mapeamento = sugerir_mapeamento(aba_lida["cabecalhos"])
        linhas = importacao.preparar_linhas_mapeadas(
            aba_lida["linhas"], mapeamento, "lancamentos", "2026-05"
        )
        self.assertEqual([linha["numero_linha"] for linha in linhas], [2, 3])
        self.assertEqual([linha["valor"] for linha in linhas], [Decimal("1234.56")] * 2)
        self.assertTrue(all(linha["status"] == "validado" for linha in linhas))

    def test_exportacao_exige_revisao_e_exclui_colunas_internas(self):
        linhas = [{
            "dados_brutos": {"Referência": "ABC", "empresa_id": "7"},
            "data": pd.Timestamp("2026-05-25").date(),
            "descricao": "Recebimento", "valor": Decimal("1234.56"),
            "tipo": "C", "conta_contabil": "1.1.1", "filial": "Matriz",
            "status": "pendente",
        }]
        with self.assertRaises(ValueError):
            exportar_lote_preparado(linhas, "csv")
        linhas[0]["status"] = "validado"
        resultado = exportar_lote_preparado(linhas, "csv").decode("utf-8-sig")
        self.assertIn("1.234,56".replace(".", ""), resultado)
        self.assertIn("Original: Referência", resultado)
        self.assertNotIn("empresa_id", resultado)

    def test_conciliacao_nao_confirma_duplicados_automaticamente(self):
        data = pd.Timestamp("2026-05-25").date()
        extrato = [
            {"id": 1, "data": data, "valor": Decimal("100.00"),
             "descricao": "Pagamento", "status": "validado"},
            {"id": 2, "data": data, "valor": Decimal("100.00"),
             "descricao": "Pagamento", "status": "validado"},
        ]
        referencia = [
            {"id": 10, "data": data, "valor": Decimal("100.00"),
             "descricao": "Pagamento", "status": "validado"},
        ]
        resultado = conciliar_fontes(extrato, referencia)
        self.assertEqual(resultado["pares_confirmados"], [])
        self.assertEqual(len(resultado["candidatos"]), 2)
        self.assertEqual(len(resultado["sem_correspondencia_extrato"]), 2)

    def test_conciliacao_aponta_diferenca_de_valor(self):
        data = pd.Timestamp("2026-05-25").date()
        extrato = [{"id": 1, "data": data, "valor": Decimal("100.00"),
                    "descricao": "Pagamento fornecedor", "status": "validado"}]
        referencia = [{"id": 10, "data": data, "valor": Decimal("99.00"),
                       "descricao": "Pagamento fornecedor", "status": "validado"}]
        resultado = conciliar_fontes(extrato, referencia)
        self.assertEqual(len(resultado["divergencias_valor"]), 1)
        self.assertEqual(resultado["pares_confirmados"], [])

    def test_conciliacao_sem_descricao_exige_revisao_e_exporta_linhas(self):
        data = pd.Timestamp("2026-05-25").date()
        fonte_1 = [{
            "id": 1, "numero_linha": 4, "data": data,
            "valor": Decimal("100.00"), "descricao": "", "status": "validado",
        }]
        fonte_2 = [{
            "id": 10, "numero_linha": 8, "data": data,
            "valor": Decimal("100.00"), "descricao": "", "status": "validado",
        }]
        resultado = conciliar_fontes(fonte_1, fonte_2)
        self.assertEqual(resultado["pares_confirmados"], [])
        self.assertEqual(len(resultado["candidatos"]), 1)
        self.assertEqual(resultado["faltantes_extrato"], [])
        self.assertEqual(resultado["faltantes_referencia"], [])
        csv = exportar_cruzamento_fontes(resultado, fonte_1, fonte_2).decode("utf-8-sig")
        self.assertIn("Candidato para revisão;4;8", csv)
        self.assertNotIn("empresa_id", csv)

    def test_conciliacao_distingue_linha_sem_correspondencia(self):
        data = pd.Timestamp("2026-05-25").date()
        fonte_1 = [{
            "id": 1, "numero_linha": 4, "data": data,
            "valor": Decimal("100.00"), "descricao": "Pagamento", "status": "validado",
        }]
        resultado = conciliar_fontes(fonte_1, [])
        self.assertEqual(resultado["faltantes_extrato"], fonte_1)
        self.assertEqual(resultado["faltantes_referencia"], [])


if __name__ == "__main__":
    unittest.main()
