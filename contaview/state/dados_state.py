import logging
from decimal import Decimal
import pandas as pd
import reflex as rx
import plotly.graph_objects as go
from contaview.styles import MINERAL, ECLIPSE
from contaview.utils.formatacao import formatar_moeda

logger = logging.getLogger(__name__)


class DadosState(rx.State):
    empresa_selecionada: str = ""
    periodo_selecionado: str = ""
    empresas_disponiveis: list[str] = []
    periodos_disponiveis: list[str] = []
    lancamentos: list[dict] = []
    carregando: bool = False
    tema_escuro: bool = False

    # Import
    importar_empresa: str = ""
    importar_cnpj: str = ""
    import_status: str = ""
    import_mensagem: str = ""
    import_registros: int = 0
    import_erros: list[str] = []
    import_avisos: list[str] = []
    carregando_importacao: bool = False

    # Prévia e preparação de planilhas de qualquer origem.
    preparacao_caminho_temp: str = ""
    preparacao_nome_arquivo: str = ""
    preparacao_abas: list[str] = []
    preparacao_aba: str = ""
    preparacao_linha_cabecalho: str = ""
    preparacao_linha_cabecalho_aplicada: str = ""
    preparacao_cabecalhos: list[str] = []
    preparacao_opcoes: list[str] = ["Não mapear"]
    preparacao_linhas_preview: list[list[str]] = []
    preparacao_total_linhas: int = 0
    preparacao_tipo_documento: str = ""
    preparacao_periodo: str = ""
    preparacao_mapa_data: str = "Não mapear"
    preparacao_mapa_valor: str = "Não mapear"
    preparacao_mapa_descricao: str = "Não mapear"
    preparacao_mapa_tipo: str = "Não mapear"
    preparacao_mapa_conta: str = "Não mapear"
    preparacao_mapa_filial: str = "Não mapear"
    preparacao_lote_id: int = 0
    erro_preparacao: str = ""
    lotes_preparados: list[dict] = []
    linhas_preparadas: list[dict] = []
    lote_selecionado_id: int = 0
    lote_selecionado_periodo: str = ""
    lote_selecionado_tipo: str = ""
    lote_total_linhas: int = 0
    pagina_linhas_preparadas: int = 0
    linha_edicao_aberta: bool = False
    linha_edicao_id: int = 0
    linha_edicao_data: str = ""
    linha_edicao_descricao: str = ""
    linha_edicao_valor: str = ""
    linha_edicao_tipo: str = ""
    linha_edicao_conta: str = ""
    linha_edicao_filial: str = ""

    # Nova empresa (tela de importacao)
    mostrar_nova_empresa: bool = False
    nova_empresa_nome: str = ""
    empresas_cnpj_map: dict[str, str] = {}

    # Confirmacao de substituicao
    confirmacao_pendente_empresa_id: int = 0
    confirmacao_pendente_periodo: str = ""
    confirmacao_pendente_caminho_temp: str = ""
    confirmacao_pendente_nome_arquivo: str = ""
    alert_dialog_open: bool = False

    # Dialogo de periodo manual (arquivo 100% ambiguo)
    dialog_periodo_aberto: bool = False
    periodo_manual_input: str = ""
    periodo_manual_caminho_temp: str = ""
    periodo_manual_nome_arquivo: str = ""

    # Conciliacao
    conciliacao_pares: list[dict] = []
    conciliacao_sem_par: list[dict] = []
    dados_conciliacao: dict = {}
    lotes_conciliacao_opcoes: list[str] = []
    lote_conciliacao_extrato: str = ""
    lote_conciliacao_referencia: str = ""
    conciliacao_cruzada_pares: list[dict] = []
    conciliacao_cruzada_candidatos: list[dict] = []
    conciliacao_cruzada_divergencias: list[dict] = []
    conciliacao_cruzada_sem_extrato: int = 0
    conciliacao_cruzada_sem_referencia: int = 0
    conciliacao_cruzada_faltantes_extrato: list[dict] = []
    conciliacao_cruzada_faltantes_referencia: list[dict] = []
    conciliacao_cruzada_mensagem: str = ""

    # Auditoria
    ocorrencias: list[dict] = []

    # Download
    download_data: str = ""
    download_filename: str = ""

    # Renomear empresa
    renomear_empresa_nome_atual: str = ""
    renomear_empresa_nome: str = ""
    dialog_renomear_aberto: bool = False

    def set_tema(self, valor: bool):
        self.tema_escuro = valor

    def set_importar_empresa(self, valor: str):
        self.importar_empresa = valor
        if valor in self.empresas_cnpj_map:
            cnpj = self.empresas_cnpj_map[valor]
            if cnpj:
                self.importar_cnpj = cnpj
        self.mostrar_nova_empresa = False

    def set_nova_empresa_nome(self, valor: str):
        self.nova_empresa_nome = valor
        self.importar_empresa = valor

    def toggle_nova_empresa(self):
        self.mostrar_nova_empresa = not self.mostrar_nova_empresa
        if self.mostrar_nova_empresa:
            self.importar_empresa = ""
            self.nova_empresa_nome = ""

    def set_importar_cnpj(self, valor: str):
        self.importar_cnpj = valor

    def set_preparacao_tipo_documento(self, valor: str):
        self.preparacao_tipo_documento = valor

    def set_preparacao_periodo(self, valor: str):
        self.preparacao_periodo = valor

    def set_preparacao_mapa_data(self, valor: str):
        self.preparacao_mapa_data = valor

    def set_preparacao_mapa_valor(self, valor: str):
        self.preparacao_mapa_valor = valor

    def set_preparacao_mapa_descricao(self, valor: str):
        self.preparacao_mapa_descricao = valor

    def set_preparacao_mapa_tipo(self, valor: str):
        self.preparacao_mapa_tipo = valor

    def set_preparacao_mapa_conta(self, valor: str):
        self.preparacao_mapa_conta = valor

    def set_preparacao_mapa_filial(self, valor: str):
        self.preparacao_mapa_filial = valor

    def _configurar_aba_preparacao(self, aba: dict):
        from contaview.logic.mapeamento_colunas import sugerir_mapeamento

        self.preparacao_aba = aba["nome"]
        self.preparacao_linha_cabecalho = str(aba["linha_cabecalho"])
        self.preparacao_linha_cabecalho_aplicada = self.preparacao_linha_cabecalho
        self.preparacao_cabecalhos = aba["cabecalhos"]
        self.preparacao_opcoes = ["Não mapear", *aba["cabecalhos"]]
        self.preparacao_total_linhas = aba["total_linhas"]
        self.preparacao_linhas_preview = [
            [str(linha["valores"].get(coluna, "")) for coluna in aba["cabecalhos"]]
            for linha in aba["linhas"][:15]
        ]
        sugestao = sugerir_mapeamento(aba["cabecalhos"])
        self.preparacao_mapa_data = sugestao.get("data", "Não mapear")
        self.preparacao_mapa_valor = sugestao.get("valor", "Não mapear")
        self.preparacao_mapa_descricao = sugestao.get("descricao", "Não mapear")
        self.preparacao_mapa_tipo = sugestao.get("tipo", "Não mapear")
        self.preparacao_mapa_conta = sugestao.get("conta_contabil", "Não mapear")
        self.preparacao_mapa_filial = sugestao.get("filial", "Não mapear")

    async def handle_upload_previa(self, files: list[rx.UploadFile]):
        import io
        from contaview.logic import importacao as logic_importacao

        self.import_status = ""
        self.import_mensagem = ""
        self.preparacao_lote_id = 0
        self.carregando_importacao = True
        yield
        caminho_temp = ""
        try:
            if not files:
                raise ValueError("Nenhum arquivo selecionado.")
            if not self.importar_empresa.strip():
                raise ValueError("Selecione ou cadastre a empresa antes de enviar o arquivo.")
            arquivo = files[0]
            nome_arquivo = (
                getattr(arquivo, "filename", None)
                or getattr(arquivo, "name", None)
                or "arquivo"
            )
            conteudo = await arquivo.read()
            caminho_temp = logic_importacao.salvar_arquivo_temp(conteudo, nome_arquivo)
            leitor = io.BytesIO(conteudo)
            leitor.name = nome_arquivo
            resultado = logic_importacao.prever_importacao(leitor)
            if not resultado.get("sucesso"):
                raise ValueError(resultado.get("erro", "Falha ao ler o arquivo."))

            logic_importacao.limpar_arquivo_temp(self.preparacao_caminho_temp)
            self.preparacao_caminho_temp = caminho_temp
            caminho_temp = ""
            self.preparacao_nome_arquivo = nome_arquivo
            self.preparacao_abas = [aba["nome"] for aba in resultado["abas"]]
            self._configurar_aba_preparacao(resultado["abas"][0])
            self.import_status = "previa"
            self.import_mensagem = (
                f"{self.preparacao_total_linhas} linha(s) identificada(s). "
                "Confira a aba, o tipo de documento e as colunas."
            )
        except Exception as exc:
            self.import_status = "erro"
            self.import_mensagem = str(exc)
            logger.error("Falha na prévia da importação: %s", exc)
        finally:
            self.carregando_importacao = False
            logic_importacao.limpar_arquivo_temp(caminho_temp)

    def set_preparacao_aba(self, nome_aba: str):
        import io
        from contaview.logic import importacao as logic_importacao

        try:
            with open(self.preparacao_caminho_temp, "rb") as arquivo:
                leitor = io.BytesIO(arquivo.read())
            leitor.name = self.preparacao_nome_arquivo
            resultado = logic_importacao.prever_importacao(leitor)
            if not resultado.get("sucesso"):
                raise ValueError(resultado.get("erro", "Falha ao ler a aba."))
            aba = next(
                (item for item in resultado["abas"] if item["nome"] == nome_aba), None
            )
            if aba is None:
                raise ValueError("Aba não encontrada.")
            self._configurar_aba_preparacao(aba)
        except Exception as exc:
            self.import_status = "erro"
            self.import_mensagem = str(exc)

    def set_preparacao_linha_cabecalho(self, valor: str):
        self.preparacao_linha_cabecalho = valor

    def aplicar_linha_cabecalho(self):
        import io
        from contaview.logic import importacao as logic_importacao

        try:
            numero = int(self.preparacao_linha_cabecalho.strip())
            with open(self.preparacao_caminho_temp, "rb") as arquivo:
                leitor = io.BytesIO(arquivo.read())
            leitor.name = self.preparacao_nome_arquivo
            resultado = logic_importacao.prever_importacao(
                leitor, linha_cabecalho=numero, aba_alvo=self.preparacao_aba
            )
            if not resultado.get("sucesso"):
                raise ValueError(resultado.get("erro", "Falha ao identificar cabeçalho."))
            aba = next(
                (item for item in resultado["abas"] if item["nome"] == self.preparacao_aba),
                None,
            )
            if aba is None:
                raise ValueError("A aba selecionada não contém linhas de dados.")
            self._configurar_aba_preparacao(aba)
            self.import_status = "previa"
            self.import_mensagem = "Cabeçalho aplicado. Confira novamente o mapeamento e as linhas."
        except (ValueError, OSError) as exc:
            self.import_status = "erro"
            self.import_mensagem = str(exc)

    def cancelar_preparacao(self):
        from contaview.logic import importacao as logic_importacao

        logic_importacao.limpar_arquivo_temp(self.preparacao_caminho_temp)
        self.preparacao_caminho_temp = ""
        self.preparacao_nome_arquivo = ""
        self.preparacao_abas = []
        self.preparacao_aba = ""
        self.preparacao_linha_cabecalho = ""
        self.preparacao_linha_cabecalho_aplicada = ""
        self.preparacao_cabecalhos = []
        self.preparacao_linhas_preview = []
        self.preparacao_total_linhas = 0
        self.import_status = ""
        self.import_mensagem = ""

    def confirmar_preparacao(self):
        import io
        import re
        from contaview.logic import importacao as logic_importacao

        if not self.preparacao_caminho_temp:
            self.import_status = "erro"
            self.import_mensagem = "Envie uma planilha antes de confirmar."
            return
        tipos_documento = {
            "Extrato bancário": "extrato",
            "Folha de pagamento": "folha",
            "Notas": "notas",
            "Lançamentos": "lancamentos",
            "Outro": "outro",
        }
        if self.preparacao_tipo_documento not in tipos_documento:
            self.import_status = "erro"
            self.import_mensagem = "Escolha o tipo de documento antes de confirmar."
            return
        if self.preparacao_linha_cabecalho != self.preparacao_linha_cabecalho_aplicada:
            self.import_status = "erro"
            self.import_mensagem = "Aplique a linha do cabeçalho antes de salvar o lote."
            return

        periodo = self.preparacao_periodo.strip()
        if periodo:
            if not re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", periodo):
                self.import_status = "erro"
                self.import_mensagem = "Informe o período como MM/AAAA ou deixe em branco."
                return
            periodo = periodo[3:] + "-" + periodo[:2]

        campos = {
            "data": self.preparacao_mapa_data,
            "valor": self.preparacao_mapa_valor,
            "descricao": self.preparacao_mapa_descricao,
            "tipo": self.preparacao_mapa_tipo,
            "conta_contabil": self.preparacao_mapa_conta,
            "filial": self.preparacao_mapa_filial,
        }
        mapeamento = {
            campo: coluna for campo, coluna in campos.items()
            if coluna and coluna != "Não mapear"
        }
        try:
            with open(self.preparacao_caminho_temp, "rb") as arquivo:
                leitor = io.BytesIO(arquivo.read())
            leitor.name = self.preparacao_nome_arquivo
            resultado = logic_importacao.executar_preparacao(
                leitor, self.importar_empresa, self.importar_cnpj.strip() or None,
                self.preparacao_aba, tipos_documento[self.preparacao_tipo_documento],
                periodo or None, mapeamento, int(self.preparacao_linha_cabecalho),
            )
            if not resultado.get("sucesso"):
                raise ValueError(resultado.get("erro", "Falha ao preparar o arquivo."))
            self.preparacao_lote_id = resultado["lote_id"]
            self.import_status = "sucesso"
            if resultado.get("duplicado"):
                self.import_mensagem = "Este arquivo já foi preparado para a empresa e o período selecionados."
            else:
                self.import_mensagem = (
                    f"Lote {resultado['lote_id']} preparado com "
                    f"{resultado['total_linhas']} linha(s); "
                    f"{resultado['pendentes']} com pendência(s)."
                )
            self.empresa_selecionada = self.importar_empresa.strip()
            self.periodo_selecionado = ""
            logic_importacao.limpar_arquivo_temp(self.preparacao_caminho_temp)
            self.preparacao_caminho_temp = ""
            self.preparacao_abas = []
            self.preparacao_cabecalhos = []
            self.preparacao_linhas_preview = []
            self.preparacao_aba = ""
        except ValueError as exc:
            self.import_status = "erro"
            self.import_mensagem = str(exc)
        except Exception as exc:
            self.import_status = "erro"
            self.import_mensagem = "Não foi possível preparar o arquivo. Verifique a conexão com o banco."
            logger.error("Falha ao confirmar preparação: %s", type(exc).__name__)

    def carregar_lotes_preparados(self):
        from contaview.logic import database

        self.lotes_preparados = []
        self.lotes_conciliacao_opcoes = []
        self.linhas_preparadas = []
        self.lote_selecionado_id = 0
        self.erro_preparacao = ""
        empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
        if empresa_id is None:
            return
        try:
            lotes = database.listar_lotes_preparacao(
                empresa_id, self.periodo_selecionado or None
            )
            self.lotes_preparados = [
                {
                    **lote,
                    "periodo_exibicao": (
                        lote["periodo"][5:] + "/" + lote["periodo"][:4]
                        if lote["periodo"] else "Sem período"
                    ),
                    "criado_em_exibicao": lote["criado_em"].strftime("%d/%m/%Y"),
                }
                for lote in lotes
            ]
            self.lotes_conciliacao_opcoes = [
                f"{lote['id']} | {lote['nome_arquivo']} | {lote['tipo_documento']}"
                for lote in lotes
            ]
        except Exception as exc:
            logger.error("Falha ao carregar lotes preparados: %s", exc)
            self.erro_preparacao = "Não foi possível carregar os dados preparados."

    def selecionar_lote_preparacao(self, lote_id: int):
        lote = next(
            (item for item in self.lotes_preparados if item["id"] == lote_id), None
        )
        if lote is None:
            self.erro_preparacao = "Lote não encontrado para a empresa selecionada."
            return
        self.lote_selecionado_id = lote_id
        self.lote_selecionado_periodo = lote["periodo"] or ""
        self.lote_selecionado_tipo = lote["tipo_documento"]
        self.lote_total_linhas = lote["total_linhas"]
        self.pagina_linhas_preparadas = 0
        self.carregar_linhas_preparadas()

    def carregar_linhas_preparadas(self):
        from contaview.logic import database

        empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
        if empresa_id is None or not self.lote_selecionado_id:
            self.linhas_preparadas = []
            return
        try:
            linhas = database.carregar_linhas_preparadas(
                empresa_id, self.lote_selecionado_id,
                limite=100, deslocamento=self.pagina_linhas_preparadas * 100,
            )
            self.linhas_preparadas = [
                {
                    **linha,
                    "data_exibicao": (
                        linha["data"].strftime("%d/%m/%Y") if linha["data"] else ""
                    ),
                    "valor_exibicao": (
                        formatar_moeda(linha["valor"]) if linha["valor"] is not None else ""
                    ),
                    "pendencias_exibicao": "; ".join(linha["pendencias"] or []),
                }
                for linha in linhas
            ]
            self.erro_preparacao = ""
        except Exception as exc:
            logger.error("Falha ao carregar linhas preparadas: %s", exc)
            self.linhas_preparadas = []
            self.erro_preparacao = "Não foi possível carregar as linhas do lote."

    def proxima_pagina_preparada(self):
        if (self.pagina_linhas_preparadas + 1) * 100 < self.lote_total_linhas:
            self.pagina_linhas_preparadas += 1
            self.carregar_linhas_preparadas()

    def pagina_anterior_preparada(self):
        if self.pagina_linhas_preparadas > 0:
            self.pagina_linhas_preparadas -= 1
            self.carregar_linhas_preparadas()

    def abrir_edicao_linha(self, linha_id: int):
        linha = next(
            (item for item in self.linhas_preparadas if item["id"] == linha_id), None
        )
        if linha is None:
            self.erro_preparacao = "Linha não encontrada nesta página."
            return
        self.linha_edicao_id = linha_id
        self.linha_edicao_data = linha["data_exibicao"]
        self.linha_edicao_descricao = linha["descricao"] or ""
        self.linha_edicao_valor = (
            str(linha["valor"]).replace(".", ",")
            if linha["valor"] is not None else ""
        )
        self.linha_edicao_tipo = linha["tipo"] or ""
        self.linha_edicao_conta = linha["conta_contabil"] or ""
        self.linha_edicao_filial = linha["filial"] or ""
        self.linha_edicao_aberta = True

    def set_linha_edicao_data(self, valor: str):
        self.linha_edicao_data = valor

    def set_linha_edicao_descricao(self, valor: str):
        self.linha_edicao_descricao = valor

    def set_linha_edicao_valor(self, valor: str):
        self.linha_edicao_valor = valor

    def set_linha_edicao_tipo(self, valor: str):
        self.linha_edicao_tipo = valor

    def set_linha_edicao_conta(self, valor: str):
        self.linha_edicao_conta = valor

    def set_linha_edicao_filial(self, valor: str):
        self.linha_edicao_filial = valor

    def cancelar_edicao_linha(self):
        self.linha_edicao_aberta = False
        self.linha_edicao_id = 0

    def salvar_edicao_linha(self):
        from contaview.logic import database
        from contaview.logic.importacao import validar_edicao_linha

        empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
        if empresa_id is None or not self.linha_edicao_id:
            self.erro_preparacao = "Selecione uma empresa e uma linha para corrigir."
            return
        campos, pendencias = validar_edicao_linha(
            {
                "data": self.linha_edicao_data,
                "descricao": self.linha_edicao_descricao,
                "valor": self.linha_edicao_valor,
                "tipo": self.linha_edicao_tipo,
                "conta_contabil": self.linha_edicao_conta,
                "filial": self.linha_edicao_filial,
            },
            self.lote_selecionado_tipo,
            self.lote_selecionado_periodo or None,
        )
        try:
            database.atualizar_linha_preparada(
                empresa_id, self.linha_edicao_id, campos, pendencias
            )
            self.cancelar_edicao_linha()
            self.carregar_linhas_preparadas()
        except Exception as exc:
            logger.error("Falha ao corrigir linha preparada: %s", exc)
            self.erro_preparacao = "Não foi possível salvar a correção."

    def exportar_lote_preparado(self, formato: str):
        from contaview.logic import database
        from contaview.logic.relatorios import exportar_lote_preparado

        empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
        if empresa_id is None or not self.lote_selecionado_id:
            self.erro_preparacao = "Selecione uma empresa e um lote para exportar."
            return
        try:
            linhas = database.carregar_linhas_para_exportacao(
                empresa_id, self.lote_selecionado_id
            )
            conteudo = exportar_lote_preparado(linhas, formato)
            nome = f"dados_preparados_lote_{self.lote_selecionado_id}.{formato}"
            return rx.download(data=conteudo, filename=nome)
        except ValueError as exc:
            self.erro_preparacao = str(exc)
        except Exception as exc:
            logger.error("Falha ao exportar lote preparado: %s", type(exc).__name__)
            self.erro_preparacao = "Não foi possível exportar o lote."

    def exportar_lote_csv(self):
        return self.exportar_lote_preparado("csv")

    def exportar_lote_xlsx(self):
        return self.exportar_lote_preparado("xlsx")

    def set_lote_conciliacao_extrato(self, valor: str):
        self.lote_conciliacao_extrato = valor

    def set_lote_conciliacao_referencia(self, valor: str):
        self.lote_conciliacao_referencia = valor

    def _carregar_fontes_conciliacao(self) -> tuple[list[dict], list[dict]]:
        from contaview.logic import database

        empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
        if empresa_id is None:
            raise ValueError("Selecione uma empresa para conciliar.")
        try:
            id_extrato = int(self.lote_conciliacao_extrato.split(" | ", 1)[0])
            id_referencia = int(self.lote_conciliacao_referencia.split(" | ", 1)[0])
        except ValueError as exc:
            raise ValueError("Selecione dois lotes para conciliar.") from exc
        if id_extrato == id_referencia:
            raise ValueError("Selecione dois lotes diferentes.")
        ids_permitidos = {lote["id"] for lote in self.lotes_preparados}
        if id_extrato not in ids_permitidos or id_referencia not in ids_permitidos:
            raise ValueError("Os lotes devem pertencer à empresa selecionada.")
        return (
            database.carregar_linhas_para_exportacao(empresa_id, id_extrato),
            database.carregar_linhas_para_exportacao(empresa_id, id_referencia),
        )

    def executar_conciliacao_fontes(self):
        from contaview.logic.conciliacao import conciliar_fontes

        self.conciliacao_cruzada_mensagem = ""
        self.conciliacao_cruzada_pares = []
        self.conciliacao_cruzada_candidatos = []
        self.conciliacao_cruzada_divergencias = []
        self.conciliacao_cruzada_sem_extrato = 0
        self.conciliacao_cruzada_sem_referencia = 0
        self.conciliacao_cruzada_faltantes_extrato = []
        self.conciliacao_cruzada_faltantes_referencia = []
        try:
            extrato, referencia = self._carregar_fontes_conciliacao()
            resultado = conciliar_fontes(extrato, referencia)
            self.conciliacao_cruzada_pares = resultado["pares_confirmados"][:100]
            self.conciliacao_cruzada_candidatos = resultado["candidatos"][:100]
            self.conciliacao_cruzada_divergencias = resultado["divergencias_valor"][:100]
            self.conciliacao_cruzada_sem_extrato = len(
                resultado["faltantes_extrato"]
            )
            self.conciliacao_cruzada_sem_referencia = len(
                resultado["faltantes_referencia"]
            )
            self.conciliacao_cruzada_faltantes_extrato = [
                {
                    "numero_linha": linha["numero_linha"],
                    "data": linha["data"].strftime("%d/%m/%Y"),
                    "descricao": linha.get("descricao") or "",
                    "valor": str(linha["valor"]).replace(".", ","),
                }
                for linha in resultado["faltantes_extrato"][:100]
            ]
            self.conciliacao_cruzada_faltantes_referencia = [
                {
                    "numero_linha": linha["numero_linha"],
                    "data": linha["data"].strftime("%d/%m/%Y"),
                    "descricao": linha.get("descricao") or "",
                    "valor": str(linha["valor"]).replace(".", ","),
                }
                for linha in resultado["faltantes_referencia"][:100]
            ]
            self.conciliacao_cruzada_mensagem = (
                f"{len(resultado['pares_confirmados'])} par(es) exato(s); "
                f"{len(resultado['candidatos'])} candidato(s) para revisão; "
                f"{len(resultado['divergencias_valor'])} diferença(s) de valor; "
                f"{self.conciliacao_cruzada_sem_extrato + self.conciliacao_cruzada_sem_referencia} "
                "linha(s) sem correspondência. A tela mostra até 100 itens por grupo; "
                "o CSV contém o resultado completo."
            )
        except ValueError as exc:
            self.conciliacao_cruzada_mensagem = str(exc)
        except Exception as exc:
            self.conciliacao_cruzada_mensagem = "Não foi possível cruzar as fontes."
            logger.error("Falha na conciliação entre fontes: %s", type(exc).__name__)

    def exportar_conciliacao_fontes(self):
        from contaview.logic.conciliacao import conciliar_fontes
        from contaview.logic.relatorios import exportar_cruzamento_fontes

        try:
            extrato, referencia = self._carregar_fontes_conciliacao()
            resultado = conciliar_fontes(extrato, referencia)
            conteudo = exportar_cruzamento_fontes(resultado, extrato, referencia)
            return rx.download(data=conteudo, filename="cruzamento_fontes.csv")
        except ValueError as exc:
            self.conciliacao_cruzada_mensagem = str(exc)
        except Exception as exc:
            logger.error("Falha ao exportar cruzamento: %s", type(exc).__name__)
            self.conciliacao_cruzada_mensagem = "Não foi possível exportar o cruzamento."

    @staticmethod
    def _derivar_nome_empresa(nome_arquivo: str) -> str:
        nome_base = nome_arquivo.rsplit(".", 1)[0]
        return nome_base.replace("_", " ").strip()

    def _resolver_empresa_id(self, nome: str) -> int | None:
        from contaview.logic import database

        try:
            df = database.listar_empresas()
            row = df[df["nome"] == nome]
            if not row.empty:
                return int(row.iloc[0]["id"])
        except Exception as exc:
            logger.error("Erro ao resolver empresa_id: %s", exc)
        return None

    def carregar_empresas(self):
        from contaview.state.tema_state import TemaState
        from contaview.logic import database

        self.tema_escuro = TemaState.tema_escuro
        try:
            df = database.listar_empresas()
            self.empresas_disponiveis = df["nome"].tolist()
            self.empresas_cnpj_map = dict(zip(df["nome"], df["cnpj"]))
        except Exception as exc:
            logger.error("Erro ao carregar empresas: %s", exc)
            self.empresas_disponiveis = []
            self.empresas_cnpj_map = {}

    def set_empresa_selecionada(self, empresa: str):
        self.empresa_selecionada = empresa
        self.carregar_periodos()
        self.carregar_lotes_preparados()

    def carregar_periodos(self):
        from contaview.logic import database

        if not self.empresa_selecionada:
            self.periodos_disponiveis = []
            self.periodo_selecionado = ""
            return
        try:
            empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
            if empresa_id is None:
                self.periodos_disponiveis = []
                return
            periodos = database.listar_periodos(empresa_id)
            try:
                periodos = sorted(
                    set(periodos + database.listar_periodos_preparacao(empresa_id)),
                    reverse=True,
                )
            except Exception:
                # Bancos anteriores à migração ainda exibem os períodos existentes.
                pass
            self.periodos_disponiveis = [
                p[-2:] + "/" + p[:4] for p in periodos
            ]
        except Exception as exc:
            logger.error("Erro ao carregar periodos: %s", exc)
            self.periodos_disponiveis = []

    def set_periodo_selecionado(self, periodo: str):
        if not periodo:
            self.periodo_selecionado = ""
        elif "/" in periodo:
            self.periodo_selecionado = periodo[-4:] + "-" + periodo[:2]
        else:
            self.periodo_selecionado = periodo
        self.carregar_lancamentos()
        self.carregar_lotes_preparados()

    def carregar_lancamentos(self):
        from contaview.logic import database

        if not self.empresa_selecionada:
            self.lancamentos = []
            self.conciliacao_pares = []
            self.conciliacao_sem_par = []
            self.ocorrencias = []
            return
        self.carregando = True
        try:
            empresa_id = (
                self._resolver_empresa_id(self.empresa_selecionada)
                if self.empresa_selecionada
                else None
            )
            if empresa_id is None:
                self.lancamentos = []
                return
            periodo = self.periodo_selecionado if self.periodo_selecionado else None
            df = database.carregar_lancamentos(empresa_id, periodo)
            if not df.empty:
                df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y")
            self.lancamentos = df.to_dict("records")
        except Exception as exc:
            logger.error("Erro ao carregar lancamentos: %s", exc)
            self.lancamentos = []
        finally:
            self.carregando = False

        self._carregar_conciliacao_dados()
        self._carregar_ocorrencias_dados()

    def _executar_rotinas_pos_importacao(
        self,
        df_salvo: pd.DataFrame | None,
        empresa_id: int,
        periodo: str,
    ) -> str:
        from contaview.logic import auditoria as logic_auditoria
        from contaview.logic import conciliacao as logic_conciliacao

        if df_salvo is None or df_salvo.empty or not empresa_id or not periodo:
            return ""

        try:
            conc_res = logic_conciliacao.conciliar_partidas(df_salvo)
            logic_conciliacao.salvar_resultado_conciliacao(
                empresa_id, periodo, conc_res
            )
            oc_res = logic_auditoria.auditar_lancamentos(df_salvo)
            logic_auditoria.salvar_ocorrencias(oc_res, empresa_id)
            resumo = logic_auditoria.resumo_auditoria(oc_res)
            return (
                f" Auditoria: {resumo['alta']} alta(s), "
                f"{resumo['media']} media(s), "
                f"{resumo['baixa']} baixa(s)."
            )
        except Exception as exc:
            logger.warning("Auditoria/conciliacao automatica apos import: %s", exc)
            return ""

    def _preparar_confirmacao_substituicao(
        self, resultado: dict, nome_arquivo: str, caminho_temp: str,
    ):
        self.confirmacao_pendente_empresa_id = resultado["empresa_id"]
        self.confirmacao_pendente_periodo = resultado["periodo"]
        self.confirmacao_pendente_caminho_temp = caminho_temp
        self.confirmacao_pendente_nome_arquivo = nome_arquivo
        self.alert_dialog_open = True
        self.import_status = "confirmacao"

    def _carregar_conciliacao_dados(self):
        from contaview.logic.conciliacao import conciliar_partidas

        self.dados_conciliacao = {}
        self.conciliacao_pares = []
        self.conciliacao_sem_par = []
        try:
            if not self.lancamentos:
                return
            df = pd.DataFrame(self.lancamentos)
            resultado = conciliar_partidas(df)
            self.dados_conciliacao = {
                "pares_ok": resultado["pares_ok"],
                "sem_par": resultado["sem_par"],
            }
            if not resultado["df_pares"].empty:
                self.conciliacao_pares = resultado["df_pares"].to_dict("records")
            if not resultado["df_sem_par"].empty:
                self.conciliacao_sem_par = resultado["df_sem_par"].to_dict("records")
        except Exception as exc:
            logger.error("Erro ao carregar conciliacao: %s", exc)

    def _carregar_ocorrencias_dados(self):
        from contaview.logic import database

        self.ocorrencias = []
        try:
            empresa_id = (
                self._resolver_empresa_id(self.empresa_selecionada)
                if self.empresa_selecionada
                else None
            )
            periodo = self.periodo_selecionado if self.periodo_selecionado else None
            if empresa_id and periodo:
                df = database.carregar_ocorrencias(empresa_id, periodo)
                if not df.empty:
                    self.ocorrencias = df.to_dict("records")
        except Exception as exc:
            logger.error("Erro ao carregar ocorrencias: %s", exc)

    async def handle_upload_import(self, files: list[rx.UploadFile]):
        import io
        from contaview.logic import importacao as logic_importacao

        self.carregando_importacao = True
        self.import_status = ""
        self.import_mensagem = ""
        self.import_erros = []
        self.import_avisos = []
        self.import_registros = 0
        caminho_temp = ""
        yield

        try:
            if not files:
                self.import_status = "erro"
                self.import_mensagem = "Nenhum arquivo selecionado."
                return

            file = files[0]
            content = await file.read()
            nome_arquivo = file.filename or "arquivo"
            empresa_nome = self.importar_empresa.strip()
            if not empresa_nome:
                self.import_status = "erro"
                self.import_mensagem = "Selecione ou cadastre a empresa antes de importar."
                return

            caminho_temp = logic_importacao.salvar_arquivo_temp(content, nome_arquivo)

            buf = io.BytesIO(content)
            buf.name = nome_arquivo

            resultado = logic_importacao.executar_importacao(
                buf,
                empresa_nome,
                self.importar_cnpj.strip() or None,
            )

            if resultado.get("periodo_necessario"):
                df_parcial = resultado["df"]
                caminho_pkl = caminho_temp + ".pkl"
                df_parcial.to_pickle(caminho_pkl)
                self.periodo_manual_caminho_temp = caminho_pkl
                self.periodo_manual_nome_arquivo = nome_arquivo
                self.dialog_periodo_aberto = True
                self.import_status = "periodo_necessario"
                self.import_avisos = resultado.get("avisos", [])
                self.import_mensagem = (
                    "Nao foi possivel determinar o periodo contabil do arquivo. "
                    "Informe o periodo manualmente."
                )
                return

            if resultado.get("requer_confirmacao"):
                self._preparar_confirmacao_substituicao(
                    resultado, nome_arquivo, caminho_temp,
                )
                caminho_temp = ""
                return

            logic_importacao.limpar_arquivo_temp(caminho_temp)
            caminho_temp = ""

            if resultado.get("sucesso"):
                registros = resultado["registros_salvos"]
                self.import_status = "sucesso"
                self.import_registros = registros
                self.import_avisos = resultado.get("avisos", [])
                self.import_mensagem = f"{registros} lancamento(s) importado(s) com sucesso."

                empresa_id = resultado["empresa_id"]
                periodo = resultado["periodo"]
                df_salvo = resultado.get("df")

                if df_salvo is not None and not df_salvo.empty and empresa_id and periodo:
                    self.import_mensagem += self._executar_rotinas_pos_importacao(
                        df_salvo, empresa_id, periodo
                    )

                self.importar_empresa = ""
                self.importar_cnpj = ""
                self.empresa_selecionada = ""
                self.periodo_selecionado = ""
                self.lancamentos = []
                return

            self.import_status = "erro"
            erro_msg = resultado.get("erro", "Erro desconhecido ao importar.")
            self.import_mensagem = erro_msg
            if ";" in erro_msg:
                self.import_erros = [e.strip() for e in erro_msg.split(";") if e.strip()]
            else:
                self.import_erros = [erro_msg]

        except Exception as exc:
            logger.error("Erro no handle_upload_import: %s", exc)
            self.import_status = "erro"
            self.import_mensagem = f"Erro interno: {exc}"
            self.import_erros = [str(exc)]
        finally:
            self.carregando_importacao = False
            logic_importacao.limpar_arquivo_temp(caminho_temp)

    def set_periodo_manual_input(self, valor: str):
        self.periodo_manual_input = valor

    def definir_periodo_manual(self):
        import os
        import re
        import pandas as pd
        from contaview.logic import importacao as logic_importacao
        from contaview.logic.parsers import resolver_datas_para_periodo

        periodo = self.periodo_manual_input.strip()

        if not re.match(r"^\d{2}/\d{4}$", periodo):
            self.import_mensagem = "Formato invalido. Use MM/AAAA (ex: 05/2026)."
            return

        mes, ano = int(periodo[:2]), int(periodo[3:])
        if not 1 <= mes <= 12:
            self.import_mensagem = "Mes invalido. Use MM/AAAA (ex: 05/2026)."
            return

        caminho_pkl = self.periodo_manual_caminho_temp
        caminho_original = ""
        if caminho_pkl and caminho_pkl.endswith(".pkl"):
            caminho_original = caminho_pkl[:-4]

        manter_arquivo = False
        try:
            df = pd.read_pickle(caminho_pkl)
            nome_arquivo = self.periodo_manual_nome_arquivo
            empresa_nome = self.importar_empresa.strip()
            if not empresa_nome:
                self.import_mensagem = "Selecione ou cadastre a empresa antes de importar."
                manter_arquivo = True
                return
            empresa_cnpj = self.importar_cnpj.strip() or None

            df = df.copy()
            if "data" not in df.columns:
                self.import_mensagem = "O arquivo não contém datas para confirmar."
                manter_arquivo = True
                return
            datas, linhas_invalidas = resolver_datas_para_periodo(
                df["data"], f"{ano}-{mes:02d}"
            )
            if linhas_invalidas:
                self.import_mensagem = (
                    "O período informado não resolve as datas das linhas: "
                    + ", ".join(map(str, linhas_invalidas[:10]))
                    + ("..." if len(linhas_invalidas) > 10 else "")
                )
                manter_arquivo = True
                return
            df["data"] = pd.to_datetime(datas)
            df["periodo"] = f"{ano}-{mes:02d}"

            self.dialog_periodo_aberto = False
            self.carregando_importacao = True
            self.import_status = ""
            self.import_mensagem = "Periodo definido. Processando importacao..."
            yield

            resultado = logic_importacao.executar_importacao_dataframe(
                df,
                empresa_nome,
                empresa_cnpj,
                nome_arquivo,
            )

            if resultado.get("requer_confirmacao"):
                self._preparar_confirmacao_substituicao(
                    resultado, nome_arquivo, caminho_pkl,
                )
                manter_arquivo = True
                return

            if resultado.get("sucesso"):
                registros = resultado["registros_salvos"]
                self.import_status = "sucesso"
                self.import_registros = registros
                self.import_avisos = resultado.get("avisos", [])
                self.import_mensagem = (
                    f"{registros} lancamento(s) importado(s) com sucesso."
                )

                empresa_id = resultado["empresa_id"]
                periodo_salvo = resultado["periodo"]
                df_salvo = resultado.get("df")
                self.import_mensagem += self._executar_rotinas_pos_importacao(
                    df_salvo, empresa_id, periodo_salvo
                )

                self.importar_empresa = ""
                self.importar_cnpj = ""
                self.empresa_selecionada = ""
                self.periodo_selecionado = ""
                self.lancamentos = []
                return

            self.import_status = "erro"
            erro_msg = resultado.get("erro", "Erro desconhecido ao importar.")
            self.import_mensagem = erro_msg
            if ";" in erro_msg:
                self.import_erros = [e.strip() for e in erro_msg.split(";") if e.strip()]
            else:
                self.import_erros = [erro_msg]

        except Exception as exc:
            logger.error("Erro ao definir periodo manual: %s", exc)
            self.import_status = "erro"
            self.import_mensagem = f"Erro ao processar periodo: {exc}"
            self.import_erros = [str(exc)]
        finally:
            self.carregando_importacao = False
            self.periodo_manual_input = ""
            if not manter_arquivo:
                logic_importacao.limpar_arquivo_temp(caminho_pkl)
                logic_importacao.limpar_arquivo_temp(caminho_original)
                self.periodo_manual_caminho_temp = ""
                self.periodo_manual_nome_arquivo = ""

    def cancelar_periodo_manual(self):
        from contaview.logic import importacao as logic_importacao

        self.dialog_periodo_aberto = False
        self.periodo_manual_input = ""
        self.import_status = ""
        self.import_mensagem = ""
        caminho_pkl = self.periodo_manual_caminho_temp
        caminho_original = ""
        if caminho_pkl and caminho_pkl.endswith(".pkl"):
            caminho_original = caminho_pkl[:-4]
        logic_importacao.limpar_arquivo_temp(caminho_pkl)
        logic_importacao.limpar_arquivo_temp(caminho_original)
        self.periodo_manual_caminho_temp = ""
        self.periodo_manual_nome_arquivo = ""

    def confirmar_substituicao(self):
        from contaview.logic import importacao as logic_importacao

        caminho_temp = self.confirmacao_pendente_caminho_temp
        try:
            resultado = logic_importacao.executar_importacao_confirmada(
                caminho_temp,
                self.confirmacao_pendente_empresa_id,
                self.confirmacao_pendente_periodo,
                self.confirmacao_pendente_nome_arquivo,
            )
            caminho_temp = ""

            if resultado.get("sucesso"):
                registros = resultado["registros_salvos"]
                self.import_status = "sucesso"
                self.import_registros = registros
                self.import_avisos = resultado.get("avisos", [])
                self.import_mensagem = (
                    f"Periodo substituido. {registros} lancamento(s) salvos."
                )

                empresa_id = self.confirmacao_pendente_empresa_id
                periodo = self.confirmacao_pendente_periodo
                df_salvo = resultado.get("df")

                if df_salvo is not None and not df_salvo.empty and empresa_id and periodo:
                    self.import_mensagem += self._executar_rotinas_pos_importacao(
                        df_salvo, empresa_id, periodo
                    )

                self.importar_empresa = ""
                self.importar_cnpj = ""
            else:
                self.import_status = "erro"
                self.import_mensagem = resultado.get(
                    "erro", "Erro ao substituir periodo."
                )

        except Exception as exc:
            logger.error("Erro em confirmar_substituicao: %s", exc)
            self.import_status = "erro"
            self.import_mensagem = f"Erro interno: {exc}"
        finally:
            self.alert_dialog_open = False
            self.confirmacao_pendente_empresa_id = 0
            self.confirmacao_pendente_periodo = ""
            logic_importacao.limpar_arquivo_temp(caminho_temp)
            self.confirmacao_pendente_caminho_temp = ""
            self.confirmacao_pendente_nome_arquivo = ""
            self.periodo_manual_caminho_temp = ""
            self.periodo_manual_nome_arquivo = ""

    def cancelar_substituicao(self):
        from contaview.logic import importacao as logic_importacao

        self.alert_dialog_open = False
        self.import_status = "erro"
        self.import_mensagem = "Importacao cancelada pelo usuario."
        self.import_erros = ["Cancelado"]
        logic_importacao.limpar_arquivo_temp(self.confirmacao_pendente_caminho_temp)
        self.confirmacao_pendente_empresa_id = 0
        self.confirmacao_pendente_periodo = ""
        self.confirmacao_pendente_caminho_temp = ""
        self.confirmacao_pendente_nome_arquivo = ""
        self.periodo_manual_caminho_temp = ""
        self.periodo_manual_nome_arquivo = ""

    def marcar_ocorrencia_resolvida(self, ocorrencia_id: int, resolvida: bool):
        from contaview.logic import database

        try:
            database.atualizar_ocorrencia_resolvida(ocorrencia_id, resolvida)
            for o in self.ocorrencias:
                if o.get("id") == ocorrencia_id:
                    o["resolvida"] = resolvida
                    break
        except Exception as exc:
            logger.error("Erro ao marcar ocorrencia %d: %s", ocorrencia_id, exc)

    def exportar_excel_lancamentos(self):
        import base64
        import pandas as pd
        from contaview.logic.relatorios import exportar_excel

        try:
            df = pd.DataFrame(self.lancamentos)
            bytes_data = exportar_excel(df, "Relatorio de Lancamentos")
            self.download_data = base64.b64encode(bytes_data).decode()
            self.download_filename = self._nome_arquivo("lancamentos", "xlsx")
        except Exception as exc:
            logger.error("Erro ao exportar excel lancamentos: %s", exc)
        return rx.download(data=self.download_data, filename=self.download_filename)

    def exportar_pdf_lancamentos(self):
        import base64
        import pandas as pd
        from contaview.logic.relatorios import exportar_pdf

        try:
            df = pd.DataFrame(self.lancamentos)
            dados = {"df": df}
            periodo_exib = self._periodo_exibicao()
            bytes_data = exportar_pdf(
                dados,
                "lancamentos",
                self.empresa_selecionada or "sem-empresa",
                periodo_exib,
            )
            self.download_data = base64.b64encode(bytes_data).decode()
            self.download_filename = self._nome_arquivo("lancamentos", "pdf")
        except Exception as exc:
            logger.error("Erro ao exportar pdf lancamentos: %s", exc)
        return rx.download(data=self.download_data, filename=self.download_filename)

    def exportar_excel_conciliacao(self):
        import base64
        import pandas as pd
        from contaview.logic.relatorios import exportar_excel
        from contaview.logic.conciliacao import gerar_relatorio_conciliacao

        try:
            resultado = {
                "df_pares": pd.DataFrame(self.conciliacao_pares),
                "df_sem_par": pd.DataFrame(self.conciliacao_sem_par),
            }
            df_relatorio = gerar_relatorio_conciliacao(resultado)
            bytes_data = exportar_excel(df_relatorio, "Relatorio de Conciliacao")
            self.download_data = base64.b64encode(bytes_data).decode()
            self.download_filename = self._nome_arquivo("conciliacao", "xlsx")
        except Exception as exc:
            logger.error("Erro ao exportar excel conciliacao: %s", exc)
        return rx.download(data=self.download_data, filename=self.download_filename)

    def exportar_pdf_conciliacao(self):
        import base64
        import pandas as pd
        from contaview.logic.relatorios import exportar_pdf
        from contaview.logic.conciliacao import gerar_relatorio_conciliacao

        try:
            resultado = {
                "df_pares": pd.DataFrame(self.conciliacao_pares),
                "df_sem_par": pd.DataFrame(self.conciliacao_sem_par),
            }
            df_relatorio = gerar_relatorio_conciliacao(resultado)
            dados = {"df_relatorio": df_relatorio}
            periodo_exib = self._periodo_exibicao()
            bytes_data = exportar_pdf(
                dados,
                "conciliacao",
                self.empresa_selecionada or "sem-empresa",
                periodo_exib,
            )
            self.download_data = base64.b64encode(bytes_data).decode()
            self.download_filename = self._nome_arquivo("conciliacao", "pdf")
        except Exception as exc:
            logger.error("Erro ao exportar pdf conciliacao: %s", exc)
        return rx.download(data=self.download_data, filename=self.download_filename)

    def exportar_excel_auditoria(self):
        import base64
        import pandas as pd
        from contaview.logic.relatorios import exportar_excel

        try:
            df = pd.DataFrame(self.ocorrencias)
            cols = [
                c for c in ["tipo_ocorrencia", "descricao", "severidade", "resolvida"]
                if c in df.columns
            ]
            df = df[cols]
            df.columns = ["Tipo", "Descricao", "Severidade", "Resolvida"]
            bytes_data = exportar_excel(df, "Relatorio de Auditoria")
            self.download_data = base64.b64encode(bytes_data).decode()
            self.download_filename = self._nome_arquivo("auditoria", "xlsx")
        except Exception as exc:
            logger.error("Erro ao exportar excel auditoria: %s", exc)
        return rx.download(data=self.download_data, filename=self.download_filename)

    def _periodo_exibicao(self) -> str:
        if self.periodo_selecionado and "-" in self.periodo_selecionado:
            return self.periodo_selecionado[-2:] + "/" + self.periodo_selecionado[:4]
        return "sem-periodo"

    def _nome_arquivo(self, tipo: str, ext: str) -> str:
        return f"{tipo}_{self.empresa_selecionada}_{self._periodo_exibicao()}.{ext}"

    @rx.var
    def total_lotes_preparados(self) -> int:
        return len(self.lotes_preparados)

    @rx.var
    def total_linhas_pendentes(self) -> int:
        return sum(int(lote.get("pendentes", 0)) for lote in self.lotes_preparados)

    @rx.var
    def total_linhas_preparadas(self) -> int:
        return sum(int(lote.get("total_linhas", 0)) for lote in self.lotes_preparados)

    @rx.var
    def total_debitos(self) -> float:
        return float(sum((
            Decimal(str(l["valor"]))
            for l in self.lancamentos
            if l.get("tipo") == "D"
        ), Decimal("0.00")))

    @rx.var
    def total_creditos(self) -> float:
        return float(sum((
            Decimal(str(l["valor"]))
            for l in self.lancamentos
            if l.get("tipo") == "C"
        ), Decimal("0.00")))

    @rx.var
    def saldo(self) -> float:
        return float(
            Decimal(str(self.total_creditos)) - Decimal(str(self.total_debitos))
        )

    @rx.var
    def conciliacao_total_pares(self) -> int:
        return (
            self.dados_conciliacao.get("pares_ok", 0)
            + self.dados_conciliacao.get("sem_par", 0)
        )

    @rx.var
    def conciliacao_pares_ok(self) -> int:
        return self.dados_conciliacao.get("pares_ok", 0)

    @rx.var
    def conciliacao_qtd_sem_par(self) -> int:
        return self.dados_conciliacao.get("sem_par", 0)

    @rx.var
    def conciliacao_df_pares(self) -> list[list]:
        dados = []
        for item in self.conciliacao_pares:
            dados.append([
                item.get("seq_c", ""),
                item.get("seq_d", ""),
                item.get("data", ""),
                item.get("conta_contabil", ""),
                formatar_moeda(float(item.get("valor", 0))),
                item.get("status", ""),
            ])
        return dados

    @rx.var
    def conciliacao_colunas(self) -> list[str]:
        return ["Seq. C", "Seq. D", "Data", "Conta", "Valor (R$)", "Status"]

    @rx.var
    def conciliacao_df_sem_par(self) -> list[list]:
        dados = []
        for item in self.conciliacao_sem_par:
            dados.append([
                item.get("sequencial_lote", ""),
                item.get("tipo", ""),
                item.get("data", ""),
                item.get("conta_contabil", ""),
                formatar_moeda(float(item.get("valor", 0))),
                "Sem par",
            ])
        return dados

    @rx.var
    def conciliacao_colunas_sem_par(self) -> list[str]:
        return ["Seq.", "Tipo", "Data", "Conta", "Valor (R$)", "Status"]

    @rx.var
    def ocorrencias_total_alta(self) -> int:
        return sum(1 for o in self.ocorrencias if o.get("severidade") == "alta")

    @rx.var
    def ocorrencias_total_media(self) -> int:
        return sum(1 for o in self.ocorrencias if o.get("severidade") == "media")

    @rx.var
    def ocorrencias_total_baixa(self) -> int:
        return sum(1 for o in self.ocorrencias if o.get("severidade") == "baixa")

    @rx.var
    def fig_mensal(self) -> go.Figure:
        return self._criar_fig_mensal()

    @rx.var
    def fig_top_contas(self) -> go.Figure:
        return self._criar_fig_top_contas()

    @rx.var
    def lancamentos_tabela(self) -> list[list]:
        dados = []
        for l in self.lancamentos:
            dados.append([
                l.get("data", ""),
                l.get("conta_contabil", ""),
                formatar_moeda(float(l.get("valor", 0))),
                l.get("tipo", ""),
                l.get("historico", ""),
                l.get("filial", ""),
            ])
        return dados

    @rx.var
    def colunas_tabela(self) -> list[str]:
        return ["Data", "Conta Contábil", "Valor (R$)", "Tipo", "Histórico", "Filial"]

    @rx.var
    def subtitulo_painel(self) -> str:
        partes = []
        if self.empresa_selecionada:
            partes.append(self.empresa_selecionada)
        if self.periodo_selecionado and "-" in self.periodo_selecionado:
            partes.append(self.periodo_selecionado[-2:] + "/" + self.periodo_selecionado[:4])
        if partes:
            return " - ".join(partes)
        return ""

    def _get_cores(self) -> dict:
        return ECLIPSE if self.tema_escuro else MINERAL

    def _layout_padrao(self, cores: dict) -> dict:
        return dict(
            plot_bgcolor=cores["card_bg"],
            paper_bgcolor=cores["card_bg"],
            font=dict(color=cores["text_primary"]),
            xaxis=dict(
                title="",
                gridcolor=cores["border"],
                tickfont=dict(color=cores["text_secondary"]),
            ),
            yaxis=dict(
                title="",
                gridcolor=cores["border"],
                tickfont=dict(color=cores["text_secondary"]),
            ),
            margin=dict(l=40, r=20, t=40, b=40),
            height=350,
        )

    def _criar_fig_mensal(self) -> go.Figure:
        cores = self._get_cores()
        fig = go.Figure()
        fig.update_layout(**self._layout_padrao(cores))
        fig.update_layout(
            title=dict(
                text="Débitos vs Créditos por mês",
                font=dict(color=cores["text_primary"], size=14),
            ),
            barmode="group",
            legend=dict(font=dict(color=cores["text_primary"])),
        )

        if not self.lancamentos:
            fig.add_annotation(
                text="Selecione uma empresa e período para exibir os dados",
                showarrow=False,
                font=dict(color=cores["text_secondary"], size=14),
            )
            return fig

        df = pd.DataFrame(self.lancamentos)
        df["data_dt"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
        df["mes"] = df["data_dt"].dt.strftime("%m/%Y")
        agrupado = df.groupby(["mes", "tipo"])["valor"].sum().unstack(fill_value=0)

        if "D" in agrupado.columns:
            fig.add_trace(go.Bar(
                name="Débitos",
                x=agrupado.index,
                y=agrupado["D"],
                marker_color=cores["negative"],
            ))
        if "C" in agrupado.columns:
            fig.add_trace(go.Bar(
                name="Créditos",
                x=agrupado.index,
                y=agrupado["C"],
                marker_color=cores["positive"],
            ))

        return fig

    def _criar_fig_top_contas(self) -> go.Figure:
        cores = self._get_cores()
        fig = go.Figure()
        layout = self._layout_padrao(cores)
        layout["margin"]["l"] = 120
        fig.update_layout(**layout)
        fig.update_layout(
            title=dict(
                text="Top 10 contas por volume",
                font=dict(color=cores["text_primary"], size=14),
            ),
        )

        if not self.lancamentos:
            fig.add_annotation(
                text="Selecione uma empresa e período para exibir os dados",
                showarrow=False,
                font=dict(color=cores["text_secondary"], size=14),
            )
            return fig

        df = pd.DataFrame(self.lancamentos)
        agrupado = (
            df.groupby("conta_contabil")["valor"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(10)
        )

        fig.add_trace(go.Bar(
            x=agrupado.values,
            y=agrupado.index,
            orientation="h",
            marker_color=cores["accent"],
        ))

        return fig

    def abrir_renomear_empresa(self):
        if not self.empresa_selecionada:
            return
        self.renomear_empresa_nome_atual = self.empresa_selecionada
        self.renomear_empresa_nome = self.empresa_selecionada
        self.dialog_renomear_aberto = True

    def set_renomear_empresa_nome(self, valor: str):
        self.renomear_empresa_nome = valor

    def confirmar_renomear_empresa(self):
        from contaview.logic import database

        novo_nome = self.renomear_empresa_nome.strip()
        if not novo_nome:
            return
        empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
        if empresa_id:
            database.renomear_empresa(empresa_id, novo_nome)
            self.carregar_empresas()
            self.empresa_selecionada = novo_nome
        self.dialog_renomear_aberto = False

    def cancelar_renomear_empresa(self):
        self.dialog_renomear_aberto = False
