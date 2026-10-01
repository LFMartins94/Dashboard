"""Middleware para identificar e correlacionar cada requisição."""

from __future__ import annotations

import logging
import re
from time import monotonic
from uuid import uuid4

from django.shortcuts import redirect
from django.urls import reverse

from .logs import identificador_requisicao
from .servicos.contexto import carregar_contexto

logger = logging.getLogger(__name__)
PADRAO_IDENTIFICADOR = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")


class IdentificadorRequisicaoMiddleware:
    def __init__(self, obter_resposta):
        self.obter_resposta = obter_resposta

    def __call__(self, requisicao):
        recebido = requisicao.headers.get("X-Request-ID", "")
        requisicao_id = (
            recebido if PADRAO_IDENTIFICADOR.fullmatch(recebido) else str(uuid4())
        )
        requisicao.id_requisicao = requisicao_id
        token = identificador_requisicao.set(requisicao_id)
        inicio = monotonic()
        try:
            resposta = self.obter_resposta(requisicao)
            resposta["X-Request-ID"] = requisicao_id
            logger.info(
                "Requisição concluída",
                extra={
                    "requisicao_id": requisicao_id,
                    "metodo": requisicao.method,
                    "caminho": requisicao.path,
                    "status": resposta.status_code,
                    "duracao_ms": round((monotonic() - inicio) * 1000, 2),
                },
            )
            return resposta
        finally:
            identificador_requisicao.reset(token)


class ContextoTrabalhoMiddleware:
    """Exige empresa e competência em todas as rotas operacionais."""

    def __init__(self, obter_resposta):
        self.obter_resposta = obter_resposta

    def __call__(self, requisicao):
        requisicao.contexto_trabalho = carregar_contexto(requisicao)
        return self.obter_resposta(requisicao)

    def process_view(self, requisicao, view_func, view_args, view_kwargs):
        if not requisicao.user.is_authenticated:
            return None
        if getattr(view_func, "contexto_obrigatorio", True) is False:
            return None
        if requisicao.contexto_trabalho is not None:
            return None
        destino = reverse("nucleo:selecionar_contexto")
        return redirect(f"{destino}?proximo={requisicao.get_full_path()}")
