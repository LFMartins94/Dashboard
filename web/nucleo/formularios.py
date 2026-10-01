"""Formulários validados no servidor."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class FormularioLogin(AuthenticationForm):
    error_messages = {
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Usuário ou senha incorretos.",
    }
    username = forms.CharField(
        label="Usuário",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": True,
                "placeholder": "Digite seu usuário",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "Digite sua senha",
            }
        ),
    )

    def __init__(self, *args, bloqueado: bool = False, **kwargs):
        self.bloqueado = bloqueado
        super().__init__(*args, **kwargs)

    def clean(self):
        if self.bloqueado:
            raise forms.ValidationError(
                "Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente.",
                code="bloqueado",
            )
        return super().clean()


class FormularioContexto(forms.Form):
    empresa = forms.ChoiceField(label="Empresa")
    competencia = forms.CharField(
        label="Competência",
        max_length=7,
        widget=forms.TextInput(
            attrs={
                "type": "month",
                "inputmode": "numeric",
                "pattern": "[0-9]{4}-(0[1-9]|1[0-2])",
            }
        ),
    )

    def __init__(self, *args, empresas: list[dict] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["empresa"].choices = [
            (str(empresa["id"]), empresa["nome"]) for empresa in (empresas or [])
        ]

    def clean_empresa(self) -> int:
        try:
            return int(self.cleaned_data["empresa"])
        except (TypeError, ValueError) as erro:
            raise forms.ValidationError("Selecione uma empresa válida.") from erro

    def clean_competencia(self) -> str:
        competencia = self.cleaned_data["competencia"]
        if (
            len(competencia) != 7
            or competencia[4] != "-"
            or not competencia[:4].isdigit()
            or not competencia[5:].isdigit()
            or not 1 <= int(competencia[5:]) <= 12
        ):
            raise forms.ValidationError("Informe uma competência válida.")
        return competencia
