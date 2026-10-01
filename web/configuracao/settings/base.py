"""Configurações compartilhadas pelos ambientes Django."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
RAIZ_PROJETO = BASE_DIR.parent

load_dotenv(RAIZ_PROJETO / ".env")


def obter_booleano(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


def obter_lista(nome: str, padrao: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(nome, padrao).split(",") if item.strip()]


def configurar_banco(url: str | None) -> dict[str, object]:
    """Converte DATABASE_URL em configuração Django sem expor credenciais."""
    if not url:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("PGDATABASE", "contaview"),
            "USER": os.getenv("PGUSER", "postgres"),
            "PASSWORD": os.getenv("PGPASSWORD", ""),
            "HOST": os.getenv("PGHOST", "127.0.0.1"),
            "PORT": os.getenv("PGPORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DJANGO_DATABASE_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
        }

    url_normalizada = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    partes = urlparse(url_normalizada)
    if partes.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL deve usar o protocolo PostgreSQL.")

    opcoes = dict(parse_qsl(partes.query, keep_blank_values=False))
    if partes.hostname and partes.hostname.endswith("supabase.co"):
        opcoes.setdefault("sslmode", "require")

    configuracao: dict[str, object] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(partes.path.lstrip("/")) or "postgres",
        "USER": unquote(partes.username or ""),
        "PASSWORD": unquote(partes.password or ""),
        "HOST": partes.hostname or "",
        "PORT": str(partes.port or 5432),
        "CONN_MAX_AGE": int(os.getenv("DJANGO_DATABASE_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": opcoes,
    }
    if str(partes.port or "") == "6543":
        configuracao["DISABLE_SERVER_SIDE_CURSORS"] = True
    return configuracao


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50)

DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "nucleo.apps.NucleoConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "nucleo.middleware.IdentificadorRequisicaoMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "nucleo.middleware.ContextoTrabalhoMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "configuracao.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "nucleo.contexto.contexto_requisicao",
            ],
        },
    },
]

WSGI_APPLICATION = "configuracao.wsgi.application"
ASGI_APPLICATION = "configuracao.asgi.application"

DATABASES = {"default": configurar_banco(os.getenv("DATABASE_URL"))}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = RAIZ_PROJETO / "staticfiles"
MEDIA_URL = "/arquivos/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "nucleo:login"
LOGIN_REDIRECT_URL = "nucleo:trabalho"
SESSION_COOKIE_AGE = int(os.getenv("DJANGO_SESSION_COOKIE_AGE", "28800"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "nucleo.views.falha_csrf"
LOGIN_TENTATIVAS_LIMITE = int(os.getenv("LOGIN_TENTATIVAS_LIMITE", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "900"))
LOGIN_BLOQUEIO_SEGUNDOS = int(os.getenv("LOGIN_BLOQUEIO_SEGUNDOS", "900"))
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "nucleo.logs.FormatadorJson"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": os.getenv("NIVEL_LOG", "INFO")},
    "loggers": {
        "django.server": {
            "handlers": ["console"],
            "level": os.getenv("NIVEL_LOG", "INFO"),
            "propagate": False,
        }
    },
}
