"""Valida a consulta pública do Assistente sem registrar credenciais ou conversas."""

from __future__ import annotations

import argparse
import http.cookiejar
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


RAIZ = Path(__file__).resolve().parents[1]
BASE = "https://contaview-web-production.up.railway.app"
COMPETENCIA_TESTE = "2026-10"


class SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, novo_url):
        return None


def requisitar(abertura, requisicao):
    try:
        return abertura.open(requisicao, timeout=45)
    except urllib.error.HTTPError as erro:
        return erro


def extrair_csrf(corpo: str) -> str:
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', corpo)
    if not token:
        raise SystemExit("A página não forneceu o token CSRF esperado.")
    return token.group(1)


def enviar_formulario(abertura, url: str, dados: dict[str, str]):
    corpo = urllib.parse.urlencode(dados).encode()
    return requisitar(
        abertura,
        urllib.request.Request(url, data=corpo, headers={"Referer": url}),
    )


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--executar", action="store_true", help="Confirma o teste público temporário."
    )
    argumentos = parser.parse_args()
    load_dotenv(RAIZ / ".env")
    usuario = os.getenv("APP_USUARIO", "")
    senha = os.getenv("APP_SENHA", "")
    if not usuario or not senha:
        raise SystemExit("APP_USUARIO e APP_SENHA são obrigatórios no arquivo .env.")
    if not argumentos.executar:
        print("Pré-requisitos aprovados. Execute novamente com --executar para testar o Assistente.")
        return

    cookies = http.cookiejar.CookieJar()
    abertura = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies), SemRedirecionamento()
    )
    url_acesso = f"{BASE}/acesso/"
    pagina_acesso = requisitar(abertura, urllib.request.Request(url_acesso))
    csrf_acesso = extrair_csrf(pagina_acesso.read().decode("utf-8"))
    resposta_login = enviar_formulario(
        abertura,
        url_acesso,
        {"username": usuario, "password": senha, "csrfmiddlewaretoken": csrf_acesso},
    )
    if resposta_login.status != 302:
        raise SystemExit(f"O login não redirecionou como esperado: HTTP {resposta_login.status}.")

    url_contexto = f"{BASE}/contexto/"
    pagina_contexto = requisitar(abertura, urllib.request.Request(url_contexto))
    corpo_contexto = pagina_contexto.read().decode("utf-8")
    csrf_contexto = extrair_csrf(corpo_contexto)
    empresa = re.search(r'<option value="([1-9][0-9]*)">', corpo_contexto)
    if not empresa:
        raise SystemExit("Não há empresa ativa disponível para o teste do Assistente.")
    resposta_contexto = enviar_formulario(
        abertura,
        url_contexto,
        {
            "empresa": empresa.group(1),
            "competencia": COMPETENCIA_TESTE,
            "csrfmiddlewaretoken": csrf_contexto,
            "proximo": "/assistente/",
        },
    )
    if resposta_contexto.status != 302:
        raise SystemExit("Não foi possível selecionar o contexto temporário do Assistente.")

    url_assistente = f"{BASE}/assistente/"
    pagina_assistente = requisitar(abertura, urllib.request.Request(url_assistente))
    if pagina_assistente.status != 200:
        raise SystemExit(f"A tela do Assistente retornou HTTP {pagina_assistente.status}.")
    corpo_assistente = pagina_assistente.read().decode("utf-8")
    csrf_assistente = extrair_csrf(corpo_assistente)
    resposta = enviar_formulario(
        abertura,
        url_assistente,
        {
            "acao": "mensagem",
            "conteudo": "Explique em uma frase o que é um balancete.",
            "csrfmiddlewaretoken": csrf_assistente,
        },
    )
    if resposta.status != 200:
        raise SystemExit(f"A consulta ao Assistente retornou HTTP {resposta.status}.")
    corpo_resposta = resposta.read().decode("utf-8")
    mensagens_erro = (
        "Assistente indisponível.",
        "Não foi possível obter uma resposta agora.",
        "Não foi possível carregar o assistente agora.",
    )
    if any(mensagem in corpo_resposta for mensagem in mensagens_erro):
        raise SystemExit("O Assistente não respondeu à consulta de teste.")
    conversa = re.search(r'name="conversa_id" value="([1-9][0-9]*)"', corpo_resposta)
    if not conversa:
        raise SystemExit("A conversa temporária não foi identificada para limpeza.")

    csrf_limpeza = extrair_csrf(corpo_resposta)
    limpeza = enviar_formulario(
        abertura,
        url_assistente,
        {
            "acao": "excluir",
            "conversa_id": conversa.group(1),
            "csrfmiddlewaretoken": csrf_limpeza,
        },
    )
    if limpeza.status != 200:
        raise SystemExit("A conversa temporária não foi removida após o teste.")
    print("Smoke do Assistente aprovado: tela, consulta controlada e limpeza da conversa temporária.")


if __name__ == "__main__":
    principal()
