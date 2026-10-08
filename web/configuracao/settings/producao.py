"""Configuração endurecida para o contêiner de produção."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

if not os.getenv("DJANGO_SECRET_KEY"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY é obrigatória em produção.")
if not os.getenv("DATABASE_URL"):
    raise ImproperlyConfigured("DATABASE_URL é obrigatória em produção.")

ALLOWED_HOSTS = obter_lista("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS é obrigatória em produção.")

# A verificação de saúde da Railway alcança o serviço pelo domínio privado.
# O domínio público continua obrigatório e o host interno só é incluído quando
# a própria plataforma o fornece ao contêner.
dominio_privado_railway = os.getenv("RAILWAY_PRIVATE_DOMAIN", "").strip().lower()
if dominio_privado_railway and dominio_privado_railway not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(dominio_privado_railway)

CSRF_TRUSTED_ORIGINS = obter_lista("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured("DJANGO_CSRF_TRUSTED_ORIGINS é obrigatória em produção.")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = obter_booleano("DJANGO_SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
