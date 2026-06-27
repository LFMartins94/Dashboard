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

            resposta = assistente.perguntar_ao_assistente(self.mensagens)
            database.salvar_mensagem(self.conversa_ativa, "assistant", resposta)
            self.mensagens.append({"role": "assistant", "content": resposta})
        except Exception as exc:
            logger.error("Erro ao enviar mensagem: %s", exc)
            self.erro_assistente = "O assistente está indisponível no momento. Verifique a chave da API e tente novamente."
        finally:
            self.carregando_resposta = False
