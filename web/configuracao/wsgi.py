"""Ponto de entrada WSGI do ContaView."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuracao.settings.producao")

application = get_wsgi_application()
