import io
from datetime import datetime
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def exportar_excel(df: pd.DataFrame, titulo: str) -> bytes:
    """Gera um arquivo .xlsx em memória com formatação específica."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Relatorio', startrow=2, header=False, index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['Relatorio']
        
        # Formatos
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#DDEBF7', 'border': 1})
        currency_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})

        # Título
        worksheet.write(0, 0, titulo, title_format)

        # Cabeçalho
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(2, col_num, value, header_format)
            
        # Aplica formatos e ajusta largura das colunas
        for idx, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(idx, idx, max_len)
            
            if pd.api.types.is_numeric_dtype(df[col]):
                 worksheet.set_column(idx, idx, max_len, currency_format)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                 worksheet.set_column(idx, idx, max_len, date_format)

    return output.getvalue()

def exportar_pdf(dados: dict, tipo_relatorio: str, empresa: str, periodo: str) -> bytes:
    """Gera um relatório em PDF em memória."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Título
    titulo = f"ContaView — Relatório de {tipo_relatorio.title()}"
    elements.append(Paragraph(titulo, styles['h1']))
    elements.append(Paragraph(f"Empresa: {empresa}", styles['Normal']))
    elements.append(Paragraph(f"Período: {periodo}", styles['Normal']))
    elements.append(Spacer(1, 0.25 * inch))

    # Tabela de dados
    df = pd.DataFrame()
    if tipo_relatorio == 'conciliacao' and 'df_relatorio' in dados:
        df = dados['df_relatorio']
    elif tipo_relatorio == 'auditoria' and 'df_oc' in dados:
        df = dados['df_oc']
    elif tipo_relatorio == 'lancamentos' and 'df' in dados:
        df = dados['df']

    if not df.empty:
        # Limita colunas para caber na página
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
    
    # Rodapé
    elements.append(Paragraph(f"Relatório gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['small']))

    doc.build(elements)
    
    return buffer.getvalue()
