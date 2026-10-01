"""Conciliação determinística entre dois lotes preparados."""

from __future__ import annotations

from django.db import transaction

from contaview.logic import database
from contaview.logic.conciliacao import conciliar_fontes

from ..models import DecisaoConciliacao, RevisaoConciliacao
from .contexto import ContextoTrabalho, obter_empresa_ativa


class ErroConciliacao(ValueError):
    pass


def _validar_contexto(contexto: ContextoTrabalho) -> None:
    if not obter_empresa_ativa(contexto.empresa_id):
        raise ErroConciliacao("A empresa selecionada não está ativa.")


def _lotes_permitidos(contexto: ContextoTrabalho) -> dict[int, dict]:
    return {
        int(lote["id"]): lote
        for lote in database.listar_lotes_preparacao(contexto.empresa_id, contexto.competencia)
        if lote.get("status") != "cancelado"
    }


def _carregar_fontes(contexto: ContextoTrabalho, lote_extrato_id: int, lote_referencia_id: int) -> tuple[dict, dict, list[dict], list[dict]]:
    _validar_contexto(contexto)
    if lote_referencia_id and lote_extrato_id == lote_referencia_id:
        raise ErroConciliacao("Selecione dois lotes diferentes para conciliar.")
    lotes = _lotes_permitidos(contexto)
    extrato = lotes.get(lote_extrato_id)
    if extrato is None:
        raise ErroConciliacao("O extrato deve pertencer à empresa e competência selecionadas.")
    if extrato.get("tipo_documento") != "extrato":
        raise ErroConciliacao("A primeira fonte deve ser um extrato bancário.")
    linhas_extrato = database.carregar_linhas_para_exportacao(contexto.empresa_id, lote_extrato_id)
    if lote_referencia_id == 0:
        quadro = database.carregar_lancamentos(contexto.empresa_id, contexto.competencia)
        linhas_referencia = [
            {
                "id": int(linha["id"]),
                "numero_linha": int(linha.get("sequencial_lote") or linha["id"]),
                "data": linha["data"],
                "descricao": linha.get("historico") or "",
                "valor": linha["valor"],
                "tipo": linha.get("tipo"),
                "conta_contabil": linha.get("conta_contabil") or "",
                "status": "validado",
            }
            for linha in quadro.to_dict(orient="records")
        ]
        referencia = {
            "id": 0, "nome_arquivo": "Lançamentos aprovados",
            "tipo_documento": "lancamentos", "total_linhas": len(linhas_referencia),
        }
    else:
        referencia = lotes.get(lote_referencia_id)
        if referencia is None:
            raise ErroConciliacao("A referência deve pertencer à empresa e competência selecionadas.")
        linhas_referencia = database.carregar_linhas_para_exportacao(contexto.empresa_id, lote_referencia_id)
    return extrato, referencia, linhas_extrato, linhas_referencia


def _chave_decisao(registro: dict) -> tuple[int, int]:
    return int(registro["extrato_id"]), int(registro["referencia_id"])


def _resultado_com_decisoes(contexto: ContextoTrabalho, lote_extrato_id: int, lote_referencia_id: int, resultado: dict) -> dict:
    revisoes = RevisaoConciliacao.objects.filter(
        empresa_id=contexto.empresa_id,
        competencia=contexto.competencia,
        lote_extrato_id=lote_extrato_id,
        lote_referencia_id=lote_referencia_id,
    )
    decisoes = {
        (item.linha_extrato_id, item.linha_referencia_id): item.decisao
        for item in revisoes
    }
    for grupo in ("candidatos", "divergencias_valor"):
        for item in resultado[grupo]:
            item["decisao"] = decisoes.get(_chave_decisao(item), "")
    confirmadas = sum(valor in {DecisaoConciliacao.CONFIRMADA, DecisaoConciliacao.MANUAL} for valor in decisoes.values())
    rejeitadas = sum(valor == DecisaoConciliacao.REJEITADA for valor in decisoes.values())
    pendentes = sum(
        not item.get("decisao")
        for grupo in ("candidatos", "divergencias_valor")
        for item in resultado[grupo]
    )
    resultado["revisoes_confirmadas"] = confirmadas
    resultado["revisoes_rejeitadas"] = rejeitadas
    resultado["revisoes_pendentes"] = pendentes
    resultado["sem_correspondencia_total"] = (
        len(resultado["faltantes_extrato"]) + len(resultado["faltantes_referencia"])
    )
    return resultado


def _salvar_resumo(contexto: ContextoTrabalho, resultado: dict) -> None:
    pares_ok = len(resultado["pares_confirmados"]) + resultado.get("revisoes_confirmadas", 0)
    pares_com_erro = (
        resultado.get("revisoes_pendentes", 0)
        + resultado.get("revisoes_rejeitadas", 0)
        + len(resultado["faltantes_extrato"])
        + len(resultado["faltantes_referencia"])
    )
    database.inserir_conciliacao(
        contexto.empresa_id,
        contexto.competencia,
        pares_ok + pares_com_erro,
        pares_ok,
        pares_com_erro,
    )


def executar(contexto: ContextoTrabalho, lote_extrato_id: int, lote_referencia_id: int) -> dict:
    extrato, referencia, linhas_extrato, linhas_referencia = _carregar_fontes(
        contexto, lote_extrato_id, lote_referencia_id
    )
    resultado = conciliar_fontes(linhas_extrato, linhas_referencia)
    resultado = _resultado_com_decisoes(contexto, lote_extrato_id, lote_referencia_id, resultado)
    _salvar_resumo(contexto, resultado)
    return {
        "lotes": list(_lotes_permitidos(contexto).values()),
        "extrato": extrato,
        "referencia": referencia,
        "resultado": resultado,
    }


@transaction.atomic
def decidir(
    contexto: ContextoTrabalho, usuario, lote_extrato_id: int, lote_referencia_id: int,
    linha_extrato_id: int, linha_referencia_id: int, decisao: str, justificativa: str = "",
) -> dict:
    if decisao not in DecisaoConciliacao.values:
        raise ErroConciliacao("A decisão de conciliação é inválida.")
    dados = executar(contexto, lote_extrato_id, lote_referencia_id)
    revisaveis = dados["resultado"]["candidatos"] + dados["resultado"]["divergencias_valor"]
    if (linha_extrato_id, linha_referencia_id) not in {_chave_decisao(item) for item in revisaveis}:
        raise ErroConciliacao("A decisão deve corresponder a um candidato da conciliação atual.")
    RevisaoConciliacao.objects.update_or_create(
        empresa_id=contexto.empresa_id,
        competencia=contexto.competencia,
        lote_extrato_id=lote_extrato_id,
        lote_referencia_id=lote_referencia_id,
        linha_extrato_id=linha_extrato_id,
        linha_referencia_id=linha_referencia_id,
        defaults={
            "decisao": decisao,
            "justificativa": justificativa.strip()[:500],
            "decidido_por": usuario,
        },
    )
    return executar(contexto, lote_extrato_id, lote_referencia_id)


def contexto_inicial(contexto: ContextoTrabalho) -> dict:
    _validar_contexto(contexto)
    return {"lotes": list(_lotes_permitidos(contexto).values()), "resultado": None, "extrato": None, "referencia": None}
