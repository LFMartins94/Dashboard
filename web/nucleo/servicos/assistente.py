"""Fluxo web do assistente, com conversas limitadas à sessão autenticada."""

from __future__ import annotations

import re

from contaview.logic import assistente as logica_assistente
from contaview.logic import database

CHAVE_CONVERSAS = "assistente_conversas"
LIMITE_HISTORICO = 30


class ErroAssistente(ValueError):
    pass


def _ids_sessao(requisicao) -> list[int]:
    ids = requisicao.session.get(CHAVE_CONVERSAS, [])
    return [int(item) for item in ids if str(item).isdigit()]


def _registrar_sessao(requisicao, conversa_id: int) -> None:
    ids = _ids_sessao(requisicao)
    if conversa_id not in ids:
        requisicao.session[CHAVE_CONVERSAS] = [conversa_id, *ids[:49]]
        requisicao.session.modified = True


def listar(requisicao) -> list[dict]:
    permitidas = set(_ids_sessao(requisicao))
    return [item for item in database.listar_conversas() if int(item["id"]) in permitidas]


def obter_mensagens(requisicao, conversa_id: int) -> list[dict]:
    if conversa_id not in _ids_sessao(requisicao):
        raise ErroAssistente("Esta conversa não está disponível nesta sessão.")
    return database.carregar_mensagens(conversa_id)


def nova_conversa(requisicao, titulo: str = "Nova conversa") -> int:
    conversa_id = database.criar_conversa(titulo[:80] or "Nova conversa")
    _registrar_sessao(requisicao, conversa_id)
    return conversa_id


def excluir(requisicao, conversa_id: int) -> None:
    if conversa_id not in _ids_sessao(requisicao):
        raise ErroAssistente("Esta conversa não está disponível nesta sessão.")
    database.deletar_conversa(conversa_id)
    requisicao.session[CHAVE_CONVERSAS] = [item for item in _ids_sessao(requisicao) if item != conversa_id]
    requisicao.session.modified = True


def enviar(requisicao, contexto, conversa_id: int | None, conteudo: str) -> int:
    texto = re.sub(r"\s+", " ", conteudo or "").strip()
    if not texto:
        raise ErroAssistente("Digite uma mensagem antes de enviar.")
    if len(texto) > 4000:
        raise ErroAssistente("A mensagem deve ter no máximo 4.000 caracteres.")
    if conversa_id is None:
        conversa_id = nova_conversa(requisicao, logica_assistente.gerar_titulo_conversa(texto))
    elif conversa_id not in _ids_sessao(requisicao) or not database.conversa_existe(conversa_id):
        raise ErroAssistente("Selecione uma conversa válida.")
    historico = database.carregar_mensagens(conversa_id)[-LIMITE_HISTORICO:]
    database.salvar_mensagem(conversa_id, "user", texto)
    try:
        resposta = logica_assistente.perguntar_ao_assistente(
            historico + [{"role": "user", "content": texto}],
            empresa_permitida=contexto.empresa_nome,
            periodo_permitido=contexto.competencia,
        )
    except Exception:
        resposta = "Não foi possível obter uma resposta agora. Tente novamente em instantes."
    database.salvar_mensagem(conversa_id, "assistant", resposta or "Não foi possível obter uma resposta.")
    return conversa_id
