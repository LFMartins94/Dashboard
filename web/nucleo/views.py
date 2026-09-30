"""Views básicas do esqueleto Django."""

from __future__ import annotations

import logging

from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

SECOES = {
    "entradas": {
        "titulo": "Entradas",
        "descricao": "Recebimento, leitura e preparação de arquivos contábeis.",
    },
    "conferencia": {
        "titulo": "Conferência",
        "descricao": "Revisão de linhas preparadas, lançamentos e exceções.",
    },
    "entregas": {
        "titulo": "Entregas",
        "descricao": "Relatórios e arquivos prontos para o sistema contábil.",
    },
    "assistente": {
        "titulo": "Assistente",
        "descricao": "Consultas controladas sobre a rotina e os dados disponíveis.",
    },
}


@require_GET
def trabalho(requisicao: HttpRequest) -> HttpResponse:
    return render(
        requisicao,
        "nucleo/trabalho.html",
        {"titulo_pagina": "Trabalho", "secao_ativa": "trabalho"},
    )


@require_GET
def modulo(requisicao: HttpRequest, secao: str) -> HttpResponse:
    dados = SECOES[secao]
    return render(
        requisicao,
        "nucleo/modulo.html",
        {"titulo_pagina": dados["titulo"], "secao_ativa": secao, **dados},
    )


@never_cache
@require_GET
def saude_aplicacao(requisicao: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "disponivel", "aplicacao": "disponivel"})


@never_cache
@require_GET
def saude(requisicao: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Falha no diagnóstico de conexão com o banco")
        return JsonResponse(
            {
                "status": "degradado",
                "aplicacao": "disponivel",
                "banco": "indisponivel",
            },
            status=503,
        )
    return JsonResponse(
        {
            "status": "disponivel",
            "aplicacao": "disponivel",
            "banco": "disponivel",
        }
    )


@require_GET
def estado_aplicacao(requisicao: HttpRequest) -> HttpResponse:
    return render(requisicao, "nucleo/fragmentos/estado_aplicacao.html")


def renderizar_erro(
    requisicao: HttpRequest, status: int, titulo: str, mensagem: str
) -> HttpResponse:
    return render(
        requisicao,
        "erros/erro.html",
        {"status_erro": status, "titulo_erro": titulo, "mensagem_erro": mensagem},
        status=status,
    )


def erro_400(requisicao: HttpRequest, exception=None) -> HttpResponse:
    return renderizar_erro(
        requisicao, 400, "Solicitação inválida", "Revise os dados e tente novamente."
    )


def erro_403(requisicao: HttpRequest, exception=None) -> HttpResponse:
    return renderizar_erro(
        requisicao, 403, "Acesso não permitido", "Sua sessão não permite esta ação."
    )


def erro_404(requisicao: HttpRequest, exception=None) -> HttpResponse:
    return renderizar_erro(
        requisicao,
        404,
        "Página não encontrada",
        "O endereço informado não existe ou foi movido.",
    )


def erro_500(requisicao: HttpRequest) -> HttpResponse:
    return renderizar_erro(
        requisicao,
        500,
        "Não foi possível concluir",
        "Tente novamente. Se o problema continuar, informe a referência abaixo.",
    )
