from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    ArquivoEntradaTemporario,
    EstadoArquivoEntrada,
    EstadoTarefaAutomacao,
    ItemChecklistTrabalho,
    ModeloDocumentoEsperado,
    PerfilOrigemEntrada,
    TarefaAutomacao,
    TipoTarefaAutomacao,
)
from .servicos import automacoes, trabalho
from .servicos.contexto import ContextoTrabalho
from .servicos.entradas import receber_arquivo


class AutomacoesRecorrentesTest(TestCase):
    contexto = ContextoTrabalho(7, "Empresa teste", "2026-05")

    def setUp(self):
        self.usuario = get_user_model().objects.create_user("contadora", password="senha-segura")

    def test_modelo_de_documento_entra_no_novo_checklist_e_cria_verificacao(self):
        ModeloDocumentoEsperado.objects.create(
            empresa_id=7, nome="Extrato bancário", tipo_documento="extrato", dia_limite=5
        )
        with patch.object(trabalho, "obter_empresa_ativa", return_value={"id": 7}), \
             patch.object(automacoes, "obter_empresa_ativa", return_value={"id": 7}):
            competencia = trabalho.iniciar_competencia(self.contexto, self.usuario)
        self.assertTrue(ItemChecklistTrabalho.objects.filter(
            competencia_trabalho=competencia, titulo="Receber: Extrato bancário"
        ).exists())
        self.assertTrue(TarefaAutomacao.objects.filter(
            tipo=TipoTarefaAutomacao.VERIFICAR_PENDENCIAS,
            estado=EstadoTarefaAutomacao.CONCLUIDA,
        ).exists())

    def test_perfil_de_origem_e_processamento_sao_registrados_para_arquivo_recebido(self):
        PerfilOrigemEntrada.objects.create(
            empresa_id=7, nome="Banco", prefixo_nome="extrato_", tipo_documento="extrato"
        )
        arquivo = BytesIO(b"data;valor\n01/05/2026;10,00\n")
        arquivo.name = "extrato_maio.csv"
        inspecao = {"sucesso": True, "abas": [{"nome": "Dados", "linha_cabecalho": 0, "cabecalhos": [], "total_linhas": 0, "linhas": []}]}
        with patch("nucleo.servicos.automacoes.obter_empresa_ativa", return_value={"id": 7}), \
             patch("nucleo.servicos.entradas._existe_lote_final", return_value=None), \
             patch("nucleo.servicos.entradas.inspecionar_planilha", return_value=inspecao):
            temporario = receber_arquivo(arquivo, self.contexto, self.usuario)
        self.assertEqual(temporario.perfil_origem.nome, "Banco")
        tarefa = TarefaAutomacao.objects.get(arquivo_entrada=temporario)
        self.assertEqual(tarefa.estado, EstadoTarefaAutomacao.CONCLUIDA)
        self.assertEqual(tarefa.tipo, TipoTarefaAutomacao.PROCESSAR_ARQUIVO)

    def test_perfil_de_origem_persiste_modo_e_regra_de_competencia(self):
        with patch.object(automacoes, "obter_empresa_ativa", return_value={"id": 7}):
            perfil = automacoes.criar_perfil_origem(
                self.contexto,
                nome="Razão do ERP",
                prefixo_nome="razao_",
                pasta_referencia="",
                tipo_documento="lancamentos",
                modo="contabil_estruturado",
                regra_competencia="ampliada",
            )

        self.assertEqual(perfil.modo, "contabil_estruturado")
        self.assertEqual(perfil.regra_competencia, "ampliada")

    def test_falha_de_processamento_pode_ser_reexecutada_no_contexto(self):
        arquivo = ArquivoEntradaTemporario.objects.create(
            usuario=self.usuario, empresa_id=7, competencia="2026-05",
            nome_original="extrato.csv", extensao="csv", tamanho_bytes=10,
            arquivo_sha256="a" * 64, conteudo=b"data;valor", inspecao={},
            status=EstadoArquivoEntrada.EM_MAPEAMENTO,
        )
        tarefa = TarefaAutomacao.objects.create(
            empresa_id=7, competencia="2026-05", tipo=TipoTarefaAutomacao.PROCESSAR_ARQUIVO,
            estado=EstadoTarefaAutomacao.FALHA, arquivo_entrada=arquivo,
            tentativas=1, mensagem_erro="Falha anterior",
        )
        resultado = {"sucesso": True, "abas": []}
        with patch.object(automacoes, "obter_empresa_ativa", return_value={"id": 7}), \
             patch("nucleo.servicos.automacoes.inspecionar_planilha", return_value=resultado):
            tarefa = automacoes.reexecutar_tarefa(self.contexto, tarefa.id, self.usuario)
        self.assertEqual(tarefa.estado, EstadoTarefaAutomacao.CONCLUIDA)
        self.assertEqual(tarefa.tentativas, 2)

    def test_tarefa_de_outra_empresa_nao_pode_ser_reexecutada(self):
        tarefa = TarefaAutomacao.objects.create(
            empresa_id=8, competencia="2026-05", tipo=TipoTarefaAutomacao.VERIFICAR_PENDENCIAS,
            estado=EstadoTarefaAutomacao.FALHA,
        )
        with patch.object(automacoes, "obter_empresa_ativa", return_value={"id": 7}):
            with self.assertRaisesMessage(ValueError, "contexto selecionado"):
                automacoes.reexecutar_tarefa(self.contexto, tarefa.id, self.usuario)

    def test_tela_de_automacoes_exige_contexto_e_renderiza_fila(self):
        self.client.force_login(self.usuario)
        sessao = self.client.session
        sessao["contexto_trabalho"] = {
            "empresa_id": 7, "empresa_nome": "Empresa teste", "competencia": "2026-05",
        }
        sessao.save()
        with patch("nucleo.views.servico_automacoes.carregar", return_value={
            "modelos_documento": [], "perfis_origem": [], "tarefas": [], "lembretes": [],
        }):
            resposta = self.client.get(reverse("nucleo:automacoes"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Automatize o acompanhamento")
        self.assertContains(resposta, "Fila de processamento")
