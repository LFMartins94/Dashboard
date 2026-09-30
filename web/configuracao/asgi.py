"""Ponto de entrada ASGI do ContaView."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuracao.settings.producao")

application = get_asgi_application()
