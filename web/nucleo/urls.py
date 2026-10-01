from django.urls import path

from . import views

app_name = "nucleo"

urlpatterns = [
    path("acesso/", views.acesso, name="login"),
    path("sair/", views.sair, name="logout"),
    path("contexto/", views.selecionar_contexto, name="selecionar_contexto"),
    path("", views.trabalho, name="trabalho"),
    path(
        "trabalho/iniciar/",
        views.iniciar_contexto_trabalho,
        name="iniciar_trabalho",
    ),
    path(
        "trabalho/item/atualizar/",
        views.atualizar_item_trabalho,
        name="atualizar_item_trabalho",
    ),
    path(
        "trabalho/alternar/",
        views.alternar_competencia_trabalho,
        name="alternar_competencia_trabalho",
    ),
    path("entradas/", views.modulo, {"secao": "entradas"}, name="entradas"),
    path(
        "conferencia/",
        views.modulo,
        {"secao": "conferencia"},
        name="conferencia",
    ),
    path("entregas/", views.modulo, {"secao": "entregas"}, name="entregas"),
    path(
        "assistente/",
        views.modulo,
        {"secao": "assistente"},
        name="assistente",
    ),
    path("saude/", views.saude, name="saude"),
    path("saude/aplicacao/", views.saude_aplicacao, name="saude_aplicacao"),
    path(
        "fragmentos/estado-aplicacao/",
        views.estado_aplicacao,
        name="estado_aplicacao",
    ),
]
