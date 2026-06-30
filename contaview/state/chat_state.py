import logging
import reflex as rx

logger = logging.getLogger(__name__)


class ChatState(rx.State):
    conversas: list[dict] = []
    conversa_ativa: int | None = None
    mensagens: list[dict] = []
    entrada_atual: str = ""
    carregando_resposta: bool = False
    erro_assistente: str = ""

    renomeando_id: int | None = None
    renomear_titulo_temp: str = ""

    @rx.var
    def conversas_favoritas(self) -> list[dict]:
        return [c for c in self.conversas if c.get("favorito")]

    @rx.var
    def tem_favoritas(self) -> bool:
        return any(c.get("favorito") for c in self.conversas)

    def set_entrada_atual(self, valor: str):
        self.entrada_atual = valor

    def carregar_conversas(self):
        from contaview.logic import database

        try:
            self.conversas = database.listar_conversas()
        except Exception as exc:
            logger.error("Erro ao carregar conversas: %s", exc)
            self.conversas = []

    def iniciar_assistente(self):
        self.carregar_conversas()
        if self.conversa_ativa is None:
            return ChatState.nova_conversa

    def selecionar_conversa(self, conversa_id: int):
        from contaview.logic import database

        try:
            self.conversa_ativa = conversa_id
            self.mensagens = database.carregar_mensagens(conversa_id)
            self.erro_assistente = ""
        except Exception as exc:
            logger.error("Erro ao selecionar conversa: %s", exc)
        return rx.redirect("/assistente")

    def nova_conversa(self):
        from contaview.logic import database

        try:
            novo_id = database.criar_conversa()
            self.conversa_ativa = novo_id
            self.mensagens = []
            self.erro_assistente = ""
        except Exception as exc:
            logger.error("Erro ao criar conversa: %s", exc)
        return ChatState.carregar_conversas

    def excluir_conversa(self, conversa_id: int):
        from contaview.logic import database

        try:
            if database.conversa_existe(conversa_id):
                database.deletar_conversa(conversa_id)
        except Exception as exc:
            logger.error("Erro ao excluir conversa: %s", exc)

        if self.conversa_ativa == conversa_id:
            self.conversa_ativa = None
            self.mensagens = []

        if self.conversa_ativa is None:
            return ChatState.nova_conversa

        return ChatState.carregar_conversas

    def iniciar_renomear_conversa(self, conversa_id: int):
        titulo_atual = ""
        for c in self.conversas:
            if c["id"] == conversa_id:
                titulo_atual = c["titulo"]
                break
        self.renomeando_id = conversa_id
        self.renomear_titulo_temp = titulo_atual

    def set_renomear_titulo_temp(self, valor: str):
        self.renomear_titulo_temp = valor

    def confirmar_renomear_conversa(self):
        from contaview.logic import database

        novo_titulo = self.renomear_titulo_temp.strip()
        if not novo_titulo or self.renomeando_id is None:
            self.renomeando_id = None
            self.renomear_titulo_temp = ""
            return

        try:
            database.renomear_conversa(self.renomeando_id, novo_titulo)
        except Exception as exc:
            logger.error("Erro ao renomear conversa: %s", exc)
        finally:
            self.renomeando_id = None
            self.renomear_titulo_temp = ""
            self.carregar_conversas()

    def cancelar_renomear_conversa(self):
        self.renomeando_id = None
        self.renomear_titulo_temp = ""

    def handle_rename_key(self, key_data):
        key = key_data.get("key", "") if isinstance(key_data, dict) else ""
        if key == "Enter":
            self.confirmar_renomear_conversa()
        elif key == "Escape":
            self.cancelar_renomear_conversa()

    def alternar_favorito(self, conversa_id: int):
        from contaview.logic import database

        favorito = False
        for c in self.conversas:
            if c["id"] == conversa_id:
                favorito = not c.get("favorito", False)
                break

        try:
            database.favoritar_conversa(conversa_id, favorito)
        except Exception as exc:
            logger.error("Erro ao alternar favorito: %s", exc)
        self.carregar_conversas()

    async def enviar_mensagem(self):
        from contaview.logic import database, assistente

        self.carregando_resposta = True
        self.erro_assistente = ""
        yield

        try:
            if self.conversa_ativa is None:
                self.conversa_ativa = database.criar_conversa()

            texto = self.entrada_atual
            self.entrada_atual = ""
            database.salvar_mensagem(self.conversa_ativa, "user", texto)
            self.mensagens.append({"role": "user", "content": texto})

            if len(self.mensagens) == 1:
                titulo = assistente.gerar_titulo_conversa(texto)
                database.renomear_conversa(self.conversa_ativa, titulo)
                self.carregar_conversas()

            resposta = assistente.perguntar_ao_assistente(self.mensagens)
            database.salvar_mensagem(self.conversa_ativa, "assistant", resposta)
            self.mensagens.append({"role": "assistant", "content": resposta})
        except Exception as exc:
            logger.error("Erro ao enviar mensagem: %s", exc)
            self.erro_assistente = "O assistente está indisponível no momento. Verifique a chave da API e tente novamente."
        finally:
            self.carregando_resposta = False
