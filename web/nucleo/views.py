"""Autenticação, contexto e páginas básicas da aplicação web."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

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
from .formularios import (
    FormularioAlternarCompetencia,
    FormularioConfigurarEntrada,
    FormularioContexto,
    FormularioEstadoItem,
    FormularioLogin,
    FormularioMapeamentoEntrada,
    FormularioUploadEntrada,
    FormularioEditarLinhaConferencia,
    FormularioEdicaoEmLote,
    FormularioLote,
    FormularioMensagemAssistente,
    FormularioConversaAssistente,
    FormularioExecutarConciliacao,
    FormularioDecisaoConciliacao,
)
from .models import ArquivoEntradaTemporario, EstadoArquivoEntrada
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
from .servicos.entradas import (
    ErroEntrada,
    confirmar_preparacao,
    descartar_arquivo,
    inspecionar_selecao,
    listar_lotes_contexto,
    obter_arquivo_contexto,
    receber_arquivo,
)
from .servicos.trabalho import (
    PainelTrabalho,
    atualizar_item_checklist,
    iniciar_competencia,
    montar_painel_trabalho,
    obter_competencia_para_alternar,
)
from .servicos import conferencia as servico_conferencia
from .servicos import assistente as servico_assistente
from .servicos import conciliacao as servico_conciliacao

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
    falha_fila = False
    try:
        painel = montar_painel_trabalho(contexto)
    except DatabaseError:
        logger.exception("Falha ao montar a fila operacional")
        painel = PainelTrabalho()
        falha_fila = True
        messages.error(
            requisicao,
            "Não foi possível carregar a fila de trabalho. Tente novamente em instantes.",
        )
    return render(
        requisicao,
        "nucleo/trabalho.html",
        {
            "titulo_pagina": "Trabalho",
            "secao_ativa": "trabalho",
            "contexto": contexto,
            "painel": painel,
            "falha_fila": falha_fila,
            "estados_operacionais": FormularioEstadoItem.base_fields["estado"].choices,
        },
    )


@require_POST
def iniciar_contexto_trabalho(requisicao: HttpRequest) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    try:
        iniciar_competencia(contexto, requisicao.user)
    except ValueError as erro:
        logger.warning("Competência operacional recusada: %s", erro)
        messages.error(requisicao, str(erro))
    except DatabaseError:
        logger.exception("Falha ao iniciar a competência operacional")
        messages.error(requisicao, "Não foi possível iniciar a competência.")
    else:
        messages.success(requisicao, "Competência iniciada com o checklist recorrente.")
    return redirect("nucleo:trabalho")


@require_POST
def atualizar_item_trabalho(requisicao: HttpRequest) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    formulario = FormularioEstadoItem(requisicao.POST)
    if not formulario.is_valid():
        messages.error(requisicao, "Não foi possível atualizar o item informado.")
        return redirect("nucleo:trabalho")
    try:
        atualizar_item_checklist(
            contexto,
            formulario.cleaned_data["item_id"],
            formulario.cleaned_data["estado"],
            requisicao.user,
        )
    except ValueError as erro:
        logger.warning("Atualização de checklist recusada: %s", erro)
        messages.error(requisicao, str(erro))
    except DatabaseError:
        logger.exception("Falha ao atualizar item do checklist")
        messages.error(requisicao, "Não foi possível atualizar o item.")
    else:
        messages.success(requisicao, "Estado do item atualizado.")
    return redirect("nucleo:trabalho")


@require_POST
def alternar_competencia_trabalho(requisicao: HttpRequest) -> HttpResponse:
    exigir_contexto(requisicao)
    formulario = FormularioAlternarCompetencia(requisicao.POST)
    if not formulario.is_valid():
        messages.error(requisicao, "Selecione uma competência válida.")
        return redirect("nucleo:trabalho")
    try:
        competencia, empresa = obter_competencia_para_alternar(
            formulario.cleaned_data["competencia_id"]
        )
        salvar_contexto(requisicao, empresa, competencia.competencia)
    except ValueError as erro:
        logger.warning("Alternância de competência recusada: %s", erro)
        messages.error(requisicao, str(erro))
    except DatabaseError:
        logger.exception("Falha ao alternar competência operacional")
        messages.error(requisicao, "Não foi possível alternar a competência.")
    else:
        messages.success(requisicao, "Contexto de trabalho atualizado.")
    return redirect("nucleo:trabalho")


@require_http_methods(["GET", "POST"])
def entradas(requisicao: HttpRequest) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    formulario = FormularioUploadEntrada(
        requisicao.POST or None,
        requisicao.FILES or None,
    )
    if requisicao.method == "POST" and formulario.is_valid():
        recebidos = []
        for arquivo_enviado in formulario.cleaned_data["arquivos"]:
            try:
                recebidos.append(
                    receber_arquivo(arquivo_enviado, contexto, requisicao.user)
                )
            except ErroEntrada as erro:
                messages.error(requisicao, str(erro))
            except DatabaseError:
                logger.exception("Falha de banco ao receber arquivo de entrada")
                messages.error(
                    requisicao,
                    f"Arquivo {arquivo_enviado.name}: não foi possível verificar ou preservar o arquivo.",
                )
        if recebidos:
            messages.success(
                requisicao,
                f"{len(recebidos)} arquivo(s) recebido(s) para mapeamento.",
            )
            if len(recebidos) == 1:
                return redirect("nucleo:mapear_entrada", identificador=recebidos[0].id)
            return redirect("nucleo:entradas")

    try:
        temporarios = list(ArquivoEntradaTemporario.objects.filter(
            usuario=requisicao.user,
            empresa_id=contexto.empresa_id,
            competencia=contexto.competencia,
            status__in=(
                EstadoArquivoEntrada.RECEBIDO,
                EstadoArquivoEntrada.EM_MAPEAMENTO,
            ),
        ).order_by("-criado_em"))
    except DatabaseError:
        logger.exception("Falha ao listar arquivos temporários de entrada")
        temporarios = []
        messages.error(requisicao, "Não foi possível carregar os arquivos em mapeamento.")
    try:
        lotes = listar_lotes_contexto(contexto)
    except DatabaseError:
        logger.exception("Falha ao listar lotes de entrada")
        lotes = []
        messages.error(requisicao, "Não foi possível carregar os lotes preparados.")
    return render(
        requisicao,
        "nucleo/entradas.html",
        {
            "titulo_pagina": "Entradas",
            "secao_ativa": "entradas",
            "contexto": contexto,
            "formulario": formulario,
            "temporarios": temporarios,
            "lotes": lotes,
        },
    )


def _contexto_mapeamento(requisicao, arquivo, usar_ia=False):
    abas = arquivo.inspecao.get("abas", [])
    aba_padrao = abas[0]["nome"] if abas else ""
    aba_solicitada = requisicao.POST.get("aba") or requisicao.GET.get("aba") or aba_padrao
    resumo_aba = next((item for item in abas if item["nome"] == aba_solicitada), None)
    cabecalho_padrao = resumo_aba["linha_cabecalho"] if resumo_aba else 0
    valor_cabecalho = (
        requisicao.POST.get("linha_cabecalho")
        or requisicao.GET.get("linha_cabecalho")
        or cabecalho_padrao
    )
    tipo = (
        requisicao.POST.get("tipo_documento")
        or requisicao.GET.get("tipo_documento")
        or "lancamentos"
    )
    try:
        linha_cabecalho = int(valor_cabecalho)
    except (TypeError, ValueError):
        linha_cabecalho = cabecalho_padrao

    configurar = FormularioConfigurarEntrada(
        initial={
            "aba": aba_solicitada,
            "linha_cabecalho": linha_cabecalho,
            "tipo_documento": tipo,
        },
        abas=abas,
    )
    selecao = inspecionar_selecao(
        arquivo, aba_solicitada, linha_cabecalho, tipo, usar_ia=usar_ia
    )
    inicial = {
        "aba": aba_solicitada,
        "linha_cabecalho": linha_cabecalho,
        "tipo_documento": tipo,
        **selecao.sugestao,
    }
    formulario = FormularioMapeamentoEntrada(
        initial=inicial,
        cabecalhos=selecao.aba["cabecalhos"],
        sugestao=selecao.sugestao,
    )
    previa = [
        {
            "numero_linha": linha["numero_linha"],
            "valores": [linha["valores"].get(cabecalho, "") for cabecalho in selecao.aba["cabecalhos"]],
        }
        for linha in selecao.aba["linhas"][:12]
    ]
    return {
        "configurar": configurar,
        "formulario": formulario,
        "campos_mapeamento": [
            formulario[campo] for campo, _ in FormularioMapeamentoEntrada.CAMPOS
        ],
        "selecao": selecao,
        "previa": previa,
        "sugestao_incompleta": not {"data", "valor"}.issubset(selecao.sugestao),
        "ia_solicitada": usar_ia,
    }


@require_http_methods(["GET", "POST"])
def mapear_entrada(requisicao: HttpRequest, identificador) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    try:
        arquivo = obter_arquivo_contexto(identificador, contexto, requisicao.user)
        dados = _contexto_mapeamento(
            requisicao,
            arquivo,
            usar_ia=(requisicao.method == "POST" and requisicao.POST.get("acao") == "sugerir_ia"),
        )
    except ErroEntrada as erro:
        messages.error(requisicao, str(erro))
        return redirect("nucleo:entradas")
    except DatabaseError:
        logger.exception("Falha ao carregar mapeamento de entrada")
        messages.error(requisicao, "Não foi possível carregar o arquivo para mapeamento.")
        return redirect("nucleo:entradas")
    return render(
        requisicao,
        "nucleo/mapear_entrada.html",
        {
            "titulo_pagina": "Mapear entrada",
            "secao_ativa": "entradas",
            "contexto": contexto,
            "arquivo": arquivo,
            **dados,
        },
    )


@require_POST
def confirmar_entrada(requisicao: HttpRequest, identificador) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    try:
        arquivo = obter_arquivo_contexto(identificador, contexto, requisicao.user)
        nome_aba = requisicao.POST.get("aba", "")
        linha_cabecalho = int(requisicao.POST.get("linha_cabecalho", "0"))
        tipo_documento = requisicao.POST.get("tipo_documento", "")
        selecao = inspecionar_selecao(
            arquivo, nome_aba, linha_cabecalho, tipo_documento
        )
        formulario = FormularioMapeamentoEntrada(
            requisicao.POST,
            cabecalhos=selecao.aba["cabecalhos"],
        )
        if not formulario.is_valid():
            messages.error(
                requisicao,
                "Revise o mapeamento: cada coluna original pode ser usada uma vez.",
            )
            consulta = urlencode({
                "aba": nome_aba,
                "linha_cabecalho": linha_cabecalho,
                "tipo_documento": tipo_documento,
            })
            return redirect(
                f"{reverse('nucleo:mapear_entrada', args=[identificador])}?{consulta}"
            )
        mapeamento = {
            campo: formulario.cleaned_data.get(campo, "")
            for campo, _ in FormularioMapeamentoEntrada.CAMPOS
        }
        resultado = confirmar_preparacao(
            arquivo,
            contexto,
            requisicao.user,
            nome_aba,
            linha_cabecalho,
            tipo_documento,
            mapeamento,
        )
    except (ErroEntrada, ValueError) as erro:
        messages.error(requisicao, str(erro))
        return redirect("nucleo:mapear_entrada", identificador=identificador)
    except DatabaseError:
        logger.exception("Falha ao confirmar entrada")
        messages.error(requisicao, "Não foi possível preparar o arquivo. Nenhum lote parcial foi mantido.")
        return redirect("nucleo:mapear_entrada", identificador=identificador)

    if resultado.get("duplicado"):
        messages.info(requisicao, f"O arquivo já corresponde ao lote {resultado['lote_id']}.")
    else:
        messages.success(
            requisicao,
            f"Lote {resultado['lote_id']} preparado com {resultado['total_linhas']} linha(s) e {resultado['pendentes']} pendência(s).",
        )
    return redirect("nucleo:entradas")


@require_POST
def descartar_entrada(requisicao: HttpRequest, identificador) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    try:
        arquivo = obter_arquivo_contexto(identificador, contexto, requisicao.user)
        descartar_arquivo(arquivo, contexto, requisicao.user)
    except ErroEntrada as erro:
        messages.error(requisicao, str(erro))
    except DatabaseError:
        logger.exception("Falha ao descartar arquivo temporário")
        messages.error(requisicao, "Não foi possível descartar o arquivo agora.")
    else:
        messages.success(requisicao, "Arquivo descartado da área temporária.")
    return redirect("nucleo:entradas")


@require_http_methods(["GET", "POST"])
def conferencia(requisicao: HttpRequest) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    lote_bruto = requisicao.POST.get("lote_id") or requisicao.GET.get("lote")
    try:
        lote_id = int(lote_bruto) if lote_bruto else None
        if requisicao.method == "POST":
            acao = requisicao.POST.get("acao")
            formulario_lote = FormularioLote(requisicao.POST)
            if not formulario_lote.is_valid():
                raise servico_conferencia.ErroConferencia("Lote informado inválido.")
            lote_id = formulario_lote.cleaned_data["lote_id"]
            if acao == "editar_linha":
                formulario = FormularioEditarLinhaConferencia(requisicao.POST)
                if not formulario.is_valid():
                    raise servico_conferencia.ErroConferencia("Revise os campos da linha.")
                dados_form = formulario.cleaned_data.copy()
                linha_id = dados_form.pop("linha_id")
                servico_conferencia.editar_linha(contexto, lote_id, linha_id, dados_form)
                messages.success(requisicao, "Linha atualizada e validada.")
            elif acao == "editar_lote":
                formulario = FormularioEdicaoEmLote(requisicao.POST)
                if not formulario.is_valid():
                    raise servico_conferencia.ErroConferencia("Revise a edição em lote.")
                ids = [int(item) for item in formulario.cleaned_data["linhas"].split(",") if item.strip().isdigit()]
                total = servico_conferencia.editar_em_lote(contexto, lote_id, ids, formulario.cleaned_data["campo"], formulario.cleaned_data["valor"])
                messages.success(requisicao, f"{total} linha(s) atualizada(s).")
            elif acao == "aprovar":
                resultado = servico_conferencia.aprovar(contexto, lote_id, requisicao.POST.get("substituir") == "1")
                messages.success(requisicao, f"Lote aprovado: {resultado['registros_salvos']} lançamento(s) gravado(s).")
                return redirect("nucleo:entradas")
            elif acao == "cancelar":
                servico_conferencia.cancelar(contexto, lote_id)
                messages.success(requisicao, "Preparação cancelada. O arquivo pode ser reaberto para nova conferência.")
            elif acao == "reabrir":
                servico_conferencia.reabrir(contexto, lote_id)
                messages.success(requisicao, "Lote reaberto para conferência.")
    except servico_conferencia.PeriodoPrecisaSubstituicao as erro:
        dados = servico_conferencia.carregar_conferencia(contexto, lote_id)
        dados.update({"confirmar_substituicao": True, "erro_substituicao": str(erro)})
        return render(requisicao, "nucleo/conferencia.html", {"titulo_pagina": "Conferência", "secao_ativa": "conferencia", "contexto": contexto, **dados})
    except (ValueError, DatabaseError) as erro:
        logger.warning("Operação de conferência recusada: %s", erro)
        messages.error(requisicao, str(erro) or "Não foi possível concluir a operação.")
    try:
        dados = servico_conferencia.carregar_conferencia(contexto, lote_id)
    except (ValueError, DatabaseError) as erro:
        messages.error(requisicao, str(erro))
        dados = {"lotes": [], "lote": None, "linhas": [], "validas": 0, "pendentes": 0, "total_debito": 0, "total_credito": 0, "saldo": 0}
    return render(
        requisicao,
        "nucleo/conferencia.html",
        {
            "titulo_pagina": "Conferência",
            "secao_ativa": "conferencia",
            "contexto": contexto,
            **dados,
        },
    )


@require_http_methods(["GET", "POST"])
def conciliacao(requisicao: HttpRequest) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    dados = servico_conciliacao.contexto_inicial(contexto)
    try:
        if requisicao.method == "POST":
            acao = requisicao.POST.get("acao", "executar")
            formulario = (
                FormularioDecisaoConciliacao(requisicao.POST)
                if acao == "decidir" else FormularioExecutarConciliacao(requisicao.POST)
            )
            if not formulario.is_valid():
                raise servico_conciliacao.ErroConciliacao("Revise os lotes e a decisão informados.")
            campos = formulario.cleaned_data
            if acao == "decidir":
                dados = servico_conciliacao.decidir(
                    contexto, requisicao.user,
                    campos["lote_extrato_id"], campos["lote_referencia_id"],
                    campos["linha_extrato_id"], campos["linha_referencia_id"],
                    campos["decisao"], campos["justificativa"],
                )
                messages.success(requisicao, "Decisão de conciliação registrada.")
            else:
                dados = servico_conciliacao.executar(
                    contexto, campos["lote_extrato_id"], campos["lote_referencia_id"]
                )
                messages.success(requisicao, "Conciliação executada com regras determinísticas.")
    except (ValueError, DatabaseError) as erro:
        logger.warning("Operação de conciliação recusada: %s", erro)
        messages.error(requisicao, str(erro) or "Não foi possível executar a conciliação.")
    return render(requisicao, "nucleo/conciliacao.html", {
        "titulo_pagina": "Conciliação", "secao_ativa": "conciliacao",
        "contexto": contexto, **dados,
    })


@require_GET
def modulo(requisicao: HttpRequest, secao: str) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    dados = SECOES[secao]
    return render(requisicao, "nucleo/modulo.html", {"titulo_pagina": dados["titulo"], "secao_ativa": secao, "contexto": contexto, **dados})


@require_http_methods(["GET", "POST"])
def assistente(requisicao: HttpRequest) -> HttpResponse:
    contexto = exigir_contexto(requisicao)
    conversa_bruta = requisicao.POST.get("conversa_id") or requisicao.GET.get("conversa")
    try:
        conversa_id = int(conversa_bruta) if conversa_bruta else None
    except (TypeError, ValueError):
        conversa_id = None
    try:
        if requisicao.method == "POST":
            acao = requisicao.POST.get("acao", "mensagem")
            if acao == "nova":
                conversa_id = servico_assistente.nova_conversa(requisicao)
            elif acao == "excluir":
                formulario = FormularioConversaAssistente(requisicao.POST)
                if not formulario.is_valid():
                    raise servico_assistente.ErroAssistente("Conversa inválida.")
                servico_assistente.excluir(requisicao, formulario.cleaned_data["conversa_id"])
                conversa_id = None
            else:
                formulario = FormularioMensagemAssistente(requisicao.POST)
                if not formulario.is_valid():
                    raise servico_assistente.ErroAssistente("Revise a mensagem enviada.")
                conversa_id = servico_assistente.enviar(
                    requisicao, contexto,
                    formulario.cleaned_data.get("conversa_id") or None,
                    formulario.cleaned_data["conteudo"],
                )
    except servico_assistente.ErroAssistente as erro:
        messages.error(requisicao, str(erro))
    except DatabaseError:
        logger.exception("Falha de banco no assistente")
        messages.error(requisicao, "Não foi possível carregar o assistente agora.")
    try:
        conversas = servico_assistente.listar(requisicao)
        if conversa_id is None and conversas:
            conversa_id = int(conversas[0]["id"])
        mensagens = servico_assistente.obter_mensagens(requisicao, conversa_id) if conversa_id else []
    except (ValueError, DatabaseError) as erro:
        logger.warning("Conversa indisponível: %s", erro)
        conversas, mensagens, conversa_id = servico_assistente.listar(requisicao), [], None
    return render(requisicao, "nucleo/assistente.html", {
        "titulo_pagina": "Assistente", "secao_ativa": "assistente", "contexto": contexto,
        "conversas": conversas, "mensagens": mensagens, "conversa_id": conversa_id,
        "formulario": FormularioMensagemAssistente(initial={"conversa_id": conversa_id}),
    })


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
