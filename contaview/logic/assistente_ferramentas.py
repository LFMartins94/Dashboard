"""
assistente_ferramentas.py
=========================
Ferramentas de consulta para o assistente ContaView.

Cada funcao recebe parametros em linguagem natural, normaliza
empresa e periodo, consulta o banco e retorna um dicionario.

Nenhuma funcao lanca excecao -- todas retornam {"erro": "..."}
em caso de falha, para que o modelo possa incorporar a mensagem
na resposta ao usuario.
"""

import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd

from contaview.logic import database

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dicionario de meses PT-BR
# ---------------------------------------------------------------------------
MESES_PT: Dict[str, str] = {
    "janeiro": "01", "jan": "01",
    "fevereiro": "02", "fev": "02",
    "marco": "03", "mar": "03",
    "abril": "04", "abr": "04",
    "maio": "05", "mai": "05",
    "junho": "06", "jun": "06",
    "julho": "07", "jul": "07",
    "agosto": "08", "ago": "08",
    "setembro": "09", "set": "09",
    "outubro": "10", "out": "10",
    "novembro": "11", "nov": "11",
    "dezembro": "12", "dez": "12",
}

# ---------------------------------------------------------------------------
# Normalizacao de periodo
# ---------------------------------------------------------------------------
_RE_PERIODO_ISO = re.compile(r"^(\d{4})[-/](\d{2})$")
_RE_PERIODO_BR = re.compile(r"^(\d{2})[-/](\d{4})$")
_RE_PERIODO_TEXTO = re.compile(
    r"^([a-záéíóúãõç]+)\s*(?:de\s*)?[-/]?\s*(\d{4})$", re.IGNORECASE
)


def normalizar_periodo_natural(texto: str) -> Optional[str]:
    """Converte 'maio de 2026', '05/2026', '2026-05' para 'AAAA-MM'."""
    if not texto or not texto.strip():
        return None
    t = texto.strip().lower()

    m = _RE_PERIODO_ISO.match(t)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    m = _RE_PERIODO_BR.match(t)
    if m:
        return f"{m.group(2)}-{m.group(1)}"

    m = _RE_PERIODO_TEXTO.match(t)
    if m:
        mes = MESES_PT.get(m.group(1).lower())
        if mes:
            return f"{m.group(2)}-{mes}"

    return None


# ---------------------------------------------------------------------------
# Resolucao de empresa
# ---------------------------------------------------------------------------
def resolver_nome_empresa(nome: str) -> Optional[int]:
    """Busca empresa por nome (exato, depois contem) e retorna o ID."""
    if not nome or not nome.strip():
        return None
    try:
        df = database.listar_empresas()
    except Exception as exc:
        logger.error("Erro ao listar empresas: %s", exc)
        return None
    if df.empty:
        return None
    nome_procurado = nome.strip().lower()
    match = df[df["nome"].str.lower() == nome_procurado]
    if match.empty:
        match = df[df["nome"].str.lower().str.contains(nome_procurado, na=False)]
    if match.empty:
        return None
    return int(match.iloc[0]["id"])


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _processar_parametros(
    empresa: str, periodo: Optional[str] = None,
) -> Dict[str, Any]:
    """Valida empresa e periodo. Retorna dict com empresa_id e periodo
    normalizado, ou {"erro": "..."}."""
    empresa_id = resolver_nome_empresa(empresa)
    if empresa_id is None:
        return {"erro": f"Empresa '{empresa}' nao encontrada."}

    periodo_normalizado = None
    if periodo:
        periodo_normalizado = normalizar_periodo_natural(periodo)
        if periodo_normalizado is None:
            return {
                "erro": f"Nao foi possivel interpretar o periodo '{periodo}'. "
                        "Use formato como 'maio de 2026' ou '05/2026'."
            }

    return {"empresa_id": empresa_id, "periodo": periodo_normalizado}


def _formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# Ferramentas de consulta
# ---------------------------------------------------------------------------

def consultar_saldo(empresa: str, periodo: Optional[str] = None) -> Dict[str, Any]:
    """Retorna o saldo (creditos - debitos) de uma empresa em um periodo."""
    params = _processar_parametros(empresa, periodo)
    if "erro" in params:
        return params
    try:
        df = database.carregar_lancamentos(params["empresa_id"], params["periodo"])
        if df.empty:
            return {"erro": "Nenhum lancamento encontrado para essa consulta."}
        saldo = float(df["valor"].sum())
        return {
            "saldo": round(saldo, 2),
            "saldo_formatado": _formatar_moeda(saldo),
            "empresa": empresa,
            "periodo": params["periodo"],
        }
    except Exception as exc:
        logger.error("Erro em consultar_saldo: %s", exc)
        return {"erro": "Erro ao consultar saldo. Tente novamente."}


def consultar_total_debitos(empresa: str, periodo: Optional[str] = None) -> Dict[str, Any]:
    """Retorna o total de debitos de uma empresa em um periodo."""
    params = _processar_parametros(empresa, periodo)
    if "erro" in params:
        return params
    try:
        df = database.carregar_lancamentos(params["empresa_id"], params["periodo"])
        if df.empty:
            return {"erro": "Nenhum lancamento encontrado para essa consulta."}
        total = float(df[df["tipo"] == "D"]["valor"].sum())
        return {
            "total_debitos": round(total, 2),
            "total_debitos_formatado": _formatar_moeda(total),
            "quantidade": int((df["tipo"] == "D").sum()),
            "empresa": empresa,
            "periodo": params["periodo"],
        }
    except Exception as exc:
        logger.error("Erro em consultar_total_debitos: %s", exc)
        return {"erro": "Erro ao consultar debitos. Tente novamente."}


def consultar_total_creditos(empresa: str, periodo: Optional[str] = None) -> Dict[str, Any]:
    """Retorna o total de creditos de uma empresa em um periodo."""
    params = _processar_parametros(empresa, periodo)
    if "erro" in params:
        return params
    try:
        df = database.carregar_lancamentos(params["empresa_id"], params["periodo"])
        if df.empty:
            return {"erro": "Nenhum lancamento encontrado para essa consulta."}
        total = float(df[df["tipo"] == "C"]["valor"].sum())
        return {
            "total_creditos": round(total, 2),
            "total_creditos_formatado": _formatar_moeda(total),
            "quantidade": int((df["tipo"] == "C").sum()),
            "empresa": empresa,
            "periodo": params["periodo"],
        }
    except Exception as exc:
        logger.error("Erro em consultar_total_creditos: %s", exc)
        return {"erro": "Erro ao consultar creditos. Tente novamente."}


def consultar_lancamentos(
    empresa: str, periodo: Optional[str] = None, limite: int = 20,
) -> Dict[str, Any]:
    """Retorna os lancamentos de uma empresa, opcionalmente filtrados por
    periodo."""
    params = _processar_parametros(empresa, periodo)
    if "erro" in params:
        return params
    try:
        df = database.carregar_lancamentos(params["empresa_id"], params["periodo"])
        if df.empty:
            return {"erro": "Nenhum lancamento encontrado para essa consulta."}
        registros = df.head(limite).to_dict(orient="records")
        for r in registros:
            if "valor" in r:
                r["valor"] = round(float(r["valor"]), 2)
            if "data" in r and pd.notna(r.get("data")):
                r["data"] = str(r["data"])
        return {
            "lancamentos": registros,
            "quantidade": len(registros),
            "total_no_periodo": len(df),
            "empresa": empresa,
            "periodo": params["periodo"],
        }
    except Exception as exc:
        logger.error("Erro em consultar_lancamentos: %s", exc)
        return {"erro": "Erro ao consultar lancamentos. Tente novamente."}


def consultar_conciliacao(empresa: str, periodo: str) -> Dict[str, Any]:
    """Retorna o resultado da conciliacao de uma empresa em um periodo."""
    if not periodo:
        return {"erro": "Informe o periodo para consultar a conciliacao."}
    params = _processar_parametros(empresa, periodo)
    if "erro" in params:
        return params
    try:
        df = database.carregar_conciliacao(
            params["empresa_id"], params["periodo"]
        )
        if df.empty:
            return {"erro": "Nenhuma conciliacao encontrada para esse periodo."}
        row = df.iloc[0].to_dict()
        for k, v in row.items():
            if isinstance(v, (float,)):
                row[k] = round(v, 2)
            if isinstance(v, pd.Timestamp):
                row[k] = str(v)
        return {
            "conciliacao": row,
            "empresa": empresa,
            "periodo": params["periodo"],
        }
    except Exception as exc:
        logger.error("Erro em consultar_conciliacao: %s", exc)
        return {"erro": "Erro ao consultar conciliacao. Tente novamente."}


def consultar_auditoria(empresa: str, periodo: str) -> Dict[str, Any]:
    """Retorna as ocorrencias de auditoria de uma empresa em um periodo."""
    if not periodo:
        return {"erro": "Informe o periodo para consultar a auditoria."}
    params = _processar_parametros(empresa, periodo)
    if "erro" in params:
        return params
    try:
        df = database.carregar_ocorrencias(
            params["empresa_id"], params["periodo"]
        )
        if df.empty:
            return {"erro": "Nenhuma ocorrencia de auditoria encontrada."}
        ocorrencias = df.head(50).to_dict(orient="records")
        for o in ocorrencias:
            if "valor" in o and pd.notna(o.get("valor")):
                o["valor"] = round(float(o["valor"]), 2)
            for k in ("data", "criado_em"):
                if k in o and pd.notna(o.get(k)):
                    o[k] = str(o[k])
        resumo = {
            "alta": int((df["severidade"] == "alta").sum()),
            "media": int((df["severidade"] == "media").sum()),
            "baixa": int((df["severidade"] == "baixa").sum()),
            "total": len(df),
        }
        return {
            "ocorrencias": ocorrencias,
            "resumo": resumo,
            "empresa": empresa,
            "periodo": params["periodo"],
        }
    except Exception as exc:
        logger.error("Erro em consultar_auditoria: %s", exc)
        return {"erro": "Erro ao consultar auditoria. Tente novamente."}


def listar_empresas_cadastradas() -> Dict[str, Any]:
    """Lista todas as empresas cadastradas no sistema."""
    try:
        df = database.listar_empresas()
        if df.empty:
            return {"erro": "Nenhuma empresa cadastrada."}
        empresas = []
        for _, row in df.iterrows():
            nome = str(row.get("nome", ""))
            cnpj = str(row.get("cnpj", "")) if pd.notna(row.get("cnpj")) else ""
            empresas.append({"nome": nome, "cnpj": cnpj})
        return {"empresas": empresas, "quantidade": len(empresas)}
    except Exception as exc:
        logger.error("Erro em listar_empresas_cadastradas: %s", exc)
        return {"erro": "Erro ao listar empresas. Tente novamente."}


def listar_periodos_empresa(empresa: str) -> Dict[str, Any]:
    """Lista os periodos disponiveis para uma empresa."""
    params = _processar_parametros(empresa)
    if "erro" in params:
        return params
    try:
        periodos = database.listar_periodos(params["empresa_id"])
        if not periodos:
            return {"erro": "Nenhum periodo encontrado para essa empresa."}
        return {"periodos": periodos, "quantidade": len(periodos), "empresa": empresa}
    except Exception as exc:
        logger.error("Erro em listar_periodos_empresa: %s", exc)
        return {"erro": "Erro ao listar periodos. Tente novamente."}
