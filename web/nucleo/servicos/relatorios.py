"""Casos de uso determinísticos para entregas e relatórios."""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
from django.db import transaction

from contaview.logic import database
from contaview.logic.relatorios import (
    VERSAO_RELATORIOS,
    calcular_balancete_com_saldos,
    calcular_dre_classificada,
    exportar_pdf_relatorio,
    exportar_planilha_relatorio,
)

from ..models import ClassificacaoDre, GeracaoRelatorio, PerfilExportacao
from .contexto import ContextoTrabalho, obter_empresa_ativa


CAMPOS_EXPORTAVEIS = {
    "data": "Data",
    "conta_contabil": "Conta contábil",
    "valor": "Valor",
    "tipo": "Tipo",
    "historico": "Histórico",
    "filial": "Filial",
    "periodo": "Período",
}
PERFIL_PADRAO = {
    "id": 0,
    "nome": "Contábil genérico",
    "campos": list(CAMPOS_EXPORTAVEIS),
    "padrao": True,
}


class ErroRelatorio(ValueError):
    pass


def _validar_contexto(contexto: ContextoTrabalho) -> None:
    if not obter_empresa_ativa(contexto.empresa_id):
        raise ErroRelatorio("A empresa selecionada não está ativa.")


def _formatar_valor(valor) -> str:
    numero = Decimal(str(valor or 0)).quantize(Decimal("0.01"))
    return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar_quadro(quadro: pd.DataFrame) -> pd.DataFrame:
    resultado = quadro.copy()
    for coluna in ("Débitos", "Créditos", "Saldo anterior", "Saldo final", "Valor"):
        if coluna in resultado.columns:
            resultado[coluna] = resultado[coluna].map(_formatar_valor)
    return resultado


def listar_perfis(contexto: ContextoTrabalho) -> list[dict]:
    _validar_contexto(contexto)
    personalizados = PerfilExportacao.objects.filter(
        empresa_id=contexto.empresa_id
    ).order_by("nome", "id")
    return [PERFIL_PADRAO] + [
        {"id": perfil.id, "nome": perfil.nome, "campos": perfil.campos, "padrao": False}
        for perfil in personalizados
    ]


@transaction.atomic
def criar_perfil(contexto: ContextoTrabalho, usuario, nome: str, campos: str) -> PerfilExportacao:
    _validar_contexto(contexto)
    escolhidos = []
    for campo in (item.strip() for item in campos.split(",")):
        if campo not in CAMPOS_EXPORTAVEIS:
            raise ErroRelatorio(f"O campo '{campo}' não pode ser exportado.")
        if campo not in escolhidos:
            escolhidos.append(campo)
    if not escolhidos:
        raise ErroRelatorio("Selecione ao menos um campo permitido para o perfil.")
    return PerfilExportacao.objects.create(
        empresa_id=contexto.empresa_id,
        nome=nome.strip(), campos=escolhidos, criado_por=usuario,
    )


@transaction.atomic
def salvar_classificacao(
    contexto: ContextoTrabalho, prefixo_conta: str, grupo: str,
    categoria: str, ordem: int,
) -> ClassificacaoDre:
    _validar_contexto(contexto)
    prefixo = prefixo_conta.strip()
    if not prefixo:
        raise ErroRelatorio("Informe o prefixo da conta para a classificação da DRE.")
    classificacao, _ = ClassificacaoDre.objects.update_or_create(
        empresa_id=contexto.empresa_id, prefixo_conta=prefixo,
        defaults={"grupo": grupo.strip(), "categoria": categoria, "ordem": ordem},
    )
    return classificacao


def _lancamentos_contexto(contexto: ContextoTrabalho) -> tuple[pd.DataFrame, pd.DataFrame]:
    todos = database.carregar_lancamentos(contexto.empresa_id)
    if todos.empty:
        return todos, todos
    atual = todos[todos["periodo"] == contexto.competencia].copy()
    anteriores = todos[todos["periodo"].fillna("") < contexto.competencia].copy()
    return atual, anteriores


def _perfil_contexto(contexto: ContextoTrabalho, perfil_id: int | None) -> dict:
    if not perfil_id:
        return PERFIL_PADRAO
    perfil = PerfilExportacao.objects.filter(
        id=perfil_id, empresa_id=contexto.empresa_id
    ).first()
    if perfil is None:
        raise ErroRelatorio("O perfil de exportação não pertence à empresa selecionada.")
    return {"id": perfil.id, "nome": perfil.nome, "campos": perfil.campos, "padrao": False}


def montar_relatorio(
    contexto: ContextoTrabalho, tipo_relatorio: str, perfil_id: int | None = None,
) -> tuple[pd.DataFrame, str, dict]:
    _validar_contexto(contexto)
    atual, anteriores = _lancamentos_contexto(contexto)
    if tipo_relatorio == "balancete":
        quadro = calcular_balancete_com_saldos(atual, anteriores)
        titulo = "Balancete"
        parametros = {"saldo_assinado": "débito positivo; crédito negativo"}
    elif tipo_relatorio == "dre":
        classificacoes = list(ClassificacaoDre.objects.filter(
            empresa_id=contexto.empresa_id
        ).values("prefixo_conta", "grupo", "categoria", "ordem"))
        quadro, resultado = calcular_dre_classificada(atual, classificacoes)
        quadro = pd.concat([quadro, pd.DataFrame([{
            "Grupo": "Resultado do período", "Categoria": "Subtotal", "Valor": resultado,
        }])], ignore_index=True)
        titulo = "DRE"
        parametros = {"classificacoes": classificacoes, "contas_nao_classificadas_visiveis": True}
    elif tipo_relatorio == "lancamentos":
        perfil = _perfil_contexto(contexto, perfil_id)
        campos = [campo for campo in perfil["campos"] if campo in atual.columns]
        quadro = atual[campos].copy() if campos else pd.DataFrame(columns=list(CAMPOS_EXPORTAVEIS.values()))
        quadro = quadro.rename(columns=CAMPOS_EXPORTAVEIS)
        titulo = f"Lançamentos — {perfil['nome']}"
        parametros = {"perfil_id": perfil["id"], "perfil": perfil["nome"], "campos": perfil["campos"]}
    else:
        raise ErroRelatorio("Tipo de relatório inválido.")
    return _formatar_quadro(quadro), titulo, parametros


@transaction.atomic
def gerar(
    contexto: ContextoTrabalho, usuario, tipo_relatorio: str,
    formato: str, perfil_id: int | None = None,
) -> tuple[bytes, str, str]:
    if formato not in {"xlsx", "pdf"}:
        raise ErroRelatorio("Formato de relatório inválido.")
    quadro, titulo, parametros = montar_relatorio(contexto, tipo_relatorio, perfil_id)
    parametros.update({"tipo": tipo_relatorio, "formato": formato, "competencia": contexto.competencia})
    if formato == "xlsx":
        conteudo = exportar_planilha_relatorio(quadro, titulo, tipo_relatorio.title())
        tipo_conteudo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        nota = "Dados calculados exclusivamente a partir de lançamentos aprovados no contexto selecionado."
        conteudo = exportar_pdf_relatorio(quadro, titulo, contexto.empresa_nome, contexto.competencia, nota)
        tipo_conteudo = "application/pdf"
    GeracaoRelatorio.objects.create(
        empresa_id=contexto.empresa_id, competencia=contexto.competencia,
        tipo_relatorio=tipo_relatorio, formato=formato, parametros=parametros,
        versao_calculo=VERSAO_RELATORIOS, gerado_por=usuario,
    )
    nome = f"{tipo_relatorio}_{contexto.competencia}.{formato}"
    return conteudo, nome, tipo_conteudo


def carregar(contexto: ContextoTrabalho) -> dict:
    _validar_contexto(contexto)
    classificacoes = ClassificacaoDre.objects.filter(empresa_id=contexto.empresa_id).order_by("ordem", "prefixo_conta")
    geracoes = GeracaoRelatorio.objects.filter(
        empresa_id=contexto.empresa_id, competencia=contexto.competencia
    ).order_by("-gerado_em")[:12]
    return {
        "perfis": listar_perfis(contexto),
        "campos_exportaveis": CAMPOS_EXPORTAVEIS,
        "classificacoes": classificacoes,
        "geracoes": geracoes,
    }
