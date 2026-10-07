"""Formulários validados no servidor."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import (
    CategoriaDre,
    EstadoOperacional,
    ModoPerfilOrigemEntrada,
    RegraCompetenciaOrigem,
)


class SeletorArquivosMultiplos(forms.ClearableFileInput):
    allow_multiple_selected = True


class CampoArquivosMultiplos(forms.FileField):
    def clean(self, data, initial=None):
        limpar = super().clean
        if isinstance(data, (list, tuple)):
            if not data:
                raise forms.ValidationError("Selecione ao menos um arquivo.")
            return [limpar(item, initial) for item in data]
        return [limpar(data, initial)]


class FormularioUploadEntrada(forms.Form):
    arquivos = CampoArquivosMultiplos(
        label="Planilhas",
        widget=SeletorArquivosMultiplos(
            attrs={
                "accept": ".ofx,.xlsx,.xls,.csv",
                "multiple": True,
            }
        ),
    )


TIPOS_DOCUMENTO = (
    ("extrato", "Extrato bancário"),
    ("folha", "Folha de pagamento"),
    ("notas", "Notas fiscais"),
    ("lancamentos", "Lançamentos contábeis"),
    ("outro", "Outro documento"),
)


class FormularioConfigurarEntrada(forms.Form):
    aba = forms.ChoiceField(label="Aba")
    linha_cabecalho = forms.IntegerField(
        label="Linha do cabeçalho",
        min_value=0,
        help_text="Use 0 quando o arquivo não tiver cabeçalho.",
    )
    tipo_documento = forms.ChoiceField(
        label="Tipo de documento", choices=TIPOS_DOCUMENTO
    )

    def __init__(self, *args, abas: list[dict] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["aba"].choices = [
            (aba["nome"], aba["nome"]) for aba in (abas or [])
        ]


class FormularioMapeamentoEntrada(forms.Form):
    CAMPOS = (
        ("data", "Data"),
        ("valor", "Valor"),
        ("descricao", "Descrição"),
        ("tipo", "Tipo (C/D)"),
        ("conta_contabil", "Conta contábil"),
        ("filial", "Filial"),
    )

    aba = forms.CharField(widget=forms.HiddenInput())
    linha_cabecalho = forms.IntegerField(min_value=0, widget=forms.HiddenInput())
    tipo_documento = forms.ChoiceField(
        choices=TIPOS_DOCUMENTO, widget=forms.HiddenInput()
    )

    def __init__(
        self, *args, cabecalhos: list[str] | None = None,
        sugestao: dict[str, str] | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        escolhas = [("", "Não mapear")] + [
            (cabecalho, cabecalho) for cabecalho in (cabecalhos or [])
        ]
        for campo, rotulo in self.CAMPOS:
            self.fields[campo] = forms.ChoiceField(
                label=rotulo,
                choices=escolhas,
                required=False,
                initial=(sugestao or {}).get(campo, ""),
            )

    def clean(self):
        dados = super().clean()
        escolhidas = [
            dados.get(campo) for campo, _ in self.CAMPOS if dados.get(campo)
        ]
        if len(escolhidas) != len(set(escolhidas)):
            raise forms.ValidationError(
                "Cada coluna original pode alimentar somente um campo."
            )
        return dados


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


class FormularioEstadoItem(forms.Form):
    item_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput())
    estado = forms.ChoiceField(
        label="Estado",
        choices=EstadoOperacional.choices,
    )


class FormularioAlternarCompetencia(forms.Form):
    competencia_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput())


class FormularioEditarLinhaConferencia(forms.Form):
    linha_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput())
    data = forms.CharField(label="Data", required=False)
    descricao = forms.CharField(label="Descrição", required=False)
    valor = forms.CharField(label="Valor", required=False)
    tipo = forms.CharField(label="Tipo", required=False, max_length=1)
    conta_contabil = forms.CharField(label="Conta contábil", required=False)
    filial = forms.CharField(label="Filial", required=False)


class FormularioEdicaoEmLote(forms.Form):
    linhas = forms.CharField(widget=forms.HiddenInput())
    campo = forms.ChoiceField(choices=(
        ("data", "Data"), ("descricao", "Descrição"), ("valor", "Valor"),
        ("tipo", "Tipo"), ("conta_contabil", "Conta contábil"), ("filial", "Filial"),
    ))
    valor = forms.CharField(label="Novo valor")


class FormularioLote(forms.Form):
    lote_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput())


class FormularioMensagemAssistente(forms.Form):
    conversa_id = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput())
    conteudo = forms.CharField(
        label="Mensagem",
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Escreva sua dúvida contábil..."}),
    )


class FormularioConversaAssistente(forms.Form):
    conversa_id = forms.IntegerField(min_value=1, widget=forms.HiddenInput())


class FormularioExecutarConciliacao(forms.Form):
    lote_extrato_id = forms.IntegerField(min_value=1)
    lote_referencia_id = forms.IntegerField(min_value=0)


class FormularioDecisaoConciliacao(FormularioExecutarConciliacao):
    linha_extrato_id = forms.IntegerField(min_value=1)
    linha_referencia_id = forms.IntegerField(min_value=1)
    decisao = forms.ChoiceField(choices=(
        ("confirmada", "Confirmar"),
        ("rejeitada", "Rejeitar"),
        ("manual", "Ajuste manual"),
    ))
    justificativa = forms.CharField(max_length=500, required=False)


class FormularioResolucaoAuditoria(forms.Form):
    ocorrencia_id = forms.IntegerField(min_value=1)
    resolvida = forms.BooleanField(required=False)
    justificativa = forms.CharField(max_length=500, required=False)


class FormularioPerfilExportacao(forms.Form):
    nome = forms.CharField(label="Nome do perfil", max_length=80)
    campos = forms.CharField(
        label="Campos", max_length=300,
        help_text="Separe os campos por vírgula. Exemplo: data, conta_contabil, valor, tipo, historico.",
    )


class FormularioClassificacaoDre(forms.Form):
    prefixo_conta = forms.CharField(label="Prefixo da conta", max_length=50)
    grupo = forms.CharField(label="Grupo na DRE", max_length=120)
    categoria = forms.ChoiceField(label="Categoria", choices=CategoriaDre.choices)
    ordem = forms.IntegerField(label="Ordem", min_value=1, max_value=9999, initial=100)


class FormularioGerarRelatorio(forms.Form):
    tipo_relatorio = forms.ChoiceField(choices=(
        ("balancete", "Balancete"),
        ("dre", "DRE"),
        ("lancamentos", "Lançamentos"),
    ))
    formato = forms.ChoiceField(choices=(("xlsx", "Excel"), ("pdf", "PDF")))
    perfil_id = forms.IntegerField(required=False, min_value=1)


class FormularioModeloDocumentoEsperado(forms.Form):
    nome = forms.CharField(label="Documento", max_length=160)
    tipo_documento = forms.ChoiceField(label="Tipo", choices=TIPOS_DOCUMENTO)
    dia_limite = forms.IntegerField(label="Dia limite", required=False, min_value=1, max_value=31)
    obrigatorio = forms.BooleanField(label="Obrigatório", required=False, initial=True)


class FormularioPerfilOrigemEntrada(forms.Form):
    nome = forms.CharField(label="Nome do perfil", max_length=80)
    prefixo_nome = forms.CharField(label="Prefixo do arquivo", max_length=80)
    pasta_referencia = forms.CharField(label="Pasta de referência", max_length=255, required=False)
    tipo_documento = forms.ChoiceField(label="Tipo sugerido", choices=TIPOS_DOCUMENTO)
    modo = forms.ChoiceField(label="Modo da origem", choices=ModoPerfilOrigemEntrada.choices)
    regra_competencia = forms.ChoiceField(
        label="Regra de competência", choices=RegraCompetenciaOrigem.choices
    )


class FormularioTarefaAutomacao(forms.Form):
    tarefa_id = forms.IntegerField(min_value=1)
