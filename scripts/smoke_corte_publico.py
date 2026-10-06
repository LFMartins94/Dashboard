"""Valida o fluxo público de sessão no domínio de produção sem registrar credenciais."""

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


class SemRedirecionamento(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, novo_url):
        return None


def requisitar(abertura, requisicao):
    try:
        return abertura.open(requisicao, timeout=30)
    except urllib.error.HTTPError as erro:
        return erro


def abrir_com_redirecionamentos(abertura, url: str):
    for _ in range(5):
        resposta = requisitar(abertura, urllib.request.Request(url))
        if resposta.status not in {301, 302, 303, 307, 308}:
            return resposta
        destino = resposta.headers.get("Location")
        if not destino:
            raise SystemExit("Redirecionamento sem destino durante o smoke test.")
        url = urllib.parse.urljoin(url, destino)
    raise SystemExit("Quantidade excessiva de redirecionamentos durante o smoke test.")


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executar", action="store_true", help="Confirma o teste público com sessão temporária.")
    argumentos = parser.parse_args()
    load_dotenv(RAIZ / ".env")
    usuario = os.getenv("APP_USUARIO", "")
    senha = os.getenv("APP_SENHA", "")
    if not usuario or not senha:
        raise SystemExit("APP_USUARIO e APP_SENHA são obrigatórios no arquivo .env.")
    if not argumentos.executar:
        print("Pré-requisitos aprovados. Execute novamente com --executar para iniciar o smoke test.")
        return

    cookies = http.cookiejar.CookieJar()
    abertura = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies),
        SemRedirecionamento(),
    )
    url_acesso = f"{BASE}/acesso/"
    pagina_acesso = requisitar(abertura, urllib.request.Request(url_acesso))
    corpo = pagina_acesso.read().decode("utf-8")
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', corpo)
    if pagina_acesso.status != 200 or not token:
        raise SystemExit("A tela de acesso não forneceu o token CSRF esperado.")

    dados = urllib.parse.urlencode(
        {"username": usuario, "password": senha, "csrfmiddlewaretoken": token.group(1)}
    ).encode()
    resposta_login = requisitar(
        abertura,
        urllib.request.Request(url_acesso, data=dados, headers={"Referer": url_acesso}),
    )
    if resposta_login.status != 302:
        raise SystemExit(f"O login não redirecionou como esperado: HTTP {resposta_login.status}.")

    pagina_protegida = abrir_com_redirecionamentos(abertura, f"{BASE}/")
    if pagina_protegida.status != 200:
        raise SystemExit(f"A rota protegida não abriu após login: HTTP {pagina_protegida.status}.")
    token_saida = re.search(
        r'name="csrfmiddlewaretoken" value="([^"]+)"',
        pagina_protegida.read().decode("utf-8"),
    )
    if not token_saida:
        raise SystemExit("A área protegida não forneceu o token CSRF de saída.")

    dados_saida = urllib.parse.urlencode({"csrfmiddlewaretoken": token_saida.group(1)}).encode()
    resposta_saida = requisitar(
        abertura,
        urllib.request.Request(f"{BASE}/sair/", data=dados_saida, headers={"Referer": f"{BASE}/"}),
    )
    if resposta_saida.status != 302:
        raise SystemExit(f"O logout não redirecionou como esperado: HTTP {resposta_saida.status}.")

    rota_apos_saida = requisitar(abertura, urllib.request.Request(f"{BASE}/"))
    if rota_apos_saida.status != 302:
        raise SystemExit("A rota protegida continuou acessível depois do logout.")
    print("Smoke público aprovado: saúde, login, rota protegida, logout e bloqueio pós-saída.")


if __name__ == "__main__":
    principal()
