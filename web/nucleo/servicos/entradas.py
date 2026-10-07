"""Recebimento seguro, inspeção e confirmação de planilhas."""

from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

from django.db import connection, transaction
from django.db.models import F
from sqlalchemy.exc import SQLAlchemyError

from contaview.logic.importacao import salvar_preparacao_confirmada
from contaview.logic.mapeamento_colunas import mapear_colunas, sugerir_mapeamento
from contaview.logic.parsers import inspecionar_planilha

from ..models import (
    ArquivoEntradaTemporario,
    EstadoArquivoEntrada,
    ModeloMapeamentoEntrada,
)
from .contexto import ContextoTrabalho, obter_empresa_ativa
from .automacoes import identificar_perfil_origem, registrar_processamento_concluido

EXTENSOES_PERMITIDAS = {"xlsx", "xls", "csv", "ofx"}
LIMITE_BYTES = 20 * 1024 * 1024
LIMITE_XLSX_DESCOMPACTADO = 100 * 1024 * 1024
LIMITE_MEMBROS_XLSX = 1_000
LIMITE_PREVIA = 12
TIPOS_DOCUMENTO = {"extrato", "folha", "notas", "lancamentos", "outro"}
CAMPOS_MAPEAMENTO = {
    "data", "valor", "descricao", "tipo", "conta_contabil", "filial"
}


class ErroEntrada(ValueError):
    """Erro que pode ser exibido sem expor detalhes internos."""


class ReenvioArquivo(ErroEntrada):
    pass


@dataclass(frozen=True, slots=True)
class InspecaoSelecionada:
    resultado: dict
    aba: dict
    sugestao: dict[str, str]
    assinatura: str
    modelo_reutilizado: bool


class ArquivoEmMemoria(io.BytesIO):
    def __init__(self, conteudo: bytes, nome: str):
        super().__init__(conteudo)
        self.name = nome


def _nome_seguro(nome: str) -> str:
    nome_limpo = Path(str(nome).replace("\\", "/")).name.strip()
    nome_limpo = "".join(
        caractere for caractere in nome_limpo
        if unicodedata.category(caractere)[0] != "C"
    )
    if not nome_limpo or len(nome_limpo) > 255:
        raise ErroEntrada("O nome do arquivo é vazio ou maior que 255 caracteres.")
    return nome_limpo


def _validar_conteudo(nome: str, conteudo: bytes) -> str:
    extensao = Path(nome).suffix.lower().lstrip(".")
    if extensao not in EXTENSOES_PERMITIDAS:
        raise ErroEntrada(
            f"Arquivo {nome}: extensão inválida. Use OFX, XLSX, XLS ou CSV."
        )
    if not conteudo:
        raise ErroEntrada(f"Arquivo {nome}: o arquivo está vazio.")
    if len(conteudo) > LIMITE_BYTES:
        raise ErroEntrada(
            f"Arquivo {nome}: tamanho maior que 20 MB. Divida o arquivo."
        )
    if extensao == "xlsx":
        if not conteudo.startswith(b"PK"):
            raise ErroEntrada(f"Arquivo {nome}: o conteúdo não é um XLSX válido.")
        try:
            with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
                membros = pacote.infolist()
                if len(membros) > LIMITE_MEMBROS_XLSX:
                    raise ErroEntrada(
                        f"Arquivo {nome}: o XLSX possui arquivos internos em excesso."
                    )
                if sum(item.file_size for item in membros) > LIMITE_XLSX_DESCOMPACTADO:
                    raise ErroEntrada(
                        f"Arquivo {nome}: o XLSX descompactado excede 100 MB."
                    )
        except zipfile.BadZipFile as erro:
            raise ErroEntrada(f"Arquivo {nome}: o XLSX está corrompido.") from erro
    elif extensao == "xls" and not (
        conteudo.startswith(bytes.fromhex("D0CF11E0"))
        or b"<?xml" in conteudo[:300].lower()
    ):
        raise ErroEntrada(f"Arquivo {nome}: o conteúdo não é um XLS válido.")
    elif extensao == "csv" and b"\x00" in conteudo[:8192]:
        raise ErroEntrada(f"Arquivo {nome}: o CSV contém dados binários inválidos.")
    elif extensao == "ofx" and b"<OFX" not in conteudo.upper():
        raise ErroEntrada(f"Arquivo {nome}: o conteúdo não é um OFX válido.")
    return extensao


def _texto_json(valor) -> str:
    if valor is None:
        return ""
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


def resumir_inspecao(resultado: dict) -> dict:
    resumo = {
        "abas": [
            {
                "nome": aba["nome"],
                "linha_cabecalho": aba["linha_cabecalho"],
                "cabecalhos": aba["cabecalhos"],
                "total_linhas": aba["total_linhas"],
                "previa": [
                    {
                        "numero_linha": linha["numero_linha"],
                        "valores": {
                            coluna: _texto_json(valor)
                            for coluna, valor in linha["valores"].items()
                        },
                    }
                    for linha in aba["linhas"][:LIMITE_PREVIA]
                ],
            }
            for aba in resultado["abas"]
        ]
    }
    if resultado.get("metadados_origem"):
        resumo["metadados_origem"] = {
            chave: _texto_json(valor)
            if not isinstance(valor, list) else [_texto_json(item) for item in valor]
            for chave, valor in resultado["metadados_origem"].items()
        }
    return resumo


def _existe_lote_final(empresa_id: int, arquivo_sha256: str) -> tuple | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nome_arquivo, criado_em
            FROM lotes_importacao
            WHERE empresa_id = %s AND arquivo_sha256 = %s
              AND status <> 'cancelado'
            ORDER BY id DESC LIMIT 1
            """,
            [empresa_id, arquivo_sha256],
        )
        return cursor.fetchone()


def receber_arquivo(arquivo, contexto: ContextoTrabalho, usuario) -> ArquivoEntradaTemporario:
    nome = _nome_seguro(arquivo.name)
    conteudo = arquivo.read()
    extensao = _validar_conteudo(nome, conteudo)
    arquivo_sha256 = hashlib.sha256(conteudo).hexdigest()

    lote = _existe_lote_final(contexto.empresa_id, arquivo_sha256)
    if lote:
        raise ReenvioArquivo(
            f"Arquivo {nome}: este conteúdo já foi recebido no lote {lote[0]}."
        )
    temporario = ArquivoEntradaTemporario.objects.filter(
        usuario=usuario,
        empresa_id=contexto.empresa_id,
        arquivo_sha256=arquivo_sha256,
        status__in=(EstadoArquivoEntrada.RECEBIDO, EstadoArquivoEntrada.EM_MAPEAMENTO),
    ).first()
    if temporario:
        raise ReenvioArquivo(
            f"Arquivo {nome}: este conteúdo já está aguardando mapeamento."
        )

    resultado = inspecionar_planilha(ArquivoEmMemoria(conteudo, nome))
    if not resultado.get("sucesso"):
        raise ErroEntrada(f"Arquivo {nome}: {resultado.get('erro', 'falha na leitura')}.")

    perfil_origem = identificar_perfil_origem(contexto, nome, validar_contexto=False)
    with transaction.atomic():
        temporario = ArquivoEntradaTemporario.objects.create(
            usuario=usuario,
            empresa_id=contexto.empresa_id,
            competencia=contexto.competencia,
            nome_original=nome,
            extensao=extensao,
            tamanho_bytes=len(conteudo),
            arquivo_sha256=arquivo_sha256,
            conteudo=conteudo,
            inspecao=resumir_inspecao(resultado),
            perfil_origem=perfil_origem,
            status=EstadoArquivoEntrada.EM_MAPEAMENTO,
        )
        registrar_processamento_concluido(temporario, contexto, usuario)
    return temporario


def obter_arquivo_contexto(
    identificador, contexto: ContextoTrabalho, usuario
) -> ArquivoEntradaTemporario:
    try:
        return ArquivoEntradaTemporario.objects.get(
            id=identificador,
            usuario=usuario,
            empresa_id=contexto.empresa_id,
            competencia=contexto.competencia,
            status__in=(EstadoArquivoEntrada.RECEBIDO, EstadoArquivoEntrada.EM_MAPEAMENTO),
        )
    except ArquivoEntradaTemporario.DoesNotExist as erro:
        raise ErroEntrada("O arquivo não existe neste contexto ou já foi concluído.") from erro


def _normalizar_cabecalho(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", normalizado.casefold()).strip()


def assinatura_estrutura(aba: dict) -> str:
    estrutura = {
        "cabecalhos": [_normalizar_cabecalho(item) for item in aba["cabecalhos"]],
        "quantidade": len(aba["cabecalhos"]),
    }
    serializado = json.dumps(estrutura, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(serializado.encode()).hexdigest()


def _sugestao_local(cabecalhos: list[str]) -> dict[str, str]:
    sugestao = {
        campo: coluna
        for coluna, campo in mapear_colunas(cabecalhos).items()
        if campo in {"data", "valor", "tipo", "conta_contabil", "filial", "historico"}
    }
    if "historico" in sugestao:
        sugestao["descricao"] = sugestao.pop("historico")
    return sugestao


def inspecionar_selecao(
    arquivo: ArquivoEntradaTemporario, nome_aba: str,
    linha_cabecalho: int, tipo_documento: str,
    usar_ia: bool = False,
) -> InspecaoSelecionada:
    if tipo_documento not in TIPOS_DOCUMENTO:
        raise ErroEntrada("Selecione um tipo de documento válido.")
    resultado = inspecionar_planilha(
        ArquivoEmMemoria(bytes(arquivo.conteudo), arquivo.nome_original),
        linha_cabecalho=linha_cabecalho,
        aba_alvo=nome_aba,
    )
    if not resultado.get("sucesso"):
        raise ErroEntrada(
            f"Aba {nome_aba}, linha {linha_cabecalho}: {resultado.get('erro', 'falha na leitura')}."
        )
    aba = next((item for item in resultado["abas"] if item["nome"] == nome_aba), None)
    if not aba:
        raise ErroEntrada(f"Aba {nome_aba}: a aba selecionada não foi encontrada.")
    assinatura = assinatura_estrutura(aba)
    modelos = ModeloMapeamentoEntrada.objects.filter(
        empresa_id=arquivo.empresa_id,
        assinatura_estrutura=assinatura,
        tipo_documento=tipo_documento,
    )
    if arquivo.perfil_origem_id:
        modelo = modelos.filter(perfil_origem_id=arquivo.perfil_origem_id).first()
    else:
        modelo = modelos.filter(perfil_origem__isnull=True).first()
    if modelo:
        sugestao = {
            campo: coluna for campo, coluna in modelo.mapeamento.items()
            if campo in CAMPOS_MAPEAMENTO and coluna in aba["cabecalhos"]
        }
        reutilizado = True
    else:
        sugestao = _sugestao_local(aba["cabecalhos"])
        reutilizado = False
        if usar_ia and not {"data", "valor"}.issubset(sugestao):
            sugestao.update(sugerir_mapeamento(aba["cabecalhos"]))
            sugestao = {
                campo: coluna for campo, coluna in sugestao.items()
                if campo in CAMPOS_MAPEAMENTO and coluna in aba["cabecalhos"]
            }
    return InspecaoSelecionada(resultado, aba, sugestao, assinatura, reutilizado)


@transaction.atomic
def confirmar_preparacao(
    arquivo: ArquivoEntradaTemporario, contexto: ContextoTrabalho,
    usuario, nome_aba: str, linha_cabecalho: int,
    tipo_documento: str, mapeamento: dict[str, str],
) -> dict:
    bloqueado = ArquivoEntradaTemporario.objects.select_for_update().get(pk=arquivo.pk)
    if (
        bloqueado.usuario_id != usuario.pk
        or bloqueado.empresa_id != contexto.empresa_id
        or bloqueado.competencia != contexto.competencia
        or bloqueado.status not in {
            EstadoArquivoEntrada.RECEBIDO, EstadoArquivoEntrada.EM_MAPEAMENTO
        }
    ):
        raise ErroEntrada("O arquivo não está disponível neste contexto.")
    if not obter_empresa_ativa(contexto.empresa_id):
        raise ErroEntrada("A empresa selecionada não está ativa.")

    selecao = inspecionar_selecao(
        bloqueado, nome_aba, linha_cabecalho, tipo_documento
    )
    mapeamento_limpo = {
        campo: coluna for campo, coluna in mapeamento.items()
        if campo in CAMPOS_MAPEAMENTO and coluna
    }
    try:
        resultado = salvar_preparacao_confirmada(
            ArquivoEmMemoria(bytes(bloqueado.conteudo), bloqueado.nome_original),
            contexto.empresa_id,
            nome_aba,
            tipo_documento,
            contexto.competencia,
            mapeamento_limpo,
            linha_cabecalho,
            validar_periodo=(
                not bloqueado.perfil_origem
                or bloqueado.perfil_origem.regra_competencia == "restrita"
            ),
        )
    except SQLAlchemyError as erro:
        raise ErroEntrada(
            "O banco não concluiu a preparação. O arquivo continua disponível para nova tentativa."
        ) from erro
    if not resultado.get("sucesso"):
        raise ErroEntrada(str(resultado.get("erro", "Não foi possível preparar o arquivo.")))

    modelo, criado = ModeloMapeamentoEntrada.objects.update_or_create(
        empresa_id=contexto.empresa_id,
        perfil_origem=bloqueado.perfil_origem,
        assinatura_estrutura=selecao.assinatura,
        tipo_documento=tipo_documento,
        defaults={
            "aba": nome_aba,
            "linha_cabecalho": linha_cabecalho,
            "mapeamento": mapeamento_limpo,
            "confirmado_por": usuario,
        },
    )
    if not criado:
        ModeloMapeamentoEntrada.objects.filter(pk=modelo.pk).update(
            vezes_utilizado=F("vezes_utilizado") + 1
        )
    bloqueado.status = EstadoArquivoEntrada.PREPARADO
    # O original já foi preservado no lote definitivo; evitar uma segunda
    # cópia de dados sensíveis na área temporária.
    bloqueado.conteudo = b""
    bloqueado.save(update_fields=["status", "conteudo", "atualizado_em"])
    return resultado


def descartar_arquivo(
    arquivo: ArquivoEntradaTemporario, contexto: ContextoTrabalho, usuario
) -> None:
    if arquivo.usuario_id != usuario.pk or arquivo.empresa_id != contexto.empresa_id:
        raise ErroEntrada("O arquivo não está disponível neste contexto.")
    arquivo.status = EstadoArquivoEntrada.DESCARTADO
    arquivo.conteudo = b""
    arquivo.save(update_fields=["status", "conteudo", "atualizado_em"])


def listar_lotes_contexto(contexto: ContextoTrabalho) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nome_arquivo, aba, tipo_documento, total_linhas,
                   status, criado_em,
                   (SELECT COUNT(*) FROM linhas_preparadas linha
                    WHERE linha.lote_id = lote.id AND linha.status = 'pendente')
            FROM lotes_importacao lote
            WHERE empresa_id = %s AND periodo = %s
            ORDER BY criado_em DESC, id DESC LIMIT 30
            """,
            [contexto.empresa_id, contexto.competencia],
        )
        return [
            {
                "id": linha[0], "nome_arquivo": linha[1], "aba": linha[2],
                "tipo_documento": linha[3], "total_linhas": linha[4],
                "status": linha[5], "criado_em": linha[6], "pendentes": linha[7],
            }
            for linha in cursor.fetchall()
        ]
