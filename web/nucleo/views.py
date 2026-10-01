"""Autenticação, contexto e páginas básicas da aplicação web."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_not_required
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .decoradores import contexto_nao_obrigatorio
from .formularios import FormularioContexto, FormularioLogin
from .servicos.contexto import (
    carregar_contexto,
    exigir_contexto,
    listar_empresas_ativas,
    limpar_contexto,
    obter_empresa_ativa,
    salvar_contexto,
)
from .servicos.limite_login import (
    criar_chave,
    limpar_falhas,
    registrar_falha,
    segundos_para_liberacao,
)

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


def _destino_seguro(requisicao: HttpRequest, valor: str | None, padrao: str) -> str:
    if valor and url_has_allowed_host_and_scheme(
        valor,
        allowed_hosts={requisicao.get_host()},
        require_https=requisicao.is_secure(),
    ):
        return valor
    return reverse(padrao)


@login_not_required
@contexto_nao_obrigatorio
@never_cache
@require_http_methods(["GET", "POST"])
def acesso(requisicao: HttpRequest) -> HttpResponse:
    if requisicao.user.is_authenticated:
        destino = (
            "nucleo:trabalho"
            if carregar_contexto(requisicao)
            else "nucleo:selecionar_contexto"
        )
        return redirect(destino)

    formulario = FormularioLogin(requisicao, data=requisicao.POST or None)
    if requisicao.method == "POST":
        usuario = requisicao.POST.get("username", "")
        chave_hash = criar_chave(requisicao, usuario)
        try:
            if segundos_para_liberacao(chave_hash) > 0:
                formulario = FormularioLogin(
                    requisicao,
                    data=requisicao.POST,
                    bloqueado=True,
                )
                formulario.is_valid()
            elif formulario.is_valid():
                login(requisicao, formulario.get_user())
                limpar_contexto(requisicao)
                limpar_falhas(chave_hash)
                proximo = _destino_seguro(
                    requisicao,
                    requisicao.POST.get("proximo"),
                    "nucleo:trabalho",
                )
                return redirect(
                    f"{reverse('nucleo:selecionar_contexto')}?proximo={proximo}"
                )
            else:
                registrar_falha(chave_hash)
        except DatabaseError:
            logger.exception("Falha de banco durante a autenticação")
            formulario.add_error(
                None,
                "O acesso está temporariamente indisponível. Tente novamente em instantes.",
            )

    return render(
        requisicao,
        "autenticacao/login.html",
        {
            "formulario": formulario,
            "proximo": _destino_seguro(
                requisicao, requisicao.GET.get("next"), "nucleo:trabalho"
            ),
        },
    )


@contexto_nao_obrigatorio
@require_POST
def sair(requisicao: HttpRequest) -> HttpResponse:
    logout(requisicao)
    return redirect("nucleo:login")


@contexto_nao_obrigatorio
@never_cache
@require_http_methods(["GET", "POST"])
def selecionar_contexto(requisicao: HttpRequest) -> HttpResponse:
    try:
        empresas = listar_empresas_ativas()
    except DatabaseError:
        logger.exception("Falha ao listar empresas para o contexto")
        empresas = []
        messages.error(
            requisicao,
            "Não foi possível carregar as empresas. Tente novamente em instantes.",
        )

    atual = carregar_contexto(requisicao)
    inicial = {
        "empresa": atual.empresa_id if atual else "",
        "competencia": (
            atual.competencia if atual else timezone.localdate().strftime("%Y-%m")
        ),
    }
    formulario = FormularioContexto(
        requisicao.POST or None,
        empresas=empresas,
        initial=inicial,
    )
    proximo = _destino_seguro(
        requisicao,
        requisicao.POST.get("proximo") or requisicao.GET.get("proximo"),
        "nucleo:trabalho",
    )

    if requisicao.method == "POST" and formulario.is_valid():
        try:
            empresa = obter_empresa_ativa(formulario.cleaned_data["empresa"])
        except DatabaseError:
            logger.exception("Falha ao validar empresa do contexto")
            empresa = None
            formulario.add_error(
                None, "Não foi possível validar a empresa. Tente novamente."
            )
        if empresa:
            salvar_contexto(
                requisicao, empresa, formulario.cleaned_data["competencia"]
            )
            messages.success(requisicao, "Contexto de trabalho atualizado.")
            return redirect(proximo)
        if not formulario.non_field_errors():
            formulario.add_error(None, "Selecione uma empresa ativa.")

    return render(
        requisicao,
        "autenticacao/contexto.html",
        {
            "titulo_pagina": "Contexto de trabalho",
            "secao_ativa": "",
            "formulario": formulario,
            "proximo": proximo,
            "tem_empresas": bool(empresas),
        },
    )


@require_GET
def trabalho(requisicao: HttpRequest) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    return render(
        requisicao,
        "nucleo/trabalho.html",
        {
            "titulo_pagina": "Trabalho",
            "secao_ativa": "trabalho",
            "contexto": contexto,
        },
    )


@require_GET
def modulo(requisicao: HttpRequest, secao: str) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    dados = SECOES[secao]
    return render(
        requisicao,
        "nucleo/modulo.html",
        {
            "titulo_pagina": dados["titulo"],
            "secao_ativa": secao,
            "contexto": contexto,
            **dados,
        },
    )


@login_not_required
@contexto_nao_obrigatorio
@never_cache
@require_GET
def saude_aplicacao(requisicao: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "disponivel", "aplicacao": "disponivel"})


@login_not_required
@contexto_nao_obrigatorio
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


@contexto_nao_obrigatorio
@require_GET
def estado_aplicacao(requisicao: HttpRequest) -> HttpResponse:
    return render(requisicao, "nucleo/fragmentos/estado_aplicacao.html")


def renderizar_erro(
    requisicao: HttpRequest, status: int, titulo: str, mensagem: str
) -> HttpResponse:
    return render(
        requisicao,
        "erros/erro.html",
        {
            "status_erro": status,
            "titulo_erro": titulo,
            "mensagem_erro": mensagem,
            "template_base": (
                "base.html"
                if getattr(requisicao, "user", None)
                and requisicao.user.is_authenticated
                else "base_publica.html"
            ),
        },
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


@login_not_required
@contexto_nao_obrigatorio
def falha_csrf(requisicao: HttpRequest, reason="") -> HttpResponse:
    logger.warning("Solicitação recusada pela proteção CSRF")
    return render(
        requisicao,
        "erros/csrf.html",
        {"requisicao_id": getattr(requisicao, "id_requisicao", "indisponível")},
        status=403,
    )
