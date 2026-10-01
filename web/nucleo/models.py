"""Modelos internos da aplicação web."""

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
