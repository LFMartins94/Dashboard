import os
import reflex as rx

if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()
from contaview.pages.login import login
from contaview.pages.painel import painel
from contaview.pages.lancamentos import lancamentos
from contaview.pages.importar import importar
from contaview.pages.conciliacao import conciliacao
from contaview.pages.auditoria import auditoria
from contaview.pages.relatorios import relatorios
from contaview.pages.assistente import assistente
from contaview.state.dados_state import DadosState

app = rx.App(
    stylesheets=["styles.css"],
)

app.add_page(login, route="/")
app.add_page(painel, route="/painel", on_load=DadosState.carregar_empresas)
app.add_page(lancamentos, route="/lancamentos", on_load=DadosState.carregar_empresas)
app.add_page(importar, route="/importar", on_load=DadosState.carregar_empresas)
app.add_page(conciliacao, route="/conciliacao", on_load=DadosState.carregar_empresas)
app.add_page(auditoria, route="/auditoria", on_load=DadosState.carregar_empresas)
app.add_page(relatorios, route="/relatorios", on_load=DadosState.carregar_empresas)
app.add_page(assistente, route="/assistente")
