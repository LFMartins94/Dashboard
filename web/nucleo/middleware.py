"""Middleware para identificar e correlacionar cada requisição."""

from __future__ import annotations

import logging
import re
from time import monotonic
from uuid import uuid4

from .logs import identificador_requisicao

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
