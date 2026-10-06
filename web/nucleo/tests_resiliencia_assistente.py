"""Comportamento da tela do Assistente quando a camada legada falha."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from . import views
from .servicos import assistente
from .servicos.contexto import ContextoTrabalho


class AssistenteViewTest(TestCase):
    def test_indisponibilidade_da_camada_legada_mantem_tela_acessivel(self):
        usuario = get_user_model().objects.create_user(
            "assistente-view", password="senha-segura"
        )
        requisicao = RequestFactory().get("/assistente/")
        SessionMiddleware(lambda _requisicao: None).process_request(requisicao)
        requisicao.session.save()
        requisicao.user = usuario
        setattr(requisicao, "_messages", FallbackStorage(requisicao))
        contexto = ContextoTrabalho(7, "Empresa", "2026-05")

        with patch.object(views, "exigir_contexto", return_value=contexto), patch.object(
            assistente, "listar", side_effect=RuntimeError("falha temporária")
        ):
            resposta = views.assistente(requisicao)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Como posso ajudar?")
