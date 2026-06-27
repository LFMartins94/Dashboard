"""
mapeamento_colunas.py
=====================
Mapeamento fuzzy de nomes de colunas de planilha para campos padronizados
do ContaView, usando rapidfuzz.

Funciona como fallback quando as 3 estrategias de parser nao conseguem
identificar as colunas obrigatorias.
"""

import logging
from typing import Dict, Optional

import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

LIMIAR_SIMILARIDADE = 75

DICIONARIO_SINONIMOS: Dict[str, list[str]] = {
    "data": ["data", "dt", "data lancamento", "vencimento", "data pagamento"],
    "valor": ["valor", "vlr", "total", "quantia", "valor (r$)",
              "entrada (r$)", "saida (r$)"],
    "debito": ["debito", "débito", "saida", "saída"],
    "credito": ["credito", "crédito", "entrada"],
    "conta_contabil": ["conta", "conta contabil", "codigo", "cod conta",
                       "código"],
    "tipo": ["tipo", "tp", "c/d", "natureza"],
    "historico": ["historico", "histórico", "descricao", "descrição",
                  "lancamento", "obs"],
    "filial": ["filial", "unidade", "loja"],
}


def _parse_valor(raw) -> float:
    if isinstance(raw, (int, float)):
        return round(float(raw), 2)
    try:
        if pd.isna(raw):
            return 0.0
    except (TypeError, ValueError):
        pass
    texto = str(raw).strip().replace("R$", "").replace(" ", "")
    if not texto or texto in ("nan", "None", ""):
        return 0.0
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return round(float(texto), 2)
    except ValueError:
        return 0.0


def mapear_colunas(colunas_planilha: list[str]) -> Dict[str, str]:
    """
    Mapeia nomes de colunas da planilha para campos padronizados
    usando similaridade fuzzy (token_sort_ratio >= 75).

    Args:
        colunas_planilha: Lista de nomes de coluna vindos do arquivo.

    Returns:
        Dict {nome_original: campo_padronizado} apenas para matches
        acima do limiar.
    """
    mapeamento: Dict[str, str] = {}

    todas_referencias: list[tuple[str, str]] = []
    for campo_padrao, sinonimos in DICIONARIO_SINONIMOS.items():
        todas_referencias.append((campo_padrao, campo_padrao))
        for sinonimo in sinonimos:
            todas_referencias.append((campo_padrao, sinonimo))

    for coluna in colunas_planilha:
        coluna_str = str(coluna).strip().lower()
        if not coluna_str:
            continue

        melhor_campo: Optional[str] = None
        melhor_score = 0

        for campo_padrao, referencia in todas_referencias:
            score = fuzz.token_sort_ratio(coluna_str, referencia.lower())
            if score > melhor_score:
                melhor_score = score
                melhor_campo = campo_padrao

        if melhor_score >= LIMIAR_SIMILARIDADE:
            mapeamento[coluna] = melhor_campo
            logger.debug(
                "Coluna '%s' mapeada para '%s' (score=%d)",
                coluna, melhor_campo, melhor_score,
            )

    return mapeamento


def derivar_valor_tipo_de_debito_credito(
    df: pd.DataFrame,
    col_debito: Optional[str],
    col_credito: Optional[str],
) -> pd.DataFrame:
    """
    Converte linhas com colunas debito/credito em linhas com valor+tipo.

    Para cada linha original:
      - Se debito > 0: gera uma linha com valor=debito e tipo='D'
      - Se credito > 0: gera uma linha com valor=credito e tipo='C'

    Preserva as demais colunas (conta_contabil, historico, filial, etc.)
    em cada linha gerada.

    Args:
        df: DataFrame com colunas debito e/ou credito.
        col_debito: Nome da coluna de debito (pode ser None).
        col_credito: Nome da coluna de credito (pode ser None).

    Returns:
        Novo DataFrame com colunas valor, tipo e as preservadas.
    """
    colunas_preservar = [
        c for c in df.columns
        if c not in (col_debito, col_credito, "valor", "tipo")
    ]

    linhas: list[dict] = []
    for _, row in df.iterrows():
        deb = _parse_valor(row.get(col_debito)) if col_debito else 0.0
        cre = _parse_valor(row.get(col_credito)) if col_credito else 0.0

        if deb > 0:
            nova = {c: row[c] for c in colunas_preservar}
            nova["valor"] = deb
            nova["tipo"] = "D"
            linhas.append(nova)

        if cre > 0:
            nova = {c: row[c] for c in colunas_preservar}
            nova["valor"] = cre
            nova["tipo"] = "C"
            linhas.append(nova)

    if not linhas:
        return pd.DataFrame()

    df_resultado = pd.DataFrame(linhas)

    if "data" in df_resultado.columns:
        df_resultado["data"] = pd.to_datetime(
            df_resultado["data"], dayfirst=True, errors="coerce"
        )

    logger.info(
        "Derivacao debito/credito: %d linhas geradas de %d originais.",
        len(df_resultado), len(df),
    )
    return df_resultado
