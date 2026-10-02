"""Fluxo do Assistente com consultas agregadas e rastreáveis."""

from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal, InvalidOperation
import re

from django.db.models import Count

from contaview.logic import assistente as logica_assistente
from contaview.logic import database

from ..models import (
    CompetenciaTrabalho,
    ItemChecklistTrabalho,
    RegistroConsultaAssistente,
    TarefaAutomacao,
)
from .contexto import obter_empresa_ativa

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


def _validar_contexto(contexto) -> None:
    empresa = obter_empresa_ativa(contexto.empresa_id)
    if not empresa:
        raise ErroAssistente("A empresa selecionada não está mais disponível.")


def _moeda(valor: Decimal) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _decimal(valor) -> Decimal:
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _fonte(nome: str, descricao: str) -> dict:
    return {"nome": nome, "descricao": descricao}


def consultar_resumo_autorizado(contexto) -> dict:
    """Calcula somente números agregados da empresa e competência validadas."""
    _validar_contexto(contexto)
    fontes: list[dict] = []
    dados_ia: dict = {"competencia": contexto.competencia, "fontes": {}}

    lancamentos = database.carregar_lancamentos(contexto.empresa_id, contexto.competencia)
    if lancamentos is not None and not lancamentos.empty:
        debitos = sum(
            (_decimal(valor) for valor in lancamentos.loc[lancamentos["tipo"] == "D", "valor"]),
            Decimal("0.00"),
        )
        creditos = sum(
            (_decimal(valor) for valor in lancamentos.loc[lancamentos["tipo"] == "C", "valor"]),
            Decimal("0.00"),
        )
        resumo_lancamentos = {
            "quantidade": int(len(lancamentos)),
            "debitos": _moeda(debitos),
            "creditos": _moeda(creditos),
            "saldo": _moeda(creditos - debitos),
        }
        dados_ia["fontes"]["lancamentos_aprovados"] = resumo_lancamentos
        fontes.append(_fonte(
            "Lançamentos aprovados",
            f"{resumo_lancamentos['quantidade']} lançamento(s), débitos {resumo_lancamentos['debitos']}, "
            f"créditos {resumo_lancamentos['creditos']} e saldo {resumo_lancamentos['saldo']}.",
        ))
    else:
        dados_ia["fontes"]["lancamentos_aprovados"] = {"disponivel": False}
        fontes.append(_fonte("Lançamentos aprovados", "Nenhum lançamento aprovado na competência."))

    conciliacoes = database.carregar_conciliacao(contexto.empresa_id, contexto.competencia)
    if conciliacoes is not None and not conciliacoes.empty:
        linha = conciliacoes.iloc[0]
        resumo_conciliacao = {
            "pares_confirmados": int(linha.get("pares_ok", 0) or 0),
            "pares_com_erro": int(linha.get("pares_com_erro", 0) or 0),
            "status": str(linha.get("status", "indisponível")),
        }
        dados_ia["fontes"]["conciliacao"] = resumo_conciliacao
        fontes.append(_fonte(
            "Conciliação",
            f"{resumo_conciliacao['pares_confirmados']} par(es) confirmado(s), "
            f"{resumo_conciliacao['pares_com_erro']} com erro e status {resumo_conciliacao['status']}.",
        ))
    else:
        dados_ia["fontes"]["conciliacao"] = {"disponivel": False}
        fontes.append(_fonte("Conciliação", "Nenhuma conciliação concluída na competência."))

    ocorrencias = database.carregar_ocorrencias(contexto.empresa_id, contexto.competencia)
    if ocorrencias is not None and not ocorrencias.empty:
        resumo_auditoria = {
            severidade: int((ocorrencias["severidade"] == severidade).sum())
            for severidade in ("alta", "media", "baixa")
        }
        resumo_auditoria["total"] = int(len(ocorrencias))
        dados_ia["fontes"]["auditoria"] = resumo_auditoria
        fontes.append(_fonte(
            "Auditoria",
            f"{resumo_auditoria['total']} ocorrência(s): {resumo_auditoria['alta']} alta(s), "
            f"{resumo_auditoria['media']} média(s) e {resumo_auditoria['baixa']} baixa(s).",
        ))
    else:
        dados_ia["fontes"]["auditoria"] = {"disponivel": False}
        fontes.append(_fonte("Auditoria", "Nenhuma ocorrência registrada na competência."))

    competencia = CompetenciaTrabalho.objects.filter(
        empresa_id=contexto.empresa_id, competencia=contexto.competencia
    ).first()
    if competencia:
        pendentes = ItemChecklistTrabalho.objects.filter(
            competencia_trabalho=competencia, concluido_em__isnull=True
        ).count()
        dados_ia["fontes"]["checklist"] = {"pendentes": pendentes}
        fontes.append(_fonte("Checklist de trabalho", f"{pendentes} item(ns) ainda pendente(s)."))

    tarefas = TarefaAutomacao.objects.filter(
        empresa_id=contexto.empresa_id, competencia=contexto.competencia
    ).values("estado").annotate(total=Count("id"))
    fila = {item["estado"]: int(item["total"]) for item in tarefas}
    if fila:
        dados_ia["fontes"]["automacoes"] = fila
        fontes.append(_fonte("Automações", ", ".join(f"{quantidade} {estado}" for estado, quantidade in fila.items()) + "."))

    ha_dados_contabeis = any(
        dados_ia["fontes"][fonte].get("disponivel") is not False
        for fonte in ("lancamentos_aprovados", "conciliacao", "auditoria")
    )
    return {"dados_ia": dados_ia, "fontes": fontes, "ha_dados_contabeis": ha_dados_contabeis}


def _pergunta_sobre_dados(texto: str) -> bool:
    return bool(re.search(
        r"\b(saldo|total|d[ée]bito|cr[ée]dito|lan[çc]amento|concilia[çc][ãa]o|"
        r"auditoria|diverg[êe]ncia|pend[êe]ncia|valor|compet[êe]ncia)\b",
        texto,
        flags=re.IGNORECASE,
    ))


def _usuario_requisicao(requisicao):
    usuario = getattr(requisicao, "user", None)
    return usuario if getattr(usuario, "is_authenticated", False) else None


def _registrar_consulta(requisicao, contexto, conversa_id: int, pergunta: str, resposta: str, resumo: dict) -> None:
    usuario = _usuario_requisicao(requisicao)
    if usuario is None:
        return
    RegistroConsultaAssistente.objects.create(
        usuario=usuario,
        conversa_id=conversa_id,
        empresa_id=contexto.empresa_id,
        competencia=contexto.competencia,
        pergunta=pergunta,
        resposta=resposta,
        filtros={"empresa_id": contexto.empresa_id, "competencia": contexto.competencia},
        fontes=resumo["fontes"],
    )


def _anexar_fontes(requisicao, conversa_id: int, mensagens: list[dict]) -> list[dict]:
    usuario = _usuario_requisicao(requisicao)
    if usuario is None:
        return mensagens
    registros = RegistroConsultaAssistente.objects.filter(
        usuario=usuario, conversa_id=conversa_id
    ).order_by("criado_em")
    por_resposta: dict[str, deque] = defaultdict(deque)
    for registro in registros:
        por_resposta[registro.resposta].append(registro.fontes)
    for mensagem in mensagens:
        if mensagem.get("role") == "assistant" and por_resposta[mensagem.get("content", "")]:
            mensagem["fontes"] = por_resposta[mensagem["content"]].popleft()
    return mensagens


def listar(requisicao) -> list[dict]:
    permitidas = set(_ids_sessao(requisicao))
    return [item for item in database.listar_conversas() if int(item["id"]) in permitidas]


def obter_mensagens(requisicao, conversa_id: int) -> list[dict]:
    if conversa_id not in _ids_sessao(requisicao):
        raise ErroAssistente("Esta conversa não está disponível nesta sessão.")
    return _anexar_fontes(requisicao, conversa_id, database.carregar_mensagens(conversa_id))


def nova_conversa(requisicao, titulo: str = "Nova conversa") -> int:
    conversa_id = database.criar_conversa(titulo[:80] or "Nova conversa")
    _registrar_sessao(requisicao, conversa_id)
    return conversa_id


def excluir(requisicao, conversa_id: int) -> None:
    if conversa_id not in _ids_sessao(requisicao):
        raise ErroAssistente("Esta conversa não está disponível nesta sessão.")
    usuario = _usuario_requisicao(requisicao)
    if usuario is not None:
        RegistroConsultaAssistente.objects.filter(usuario=usuario, conversa_id=conversa_id).delete()
    database.deletar_conversa(conversa_id)
    requisicao.session[CHAVE_CONVERSAS] = [item for item in _ids_sessao(requisicao) if item != conversa_id]
    requisicao.session.modified = True


def enviar(requisicao, contexto, conversa_id: int | None, conteudo: str) -> int:
    _validar_contexto(contexto)
    texto = re.sub(r"\s+", " ", conteudo or "").strip()
    if not texto:
        raise ErroAssistente("Digite uma mensagem antes de enviar.")
    if len(texto) > 4000:
        raise ErroAssistente("A mensagem deve ter no máximo 4.000 caracteres.")
    texto_seguro = logica_assistente.sanitizar_texto_assistente(texto)
    if conversa_id is None:
        conversa_id = nova_conversa(requisicao, logica_assistente.gerar_titulo_conversa(texto_seguro))
    elif conversa_id not in _ids_sessao(requisicao) or not database.conversa_existe(conversa_id):
        raise ErroAssistente("Selecione uma conversa válida.")

    resumo = consultar_resumo_autorizado(contexto)
    historico = database.carregar_mensagens(conversa_id)[-LIMITE_HISTORICO:]
    database.salvar_mensagem(conversa_id, "user", texto_seguro)
    if not resumo["ha_dados_contabeis"] and _pergunta_sobre_dados(texto_seguro):
        resposta = (
            "Não há lançamentos, conciliações ou ocorrências de auditoria disponíveis "
            "para a competência selecionada. Não é possível informar valores sem dados."
        )
    else:
        resposta = logica_assistente.perguntar_ao_assistente(
            historico + [{"role": "user", "content": texto_seguro}],
            periodo_permitido=contexto.competencia,
            dados_consulta=resumo["dados_ia"],
        )
    resposta = resposta or "Não foi possível obter uma resposta."
    database.salvar_mensagem(conversa_id, "assistant", resposta)
    _registrar_consulta(requisicao, contexto, conversa_id, texto_seguro, resposta, resumo)
    return conversa_id
