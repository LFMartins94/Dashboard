"""Configura as variáveis de produção da Railway sem registrar valores sensíveis."""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlunparse

from dotenv import load_dotenv


RAIZ = Path(__file__).resolve().parents[1]
PROJETO = "a5d48741-2c86-4663-99e9-92d0025758cf"
AMBIENTE = "production"
SERVICO = "contaview-web"
DOMINIO = "contaview-web-production.up.railway.app"


def url_direta_supabase(url: str) -> str:
    """Converte a conexão local do pooler para a conexão direta do projeto."""
    normalizada = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    partes = urlparse(normalizada)
    hosts_permitidos = {
        "db.ylxdlhthcocznmwajbfy.supabase.co",
        "aws-1-us-east-2.pooler.supabase.com",
    }
    if partes.hostname not in hosts_permitidos or partes.port not in {5432, 6543}:
        raise SystemExit("DATABASE_URL local não possui a conexão Supabase esperada.")
    usuario = quote("postgres", safe="")
    senha = quote(unquote(partes.password or ""), safe="")
    netloc = f"{usuario}:{senha}@db.ylxdlhthcocznmwajbfy.supabase.co:5432"
    return urlunparse(partes._replace(netloc=netloc))


def url_pool_sessao_supabase(url: str) -> str:
    """Converte o pool transacional local no pool de sessão IPv4 da Railway."""
    normalizada = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    partes = urlparse(normalizada)
    if partes.hostname != "aws-1-us-east-2.pooler.supabase.com" or partes.port not in {5432, 6543}:
        raise SystemExit("DATABASE_URL local não possui o pool Supabase esperado.")
    usuario = quote(unquote(partes.username or ""), safe="")
    senha = quote(unquote(partes.password or ""), safe="")
    netloc = f"{usuario}:{senha}@{partes.hostname}:5432"
    return urlunparse(partes._replace(netloc=netloc))


def definir_variavel(nome: str, valor: str) -> None:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise SystemExit("CLI da Railway não encontrada.")
    comando = [
        railway,
        "variable",
        "set",
        nome,
        "--stdin",
        "--skip-deploys",
        "--project",
        PROJETO,
        "--environment",
        AMBIENTE,
        "--service",
        SERVICO,
    ]
    resultado = subprocess.run(comando, input=valor, text=True, capture_output=True)
    if resultado.returncode:
        raise SystemExit(f"Não foi possível configurar a variável {nome}.")
    print(f"Variável configurada: {nome}")


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executar", action="store_true", help="Confirma o envio à Railway.")
    parser.add_argument(
        "--somente-banco",
        action="store_true",
        help="Atualiza somente DATABASE_URL sem renovar outros segredos.",
    )
    argumentos = parser.parse_args()
    load_dotenv(RAIZ / ".env")
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL não foi encontrada no arquivo .env.")
    if not argumentos.executar:
        print("Pré-requisitos aprovados. Execute novamente com --executar para configurar a Railway.")
        return

    variaveis = {"DATABASE_URL": url_pool_sessao_supabase(url)}
    if not argumentos.somente_banco:
        variaveis.update(
            {
                "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
                "DJANGO_ALLOWED_HOSTS": DOMINIO,
                "DJANGO_CSRF_TRUSTED_ORIGINS": f"https://{DOMINIO}",
                "DJANGO_SETTINGS_MODULE": "configuracao.settings.producao",
                "DJANGO_SECURE_SSL_REDIRECT": "true",
                "DJANGO_DATABASE_CONN_MAX_AGE": "60",
            }
        )
        chave_openai = os.getenv("OPENAI_API_KEY", "")
        if chave_openai:
            variaveis["OPENAI_API_KEY"] = chave_openai
    for nome, valor in variaveis.items():
        definir_variavel(nome, valor)
    print("Ambiente de produção configurado sem exibir valores sensíveis.")


if __name__ == "__main__":
    principal()
