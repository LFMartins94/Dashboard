"""Casos de uso determinísticos para regras de classificação contábil."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ..models import (
    AcaoHistoricoRegraClassificacao,
    HistoricoRegraClassificacao,
    RegraClassificacaoContabil,
    SituacaoRegraClassificacao,
)
from .contexto import ContextoTrabalho, obter_empresa_ativa


class ErroClassificacao(ValueError):
    pass


CAMPOS_CRITERIO = {
    "descricao_contem",
    "favorecido_contem",
    "documento_contem",
    "tipo_operacao",
    "tipo",
    "valor_minimo",
    "valor_maximo",
}
CAMPOS_TEXTO = {
    "descricao_contem",
    "favorecido_contem",
    "documento_contem",
    "tipo_operacao",
}
ROTULOS_CRITERIO = {
    "descricao_contem": "Descrição contém",
    "favorecido_contem": "Favorecido contém",
    "documento_contem": "Documento contém",
    "tipo_operacao": "Tipo de operação",
    "tipo": "Tipo de origem",
    "valor_minimo": "Valor mínimo",
    "valor_maximo": "Valor máximo",
}


CAMPOS_FONTE = {
    "descricao_contem": ("descricao", "historico", "memo", "narrativa"),
    "favorecido_contem": ("favorecido", "beneficiario", "nome", "fornecedor"),
    "documento_contem": ("documento", "numero_documento", "referencia"),
    "tipo_operacao": ("tipo_operacao", "operacao", "transacao"),
}


@dataclass(frozen=True)
class ResultadoClassificacao:
    situacao: str
    origem: str
    regra_id: int | None = None
    regra_nome: str = ""
    conta_contabil: str = ""
    historico: str = ""
    centro_custo: str = ""
    tipo: str = ""
    motivo: str = ""
    candidatos: tuple[int, ...] = ()


def _normalizar_texto(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere)).casefold().strip()


def _decimal(valor: object, campo: str) -> Decimal:
    try:
        if isinstance(valor, Decimal):
            return valor
        if isinstance(valor, (int, float)):
            return Decimal(str(valor))
        texto = str(valor).strip()
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        return Decimal(texto)
    except (InvalidOperation, AttributeError):
        raise ErroClassificacao(f"{campo} deve conter um valor monetário válido.") from None


def _validar_contexto(contexto: ContextoTrabalho) -> None:
    if not obter_empresa_ativa(contexto.empresa_id):
        raise ErroClassificacao("A empresa selecionada não está ativa.")


def _limpar_criterios(criterios: dict[str, object]) -> dict[str, object]:
    desconhecidos = set(criterios) - CAMPOS_CRITERIO
    if desconhecidos:
        raise ErroClassificacao("A regra contém critérios desconhecidos.")
    limpos: dict[str, object] = {}
    for campo in CAMPOS_TEXTO:
        valor = str(criterios.get(campo, "")).strip()
        if valor:
            if len(_normalizar_texto(valor)) < 3:
                raise ErroClassificacao(f"O critério '{campo}' precisa ter ao menos três caracteres.")
            limpos[campo] = valor
    tipo = str(criterios.get("tipo", "")).strip().upper()
    if tipo:
        if tipo not in {"C", "D"}:
            raise ErroClassificacao("O tipo da operação deve ser C ou D.")
        limpos["tipo"] = tipo
    for campo in ("valor_minimo", "valor_maximo"):
        valor = criterios.get(campo)
        if valor not in (None, ""):
            limpos[campo] = format(_decimal(valor, campo), "f")
    if "valor_minimo" in limpos and "valor_maximo" in limpos:
        if Decimal(limpos["valor_minimo"]) > Decimal(limpos["valor_maximo"]):
            raise ErroClassificacao("O valor mínimo não pode superar o valor máximo.")
    fortes = set(limpos) & CAMPOS_TEXTO
    if not fortes:
        raise ErroClassificacao("Informe descrição, favorecido, documento ou tipo de operação para limitar a regra.")
    if _normalizar_texto(limpos.get("descricao_contem")) == "pix" and len(fortes) == 1:
        raise ErroClassificacao("Uma regra baseada apenas em PIX é ampla demais. Informe favorecido, documento ou outro critério.")
    return limpos


def _instantaneo(regra: RegraClassificacaoContabil) -> dict:
    return {
        "nome": regra.nome,
        "conta_bancaria": regra.conta_bancaria,
        "criterios": regra.criterios,
        "criterios_exibicao": [
            {"nome": ROTULOS_CRITERIO.get(campo, campo), "valor": valor}
            for campo, valor in regra.criterios.items()
        ],
        "prioridade": regra.prioridade,
        "vigente_de": regra.vigente_de.isoformat() if regra.vigente_de else "",
        "vigente_ate": regra.vigente_ate.isoformat() if regra.vigente_ate else "",
        "conta_contabil_sugerida": regra.conta_contabil_sugerida,
        "historico_sugerido": regra.historico_sugerido,
        "centro_custo_sugerido": regra.centro_custo_sugerido,
        "tipo_sugerido": regra.tipo_sugerido,
        "situacao": regra.situacao,
    }


def _registrar_historico(regra, acao: str, anterior: dict, usuario) -> None:
    HistoricoRegraClassificacao.objects.create(
        regra=regra,
        acao=acao,
        dados_anteriores=anterior,
        dados_posteriores=_instantaneo(regra),
        responsavel=usuario,
    )


def _dados_regra(regra: RegraClassificacaoContabil) -> dict:
    taxa_erro = Decimal("0")
    if regra.amostras_conferidas:
        taxa_erro = (Decimal(regra.erros_amostragem) * Decimal("100")) / Decimal(regra.amostras_conferidas)
    return {
        "id": regra.id,
        "nome": regra.nome,
        "conta_bancaria": regra.conta_bancaria,
        "criterios": regra.criterios,
        "criterios_exibicao": [
            {"nome": ROTULOS_CRITERIO.get(campo, campo), "valor": valor}
            for campo, valor in regra.criterios.items()
        ],
        "prioridade": regra.prioridade,
        "vigente_de": regra.vigente_de,
        "vigente_ate": regra.vigente_ate,
        "conta_contabil_sugerida": regra.conta_contabil_sugerida,
        "historico_sugerido": regra.historico_sugerido,
        "centro_custo_sugerido": regra.centro_custo_sugerido,
        "tipo_sugerido": regra.tipo_sugerido,
        "situacao": regra.situacao,
        "situacao_exibicao": regra.get_situacao_display(),
        "vezes_utilizada": regra.vezes_utilizada,
        "amostras_conferidas": regra.amostras_conferidas,
        "erros_amostragem": regra.erros_amostragem,
        "taxa_erro": taxa_erro.quantize(Decimal("0.01")),
        "ultimo_uso_em": regra.ultimo_uso_em,
    }


@transaction.atomic
def salvar_regra(
    contexto: ContextoTrabalho,
    usuario,
    *,
    regra_id: int | None = None,
    nome: str,
    conta_bancaria: str = "",
    criterios: dict[str, object],
    prioridade: int = 100,
    vigente_de: date | None = None,
    vigente_ate: date | None = None,
    conta_contabil_sugerida: str = "",
    historico_sugerido: str = "",
    centro_custo_sugerido: str = "",
    tipo_sugerido: str = "",
) -> RegraClassificacaoContabil:
    _validar_contexto(contexto)
    nome_limpo = nome.strip()
    if not nome_limpo:
        raise ErroClassificacao("Informe um nome para a regra.")
    if prioridade < 1:
        raise ErroClassificacao("A prioridade deve ser maior que zero.")
    if vigente_de and vigente_ate and vigente_ate < vigente_de:
        raise ErroClassificacao("A data final de vigência não pode ser anterior à inicial.")
    criterios_limpos = _limpar_criterios(criterios)
    tipo_limpo = tipo_sugerido.strip().upper()
    if tipo_limpo and tipo_limpo not in {"C", "D"}:
        raise ErroClassificacao("O tipo sugerido deve ser C ou D.")
    destinos = [conta_contabil_sugerida, historico_sugerido, centro_custo_sugerido, tipo_limpo]
    if not any(str(valor).strip() for valor in destinos):
        raise ErroClassificacao("Informe ao menos uma sugestão de conta, histórico, centro de custo ou tipo.")

    regras_com_mesmo_nome = RegraClassificacaoContabil.objects.filter(
        empresa_id=contexto.empresa_id,
        nome=nome_limpo,
    )
    if regra_id:
        regra = RegraClassificacaoContabil.objects.select_for_update().filter(
            pk=regra_id,
            empresa_id=contexto.empresa_id,
        ).first()
        if regra is None:
            raise ErroClassificacao("A regra não pertence à empresa selecionada.")
        if regras_com_mesmo_nome.exclude(pk=regra.pk).exists():
            raise ErroClassificacao("Já existe uma regra com este nome para a empresa.")
        anterior = _instantaneo(regra)
    elif regras_com_mesmo_nome.exists():
        raise ErroClassificacao("Já existe uma regra com este nome para a empresa.")
    else:
        regra = RegraClassificacaoContabil(empresa_id=contexto.empresa_id, criada_por=usuario)
        anterior = {}

    duplicada = RegraClassificacaoContabil.objects.filter(
        empresa_id=contexto.empresa_id,
        criterios=criterios_limpos,
        conta_bancaria=conta_bancaria.strip(),
        prioridade=prioridade,
        situacao=SituacaoRegraClassificacao.ATIVA,
    )
    if regra.pk:
        duplicada = duplicada.exclude(pk=regra.pk)
    if duplicada.exists():
        raise ErroClassificacao("Já existe uma regra ativa com os mesmos critérios e prioridade.")

    regra.nome = nome_limpo
    regra.conta_bancaria = conta_bancaria.strip()
    regra.criterios = criterios_limpos
    regra.prioridade = prioridade
    regra.vigente_de = vigente_de
    regra.vigente_ate = vigente_ate
    regra.conta_contabil_sugerida = conta_contabil_sugerida.strip()
    regra.historico_sugerido = historico_sugerido.strip()
    regra.centro_custo_sugerido = centro_custo_sugerido.strip()
    regra.tipo_sugerido = tipo_limpo
    if not regra.pk:
        regra.situacao = SituacaoRegraClassificacao.ATIVA
    regra.atualizada_por = usuario
    regra.save()
    _registrar_historico(
        regra,
        AcaoHistoricoRegraClassificacao.ALTERADA if anterior else AcaoHistoricoRegraClassificacao.CRIADA,
        anterior,
        usuario,
    )
    return regra


@transaction.atomic
def definir_situacao(contexto: ContextoTrabalho, usuario, regra_id: int, situacao: str) -> RegraClassificacaoContabil:
    _validar_contexto(contexto)
    if situacao not in {
        SituacaoRegraClassificacao.ATIVA,
        SituacaoRegraClassificacao.EM_REVISAO,
        SituacaoRegraClassificacao.DESATIVADA,
    }:
        raise ErroClassificacao("A situação solicitada é inválida.")
    regra = RegraClassificacaoContabil.objects.select_for_update().filter(
        pk=regra_id, empresa_id=contexto.empresa_id
    ).first()
    if regra is None:
        raise ErroClassificacao("A regra não pertence à empresa selecionada.")
    anterior = _instantaneo(regra)
    regra.situacao = situacao
    regra.atualizada_por = usuario
    regra.save(update_fields=["situacao", "atualizada_por", "atualizado_em"])
    _registrar_historico(
        regra,
        (
            AcaoHistoricoRegraClassificacao.REATIVADA
            if situacao == SituacaoRegraClassificacao.ATIVA
            else (
                AcaoHistoricoRegraClassificacao.DESATIVADA
                if situacao == SituacaoRegraClassificacao.DESATIVADA
                else AcaoHistoricoRegraClassificacao.ALTERADA
            )
        ),
        anterior,
        usuario,
    )
    return regra


def listar_regras(contexto: ContextoTrabalho) -> list[dict]:
    _validar_contexto(contexto)
    regras = RegraClassificacaoContabil.objects.filter(empresa_id=contexto.empresa_id).order_by(
        "situacao", "prioridade", "nome", "id"
    )
    return [_dados_regra(regra) for regra in regras]


def obter_regra(contexto: ContextoTrabalho, regra_id: int) -> dict:
    _validar_contexto(contexto)
    regra = RegraClassificacaoContabil.objects.filter(
        pk=regra_id, empresa_id=contexto.empresa_id
    ).first()
    if regra is None:
        raise ErroClassificacao("A regra não pertence à empresa selecionada.")
    return _dados_regra(regra)


def _valor_fonte(linha: dict, aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        valor = linha.get(alias)
        if valor not in (None, ""):
            return str(valor)
    dados_brutos = linha.get("dados_brutos") or {}
    if isinstance(dados_brutos, dict):
        normalizados = {_normalizar_texto(chave): valor for chave, valor in dados_brutos.items()}
        for alias in aliases:
            valor = normalizados.get(_normalizar_texto(alias))
            if valor not in (None, ""):
                return str(valor)
    return ""


def _data_linha(linha: dict) -> date | None:
    valor = linha.get("data")
    if isinstance(valor, date):
        return valor
    if not valor:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return date.fromisoformat(str(valor)) if formato == "%Y-%m-%d" else datetime.strptime(str(valor), formato).date()
        except ValueError:
            continue
    return None


def _regra_corresponde(regra: RegraClassificacaoContabil, linha: dict, conta_bancaria: str, referencia: date) -> bool:
    if regra.conta_bancaria and _normalizar_texto(regra.conta_bancaria) != _normalizar_texto(conta_bancaria):
        return False
    if regra.vigente_de and referencia < regra.vigente_de:
        return False
    if regra.vigente_ate and referencia > regra.vigente_ate:
        return False
    criterios = regra.criterios
    for campo in CAMPOS_TEXTO:
        termo = criterios.get(campo)
        if termo and _normalizar_texto(termo) not in _normalizar_texto(_valor_fonte(linha, CAMPOS_FONTE[campo])):
            return False
    if criterios.get("tipo") and _normalizar_texto(linha.get("tipo")) != _normalizar_texto(criterios["tipo"]):
        return False
    valor = linha.get("valor")
    if ("valor_minimo" in criterios or "valor_maximo" in criterios) and valor in (None, ""):
        return False
    if valor not in (None, ""):
        numero = _decimal(valor, "valor da linha")
        if "valor_minimo" in criterios and numero < Decimal(criterios["valor_minimo"]):
            return False
        if "valor_maximo" in criterios and numero > Decimal(criterios["valor_maximo"]):
            return False
    return True


def sugerir_para_linha(contexto: ContextoTrabalho, linha: dict, conta_bancaria: str = "", referencia: date | None = None) -> ResultadoClassificacao:
    _validar_contexto(contexto)
    data_referencia = referencia or _data_linha(linha) or timezone.localdate()
    regras = RegraClassificacaoContabil.objects.filter(
        empresa_id=contexto.empresa_id,
        situacao=SituacaoRegraClassificacao.ATIVA,
    ).order_by("prioridade", "id")
    candidatas = [regra for regra in regras if _regra_corresponde(regra, linha, conta_bancaria, data_referencia)]
    if not candidatas:
        return ResultadoClassificacao("sem_regra", "nenhuma", motivo="Nenhuma regra confirmada corresponde à linha.")
    prioridade = candidatas[0].prioridade
    melhores = [regra for regra in candidatas if regra.prioridade == prioridade]
    if len(melhores) > 1:
        return ResultadoClassificacao(
            "conflito", "conflito", motivo="Mais de uma regra ativa corresponde com a mesma prioridade.",
            candidatos=tuple(regra.id for regra in melhores),
        )
    regra = melhores[0]
    return ResultadoClassificacao(
        "sugerida", "regra_confirmada", regra_id=regra.id, regra_nome=regra.nome,
        conta_contabil=regra.conta_contabil_sugerida,
        historico=regra.historico_sugerido,
        centro_custo=regra.centro_custo_sugerido,
        tipo=regra.tipo_sugerido,
        motivo="Sugestão baseada em regra confirmada; revise antes de aplicar.",
    )


@transaction.atomic
def registrar_amostra(contexto: ContextoTrabalho, regra_id: int, houve_erro: bool) -> None:
    _validar_contexto(contexto)
    regra = RegraClassificacaoContabil.objects.select_for_update().filter(
        pk=regra_id, empresa_id=contexto.empresa_id
    ).first()
    if regra is None:
        raise ErroClassificacao("A regra não pertence à empresa selecionada.")
    RegraClassificacaoContabil.objects.filter(pk=regra.pk).update(
        amostras_conferidas=F("amostras_conferidas") + 1,
        erros_amostragem=F("erros_amostragem") + (1 if houve_erro else 0),
        vezes_utilizada=F("vezes_utilizada") + 1,
        ultimo_uso_em=timezone.now(),
    )
