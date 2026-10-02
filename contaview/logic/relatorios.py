import io
import csv
from decimal import Decimal
from datetime import datetime
import pandas as pd

from reportlab.lib.pagesizes import A4, landscape, letter
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

VERSAO_RELATORIOS = "1.0"
COLUNAS_TECNICAS = {
    "id", "empresa_id", "sequencial_lote", "origem", "arquivo_origem", "criado_em",
}


def _decimal(valor) -> Decimal:
    return Decimal(str(valor if valor is not None else 0)).quantize(Decimal("0.01"))


def calcular_balancete(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula débitos, créditos e saldo por conta contábil."""
    colunas = ["Conta contábil", "Débitos", "Créditos", "Saldo"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    obrigatorias = {"conta_contabil", "valor", "tipo"}
    if not obrigatorias.issubset(df.columns):
        raise ValueError("Não há colunas suficientes para calcular o balancete.")

    linhas = []
    for conta, grupo in df.groupby("conta_contabil", dropna=False):
        conta_exibida = str(conta or "").strip() or "Sem conta"
        debitos = sum(
            (_decimal(valor) for valor in grupo.loc[grupo["tipo"] == "D", "valor"]),
            Decimal("0.00"),
        )
        creditos = sum(
            (_decimal(valor) for valor in grupo.loc[grupo["tipo"] == "C", "valor"]),
            Decimal("0.00"),
        )
        linhas.append({
            "Conta contábil": conta_exibida,
            "Débitos": debitos,
            "Créditos": creditos,
            "Saldo": debitos - creditos,
        })
    return pd.DataFrame(linhas).sort_values("Conta contábil").reset_index(drop=True)


def calcular_dre(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula uma DRE determinística por prefixo de conta.

    Contas iniciadas por 3 são tratadas como receitas e contas iniciadas por
    4 como despesas. As demais ficam visíveis como não classificadas para não
    serem escondidas do usuário.
    """
    colunas = ["Natureza", "Conta contábil", "Movimento", "Resultado"]
    if df.empty:
        return pd.DataFrame(columns=colunas)
    obrigatorias = {"conta_contabil", "valor", "tipo"}
    if not obrigatorias.issubset(df.columns):
        raise ValueError("Não há colunas suficientes para calcular a DRE.")

    linhas = []
    for conta, grupo in df.groupby("conta_contabil", dropna=False):
        conta_exibida = str(conta or "").strip() or "Sem conta"
        if conta_exibida.startswith("3"):
            natureza = "Receita"
            resultado = sum(
                (_decimal(valor) for valor in grupo.loc[grupo["tipo"] == "C", "valor"]),
                Decimal("0.00"),
            ) - sum(
                (_decimal(valor) for valor in grupo.loc[grupo["tipo"] == "D", "valor"]),
                Decimal("0.00"),
            )
        elif conta_exibida.startswith("4"):
            natureza = "Despesa"
            resultado = sum(
                (_decimal(valor) for valor in grupo.loc[grupo["tipo"] == "D", "valor"]),
                Decimal("0.00"),
            ) - sum(
                (_decimal(valor) for valor in grupo.loc[grupo["tipo"] == "C", "valor"]),
                Decimal("0.00"),
            )
        else:
            natureza = "Não classificada"
            resultado = Decimal("0.00")
        movimento = sum((_decimal(valor) for valor in grupo["valor"]), Decimal("0.00"))
        linhas.append({
            "Natureza": natureza,
            "Conta contábil": conta_exibida,
            "Movimento": movimento,
            "Resultado": resultado,
        })
    return pd.DataFrame(linhas).sort_values(
        ["Natureza", "Conta contábil"]
    ).reset_index(drop=True)


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
    elif tipo_relatorio in {'balancete', 'dre'} and 'df' in dados:
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


def calcular_balancete_com_saldos(
    lancamentos_periodo: pd.DataFrame,
    lancamentos_anteriores: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Apura saldos por conta usando débito positivo e crédito negativo."""
    colunas = [
        "Conta contábil", "Saldo anterior", "Débitos", "Créditos", "Saldo final",
    ]
    obrigatorias = {"conta_contabil", "valor", "tipo"}
    anterior = lancamentos_anteriores if lancamentos_anteriores is not None else pd.DataFrame()
    for quadro in (lancamentos_periodo, anterior):
        if not quadro.empty and not obrigatorias.issubset(quadro.columns):
            raise ValueError("Não há colunas suficientes para calcular o balancete.")

    acumulados: dict[str, dict[str, Decimal]] = {}

    def acumular(quadro: pd.DataFrame, campo: str | None = None) -> None:
        if quadro.empty:
            return
        for linha in quadro.to_dict(orient="records"):
            conta = str(linha.get("conta_contabil") or "").strip() or "Sem conta"
            saldo = acumulados.setdefault(conta, {
                "Saldo anterior": Decimal("0.00"),
                "Débitos": Decimal("0.00"),
                "Créditos": Decimal("0.00"),
            })
            valor = _decimal(linha.get("valor"))
            tipo = str(linha.get("tipo") or "").upper()
            if campo:
                saldo[campo] += valor if tipo == "D" else -valor if tipo == "C" else Decimal("0.00")
            elif tipo == "D":
                saldo["Débitos"] += valor
            elif tipo == "C":
                saldo["Créditos"] += valor

    acumular(anterior, "Saldo anterior")
    acumular(lancamentos_periodo)
    linhas = []
    for conta, valores in sorted(acumulados.items()):
        saldo_final = valores["Saldo anterior"] + valores["Débitos"] - valores["Créditos"]
        linhas.append({"Conta contábil": conta, **valores, "Saldo final": saldo_final})
    return pd.DataFrame(linhas, columns=colunas)


def calcular_dre_classificada(
    lancamentos: pd.DataFrame, classificacoes: list[dict] | None = None,
) -> tuple[pd.DataFrame, Decimal]:
    """Agrupa DRE pelo plano confirmado e mantém contas sem classificação visíveis."""
    obrigatorias = {"conta_contabil", "valor", "tipo"}
    if not lancamentos.empty and not obrigatorias.issubset(lancamentos.columns):
        raise ValueError("Não há colunas suficientes para calcular a DRE.")
    regras = sorted(
        classificacoes or [], key=lambda item: len(str(item.get("prefixo_conta") or "")), reverse=True
    )
    grupos: dict[tuple[int, str, str], Decimal] = {}
    for linha in lancamentos.to_dict(orient="records"):
        conta = str(linha.get("conta_contabil") or "").strip()
        regra = next((item for item in regras if conta.startswith(str(item.get("prefixo_conta") or ""))), None)
        categoria = str(regra.get("categoria") if regra else "nao_classificada")
        grupo = str(regra.get("grupo") if regra else "Não classificado")
        ordem = int(regra.get("ordem") if regra else 9999)
        saldo_assinado = _decimal(linha.get("valor")) * (
            Decimal("1") if str(linha.get("tipo") or "").upper() == "C" else Decimal("-1")
        )
        fator = Decimal("-1") if categoria in {"custo", "despesa"} else Decimal("1")
        chave = (ordem, categoria, grupo)
        grupos[chave] = grupos.get(chave, Decimal("0.00")) + saldo_assinado * fator

    linhas = [
        {"Grupo": grupo, "Categoria": categoria.replace("_", " ").title(), "Valor": valor}
        for (_, categoria, grupo), valor in sorted(grupos.items())
    ]
    resultado = pd.DataFrame(linhas, columns=["Grupo", "Categoria", "Valor"])
    receitas = sum((valor for (_, categoria, _), valor in grupos.items() if categoria == "receita"), Decimal("0.00"))
    custos = sum((valor for (_, categoria, _), valor in grupos.items() if categoria == "custo"), Decimal("0.00"))
    despesas = sum((valor for (_, categoria, _), valor in grupos.items() if categoria == "despesa"), Decimal("0.00"))
    outros = sum((valor for (_, categoria, _), valor in grupos.items() if categoria == "outro"), Decimal("0.00"))
    return resultado, receitas - custos - despesas + outros


def exportar_planilha_relatorio(quadro: pd.DataFrame, titulo: str, aba: str = "Relatorio") -> bytes:
    """Gera planilha sem metadados internos e com colunas dimensionadas."""
    exibicao = quadro.copy()
    exibicao = exibicao[[coluna for coluna in exibicao.columns if coluna not in COLUNAS_TECNICAS]]
    saida = io.BytesIO()
    with pd.ExcelWriter(saida, engine="xlsxwriter") as escritor:
        exibicao.to_excel(escritor, sheet_name=aba[:31], startrow=2, index=False)
        planilha = escritor.sheets[aba[:31]]
        pasta = escritor.book
        formato_titulo = pasta.add_format({"bold": True, "font_size": 14})
        formato_cabecalho = pasta.add_format({"bold": True, "bg_color": "#DDE5DF", "border": 1})
        formato_monetario = pasta.add_format({"num_format": "R$ #,##0.00;[Red]-R$ #,##0.00"})
        planilha.write(0, 0, titulo, formato_titulo)
        for indice, coluna in enumerate(exibicao.columns):
            planilha.write(2, indice, coluna, formato_cabecalho)
            tamanho = len(str(coluna)) + 2
            if not exibicao.empty:
                tamanho = max(tamanho, max(len(str(valor)) for valor in exibicao[coluna].head(300)) + 2)
            formato = formato_monetario if coluna in {"Valor", "Débitos", "Créditos", "Saldo anterior", "Saldo final"} else None
            planilha.set_column(indice, indice, min(max(tamanho, 12), 44), formato)
        planilha.freeze_panes(3, 0)
    return saida.getvalue()


def exportar_pdf_relatorio(
    quadro: pd.DataFrame, titulo: str, empresa: str, periodo: str, nota: str = "",
) -> bytes:
    """Gera PDF em A4 horizontal com todas as colunas de negócio visíveis."""
    exibicao = quadro.copy()
    exibicao = exibicao[[coluna for coluna in exibicao.columns if coluna not in COLUNAS_TECNICAS]]
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    estilos = getSampleStyleSheet()
    estilo_nota = ParagraphStyle("nota_relatorio", parent=estilos["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#59655D"))
    elementos = [
        Paragraph(titulo, estilos["Heading1"]),
        Paragraph(f"Empresa: {empresa} &nbsp;&nbsp;&nbsp; Competência: {periodo}", estilos["BodyText"]),
    ]
    if nota:
        elementos.append(Paragraph(nota, estilo_nota))
    elementos.append(Spacer(1, 5 * mm))
    if exibicao.empty:
        elementos.append(Paragraph("Não há dados aprovados para este relatório.", estilos["BodyText"]))
    else:
        linhas = [[Paragraph(str(coluna), estilo_nota) for coluna in exibicao.columns]]
        linhas.extend([ [Paragraph(str(valor), estilo_nota) for valor in linha] for linha in exibicao.itertuples(index=False, name=None) ])
        largura = (landscape(A4)[0] - 24 * mm) / len(exibicao.columns)
        tabela = Table(linhas, colWidths=[largura] * len(exibicao.columns), repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334139")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD3CD")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elementos.append(tabela)
    elementos.extend([Spacer(1, 6 * mm), Paragraph(f"Versão de cálculo: {VERSAO_RELATORIOS}. Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_nota)])
    documento.build(elementos)
    return buffer.getvalue()
