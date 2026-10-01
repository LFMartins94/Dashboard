"""Limitação determinística de tentativas de login."""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from nucleo.models import TentativaLogin


def criar_chave(requisicao, usuario: str) -> str:
    endereco = requisicao.META.get("REMOTE_ADDR", "desconhecido")
    material = f"{endereco}|{usuario.strip().casefold()}"
    return salted_hmac(
        "contaview.limite_login", material, algorithm="sha256"
    ).hexdigest()


def segundos_para_liberacao(chave_hash: str) -> int:
    tentativa = TentativaLogin.objects.filter(pk=chave_hash).first()
    if not tentativa or not tentativa.bloqueado_ate:
        return 0
    restante = int((tentativa.bloqueado_ate - timezone.now()).total_seconds())
    return max(restante, 0)


def registrar_falha(chave_hash: str) -> int:
    agora = timezone.now()
    janela = timedelta(seconds=settings.LOGIN_JANELA_SEGUNDOS)
    bloqueio = timedelta(seconds=settings.LOGIN_BLOQUEIO_SEGUNDOS)

    with transaction.atomic():
        tentativa = TentativaLogin.objects.select_for_update().filter(pk=chave_hash).first()
        if tentativa is None:
            try:
                tentativa = TentativaLogin.objects.create(
                    chave_hash=chave_hash,
                    tentativas=0,
                    janela_iniciada_em=agora,
                )
            except IntegrityError:
                tentativa = TentativaLogin.objects.select_for_update().get(pk=chave_hash)

        if agora - tentativa.janela_iniciada_em >= janela:
            tentativa.tentativas = 0
            tentativa.janela_iniciada_em = agora
            tentativa.bloqueado_ate = None

        tentativa.tentativas += 1
        if tentativa.tentativas >= settings.LOGIN_TENTATIVAS_LIMITE:
            tentativa.bloqueado_ate = agora + bloqueio
        tentativa.save(
            update_fields=[
                "tentativas",
                "janela_iniciada_em",
                "bloqueado_ate",
                "atualizado_em",
            ]
        )
    return segundos_para_liberacao(chave_hash)


def limpar_falhas(chave_hash: str) -> None:
    TentativaLogin.objects.filter(pk=chave_hash).delete()
