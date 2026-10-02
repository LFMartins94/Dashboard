"""Casos de uso da auditoria determinística e da resolução de exceções."""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
import pandas as pd

from contaview.logic import database
from contaview.logic.auditoria import auditar_lancamentos, salvar_ocorrencias

from ..models import EstadoOcorrenciaAuditoria
from .contexto import ContextoTrabalho, obter_empresa_ativa


class ErroAuditoria(ValueError):
    pass


def _validar_contexto(contexto: ContextoTrabalho) -> None:
    if not obter_empresa_ativa(contexto.empresa_id):
        raise ErroAuditoria("A empresa selecionada não está ativa.")


def _formatar_data(valor) -> str:
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor or "")


def _formatar_valor(valor) -> str:
    if valor is None:
        return ""
    return f"R$ {Decimal(str(valor)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def carregar(contexto: ContextoTrabalho) -> dict:
    _validar_contexto(contexto)
    quadro = database.carregar_ocorrencias(contexto.empresa_id, contexto.competencia)
    estados = {
        estado.ocorrencia_id: estado
        for estado in EstadoOcorrenciaAuditoria.objects.filter(
            empresa_id=contexto.empresa_id, competencia=contexto.competencia
        )
    }
    ocorrencias = []
    for linha in quadro.to_dict(orient="records"):
        lancamento_id = linha.get("lancamento_id")
        if lancamento_id is not None and pd.isna(lancamento_id):
            lancamento_id = None
        estado = estados.get(int(linha["id"]))
        resolvida = bool(estado.resolvida) if estado else bool(linha.get("resolvida"))
        ocorrencias.append({
            "id": int(linha["id"]),
            "lancamento_id": int(lancamento_id) if lancamento_id is not None else None,
            "tipo": str(linha.get("tipo_ocorrencia") or ""),
            "descricao": str(linha.get("descricao") or ""),
            "severidade": str(linha.get("severidade") or "baixa"),
            "resolvida": resolvida,
            "data": _formatar_data(linha.get("data")),
            "conta": str(linha.get("conta_contabil") or ""),
            "valor": _formatar_valor(linha.get("valor")),
            "justificativa": estado.justificativa if estado else "",
            "resolvida_por": str(estado.resolvida_por) if estado and estado.resolvida_por else "",
            "resolvida_em": _formatar_data(estado.resolvida_em) if estado and estado.resolvida_em else "",
        })
    historico = database.carregar_historico_alteracoes(contexto.empresa_id, limite=30)
    for item in historico:
        item["alterado_em"] = _formatar_data(item.get("alterado_em"))
    return {
        "ocorrencias": ocorrencias,
        "historico": historico,
        "total": len(ocorrencias),
        "alta": sum(item["severidade"] == "alta" for item in ocorrencias),
        "media": sum(item["severidade"] == "media" for item in ocorrencias),
        "baixa": sum(item["severidade"] == "baixa" for item in ocorrencias),
        "resolvidas": sum(item["resolvida"] for item in ocorrencias),
        "sem_vinculo": sum(item["lancamento_id"] is None for item in ocorrencias),
    }


def executar(contexto: ContextoTrabalho) -> tuple[dict, int]:
    _validar_contexto(contexto)
    lancamentos = database.carregar_lancamentos(contexto.empresa_id, contexto.competencia)
    if lancamentos.empty:
        raise ErroAuditoria("Não há lançamentos aprovados nesta competência para auditar.")
    ocorrencias = auditar_lancamentos(lancamentos)
    novas = salvar_ocorrencias(ocorrencias, contexto.empresa_id)
    return carregar(contexto), novas


@transaction.atomic
def resolver(
    contexto: ContextoTrabalho, usuario, ocorrencia_id: int,
    resolvida: bool, justificativa: str = "",
) -> dict:
    dados = carregar(contexto)
    if ocorrencia_id not in {item["id"] for item in dados["ocorrencias"]}:
        raise ErroAuditoria("A ocorrência não pertence à empresa e competência selecionadas.")
    database.atualizar_ocorrencia_resolvida_empresa(
        contexto.empresa_id, ocorrencia_id, resolvida
    )
    EstadoOcorrenciaAuditoria.objects.update_or_create(
        ocorrencia_id=ocorrencia_id,
        defaults={
            "empresa_id": contexto.empresa_id,
            "competencia": contexto.competencia,
            "resolvida": resolvida,
            "justificativa": justificativa.strip()[:500],
            "resolvida_por": usuario if resolvida else None,
            "resolvida_em": timezone.now() if resolvida else None,
        },
    )
    return carregar(contexto)


def exportar_csv(contexto: ContextoTrabalho) -> str:
    dados = carregar(contexto)
    destino = io.StringIO()
    escrita = csv.DictWriter(
        destino,
        fieldnames=["Severidade", "Tipo", "Descrição", "Data", "Conta", "Valor", "Estado", "Justificativa"],
        delimiter=";",
    )
    escrita.writeheader()
    for item in dados["ocorrencias"]:
        escrita.writerow({
            "Severidade": item["severidade"], "Tipo": item["tipo"],
            "Descrição": item["descricao"], "Data": item["data"],
            "Conta": item["conta"], "Valor": item["valor"],
            "Estado": "Resolvida" if item["resolvida"] else "Pendente",
            "Justificativa": item["justificativa"],
        })
    return destino.getvalue()
