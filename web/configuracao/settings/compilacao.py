"""Configuração sem segredos usada apenas para coletar arquivos estáticos."""

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["localhost"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
