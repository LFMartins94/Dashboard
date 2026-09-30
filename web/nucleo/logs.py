"""Logs JSON com correlação por requisição."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

identificador_requisicao: ContextVar[str] = ContextVar(
    "identificador_requisicao", default="sistema"
)


class FormatadorJson(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        conteudo = {
            "data_hora": datetime.now(UTC).isoformat(),
            "nivel": registro.levelname,
            "logger": registro.name,
            "mensagem": registro.getMessage(),
            "requisicao_id": getattr(
                registro, "requisicao_id", identificador_requisicao.get()
            ),
        }
        for campo in ("metodo", "caminho", "status", "duracao_ms"):
            if hasattr(registro, campo):
                conteudo[campo] = getattr(registro, campo)
        if registro.exc_info:
            conteudo["excecao"] = self.formatException(registro.exc_info)
        return json.dumps(conteudo, ensure_ascii=False)
