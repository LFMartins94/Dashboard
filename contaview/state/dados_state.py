import logging
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

    def carregar_periodos(self):
        from contaview.logic import database

        try:
            empresa_id = self._resolver_empresa_id(self.empresa_selecionada)
            periodos = database.listar_periodos(empresa_id)
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

    def carregar_lancamentos(self):
        from contaview.logic import database

        self.carregando = True
        try:
            empresa_id = (
                self._resolver_empresa_id(self.empresa_selecionada)
                if self.empresa_selecionada
                else None
            )
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
            empresa_nome = self.importar_empresa.strip() or self._derivar_nome_empresa(nome_arquivo)

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

        try:
            df = pd.read_pickle(caminho_pkl)
            nome_arquivo = self.periodo_manual_nome_arquivo
            empresa_nome = self.importar_empresa.strip() or self._derivar_nome_empresa(nome_arquivo)
            empresa_cnpj = self.importar_cnpj.strip() or None

            df = df.copy()
            df["data"] = pd.Timestamp(year=ano, month=mes, day=1)
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
            resultado = logic_importacao.executar_importacao_por_caminho(
                caminho_temp,
                self.confirmacao_pendente_empresa_id,
                self.confirmacao_pendente_periodo,
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
    def total_debitos(self) -> float:
        return sum(
            float(l["valor"])
            for l in self.lancamentos
            if l.get("tipo") == "D"
        )

    @rx.var
    def total_creditos(self) -> float:
        return sum(
            float(l["valor"])
            for l in self.lancamentos
            if l.get("tipo") == "C"
        )

    @rx.var
    def saldo(self) -> float:
        return self.total_creditos - self.total_debitos

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
