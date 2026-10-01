"""Fila operacional da tela Trabalho, sempre vinculada ao contexto validado."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import connection, transaction
from django.urls import reverse
from django.utils import timezone

from nucleo.models import (
    CategoriaChecklist,
    CompetenciaTrabalho,
    EstadoOperacional,
    ItemChecklistTrabalho,
)
from nucleo.servicos.contexto import (
    ContextoTrabalho,
    listar_empresas_ativas,
    obter_empresa_ativa,
)


ITENS_PADRAO = (
    {
        "titulo": "Receber documentos da competência",
        "categoria": CategoriaChecklist.DOCUMENTO,
        "ordem": 10,
        "rota_destino": "nucleo:entradas",
    },
    {
        "titulo": "Conferir dados preparados",
        "categoria": CategoriaChecklist.CONFERENCIA,
        "ordem": 20,
        "rota_destino": "nucleo:conferencia",
    },
    {
        "titulo": "Resolver divergências",
        "categoria": CategoriaChecklist.DIVERGENCIA,
        "ordem": 30,
        "rota_destino": "nucleo:conferencia",
    },
    {
        "titulo": "Preparar entrega da competência",
        "categoria": CategoriaChecklist.ENTREGA,
        "ordem": 40,
        "rota_destino": "nucleo:entregas",
    },
)


@dataclass(frozen=True, slots=True)
class MetricasTrabalho:
    arquivos_recebidos: int = 0
    lotes_pendentes: int = 0
    linhas_pendentes: int = 0
    divergencias: int = 0
    documentos_aguardando: int = 0
    entregas_prontas: int = 0
    entregas_concluidas: int = 0

    @property
    def total_pendencias(self) -> int:
        return self.lotes_pendentes + self.divergencias


@dataclass(frozen=True, slots=True)
class AlertaTrabalho:
    titulo: str
    descricao: str
    rotulo: str
    url: str
    severidade: str = "neutra"


@dataclass(frozen=True, slots=True)
class AcaoTrabalho:
    titulo: str
    descricao: str
    url: str


@dataclass(slots=True)
class PainelTrabalho:
    competencia: CompetenciaTrabalho | None = None
    itens: list[ItemChecklistTrabalho] = field(default_factory=list)
    metricas: MetricasTrabalho = field(default_factory=MetricasTrabalho)
    alertas: list[AlertaTrabalho] = field(default_factory=list)
    competencias_abertas: list[dict] = field(default_factory=list)
    proxima_acao: AcaoTrabalho | None = None


def _validar_contexto(contexto: ContextoTrabalho) -> None:
    if contexto.empresa_id <= 0 or len(contexto.competencia) != 7:
        raise ValueError("Contexto de trabalho inválido.")


def iniciar_competencia(contexto: ContextoTrabalho, usuario) -> CompetenciaTrabalho:
    """Cria o ciclo e o checklist padrão sem duplicar uma competência existente."""
    _validar_contexto(contexto)
    if obter_empresa_ativa(contexto.empresa_id) is None:
        raise ValueError("A empresa selecionada não está ativa.")

    with transaction.atomic():
        competencia, _ = CompetenciaTrabalho.objects.get_or_create(
            empresa_id=contexto.empresa_id,
            competencia=contexto.competencia,
            defaults={"iniciado_por": usuario},
        )
        for definicao in ITENS_PADRAO:
            ItemChecklistTrabalho.objects.get_or_create(
                competencia_trabalho=competencia,
                titulo=definicao["titulo"],
                defaults={
                    "categoria": definicao["categoria"],
                    "ordem": definicao["ordem"],
                    "rota_destino": definicao["rota_destino"],
                    "atualizado_por": usuario,
                },
            )
    return competencia


def _consultar_metricas_existentes(contexto: ContextoTrabalho) -> tuple[int, int, int, int]:
    parametros = [
        contexto.empresa_id,
        contexto.competencia,
        contexto.empresa_id,
        contexto.competencia,
        contexto.empresa_id,
        contexto.competencia,
        contexto.empresa_id,
        contexto.competencia,
        contexto.empresa_id,
        contexto.competencia,
    ]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM lotes_importacao
                 WHERE empresa_id = %s AND periodo = %s AND status <> 'cancelado'),
                (SELECT COUNT(*) FROM lotes_importacao
                 WHERE empresa_id = %s AND periodo = %s AND status = 'em_revisao'),
                (SELECT COUNT(*) FROM linhas_preparadas linha
                 JOIN lotes_importacao lote ON lote.id = linha.lote_id
                 WHERE linha.empresa_id = %s AND lote.periodo = %s
                   AND lote.status = 'em_revisao' AND linha.status = 'pendente'),
                COALESCE((
                    SELECT pares_com_erro FROM conciliacoes
                    WHERE empresa_id = %s AND periodo = %s
                    ORDER BY executado_em DESC, id DESC LIMIT 1
                ), 0) + (
                    SELECT COUNT(*) FROM ocorrencias_auditoria ocorrencia
                    JOIN lancamentos lancamento ON lancamento.id = ocorrencia.lancamento_id
                    WHERE ocorrencia.empresa_id = %s AND lancamento.periodo = %s
                      AND ocorrencia.resolvida = FALSE
                )
            """,
            parametros,
        )
        linha = cursor.fetchone() or (0, 0, 0, 0)
    return tuple(int(valor or 0) for valor in linha)


def _listar_lotes_pendentes(contexto: ContextoTrabalho) -> list[AlertaTrabalho]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT lote.id, lote.nome_arquivo, lote.total_linhas,
                   (SELECT COUNT(*) FROM linhas_preparadas linha
                    WHERE linha.lote_id = lote.id AND linha.status = 'pendente')
            FROM lotes_importacao lote
            WHERE lote.empresa_id = %s AND lote.periodo = %s
              AND lote.status = 'em_revisao'
            ORDER BY lote.criado_em, lote.id
            LIMIT 10
            """,
            [contexto.empresa_id, contexto.competencia],
        )
        linhas = cursor.fetchall()
    return [
        AlertaTrabalho(
            titulo=str(nome_arquivo),
            descricao=f"{int(pendentes)} de {int(total_linhas)} linhas aguardando revisão.",
            rotulo="Lote pendente",
            url=f"{reverse('nucleo:conferencia')}?lote={int(lote_id)}",
            severidade="atencao",
        )
        for lote_id, nome_arquivo, total_linhas, pendentes in linhas
    ]


def _listar_competencias_abertas(contexto: ContextoTrabalho) -> list[dict]:
    nomes = {empresa["id"]: empresa["nome"] for empresa in listar_empresas_ativas()}
    competencias = (
        CompetenciaTrabalho.objects.exclude(estado=EstadoOperacional.ENTREGUE)
        .order_by("-competencia", "empresa_id")
        .values("id", "empresa_id", "competencia", "estado")
    )
    resultado = []
    for competencia in competencias:
        nome = nomes.get(competencia["empresa_id"])
        if not nome:
            continue
        periodo = competencia["competencia"]
        resultado.append(
            {
                **competencia,
                "empresa_nome": nome,
                "competencia_exibicao": f"{periodo[5:]}/{periodo[:4]}",
                "estado_exibicao": EstadoOperacional(competencia["estado"]).label,
                "selecionada": (
                    competencia["empresa_id"] == contexto.empresa_id
                    and periodo == contexto.competencia
                ),
            }
        )
    resultado.sort(key=lambda item: not item["selecionada"])
    return resultado


def _definir_proxima_acao(
    competencia: CompetenciaTrabalho | None,
    itens: list[ItemChecklistTrabalho],
    metricas: MetricasTrabalho,
) -> AcaoTrabalho | None:
    if competencia is None:
        return None
    if metricas.lotes_pendentes:
        return AcaoTrabalho(
            "Revisar o lote pendente",
            f"Há {metricas.linhas_pendentes} linha(s) esperando conferência.",
            reverse("nucleo:conferencia"),
        )
    if metricas.divergencias:
        return AcaoTrabalho(
            "Resolver divergências",
            f"Há {metricas.divergencias} divergência(s) aberta(s) na competência.",
            f"{reverse('nucleo:conferencia')}?origem=divergencias",
        )
    for item in itens:
        if item.estado != EstadoOperacional.ENTREGUE:
            return AcaoTrabalho(
                item.titulo,
                f"Estado atual: {item.get_estado_display().lower()}.",
                reverse(item.rota_destino),
            )
    return AcaoTrabalho(
        "Competência concluída",
        "Todos os itens obrigatórios foram entregues.",
        reverse("nucleo:entregas"),
    )


def montar_painel_trabalho(contexto: ContextoTrabalho) -> PainelTrabalho:
    _validar_contexto(contexto)
    competencia = CompetenciaTrabalho.objects.filter(
        empresa_id=contexto.empresa_id,
        competencia=contexto.competencia,
    ).first()
    itens = list(competencia.itens.order_by("ordem", "id")) if competencia else []
    arquivos, lotes, linhas, divergencias = _consultar_metricas_existentes(contexto)
    documentos = sum(
        item.categoria == CategoriaChecklist.DOCUMENTO
        and item.estado == EstadoOperacional.AGUARDANDO
        for item in itens
    )
    entregas_prontas = sum(
        item.categoria == CategoriaChecklist.ENTREGA
        and item.estado == EstadoOperacional.REVISADO
        for item in itens
    )
    entregas_concluidas = sum(
        item.categoria == CategoriaChecklist.ENTREGA
        and item.estado == EstadoOperacional.ENTREGUE
        for item in itens
    )
    metricas = MetricasTrabalho(
        arquivos_recebidos=arquivos,
        lotes_pendentes=lotes,
        linhas_pendentes=linhas,
        divergencias=divergencias,
        documentos_aguardando=documentos,
        entregas_prontas=entregas_prontas,
        entregas_concluidas=entregas_concluidas,
    )
    alertas = _listar_lotes_pendentes(contexto)
    if divergencias:
        alertas.append(
            AlertaTrabalho(
                titulo="Divergências abertas",
                descricao=f"{divergencias} ocorrência(s) exigem decisão humana.",
                rotulo="Conferência",
                url=f"{reverse('nucleo:conferencia')}?origem=divergencias",
                severidade="erro",
            )
        )
    return PainelTrabalho(
        competencia=competencia,
        itens=itens,
        metricas=metricas,
        alertas=alertas,
        competencias_abertas=_listar_competencias_abertas(contexto),
        proxima_acao=_definir_proxima_acao(competencia, itens, metricas),
    )


def _recalcular_estado(competencia: CompetenciaTrabalho) -> None:
    estados = list(competencia.itens.values_list("estado", flat=True))
    if estados and all(estado == EstadoOperacional.ENTREGUE for estado in estados):
        novo = EstadoOperacional.ENTREGUE
    elif EstadoOperacional.COM_DIVERGENCIA in estados:
        novo = EstadoOperacional.COM_DIVERGENCIA
    elif EstadoOperacional.EM_CONFERENCIA in estados:
        novo = EstadoOperacional.EM_CONFERENCIA
    elif EstadoOperacional.RECEBIDO in estados:
        novo = EstadoOperacional.RECEBIDO
    elif estados and all(
        estado in {EstadoOperacional.REVISADO, EstadoOperacional.ENTREGUE}
        for estado in estados
    ):
        novo = EstadoOperacional.REVISADO
    else:
        novo = EstadoOperacional.AGUARDANDO
    if competencia.estado != novo:
        competencia.estado = novo
        competencia.save(update_fields=["estado", "atualizado_em"])


def atualizar_item_checklist(
    contexto: ContextoTrabalho,
    item_id: int,
    estado: str,
    usuario,
) -> ItemChecklistTrabalho:
    _validar_contexto(contexto)
    if estado not in EstadoOperacional.values:
        raise ValueError("Estado operacional inválido.")
    with transaction.atomic():
        item = (
            ItemChecklistTrabalho.objects.select_for_update()
            .select_related("competencia_trabalho")
            .filter(
                pk=item_id,
                competencia_trabalho__empresa_id=contexto.empresa_id,
                competencia_trabalho__competencia=contexto.competencia,
            )
            .first()
        )
        if item is None:
            raise ValueError("Item não encontrado no contexto selecionado.")
        item.estado = estado
        item.atualizado_por = usuario
        item.concluido_em = timezone.now() if estado == EstadoOperacional.ENTREGUE else None
        item.save(
            update_fields=["estado", "atualizado_por", "concluido_em", "atualizado_em"]
        )
        _recalcular_estado(item.competencia_trabalho)
    return item


def obter_competencia_para_alternar(competencia_id: int) -> tuple[CompetenciaTrabalho, dict]:
    competencia = CompetenciaTrabalho.objects.filter(pk=competencia_id).first()
    if competencia is None:
        raise ValueError("Competência não encontrada.")
    empresa = obter_empresa_ativa(competencia.empresa_id)
    if empresa is None:
        raise ValueError("A empresa desta competência não está ativa.")
    return competencia, empresa
