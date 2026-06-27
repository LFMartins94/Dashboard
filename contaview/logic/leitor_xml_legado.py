"""
leitor_xml_legado.py
====================
Detecta e le arquivos .xls que na verdade sao XML SpreadsheetML (Excel 2003).

Integracao: chamado por parsers.ler_arquivo() antes das estrategias normais.
O fluxo e:

  parsers.ler_arquivo()
    -> detectar_xml_legado(cabecalho)  -> True
    -> ler_xml_legado(conteudo)        -> {aba: df_raw}
    -> _processar_aba(df_raw)          -> estrategias 1/2/3
    -> normalizar_colunas / limpar_dataframe
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict

import pandas as pd

logger = logging.getLogger(__name__)

XMLNS = "urn:schemas-microsoft-com:office:spreadsheet"


def detectar_xml_legado(conteudo_arquivo: bytes) -> bool:
    """Retorna True se os primeiros 200 bytes indicarem XML SpreadsheetML."""
    cabecalho = conteudo_arquivo[:200]
    return b"<?xml" in cabecalho and b"urn:schemas-microsoft-com:office:spreadsheet" in cabecalho


def ler_xml_legado(conteudo: bytes) -> Dict[str, pd.DataFrame]:
    """
    Le bytes de XML SpreadsheetML e retorna {nome_da_aba: DataFrame}
    com dados crus (strings), sem cabecalho.

    Trata celulas puladas via ss:Index e ignora linhas/celulas sem dados.
    """
    root = ET.fromstring(conteudo)
    ns = {"ss": XMLNS}

    abas: Dict[str, pd.DataFrame] = {}
    for ws in root.findall(".//ss:Worksheet", ns):
        nome = ws.attrib.get(f"{{{XMLNS}}}Name", "Plan1")
        table = ws.find("ss:Table", ns)
        if table is None:
            continue

        linhas: list[list[str]] = []
        for row in table.findall("ss:Row", ns):
            celulas: list[str] = []
            col_esperada = 1
            for cell in row.findall("ss:Cell", ns):
                index_str = cell.attrib.get(f"{{{XMLNS}}}Index")
                col_atual = int(index_str) if index_str else col_esperada
                while len(celulas) < col_atual - 1:
                    celulas.append("")
                data = cell.find("ss:Data", ns)
                celulas.append(
                    data.text.strip() if data is not None and data.text else ""
                )
                col_esperada = col_atual + 1
            linhas.append(celulas)

        if linhas:
            abas[nome] = pd.DataFrame(linhas).fillna("").astype(str)

    if not abas:
        logger.warning("Nenhuma aba encontrada no XML SpreadsheetML.")

    return abas
