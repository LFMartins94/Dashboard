"""Modelos internos da aplicação web."""

from django.conf import settings
from django.db import models


class TentativaLogin(models.Model):
    """Contador sem dados pessoais brutos para limitar tentativas de acesso."""

    chave_hash = models.CharField(max_length=64, primary_key=True)
    tentativas = models.PositiveSmallIntegerField(default=0)
    janela_iniciada_em = models.DateTimeField()
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_tentativas_login"
        verbose_name = "tentativa de login"
        verbose_name_plural = "tentativas de login"
        indexes = [
            models.Index(fields=["bloqueado_ate"], name="idx_login_bloqueio"),
        ]


class EstadoOperacional(models.TextChoices):
    AGUARDANDO = "aguardando", "Aguardando"
    RECEBIDO = "recebido", "Recebido"
    EM_CONFERENCIA = "em_conferencia", "Em conferência"
    COM_DIVERGENCIA = "com_divergencia", "Com divergência"
    REVISADO = "revisado", "Revisado"
    ENTREGUE = "entregue", "Entregue"


class CompetenciaTrabalho(models.Model):
    """Ciclo operacional de uma empresa em uma competência."""

    empresa_id = models.PositiveIntegerField()
    competencia = models.CharField(max_length=7)
    estado = models.CharField(
        max_length=20,
        choices=EstadoOperacional.choices,
        default=EstadoOperacional.AGUARDANDO,
    )
    prazo_entrega = models.DateField(null=True, blank=True)
    iniciado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="competencias_iniciadas",
    )
    iniciado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_competencias_trabalho"
        verbose_name = "competência de trabalho"
        verbose_name_plural = "competências de trabalho"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa_id", "competencia"], name="uq_comp_empresa_periodo"
            ),
            models.CheckConstraint(
                condition=models.Q(empresa_id__gt=0), name="ck_comp_empresa_pos"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    competencia__regex=r"^[0-9]{4}-(0[1-9]|1[0-2])$"
                ),
                name="ck_comp_periodo",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoOperacional.values),
                name="ck_comp_estado",
            ),
        ]
        indexes = [
            models.Index(
                fields=["empresa_id", "estado", "competencia"],
                name="idx_comp_empresa_estado",
            ),
        ]

    @property
    def competencia_exibicao(self) -> str:
        return f"{self.competencia[5:]}/{self.competencia[:4]}"


class CategoriaChecklist(models.TextChoices):
    DOCUMENTO = "documento", "Documento"
    CONFERENCIA = "conferencia", "Conferência"
    DIVERGENCIA = "divergencia", "Divergência"
    ENTREGA = "entrega", "Entrega"


class ItemChecklistTrabalho(models.Model):
    """Item recorrente copiado para uma competência específica."""

    competencia_trabalho = models.ForeignKey(
        CompetenciaTrabalho,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    titulo = models.CharField(max_length=160)
    categoria = models.CharField(max_length=20, choices=CategoriaChecklist.choices)
    estado = models.CharField(
        max_length=20,
        choices=EstadoOperacional.choices,
        default=EstadoOperacional.AGUARDANDO,
    )
    ordem = models.PositiveSmallIntegerField(default=0)
    obrigatorio = models.BooleanField(default=True)
    rota_destino = models.CharField(max_length=80)
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="itens_checklist_atualizados",
    )
    concluido_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "django_itens_checklist_trabalho"
        verbose_name = "item do checklist"
        verbose_name_plural = "itens do checklist"
        constraints = [
            models.UniqueConstraint(
                fields=["competencia_trabalho", "titulo"],
                name="uq_item_comp_titulo",
            ),
            models.CheckConstraint(
                condition=models.Q(categoria__in=CategoriaChecklist.values),
                name="ck_item_categoria",
            ),
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoOperacional.values),
                name="ck_item_estado",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    rota_destino__in=(
                        "nucleo:entradas",
                        "nucleo:conferencia",
                        "nucleo:entregas",
                    )
                ),
                name="ck_item_rota",
            ),
        ]
        indexes = [
            models.Index(
                fields=["competencia_trabalho", "estado", "ordem"],
                name="idx_item_comp_estado",
            ),
        ]
