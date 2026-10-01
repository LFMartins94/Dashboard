"""Cria o primeiro usuário sem receber senha pela linha de comando."""

from __future__ import annotations

import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Cria o usuário administrativo inicial do ContaView."
    requires_migrations_checks = True

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Nome de acesso.")
        parser.add_argument("--email", default="", help="E-mail administrativo.")
        parser.add_argument("--nome", default="", help="Nome exibido na interface.")
        parser.add_argument(
            "--nao-interativo",
            action="store_true",
            help="Lê a senha da variável temporária DJANGO_ADMIN_PASSWORD.",
        )

    def handle(self, *args, **opcoes):
        modelo_usuario = get_user_model()
        usuario = opcoes["usuario"].strip()
        if not usuario:
            raise CommandError("O usuário não pode ficar vazio.")
        if modelo_usuario.objects.filter(username__iexact=usuario).exists():
            raise CommandError("Já existe um usuário com esse nome.")

        senha = self._obter_senha(opcoes["nao_interativo"])
        novo_usuario = modelo_usuario(
            username=usuario,
            email=opcoes["email"].strip(),
            first_name=opcoes["nome"].strip(),
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        try:
            validate_password(senha, user=novo_usuario)
        except ValidationError as erro:
            raise CommandError(" ".join(erro.messages)) from erro

        novo_usuario.set_password(senha)
        with transaction.atomic():
            novo_usuario.save()
        self.stdout.write(self.style.SUCCESS("Usuário administrativo criado."))

    def _obter_senha(self, nao_interativo: bool) -> str:
        if nao_interativo:
            senha = os.getenv("DJANGO_ADMIN_PASSWORD", "")
            if not senha:
                raise CommandError(
                    "DJANGO_ADMIN_PASSWORD é obrigatória no modo não interativo."
                )
            return senha

        senha = getpass.getpass("Senha: ")
        confirmacao = getpass.getpass("Confirme a senha: ")
        if senha != confirmacao:
            raise CommandError("As senhas informadas não coincidem.")
        return senha
