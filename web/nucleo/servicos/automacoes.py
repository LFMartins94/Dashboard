"""Automações internas, rastreáveis e sempre confirmadas pela contadora."""

from __future__ import annotations

import calendar
from datetime import date

from django.db import transaction
from django.utils import timezone

from contaview.logic.parsers import inspecionar_planilha

from ..models import (
    ArquivoEntradaTemporario,
    CategoriaChecklist,
    CompetenciaTrabalho,
    EstadoArquivoEntrada,
    EstadoOperacional,
    EstadoTarefaAutomacao,
    ItemChecklistTrabalho,
    ModeloDocumentoEsperado,
    PerfilOrigemEntrada,
    TarefaAutomacao,
    TipoTarefaAutomacao,
)
from .contexto import ContextoTrabalho, obter_empresa_ativa


class ErroAutomacao(ValueError):
    pass


def _validar_contexto(contexto: ContextoTrabalho) -> None:
    if not obter_empresa_ativa(contexto.empresa_id):
        raise ErroAutomacao("A empresa selecionada não está ativa.")


def identificar_perfil_origem(
    contexto: ContextoTrabalho, nome_arquivo: str, validar_contexto: bool = True,
) -> PerfilOrigemEntrada | None:
    """Sugere o perfil pelo prefixo, sem tomar decisão sobre o destino do arquivo."""
    if validar_contexto:
        _validar_contexto(contexto)
    nome = nome_arquivo.casefold()
    perfis = sorted(
        PerfilOrigemEntrada.objects.filter(
            empresa_id=contexto.empresa_id, ativo=True
        ),
        key=lambda perfil: len(perfil.prefixo_nome), reverse=True,
    )
    return next(
        (perfil for perfil in perfis if nome.startswith(perfil.prefixo_nome.casefold())),
        None,
    )


def registrar_processamento_concluido(
    arquivo: ArquivoEntradaTemporario, contexto: ContextoTrabalho, usuario,
) -> TarefaAutomacao:
    """Registra a inspeção já concluída pelo recebimento síncrono do arquivo."""
    return TarefaAutomacao.objects.create(
        empresa_id=contexto.empresa_id,
        competencia=contexto.competencia,
        tipo=TipoTarefaAutomacao.PROCESSAR_ARQUIVO,
        estado=EstadoTarefaAutomacao.CONCLUIDA,
        arquivo_entrada=arquivo,
        detalhes={"nome_arquivo": arquivo.nome_original, "etapa": "inspecao"},
        tentativas=1,
        solicitada_por=usuario,
        iniciada_em=timezone.now(),
        concluida_em=timezone.now(),
    )


@transaction.atomic
def criar_modelo_documento(
    contexto: ContextoTrabalho, nome: str, tipo_documento: str,
    dia_limite: int | None, obrigatorio: bool,
) -> ModeloDocumentoEsperado:
    _validar_contexto(contexto)
    if tipo_documento not in {"extrato", "folha", "notas", "lancamentos", "outro"}:
        raise ErroAutomacao("Tipo de documento inválido.")
    if not nome.strip():
        raise ErroAutomacao("Informe o nome do documento esperado.")
    modelo, _ = ModeloDocumentoEsperado.objects.update_or_create(
        empresa_id=contexto.empresa_id, nome=nome.strip(),
        defaults={
            "tipo_documento": tipo_documento, "dia_limite": dia_limite,
            "obrigatorio": obrigatorio, "ativo": True,
        },
    )
    return modelo


@transaction.atomic
def criar_perfil_origem(
    contexto: ContextoTrabalho, nome: str, prefixo_nome: str,
    pasta_referencia: str, tipo_documento: str, modo: str,
    regra_competencia: str,
) -> PerfilOrigemEntrada:
    _validar_contexto(contexto)
    if not nome.strip() or not prefixo_nome.strip():
        raise ErroAutomacao("Informe o nome e o prefixo do perfil de origem.")
    if tipo_documento not in {"extrato", "folha", "notas", "lancamentos", "outro"}:
        raise ErroAutomacao("Tipo de documento inválido.")
    if modo not in {"transacional", "contabil_estruturado"}:
        raise ErroAutomacao("Modo de origem inválido.")
    if regra_competencia not in {"restrita", "ampliada", "livre"}:
        raise ErroAutomacao("Regra de competência inválida.")
    perfil, _ = PerfilOrigemEntrada.objects.update_or_create(
        empresa_id=contexto.empresa_id, nome=nome.strip(),
        defaults={
            "prefixo_nome": prefixo_nome.strip(),
            "pasta_referencia": pasta_referencia.strip(),
            "tipo_documento": tipo_documento,
            "modo": modo,
            "regra_competencia": regra_competencia,
            "ativo": True,
        },
    )
    return perfil


def aplicar_modelos_documento(
    contexto: ContextoTrabalho, competencia: CompetenciaTrabalho, usuario,
    validar_contexto: bool = True,
) -> int:
    """Copia somente documentos ativos, sem modificar itens já acompanhados."""
    if validar_contexto:
        _validar_contexto(contexto)
    criados = 0
    for modelo in ModeloDocumentoEsperado.objects.filter(
        empresa_id=contexto.empresa_id, ativo=True
    ).order_by("nome"):
        _, criado = ItemChecklistTrabalho.objects.get_or_create(
            competencia_trabalho=competencia,
            titulo=f"Receber: {modelo.nome}",
            defaults={
                "categoria": CategoriaChecklist.DOCUMENTO,
                "ordem": 15,
                "obrigatorio": modelo.obrigatorio,
                "rota_destino": "nucleo:entradas",
                "atualizado_por": usuario,
            },
        )
        criados += int(criado)
    return criados


@transaction.atomic
def verificar_pendencias(
    contexto: ContextoTrabalho, usuario, validar_contexto: bool = True,
) -> TarefaAutomacao:
    if validar_contexto:
        _validar_contexto(contexto)
    competencia = CompetenciaTrabalho.objects.filter(
        empresa_id=contexto.empresa_id, competencia=contexto.competencia
    ).first()
    if competencia is None:
        raise ErroAutomacao("Inicie a competência antes de executar lembretes.")
    aguardando = ItemChecklistTrabalho.objects.filter(
        competencia_trabalho=competencia,
        estado__in=[EstadoOperacional.AGUARDANDO, EstadoOperacional.RECEBIDO],
    ).count()
    return TarefaAutomacao.objects.create(
        empresa_id=contexto.empresa_id, competencia=contexto.competencia,
        tipo=TipoTarefaAutomacao.VERIFICAR_PENDENCIAS,
        estado=EstadoTarefaAutomacao.CONCLUIDA,
        detalhes={"itens_pendentes": aguardando}, tentativas=1,
        solicitada_por=usuario, iniciada_em=timezone.now(), concluida_em=timezone.now(),
    )


def _atualizar_inspecao(arquivo: ArquivoEntradaTemporario) -> dict:
    from .entradas import ArquivoEmMemoria, resumir_inspecao

    resultado = inspecionar_planilha(
        ArquivoEmMemoria(bytes(arquivo.conteudo), arquivo.nome_original)
    )
    if not resultado.get("sucesso"):
        raise ErroAutomacao(resultado.get("erro", "Não foi possível ler o arquivo."))
    arquivo.inspecao = resumir_inspecao(resultado)
    arquivo.status = EstadoArquivoEntrada.EM_MAPEAMENTO
    arquivo.save(update_fields=["inspecao", "status", "atualizado_em"])
    return resultado


@transaction.atomic
def reexecutar_tarefa(contexto: ContextoTrabalho, tarefa_id: int, usuario) -> TarefaAutomacao:
    _validar_contexto(contexto)
    tarefa = TarefaAutomacao.objects.select_for_update().select_related("arquivo_entrada").filter(
        id=tarefa_id, empresa_id=contexto.empresa_id, competencia=contexto.competencia
    ).first()
    if tarefa is None:
        raise ErroAutomacao("A tarefa não pertence ao contexto selecionado.")
    if tarefa.estado != EstadoTarefaAutomacao.FALHA:
        raise ErroAutomacao("Somente tarefas com falha podem ser reexecutadas.")
    if tarefa.tentativas >= 3:
        raise ErroAutomacao("A tarefa atingiu o limite de três tentativas. Revise o arquivo manualmente.")
    tarefa.estado = EstadoTarefaAutomacao.PROCESSANDO
    tarefa.tentativas += 1
    tarefa.mensagem_erro = ""
    tarefa.iniciada_em = timezone.now()
    tarefa.solicitada_por = usuario
    tarefa.save(update_fields=["estado", "tentativas", "mensagem_erro", "iniciada_em", "solicitada_por"])
    try:
        if tarefa.tipo == TipoTarefaAutomacao.PROCESSAR_ARQUIVO:
            if tarefa.arquivo_entrada is None:
                raise ErroAutomacao("O arquivo original não está disponível para nova leitura.")
            _atualizar_inspecao(tarefa.arquivo_entrada)
        else:
            competencia = CompetenciaTrabalho.objects.get(
                empresa_id=contexto.empresa_id, competencia=contexto.competencia
            )
            pendentes = competencia.itens.exclude(estado=EstadoOperacional.ENTREGUE).count()
            tarefa.detalhes = {"itens_pendentes": pendentes}
    except Exception as erro:
        tarefa.estado = EstadoTarefaAutomacao.FALHA
        tarefa.mensagem_erro = str(erro)[:500]
        tarefa.concluida_em = timezone.now()
        tarefa.save(update_fields=["estado", "mensagem_erro", "concluida_em"])
        return tarefa
    tarefa.estado = EstadoTarefaAutomacao.CONCLUIDA
    tarefa.concluida_em = timezone.now()
    tarefa.save(update_fields=["estado", "detalhes", "concluida_em"])
    return tarefa


def _lembretes(contexto: ContextoTrabalho) -> list[dict]:
    competencia = CompetenciaTrabalho.objects.filter(
        empresa_id=contexto.empresa_id, competencia=contexto.competencia
    ).first()
    if competencia is None:
        return []
    hoje = date.today()
    ano, mes = (int(item) for item in contexto.competencia.split("-"))
    resultado = []
    for modelo in ModeloDocumentoEsperado.objects.filter(empresa_id=contexto.empresa_id, ativo=True):
        titulo = f"Receber: {modelo.nome}"
        item = competencia.itens.filter(titulo=titulo).first()
        if item and item.estado == EstadoOperacional.ENTREGUE:
            continue
        data_limite = None
        if modelo.dia_limite:
            data_limite = date(ano, mes, min(modelo.dia_limite, calendar.monthrange(ano, mes)[1]))
        resultado.append({
            "titulo": modelo.nome,
            "prazo": data_limite.strftime("%d/%m/%Y") if data_limite else "Sem prazo definido",
            "atrasado": bool(data_limite and hoje > data_limite),
            "obrigatorio": modelo.obrigatorio,
        })
    return sorted(resultado, key=lambda item: (not item["atrasado"], item["prazo"]))


def carregar(contexto: ContextoTrabalho) -> dict:
    _validar_contexto(contexto)
    return {
        "modelos_documento": ModeloDocumentoEsperado.objects.filter(empresa_id=contexto.empresa_id, ativo=True).order_by("nome"),
        "perfis_origem": PerfilOrigemEntrada.objects.filter(empresa_id=contexto.empresa_id, ativo=True).order_by("nome"),
        "tarefas": TarefaAutomacao.objects.filter(empresa_id=contexto.empresa_id, competencia=contexto.competencia).order_by("-criada_em")[:20],
        "lembretes": _lembretes(contexto),
    }
