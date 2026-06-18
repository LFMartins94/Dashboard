import io
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
    elements.append(Paragraph(titulo, styles['h1']))
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
