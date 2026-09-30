from django.urls import path

from . import views

app_name = "nucleo"

urlpatterns = [
    path("", views.trabalho, name="trabalho"),
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
