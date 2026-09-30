"""Configuração isolada para testes automatizados."""

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "segredo-de-teste-isolado-sem-uso-em-producao"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "[::1]"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MIDDLEWARE = [
    item
    for item in MIDDLEWARE  # noqa: F405
    if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]
