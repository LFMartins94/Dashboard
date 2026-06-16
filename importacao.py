import logging
from typing import BinaryIO

import pandas as pd

from database import (
    deletar_lancamentos_do_periodo,
    obter_ou_criar_empresa,
    salvar_lancamentos,
    verificar_periodo_existente,
)
from parsers import ler_arquivo

logger = logging.getLogger(__name__)

COLUNAS_OBRIGATORIAS = ["data", "conta_contabil", "valor", "tipo"]


def validar_pre_import(df: pd.DataFrame) -> dict:
    erros: list[str] = []
    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in df.columns:
            erros.append(f"Coluna obrigatoria ausente: '{coluna}'.")
        elif df[coluna].isna().all():
            erros.append(f"Coluna '{coluna}' esta completamente vazia.")

    if "data" in df.columns and "periodo" in df.columns:
        if df["periodo"].dropna().empty:
            erros.append("Nenhuma data valida encontrada para determinar o periodo.")

    return {"valido": len(erros) == 0, "erros": erros}


def injetar_sequencial_lote(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["sequencial_lote"] = range(1, len(df) + 1)
    return df


def executar_importacao(
    arquivo: BinaryIO,
    nome_empresa: str,
    cnpj_empresa: str = None,
) -> dict:
    # a. Ler arquivo
    resultado_leitura = ler_arquivo(arquivo)
    if not resultado_leitura["sucesso"]:
        return {
            "sucesso": False,
            "erro": resultado_leitura.get("motivo_falha", "Falha desconhecida ao ler arquivo."),
        }

    df = resultado_leitura["df"]

    # b. Validar
    validacao = validar_pre_import(df)
    if not validacao["valido"]:
        return {"sucesso": False, "erro": "; ".join(validacao["erros"])}

    # c. Injetar sequencial
    df = injetar_sequencial_lote(df)

    # d. Determinar periodo
    periodos = sorted(df["periodo"].dropna().unique())
    if not periodos:
        return {"sucesso": False, "erro": "Nenhum periodo valido encontrado nos dados."}
    periodo = periodos[0]

    # e. Obter ou criar empresa
    try:
        empresa_id = obter_ou_criar_empresa(nome_empresa, cnpj_empresa)
    except Exception as exc:
        logger.error("Erro ao obter/criar empresa '%s': %s", nome_empresa, exc)
        return {"sucesso": False, "erro": f"Erro ao identificar empresa: {exc}"}

    # f. Verificar duplicidade
    try:
        periodo_existente = verificar_periodo_existente(empresa_id, periodo)
    except Exception as exc:
        logger.error("Erro ao verificar periodo: %s", exc)
        return {"sucesso": False, "erro": f"Erro ao verificar periodo: {exc}"}

    if periodo_existente:
        return {
            "requer_confirmacao": True,
            "empresa_id": empresa_id,
            "periodo": periodo,
            "df": df,
        }

    # g. Salvar
    return _salvar_com_origem(df, empresa_id, arquivo)


def confirmar_substituicao(empresa_id: int, periodo: str, df: pd.DataFrame) -> dict:
    try:
        deletar_lancamentos_do_periodo(empresa_id, periodo)
    except Exception as exc:
        logger.error("Erro ao deletar periodo %s: %s", periodo, exc)
        return {"sucesso": False, "erro": f"Erro ao substituir periodo: {exc}"}

    return _salvar(df, empresa_id)


def _salvar(df: pd.DataFrame, empresa_id: int) -> dict:
    try:
        registros = salvar_lancamentos(df, empresa_id)
        periodo = df["periodo"].iloc[0] if "periodo" in df.columns and not df["periodo"].empty else None
        return {
            "sucesso": True,
            "registros_salvos": registros,
            "empresa_id": empresa_id,
            "periodo": periodo,
            "df": df,
        }
    except Exception as exc:
        logger.error("Erro ao salvar lancamentos: %s", exc)
        return {"sucesso": False, "erro": f"Erro ao salvar lancamentos: {exc}"}


def _salvar_com_origem(df: pd.DataFrame, empresa_id: int, arquivo: BinaryIO) -> dict:
    nome_arquivo = getattr(arquivo, "name", "arquivo")
    df = df.copy()
    df["arquivo_origem"] = nome_arquivo
    return _salvar(df, empresa_id)
