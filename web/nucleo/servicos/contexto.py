"""Seleção e validação do contexto contábil mantido na sessão."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from django.db import connection

CHAVE_CONTEXTO = "contexto_trabalho"
PADRAO_COMPETENCIA = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])$")


@dataclass(frozen=True, slots=True)
class ContextoTrabalho:
    empresa_id: int
    empresa_nome: str
    competencia: str

    @property
    def competencia_exibicao(self) -> str:
        return f"{self.competencia[5:]}/{self.competencia[:4]}"


def listar_empresas_ativas() -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, nome FROM empresas WHERE ativa = TRUE ORDER BY nome"
        )
        return [
            {"id": linha[0], "nome": linha[1]}
            for linha in cursor.fetchall()
        ]


def obter_empresa_ativa(empresa_id: int) -> dict | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, nome FROM empresas WHERE id = %s AND ativa = TRUE",
            [empresa_id],
        )
        linha = cursor.fetchone()
    if not linha:
        return None
    return {"id": linha[0], "nome": linha[1]}


def salvar_contexto(requisicao, empresa: dict, competencia: str) -> ContextoTrabalho:
    if not PADRAO_COMPETENCIA.fullmatch(competencia):
        raise ValueError("Competência inválida.")
    contexto = ContextoTrabalho(
        empresa_id=int(empresa["id"]),
        empresa_nome=str(empresa["nome"]),
        competencia=competencia,
    )
    requisicao.session[CHAVE_CONTEXTO] = asdict(contexto)
    requisicao.session.modified = True
    return contexto


def carregar_contexto(requisicao) -> ContextoTrabalho | None:
    dados = requisicao.session.get(CHAVE_CONTEXTO)
    if not isinstance(dados, dict):
        return None
    try:
        empresa_id = int(dados["empresa_id"])
        empresa_nome = str(dados["empresa_nome"])
        competencia = str(dados["competencia"])
    except (KeyError, TypeError, ValueError):
        requisicao.session.pop(CHAVE_CONTEXTO, None)
        return None
    if empresa_id <= 0 or not empresa_nome or not PADRAO_COMPETENCIA.fullmatch(competencia):
        requisicao.session.pop(CHAVE_CONTEXTO, None)
        return None
    return ContextoTrabalho(empresa_id, empresa_nome, competencia)


def limpar_contexto(requisicao) -> None:
    requisicao.session.pop(CHAVE_CONTEXTO, None)


def exigir_contexto(requisicao) -> ContextoTrabalho:
    contexto = getattr(requisicao, "contexto_trabalho", None)
    if contexto is None:
        raise RuntimeError("A operação exige empresa e competência selecionadas.")
    return contexto
