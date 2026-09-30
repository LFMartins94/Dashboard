"""Rotas principais da aplicação web."""

from django.urls import include, path

urlpatterns = [
    path("", include("nucleo.urls")),
]

handler400 = "nucleo.views.erro_400"
handler403 = "nucleo.views.erro_403"
handler404 = "nucleo.views.erro_404"
handler500 = "nucleo.views.erro_500"
