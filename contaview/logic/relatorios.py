import io
import csv
from decimal import Decimal
from datetime import datetime
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, mm

_COLUNAS_EXCEL = ["data", "conta_contabil", "valor", "tipo", "historico", "filial", "periodo"]
_CABECALHOS_EXCEL = {
    "data": "Data",
    "conta_contabil": "Conta Contábil",
    "valor": "Valor (R$)",
    "tipo": "Tipo",
    "historico": "Histórico",
    "filial": "Filial",
    "periodo": "Período",
}


def _texto_seguro_planilha(valor) -> str:
    texto = str(valor if valor is not None else "")
    return "'" + texto if texto.lstrip().startswith(("=", "+", "-", "@")) else texto


def exportar_lote_preparado(linhas: list[dict], formato: str) -> bytes:
    """Exporta dados conferidos em formato genérico, sem colunas internas."""
    if not linhas:
        raise ValueError("O lote não contém linhas para exportação.")
    if any(linha["status"] != "validado" for linha in linhas):
        raise ValueError("Resolva as pendências do lote antes de exportar.")
    if formato not in {"csv", "xlsx"}:
        raise ValueError("Formato de exportação inválido.")

    colunas = ["Data", "Descrição", "Valor", "Tipo", "Conta contábil", "Filial"]
    extras: list[str] = []
    tecnicas = {"id", "empresa_id", "sequencial_lote", "origem", "arquivo_origem", "criado_em"}
    for linha in linhas:
        for campo in linha["dados_brutos"]:
            if campo.casefold() not in tecnicas and campo not in extras:
                extras.append(campo)
    colunas.extend(f"Original: {campo}" for campo in extras)

    registros = []
    for linha in linhas:
        data = linha.get("data")
        valor = linha.get("valor")
        valor_decimal = Decimal(str(valor)).quantize(Decimal("0.01")) if valor is not None else None
        registro = {
            "Data": data.strftime("%d/%m/%Y") if data else "",
            "Descrição": _texto_seguro_planilha(linha.get("descricao")),
            "Valor": str(valor_decimal).replace(".", ",") if valor_decimal is not None else "",
            "Tipo": _texto_seguro_planilha(linha.get("tipo")),
            "Conta contábil": _texto_seguro_planilha(linha.get("conta_contabil")),
            "Filial": _texto_seguro_planilha(linha.get("filial")),
        }
        for campo in extras:
            registro[f"Original: {campo}"] = _texto_seguro_planilha(
                linha["dados_brutos"].get(campo, "")
            )
        registros.append(registro)

    if formato == "csv":
        saida = io.StringIO()
        escritor = csv.DictWriter(saida, fieldnames=colunas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(registros)
        return ("\ufeff" + saida.getvalue()).encode("utf-8")

    quadro = pd.DataFrame(registros, columns=colunas)
    saida_binaria = io.BytesIO()
    with pd.ExcelWriter(saida_binaria, engine="xlsxwriter") as escritor:
        quadro.to_excel(escritor, sheet_name="Dados preparados", index=False)
    return saida_binaria.getvalue()


def exportar_cruzamento_fontes(
    resultado: dict, fonte_1: list[dict], fonte_2: list[dict],
) -> bytes:
    """Exporta a revisão entre duas fontes com números de linha do arquivo."""
    por_id_1 = {int(linha["id"]): linha for linha in fonte_1}
    por_id_2 = {int(linha["id"]): linha for linha in fonte_2}
    colunas = [
        "Situação", "Linha fonte 1", "Linha fonte 2", "Data fonte 1",
        "Data fonte 2", "Descrição fonte 1", "Descrição fonte 2",
        "Valor fonte 1", "Valor fonte 2", "Diferença de dias",
    ]

    def data_exibida(linha: dict | None) -> str:
        if not linha or not linha.get("data"):
            return ""
        data = linha["data"]
        if hasattr(data, "strftime"):
            return data.strftime("%d/%m/%Y")
        return datetime.fromisoformat(str(data)).strftime("%d/%m/%Y")

    def valor_exibido(linha: dict | None) -> str:
        if not linha or linha.get("valor") is None:
            return ""
        return str(Decimal(str(linha["valor"])).quantize(Decimal("0.01"))).replace(".", ",")

    def registro(situacao: str, a: dict | None, b: dict | None, dias="") -> dict:
        return {
            "Situação": situacao,
            "Linha fonte 1": a.get("numero_linha", "") if a else "",
            "Linha fonte 2": b.get("numero_linha", "") if b else "",
            "Data fonte 1": data_exibida(a),
            "Data fonte 2": data_exibida(b),
            "Descrição fonte 1": _texto_seguro_planilha(a.get("descricao")) if a else "",
            "Descrição fonte 2": _texto_seguro_planilha(b.get("descricao")) if b else "",
            "Valor fonte 1": valor_exibido(a),
            "Valor fonte 2": valor_exibido(b),
            "Diferença de dias": dias,
        }

    registros = []
    for chave, situacao in (
        ("pares_confirmados", "Par exato"),
        ("candidatos", "Candidato para revisão"),
        ("divergencias_valor", "Diferença de valor"),
    ):
        for par in resultado[chave]:
            registros.append(registro(
                situacao, por_id_1[par["extrato_id"]],
                por_id_2[par["referencia_id"]], par.get("dias_diferenca", ""),
            ))
    registros.extend(
        registro("Sem correspondência na fonte 2", linha, None)
        for linha in resultado["faltantes_extrato"]
    )
    registros.extend(
        registro("Sem correspondência na fonte 1", None, linha)
        for linha in resultado["faltantes_referencia"]
    )

    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=colunas, delimiter=";")
    escritor.writeheader()
    escritor.writerows(registros)
    return ("\ufeff" + saida.getvalue()).encode("utf-8")

def exportar_excel(df: pd.DataFrame, titulo: str) -> bytes:
    """Gera um arquivo .xlsx em memória com formatação específica."""
    df = df.copy()

    # Converte data para DD/MM/AAAA
    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y")

    # Filtra colunas e renomeia cabeçalhos (lançamentos)
    if "conta_contabil" in df.columns:
        cols = [c for c in _COLUNAS_EXCEL if c in df.columns]
        df = df[cols]
        df.columns = [_CABECALHOS_EXCEL[c] for c in cols]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Relatorio', startrow=2, header=False, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Relatorio']

        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#DDEBF7', 'border': 1})
        currency_format = workbook.add_format({'num_format': 'R$ #,##0.00'})

        worksheet.write(0, 0, titulo, title_format)

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(2, col_num, value, header_format)

        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(idx, idx, max_len)
            if col == "Valor (R$)":
                worksheet.set_column(idx, idx, max_len, currency_format)

    return output.getvalue()

def exportar_pdf(dados: dict, tipo_relatorio: str, empresa: str, periodo: str) -> bytes:
    """Gera um relatório em PDF em memória."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    estilo_rodape = ParagraphStyle(
        'rodape',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor("#7A7870"),
        leading=10,
    )

    elements = []

    titulo = f"ContaView — Relatório de {tipo_relatorio.title()}"
    elements.append(Paragraph(titulo, styles['Heading1']))
    elements.append(Paragraph(f"Empresa: {empresa}", styles['Normal']))
    elements.append(Paragraph(f"Período: {periodo}", styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))

    df = pd.DataFrame()
    if tipo_relatorio == 'conciliacao' and 'df_relatorio' in dados:
        df = dados['df_relatorio'].copy()
    elif tipo_relatorio == 'auditoria' and 'df_oc' in dados:
        df = dados['df_oc'].copy()
    elif tipo_relatorio == 'lancamentos' and 'df' in dados:
        df = dados['df'].copy()

    if not df.empty:
        # Converte data para DD/MM/AAAA
        if "data" in df.columns:
            df["data"] = pd.to_datetime(df["data"]).dt.strftime("%d/%m/%Y")

        if len(df.columns) > 6:
            df = df.iloc[:, :6]

        data = [df.columns.to_list()] + df.values.tolist()

        table = Table(data, hAlign='LEFT')
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table.setStyle(style)
        elements.append(table)

    elements.append(Spacer(1, 0.5 * inch))

    elements.append(Paragraph(
        f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        estilo_rodape,
    ))

    doc.build(elements)

    return buffer.getvalue()
