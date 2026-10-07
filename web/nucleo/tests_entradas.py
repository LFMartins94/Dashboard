import io
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from contaview.logic.importacao import salvar_preparacao_confirmada
from contaview.logic.parsers import inspecionar_planilha

from .models import (
    ArquivoEntradaTemporario,
    EstadoArquivoEntrada,
    ModeloMapeamentoEntrada,
    PerfilOrigemEntrada,
)
from .servicos.contexto import CHAVE_CONTEXTO
from .servicos.entradas import (
    ArquivoEmMemoria,
    ErroEntrada,
    assinatura_estrutura,
    inspecionar_selecao,
)


RAIZ_PROJETO = Path(__file__).resolve().parents[2]
PASTA_FIXTURES = RAIZ_PROJETO / "tests" / "fixtures" / "aceitacao"


def arquivo_fixture(nome: str) -> SimpleUploadedFile:
    caminho = PASTA_FIXTURES / nome
    return SimpleUploadedFile(nome, caminho.read_bytes())


class EntradasNavegadorTestes(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="contadora", password="Senha-Segura-2026"
        )
        self.client.force_login(self.usuario)
        sessao = self.client.session
        sessao[CHAVE_CONTEXTO] = {
            "empresa_id": 7,
            "empresa_nome": "Empresa de teste",
            "competencia": "2026-01",
        }
        sessao.save()

    @mock.patch("nucleo.views.listar_lotes_contexto", return_value=[])
    def test_tela_de_entradas_abre_no_contexto(self, _listar):
        resposta = self.client.get(reverse("nucleo:entradas"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Receba primeiro")
        self.assertContains(resposta, "OFX, XLSX, XLS ou CSV")

    @mock.patch("nucleo.servicos.entradas._existe_lote_final", return_value=None)
    @mock.patch("nucleo.views.listar_lotes_contexto", return_value=[])
    def test_tres_arquivos_de_aceitacao_entram_pelo_navegador(
        self, _listar, _duplicado
    ):
        arquivos = [
            arquivo_fixture("cap_anonimizada_delimitada.xlsx"),
            arquivo_fixture("cap_anonimizada_colunas.csv"),
            arquivo_fixture("cap_anonimizada_multiplas_abas.xlsx"),
        ]

        resposta = self.client.post(reverse("nucleo:entradas"), {"arquivos": arquivos})

        self.assertRedirects(resposta, reverse("nucleo:entradas"))
        self.assertEqual(ArquivoEntradaTemporario.objects.count(), 3)
        self.assertTrue(
            all(item.inspecao["abas"] for item in ArquivoEntradaTemporario.objects.all())
        )

    @mock.patch("nucleo.servicos.entradas._existe_lote_final", return_value=None)
    def test_xls_xml_legado_tambem_entra_pelo_navegador(self, _duplicado):
        conteudo = b'''<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="Movimentos"><Table><Row><Cell><Data ss:Type="String">Data</Data></Cell><Cell><Data ss:Type="String">Valor</Data></Cell></Row><Row><Cell><Data ss:Type="String">05/01/2026</Data></Cell><Cell><Data ss:Type="String">10,00</Data></Cell></Row></Table></Worksheet></Workbook>'''

        resposta = self.client.post(
            reverse("nucleo:entradas"),
            {"arquivos": [SimpleUploadedFile("legado.xls", conteudo)]},
        )

        temporario = ArquivoEntradaTemporario.objects.get()
        self.assertRedirects(
            resposta, reverse("nucleo:mapear_entrada", args=[temporario.id])
        )
        self.assertEqual(temporario.extensao, "xls")
        self.assertEqual(temporario.inspecao["abas"][0]["total_linhas"], 1)

    @mock.patch("nucleo.servicos.entradas._existe_lote_final")
    @mock.patch("nucleo.views.listar_lotes_contexto", return_value=[])
    def test_reenvio_e_bloqueado_antes_de_criar_temporario(
        self, _listar, existe_lote
    ):
        existe_lote.return_value = (91, "cap.xlsx", None)

        resposta = self.client.post(
            reverse("nucleo:entradas"),
            {"arquivos": [arquivo_fixture("cap_anonimizada_delimitada.xlsx")]},
            follow=True,
        )

        self.assertEqual(ArquivoEntradaTemporario.objects.count(), 0)
        self.assertContains(resposta, "já foi recebido no lote 91")

    @mock.patch("nucleo.servicos.entradas._existe_lote_final", return_value=None)
    def test_formato_desconhecido_abre_mapeamento_manual_sem_perder_original(
        self, _duplicado
    ):
        conteudo = b"Quando;Quantia;Anotacao;Campo original\n05/01/2026;1.234,56;Teste;Preservar\n"
        resposta = self.client.post(
            reverse("nucleo:entradas"),
            {"arquivos": [SimpleUploadedFile("desconhecido.csv", conteudo)]},
        )
        temporario = ArquivoEntradaTemporario.objects.get()

        self.assertRedirects(
            resposta, reverse("nucleo:mapear_entrada", args=[temporario.id])
        )
        pagina = self.client.get(
            reverse("nucleo:mapear_entrada", args=[temporario.id]),
            {"aba": "Planilha", "linha_cabecalho": 1, "tipo_documento": "outro"},
        )
        self.assertContains(pagina, "Campo original")
        self.assertEqual(bytes(temporario.conteudo), conteudo)

    @mock.patch("nucleo.views.listar_lotes_contexto", return_value=[])
    @mock.patch("nucleo.servicos.entradas._existe_lote_final", return_value=None)
    def test_arquivo_corrompido_informa_nome_e_motivo(self, _duplicado, _listar):
        resposta = self.client.post(
            reverse("nucleo:entradas"),
            {"arquivos": [SimpleUploadedFile("quebrado.xlsx", b"nao e zip")]},
            follow=True,
        )

        self.assertContains(resposta, "Arquivo quebrado.xlsx")
        self.assertContains(resposta, "não é um XLSX válido")

    def test_erro_de_cabecalho_informa_aba_e_linha(self):
        conteudo = b"Data;Valor\n05/01/2026;10,00\n"
        temporario = ArquivoEntradaTemporario.objects.create(
            usuario=self.usuario,
            empresa_id=7,
            competencia="2026-01",
            nome_original="simples.csv",
            extensao="csv",
            tamanho_bytes=len(conteudo),
            arquivo_sha256="a" * 64,
            conteudo=conteudo,
            inspecao={"abas": []},
            status=EstadoArquivoEntrada.EM_MAPEAMENTO,
        )

        with self.assertRaisesRegex(ErroEntrada, "Aba Planilha, linha 99"):
            inspecionar_selecao(temporario, "Planilha", 99, "outro")

    def test_arquivo_de_outra_empresa_nao_pode_ser_aberto(self):
        temporario = ArquivoEntradaTemporario.objects.create(
            usuario=self.usuario,
            empresa_id=8,
            competencia="2026-01",
            nome_original="outra_empresa.csv",
            extensao="csv",
            tamanho_bytes=12,
            arquivo_sha256="d" * 64,
            conteudo=b"Data;Valor\n",
            inspecao={"abas": []},
            status=EstadoArquivoEntrada.EM_MAPEAMENTO,
        )

        resposta = self.client.get(
            reverse("nucleo:mapear_entrada", args=[temporario.id])
        )

        self.assertRedirects(
            resposta, reverse("nucleo:entradas"), fetch_redirect_response=False
        )

    @mock.patch("nucleo.servicos.entradas.sugerir_mapeamento")
    def test_ia_nao_e_chamada_quando_regra_local_e_suficiente(self, sugerir_ia):
        caminho = PASTA_FIXTURES / "cap_anonimizada_colunas.csv"
        conteudo = caminho.read_bytes()
        resultado = inspecionar_planilha(ArquivoEmMemoria(conteudo, caminho.name))
        temporario = ArquivoEntradaTemporario.objects.create(
            usuario=self.usuario, empresa_id=7, competencia="2026-01",
            nome_original=caminho.name, extensao="csv", tamanho_bytes=len(conteudo),
            arquivo_sha256="c" * 64, conteudo=conteudo,
            inspecao={"abas": []}, status=EstadoArquivoEntrada.EM_MAPEAMENTO,
        )

        selecao = inspecionar_selecao(
            temporario, "Planilha", resultado["abas"][0]["linha_cabecalho"],
            "lancamentos", usar_ia=True,
        )

        sugerir_ia.assert_not_called()
        self.assertEqual(selecao.sugestao["data"], resultado["abas"][0]["cabecalhos"][0])
        self.assertEqual(selecao.sugestao["valor"], resultado["abas"][0]["cabecalhos"][2])

    def test_mapeamento_de_perfil_nao_e_reutilizado_em_outra_origem(self):
        caminho = PASTA_FIXTURES / "cap_anonimizada_colunas.csv"
        conteudo = caminho.read_bytes()
        resultado = inspecionar_planilha(ArquivoEmMemoria(conteudo, caminho.name))
        aba = resultado["abas"][0]
        perfil_a = PerfilOrigemEntrada.objects.create(
            empresa_id=7, nome="Banco A", prefixo_nome="banco_a_", tipo_documento="extrato"
        )
        perfil_b = PerfilOrigemEntrada.objects.create(
            empresa_id=7, nome="Banco B", prefixo_nome="banco_b_", tipo_documento="extrato"
        )
        ModeloMapeamentoEntrada.objects.create(
            empresa_id=7,
            perfil_origem=perfil_a,
            assinatura_estrutura=assinatura_estrutura(aba),
            tipo_documento="extrato",
            aba=aba["nome"],
            linha_cabecalho=aba["linha_cabecalho"],
            mapeamento={"data": "Data", "valor": "Valor"},
            confirmado_por=self.usuario,
        )
        temporario = ArquivoEntradaTemporario.objects.create(
            usuario=self.usuario, empresa_id=7, competencia="2026-01",
            nome_original="banco_b_maio.csv", extensao="csv", tamanho_bytes=len(conteudo),
            arquivo_sha256="e" * 64, conteudo=conteudo, inspecao={"abas": []},
            perfil_origem=perfil_b, status=EstadoArquivoEntrada.EM_MAPEAMENTO,
        )

        selecao = inspecionar_selecao(
            temporario, aba["nome"], aba["linha_cabecalho"], "extrato"
        )

        self.assertFalse(selecao.modelo_reutilizado)

    @mock.patch("nucleo.servicos.entradas.obter_empresa_ativa", return_value={"id": 7})
    @mock.patch("nucleo.servicos.entradas.salvar_preparacao_confirmada")
    def test_confirmacao_persiste_modelo_e_conclui_temporario(
        self, salvar, _empresa
    ):
        caminho = PASTA_FIXTURES / "cap_anonimizada_colunas.csv"
        conteudo = caminho.read_bytes()
        resultado = inspecionar_planilha(ArquivoEmMemoria(conteudo, caminho.name))
        temporario = ArquivoEntradaTemporario.objects.create(
            usuario=self.usuario,
            empresa_id=7,
            competencia="2026-01",
            nome_original=caminho.name,
            extensao="csv",
            tamanho_bytes=len(conteudo),
            arquivo_sha256="b" * 64,
            conteudo=conteudo,
            inspecao={"abas": [{
                "nome": resultado["abas"][0]["nome"],
                "linha_cabecalho": resultado["abas"][0]["linha_cabecalho"],
                "cabecalhos": resultado["abas"][0]["cabecalhos"],
                "total_linhas": 42,
                "previa": [],
            }]},
            status=EstadoArquivoEntrada.EM_MAPEAMENTO,
        )
        salvar.return_value = {
            "sucesso": True, "duplicado": False, "lote_id": 123,
            "total_linhas": 42, "pendentes": 0,
        }
        cabecalhos = resultado["abas"][0]["cabecalhos"]
        dados = {
            "aba": "Planilha", "linha_cabecalho": 1,
            "tipo_documento": "lancamentos",
            "data": cabecalhos[0], "conta_contabil": cabecalhos[1],
            "valor": cabecalhos[2], "tipo": cabecalhos[3],
            "descricao": cabecalhos[4], "filial": cabecalhos[5],
        }

        resposta = self.client.post(
            reverse("nucleo:confirmar_entrada", args=[temporario.id]), dados
        )

        self.assertRedirects(resposta, reverse("nucleo:entradas"), fetch_redirect_response=False)
        temporario.refresh_from_db()
        self.assertEqual(temporario.status, EstadoArquivoEntrada.PREPARADO)
        self.assertEqual(bytes(temporario.conteudo), b"")
        self.assertEqual(ModeloMapeamentoEntrada.objects.count(), 1)


class PreparacaoCapTestes(TestCase):
    @mock.patch("contaview.logic.importacao.salvar_lote_preparacao")
    def test_cap_gera_42_linhas_e_preserva_colunas_originais(self, salvar_lote):
        caminho = PASTA_FIXTURES / "cap_anonimizada_delimitada.xlsx"
        conteudo = caminho.read_bytes()
        inspecao = inspecionar_planilha(ArquivoEmMemoria(conteudo, caminho.name))
        aba = inspecao["abas"][0]
        colunas = aba["cabecalhos"]

        def registrar(_empresa_id, _nome, _hash, _conteudo, _aba, _tipo, _periodo, _mapa, linhas):
            self.assertEqual(len(linhas), 42)
            self.assertEqual(set(linhas[0]["dados_brutos"]), set(colunas))
            return {"duplicado": False, "lote_id": 77, "total_linhas": len(linhas)}

        salvar_lote.side_effect = registrar
        resultado = salvar_preparacao_confirmada(
            ArquivoEmMemoria(conteudo, caminho.name),
            7,
            aba["nome"],
            "lancamentos",
            "2026-01",
            {
                "data": colunas[0], "conta_contabil": colunas[1],
                "valor": colunas[2], "tipo": colunas[3],
                "descricao": colunas[4], "filial": colunas[5],
            },
            aba["linha_cabecalho"],
        )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(resultado["total_linhas"], 42)
        # A fixture cobre vários meses; linhas fora de janeiro entram no lote
        # com pendência explícita, sem serem descartadas silenciosamente.
        self.assertEqual(resultado["pendentes"], 40)


class EntradaOfxTestes(TestCase):
    CONTEUDO_OFX = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
ENCODING:USASCII

<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKACCTFROM><ACCTID>1234</BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260503<TRNAMT>-45.10<FITID>debito-001<NAME>Tarifa bancaria</STMTTRN>
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260504<TRNAMT>100.00<FITID>credito-001<MEMO>Recebimento cliente</STMTTRN>
</BANKTRANLIST><LEDGERBAL><BALAMT>154.90<DTASOF>20260504</LEDGERBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""

    def test_ofx_preserva_identificador_e_movimentos_sem_classificar(self):
        resultado = inspecionar_planilha(
            ArquivoEmMemoria(self.CONTEUDO_OFX, "extrato.ofx")
        )

        self.assertTrue(resultado["sucesso"])
        aba = resultado["abas"][0]
        self.assertEqual(aba["nome"], "OFX")
        self.assertEqual(aba["total_linhas"], 2)
        self.assertEqual(
            aba["linhas"][0]["valores"]["Identificador OFX"], "debito-001"
        )
        self.assertEqual(aba["linhas"][0]["valores"]["Data"], "03/05/2026")
        self.assertEqual(
            aba["linhas"][0]["valores"]["Descrição"], "Tarifa bancaria"
        )
        self.assertEqual(aba["linhas"][0]["valores"]["Tipo"], "D")
        self.assertEqual(aba["linhas"][1]["valores"]["Valor"], "100,00")
        self.assertEqual(resultado["metadados_origem"]["conta_bancaria"], "1234")
        self.assertEqual(resultado["metadados_origem"]["saldo_final"], "154.90")
        self.assertIsNone(resultado["metadados_origem"]["saldo_confere"])

    def test_ofx_repetido_no_mesmo_arquivo_e_sinalizado(self):
        conteudo = self.CONTEUDO_OFX.replace(b"credito-001", b"debito-001")
        resultado = inspecionar_planilha(ArquivoEmMemoria(conteudo, "duplicado.ofx"))

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["metadados_origem"]["identificadores_duplicados"],
            ["debito-001"],
        )
