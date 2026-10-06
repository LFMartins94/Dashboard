"""Cria uma única conta administrativa a partir das credenciais locais já autorizadas."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from configurar_ambiente_railway import url_pool_sessao_supabase


RAIZ = Path(__file__).resolve().parents[1]


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executar", action="store_true", help="Confirma a criação da conta administrativa.")
    argumentos = parser.parse_args()
    load_dotenv(RAIZ / ".env")
    usuario = os.getenv("APP_USUARIO", "").strip()
    senha = os.getenv("APP_SENHA", "")
    url = os.getenv("DATABASE_URL", "")
    if not usuario or not senha or not url:
        raise SystemExit("APP_USUARIO, APP_SENHA e DATABASE_URL são obrigatórios no arquivo .env.")
    if not argumentos.executar:
        print("Pré-requisitos aprovados. Execute novamente com --executar para criar a conta.")
        return

    os.environ["DATABASE_URL"] = url_pool_sessao_supabase(url)
    os.environ["DJANGO_ADMIN_PASSWORD"] = senha
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuracao.settings.desenvolvimento")
    sys.path.insert(0, str(RAIZ / "web"))
    import django
    from django.core.management import call_command

    django.setup()
    call_command("criar_usuario_inicial", usuario=usuario, nao_interativo=True)
    print("Conta administrativa criada sem expor usuário ou senha.")


if __name__ == "__main__":
    principal()
