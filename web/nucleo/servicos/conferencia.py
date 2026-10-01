"""Casos de uso da conferência de lotes preparados."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from contaview.logic import database
from contaview.logic.importacao import validar_edicao_linha

from .contexto import ContextoTrabalho, obter_empresa_ativa


class ErroConferencia(ValueError):
    pass


class PeriodoPrecisaSubstituicao(ErroConferencia):
    pass


def _validar_empresa(contexto: ContextoTrabalho) -> None:
    if not obter_empresa_ativa(contexto.empresa_id):
        raise ErroConferencia("A empresa selecionada não está ativa.")


def _pendencias(valor) -> list[str]:
    if isinstance(valor, list):
        return [str(item) for item in valor]
    if isinstance(valor, str):
        try:
            resultado = json.loads(valor)
            return resultado if isinstance(resultado, list) else []
        except json.JSONDecodeError:
            return []
    return []


def carregar_conferencia(contexto: ContextoTrabalho, lote_id: int | None = None) -> dict:
    _validar_empresa(contexto)
    lotes = database.listar_lotes_preparacao(contexto.empresa_id, contexto.competencia)
    lote = None
    if lote_id is not None:
        lote = database.carregar_lote_preparacao(contexto.empresa_id, lote_id)
        if lote is None or lote.get("periodo") != contexto.competencia:
            raise ErroConferencia("O lote não pertence à empresa e competência selecionadas.")
    elif lotes:
        lote = database.carregar_lote_preparacao(contexto.empresa_id, int(lotes[0]["id"]))
    linhas = database.carregar_linhas_preparadas(contexto.empresa_id, int(lote["id"])) if lote else []
    for linha in linhas:
        linha["pendencias"] = _pendencias(linha.get("pendencias"))
    validas = [linha for linha in linhas if linha.get("status") == "validado"]
    pendentes = [linha for linha in linhas if linha.get("status") != "validado"]
    debito = sum((Decimal(str(linha["valor"])) for linha in linhas if linha.get("tipo") == "D" and linha.get("valor") is not None), Decimal("0"))
    credito = sum((Decimal(str(linha["valor"])) for linha in linhas if linha.get("tipo") == "C" and linha.get("valor") is not None), Decimal("0"))
    return {
        "lotes": lotes,
        "lote": lote,
        "linhas": linhas,
        "validas": len(validas),
        "pendentes": len(pendentes),
        "total_debito": debito,
        "total_credito": credito,
        "saldo": debito - credito,
    }


def editar_linha(contexto: ContextoTrabalho, lote_id: int, linha_id: int, campos: dict[str, str]) -> None:
    dados = carregar_conferencia(contexto, lote_id)
    if not dados["lote"] or dados["lote"].get("status") != "em_revisao":
        raise ErroConferencia("Somente um lote em revisão pode ser editado.")
    linha = next((item for item in dados["linhas"] if int(item["id"]) == int(linha_id)), None)
    if linha is None:
        raise ErroConferencia("A linha não pertence ao lote selecionado.")
    normalizados, pendencias = validar_edicao_linha(
        campos, str(dados["lote"].get("tipo_documento") or "lancamentos"), contexto.competencia
    )
    database.atualizar_linha_preparada(contexto.empresa_id, linha_id, normalizados, pendencias)


def editar_em_lote(contexto: ContextoTrabalho, lote_id: int, linha_ids: list[int], campo: str, valor: str) -> int:
    permitidos = {"data", "descricao", "valor", "tipo", "conta_contabil", "filial"}
    if campo not in permitidos or not linha_ids:
        raise ErroConferencia("Informe linhas e um campo válidos para a edição em lote.")
    dados = carregar_conferencia(contexto, lote_id)
    linhas = {int(item["id"]): item for item in dados["linhas"]}
    alteradas = 0
    for linha_id in linha_ids:
        linha = linhas.get(int(linha_id))
        if linha is None:
            raise ErroConferencia("Uma das linhas selecionadas não pertence ao lote.")
        campos = {nome: "" if linha.get(nome) is None else str(linha.get(nome)) for nome in permitidos}
        if isinstance(linha.get("data"), date):
            campos["data"] = linha["data"].strftime("%d/%m/%Y")
        campos[campo] = valor
        editar_linha(contexto, lote_id, linha_id, campos)
        alteradas += 1
    return alteradas


def aprovar(contexto: ContextoTrabalho, lote_id: int, substituir: bool = False) -> dict:
    dados = carregar_conferencia(contexto, lote_id)
    if not dados["lote"]:
        raise ErroConferencia("Lote não encontrado.")
    try:
        return database.aprovar_lote_preparacao(contexto.empresa_id, lote_id, substituir=substituir)
    except database.PeriodoExistenteError as erro:
        raise PeriodoPrecisaSubstituicao(str(erro)) from erro


def cancelar(contexto: ContextoTrabalho, lote_id: int) -> None:
    _validar_empresa(contexto)
    database.cancelar_lote_preparacao(contexto.empresa_id, lote_id)


def reabrir(contexto: ContextoTrabalho, lote_id: int) -> None:
    _validar_empresa(contexto)
    database.reabrir_lote_preparacao(contexto.empresa_id, lote_id)
