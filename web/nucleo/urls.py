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
    path("entradas/", views.entradas, name="entradas"),
    path(
        "entradas/<uuid:identificador>/mapear/",
        views.mapear_entrada,
        name="mapear_entrada",
    ),
    path(
        "entradas/<uuid:identificador>/confirmar/",
        views.confirmar_entrada,
        name="confirmar_entrada",
    ),
    path(
        "entradas/<uuid:identificador>/descartar/",
        views.descartar_entrada,
        name="descartar_entrada",
    ),
    path(
        "conferencia/",
        views.conferencia,
        name="conferencia",
    ),
    path("conciliacao/", views.conciliacao, name="conciliacao"),
    path("auditoria/", views.auditoria, name="auditoria"),
    path("entregas/", views.modulo, {"secao": "entregas"}, name="entregas"),
    path(
        "assistente/",
        views.assistente,
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
