"""
parsers.py
==========
Módulo de ingestão multifonte para o Dashboard Financeiro.
Cada função recebe um objeto de arquivo (BytesIO / UploadedFile) e retorna
um pd.DataFrame padronizado com as colunas: data, categoria, valor.

Regras de resiliência:
  - Campos ausentes são marcados como 'NÃO ENCONTRADO'.
  - Erros isolados por linha/slide são logados e ignorados.
  - Nenhum parser interrompe o fluxo do app — sempre retorna um DataFrame.
"""

import io
import logging
import re
from datetime import date, datetime
from typing import Any, BinaryIO

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
COLUNAS_PADRAO: list[str] = ["data", "categoria", "valor"]
SENTINEL: str = "NÃO ENCONTRADO"

# Padrões para extração heurística de valores monetários em texto livre
_RE_VALOR = re.compile(r"R?\$?\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)")
_RE_DATA = re.compile(r"\b(\d{2}[/\-]\d{2}[/\-]\d{2,4})\b")


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _df_vazio() -> pd.DataFrame:
    """Retorna um DataFrame vazio com as colunas padrão."""
    return pd.DataFrame(columns=COLUNAS_PADRAO)


def _normalizar_valor(raw: Any) -> float:
    """
    Converte string ou número bruto em float financeiro.
    Suporta formatos: '1.234,56', '1,234.56', '1234.56'.
    """
    if isinstance(raw, (int, float)):
        return round(float(raw), 2)
    texto = str(raw).strip().replace("R$", "").replace(" ", "")
    # Detecta separador decimal: último ponto ou vírgula
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return round(float(texto), 2)


def _normalizar_data(raw: Any) -> str:
    """
    Normaliza diversas representações de data para o formato ISO 'YYYY-MM-DD'.
    Retorna SENTINEL se a conversão falhar.
    """
    if isinstance(raw, (date, datetime)):
        return raw.strftime("%Y-%m-%d") if isinstance(raw, datetime) else raw.isoformat()
    texto = str(raw).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(texto, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return SENTINEL


def _construir_dataframe(registros: list[dict]) -> pd.DataFrame:
    """
    Converte uma lista de dicionários {data, categoria, valor} em
    DataFrame padronizado, preenchendo colunas ausentes com SENTINEL.
    """
    if not registros:
        return _df_vazio()
    df = pd.DataFrame(registros)
    for col in COLUNAS_PADRAO:
        if col not in df.columns:
            df[col] = SENTINEL
    return df[COLUNAS_PADRAO]


# ---------------------------------------------------------------------------
# Parser 1 — Excel / CSV
# ---------------------------------------------------------------------------
def processar_excel_csv(arquivo: BinaryIO) -> pd.DataFrame:
    """
    Lê um arquivo .xlsx ou .csv e retorna um DataFrame padronizado.

    Estratégia de mapeamento de colunas:
      - Procura por colunas cujos nomes contenham 'data', 'categ', 'valor'
        (case-insensitive), aceitando variações de nomenclatura.
      - Colunas não encontradas recebem o valor SENTINEL.

    Args:
        arquivo: Objeto de arquivo binário (.xlsx ou .csv).

    Returns:
        pd.DataFrame: Dados normalizados com colunas [data, categoria, valor].
    """
    nome: str = getattr(arquivo, "name", "arquivo")
    try:
        if nome.lower().endswith(".csv"):
            df_raw = pd.read_csv(arquivo, dtype=str)
        else:
            df_raw = pd.read_excel(arquivo, dtype=str, engine="openpyxl")
    except Exception as exc:
        logger.error("Falha ao ler '%s': %s", nome, exc)
        return _df_vazio()

    if df_raw.empty:
        logger.warning("'%s' está vazio.", nome)
        return _df_vazio()

    # Mapeamento flexível de colunas
    col_map: dict[str, str] = {}
    for col in df_raw.columns:
        col_lower = col.lower()
        if "data" in col_lower and "data" not in col_map:
            col_map["data"] = col
        elif "categ" in col_lower and "categoria" not in col_map:
            col_map["categoria"] = col
        elif ("valor" in col_lower or "value" in col_lower or "amount" in col_lower) and "valor" not in col_map:
            col_map["valor"] = col

    registros: list[dict] = []
    for idx, row in df_raw.iterrows():
        try:
            data_val = _normalizar_data(row[col_map["data"]]) if "data" in col_map else SENTINEL
            cat_val = str(row[col_map["categoria"]]).strip() if "categoria" in col_map else SENTINEL
            val_raw = row[col_map["valor"]] if "valor" in col_map else SENTINEL
            valor_val = _normalizar_valor(val_raw) if val_raw != SENTINEL else 0.0
            registros.append({"data": data_val, "categoria": cat_val, "valor": valor_val})
        except Exception as exc:
            logger.warning("Linha %d de '%s' ignorada: %s", idx, nome, exc)

    logger.info("'%s': %d registros extraídos.", nome, len(registros))
    return _construir_dataframe(registros)


# ---------------------------------------------------------------------------
# Parser 2 — PDF
# ---------------------------------------------------------------------------
def extrair_dados_pdf(arquivo: BinaryIO) -> pd.DataFrame:
    """
    Extrai dados financeiros de um PDF usando pdfplumber.

    Estratégia em duas fases:
      1. Tabelas nativas: tenta extrair tabelas estruturadas de cada página.
      2. Fallback textual: regex sobre o texto bruto da página para capturar
         pares (data, valor), categorizando como SENTINEL quando ausente.

    Args:
        arquivo: Objeto de arquivo binário (.pdf).

    Returns:
        pd.DataFrame: Dados normalizados com colunas [data, categoria, valor].
    """
    try:
        import pdfplumber  # noqa: PLC0415
    except ImportError:
        logger.error("pdfplumber não instalado. Execute: pip install pdfplumber")
        return _df_vazio()

    nome: str = getattr(arquivo, "name", "arquivo.pdf")
    registros: list[dict] = []

    try:
        with pdfplumber.open(arquivo) as pdf:
            for pg_num, page in enumerate(pdf.pages, start=1):
                # Fase 1: tabelas nativas
                tabelas = page.extract_tables()
                for tabela in tabelas:
                    if not tabela:
                        continue
                    headers = [str(h).lower().strip() if h else "" for h in tabela[0]]
                    idx_data = next((i for i, h in enumerate(headers) if "data" in h), None)
                    idx_cat  = next((i for i, h in enumerate(headers) if "categ" in h), None)
                    idx_val  = next((i for i, h in enumerate(headers) if "valor" in h or "value" in h), None)

                    for linha in tabela[1:]:
                        if not any(linha):
                            continue
                        try:
                            data_val = _normalizar_data(linha[idx_data]) if idx_data is not None else SENTINEL
                            cat_val  = str(linha[idx_cat]).strip() if idx_cat is not None else SENTINEL
                            val_raw  = linha[idx_val] if idx_val is not None else SENTINEL
                            valor_val = _normalizar_valor(val_raw) if val_raw not in (None, SENTINEL, "") else 0.0
                            registros.append({"data": data_val, "categoria": cat_val, "valor": valor_val})
                        except Exception as exc:
                            logger.warning("Tabela pg.%d linha ignorada: %s", pg_num, exc)

                # Fase 2: fallback textual se sem tabelas
                if not tabelas:
                    texto = page.extract_text() or ""
                    datas_encontradas = _RE_DATA.findall(texto)
                    valores_encontrados = _RE_VALOR.findall(texto)
                    pares = zip(datas_encontradas, valores_encontrados)
                    for dt, vl in pares:
                        try:
                            registros.append({
                                "data": _normalizar_data(dt),
                                "categoria": SENTINEL,
                                "valor": _normalizar_valor(vl),
                            })
                        except Exception as exc:
                            logger.warning("Extração textual pg.%d ignorada: %s", pg_num, exc)

    except Exception as exc:
        logger.error("Falha crítica ao processar PDF '%s': %s", nome, exc)
        return _df_vazio()

    logger.info("PDF '%s': %d registros extraídos.", nome, len(registros))
    return _construir_dataframe(registros)


# ---------------------------------------------------------------------------
# Parser 3 — PowerPoint
# ---------------------------------------------------------------------------
def extrair_dados_powerpoint(arquivo: BinaryIO) -> pd.DataFrame:
    """
    Extrai dados financeiros de uma apresentação .pptx.

    Estratégia em duas fases por slide:
      1. Tabelas nativas (python-pptx): itera sobre shapes do tipo TABLE
         e aplica o mesmo mapeamento de colunas do parser Excel.
      2. Fallback textual: regex sobre o texto de cada shape para capturar
         valores monetários e datas.

    Args:
        arquivo: Objeto de arquivo binário (.pptx).

    Returns:
        pd.DataFrame: Dados normalizados com colunas [data, categoria, valor].
    """
    try:
        from pptx import Presentation          # noqa: PLC0415
        from pptx.util import Pt               # noqa: PLC0415, F401
        from pptx.enum.shapes import MSO_SHAPE_TYPE  # noqa: PLC0415
    except ImportError:
        logger.error("python-pptx não instalado. Execute: pip install python-pptx")
        return _df_vazio()

    nome: str = getattr(arquivo, "name", "arquivo.pptx")
    registros: list[dict] = []

    try:
        prs = Presentation(arquivo)

        for slide_num, slide in enumerate(prs.slides, start=1):
            for shape in slide.shapes:
                # Fase 1: tabelas nativas
                if shape.has_table:
                    tbl = shape.table
                    headers = [
                        tbl.cell(0, c).text.lower().strip()
                        for c in range(tbl.columns.__len__())
                    ]
                    idx_data = next((i for i, h in enumerate(headers) if "data" in h), None)
                    idx_cat  = next((i for i, h in enumerate(headers) if "categ" in h), None)
                    idx_val  = next((i for i, h in enumerate(headers) if "valor" in h or "value" in h), None)

                    for row_idx in range(1, len(tbl.rows)):
                        try:
                            get = lambda c: tbl.cell(row_idx, c).text.strip() if c is not None else SENTINEL  # noqa: E731
                            data_val  = _normalizar_data(get(idx_data)) if idx_data is not None else SENTINEL
                            cat_val   = get(idx_cat) or SENTINEL
                            val_raw   = get(idx_val)
                            valor_val = _normalizar_valor(val_raw) if val_raw and val_raw != SENTINEL else 0.0
                            registros.append({"data": data_val, "categoria": cat_val, "valor": valor_val})
                        except Exception as exc:
                            logger.warning("Slide %d, tabela linha %d ignorada: %s", slide_num, row_idx, exc)

                # Fase 2: fallback textual em shapes de texto
                elif shape.has_text_frame:
                    texto = "\n".join(p.text for p in shape.text_frame.paragraphs)
                    datas   = _RE_DATA.findall(texto)
                    valores = _RE_VALOR.findall(texto)
                    for dt, vl in zip(datas, valores):
                        try:
                            registros.append({
                                "data": _normalizar_data(dt),
                                "categoria": SENTINEL,
                                "valor": _normalizar_valor(vl),
                            })
                        except Exception as exc:
                            logger.warning("Slide %d texto ignorado: %s", slide_num, exc)

    except Exception as exc:
        logger.error("Falha crítica ao processar PPTX '%s': %s", nome, exc)
        return _df_vazio()

    logger.info("PPTX '%s': %d registros extraídos.", nome, len(registros))
    return _construir_dataframe(registros)


# ---------------------------------------------------------------------------
# Dispatcher público
# ---------------------------------------------------------------------------
def processar_arquivo(arquivo: BinaryIO) -> tuple[pd.DataFrame, str]:
    """
    Dispatcher: detecta a extensão do arquivo e chama o parser correto.

    Args:
        arquivo: Objeto de arquivo binário com atributo `.name`.

    Returns:
        tuple[pd.DataFrame, str]: (DataFrame extraído, extensão sem ponto).

    Raises:
        ValueError: Se a extensão não for suportada.
    """
    nome: str = getattr(arquivo, "name", "")
    ext = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""

    if ext in ("xlsx", "xls"):
        return processar_excel_csv(arquivo), "excel"
    elif ext == "csv":
        return processar_excel_csv(arquivo), "csv"
    elif ext == "pdf":
        return extrair_dados_pdf(arquivo), "pdf"
    elif ext == "pptx":
        return extrair_dados_powerpoint(arquivo), "pptx"
    else:
        raise ValueError(f"Extensão '.{ext}' não suportada. Use: xlsx, csv, pdf ou pptx.")
