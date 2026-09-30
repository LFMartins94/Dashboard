"""Configuração para desenvolvimento local."""

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = obter_lista(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver"
)
