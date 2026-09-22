import io
import hashlib
import logging
import os
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import BinaryIO

import pandas as pd

from contaview.logic.database import (
    obter_ou_criar_empresa,
    salvar_lancamentos,
    salvar_lote_preparacao,
    substituir_lancamentos_do_periodo,
    verificar_periodo_existente,
)
from contaview.logic.parsers import (
    inspecionar_planilha, ler_arquivo, limpar_dataframe,
    normalizar_colunas, resolver_datas_para_periodo,
)

logger = logging.getLogger(__name__)

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp")


def salvar_arquivo_temp(conteudo: bytes, nome_arquivo: str) -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    ext = os.path.splitext(nome_arquivo)[1] or ".tmp"
    nome_temp = f"{uuid.uuid4().hex}{ext}"
    caminho = os.path.join(TEMP_DIR, nome_temp)
    with open(caminho, "wb") as f:
        f.write(conteudo)
    logger.info("Arquivo temp salvo: %s", caminho)
    return caminho


def limpar_arquivo_temp(caminho: str):
    if not caminho:
        return
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
            logger.info("Arquivo temp removido: %s", caminho)
    except OSError:
        logger.warning("Nao foi possivel remover arquivo temp: %s", caminho)

COLUNAS_OBRIGATORIAS = ["data", "conta_contabil", "valor", "tipo"]


def _converter_valor_preparado(valor) -> Decimal | None:
    texto = str(valor if valor is not None else "").strip().replace("R$", "").replace(" ", "")
    if not texto:
        return None
    negativo_parenteses = texto.startswith("(") and texto.endswith(")")
    if negativo_parenteses:
        texto = texto[1:-1]
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".") if texto.rfind(",") > texto.rfind(".") else texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        convertido = Decimal(texto)
        if not convertido.is_finite():
            return None
        return (-convertido if negativo_parenteses else convertido).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _converter_data_preparada(valor, periodo: str | None) -> date | None:
    if isinstance(valor, (date, datetime, pd.Timestamp)) and not pd.isna(valor):
        data_convertida = pd.Timestamp(valor).date()
    else:
        texto = str(valor or "").strip()
        if not texto:
            return None
        if periodo:
            datas, invalidas = resolver_datas_para_periodo(pd.Series([texto]), periodo)
            return None if invalidas else datas.iloc[0]
        if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", texto):
            try:
                data_convertida = date.fromisoformat(texto)
            except ValueError:
                return None
        else:
            partes = re.fullmatch(r"(\d{1,2})[\/-](\d{1,2})[\/-](\d{2,4})", texto)
            if not partes:
                return None
            primeiro, segundo, ano = map(int, partes.groups())
            if ano < 100:
                ano += 2000
            if primeiro <= 12 and segundo <= 12 and primeiro != segundo:
                return None
            mes, dia = (primeiro, segundo) if segundo > 12 else (segundo, primeiro)
            try:
                data_convertida = date(ano, mes, dia)
            except ValueError:
                return None
    if periodo and data_convertida.strftime("%Y-%m") != periodo:
        return None
    return data_convertida


def preparar_linhas_mapeadas(
    linhas: list[dict], mapeamento: dict[str, str],
    tipo_documento: str, periodo: str | None,
) -> list[dict]:
    """Converte os campos escolhidos e preserva cada linha original."""
    preparadas: list[dict] = []
    for linha in linhas:
        brutos = linha["valores"]
        campo = lambda nome: brutos.get(mapeamento.get(nome, ""), "")
        valor_bruto = campo("valor")
        data_bruta = campo("data")
        valor = _converter_valor_preparado(valor_bruto)
        data_linha = _converter_data_preparada(data_bruta, periodo)
        descricao = str(campo("descricao") or "").strip()
        tipo_bruto = str(campo("tipo") or "").strip().upper()
        tipo = tipo_bruto if tipo_bruto in {"C", "D"} else None
        conta = str(campo("conta_contabil") or "").strip() or None
        filial = str(campo("filial") or "").strip() or None
        pendencias: list[str] = []

        if mapeamento.get("valor") and valor is None:
            pendencias.append("Valor não identificado ou inválido.")
        if mapeamento.get("data") and data_linha is None:
            pendencias.append("Data não identificada ou fora do período informado.")
        if tipo_documento in {"extrato", "lancamentos"}:
            if data_linha is None and not mapeamento.get("data"):
                pendencias.append("Coluna de data não mapeada.")
            if valor is None and not mapeamento.get("valor"):
                pendencias.append("Coluna de valor não mapeada.")
        if tipo_documento == "lancamentos":
            if not conta:
                pendencias.append("Conta contábil não informada.")
            if not tipo:
                pendencias.append("Tipo C/D não identificado.")

        preparadas.append({
            "numero_linha": linha["numero_linha"],
            "dados_brutos": brutos,
            "data": data_linha,
            "descricao": descricao,
            "valor": valor,
            "tipo": tipo,
            "conta_contabil": conta,
            "filial": filial,
            "status": "pendente" if pendencias else "validado",
            "pendencias": pendencias,
        })

    if tipo_documento in {"extrato", "lancamentos"}:
        grupos: dict[tuple, list[dict]] = {}
        for linha in preparadas:
            if linha["data"] is not None and linha["valor"] is not None:
                chave = (
                    linha["data"], linha["valor"],
                    linha["descricao"].casefold().strip(), linha["tipo"],
                )
                grupos.setdefault(chave, []).append(linha)
        for grupo in grupos.values():
            if len(grupo) > 1:
                for linha in grupo:
                    linha["pendencias"].append("Possível duplicidade no arquivo.")
                    linha["status"] = "pendente"
    return preparadas


def executar_preparacao(
    arquivo: BinaryIO, nome_empresa: str, cnpj_empresa: str | None,
    nome_aba: str, tipo_documento: str, periodo: str | None,
    mapeamento: dict[str, str], linha_cabecalho: int | None = None,
) -> dict:
    """Passagem obrigatória da prévia confirmada até o banco de preparação."""
    conteudo = arquivo.read()
    arquivo.seek(0)
    resultado = inspecionar_planilha(
        arquivo, linha_cabecalho=linha_cabecalho, aba_alvo=nome_aba
    )
    if not resultado["sucesso"]:
        return resultado
    aba = next((item for item in resultado["abas"] if item["nome"] == nome_aba), None)
    if aba is None:
        return {"sucesso": False, "erro": "Aba selecionada não encontrada no arquivo."}
    if not nome_empresa.strip():
        return {"sucesso": False, "erro": "Selecione ou cadastre a empresa."}
    if periodo and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", periodo):
        return {"sucesso": False, "erro": "Período inválido; use MM/AAAA."}
    if any(coluna not in aba["cabecalhos"] for coluna in mapeamento.values()):
        return {"sucesso": False, "erro": "O mapeamento contém colunas fora da aba selecionada."}
    if len(set(mapeamento.values())) != len(mapeamento):
        return {"sucesso": False, "erro": "Cada coluna deve ser mapeada para um único campo."}

    linhas = preparar_linhas_mapeadas(
        aba["linhas"], mapeamento, tipo_documento, periodo
    )
    empresa_id = obter_ou_criar_empresa(nome_empresa.strip(), cnpj_empresa)
    salvo = salvar_lote_preparacao(
        empresa_id, getattr(arquivo, "name", "arquivo"),
        hashlib.sha256(conteudo).hexdigest(), conteudo,
        nome_aba, tipo_documento, periodo,
        {"linha_cabecalho": aba["linha_cabecalho"], "colunas": mapeamento},
        linhas,
    )
    return {
        "sucesso": True,
        "empresa_id": empresa_id,
        "pendentes": sum(bool(linha["pendencias"]) for linha in linhas),
        **salvo,
    }


def prever_importacao(
    arquivo: BinaryIO, linha_cabecalho: int | None = None,
    aba_alvo: str | None = None,
) -> dict:
    """Exibe a estrutura antes de qualquer gravação contábil."""
    return inspecionar_planilha(arquivo, linha_cabecalho, aba_alvo)


def validar_edicao_linha(
    campos: dict[str, str], tipo_documento: str, periodo: str | None,
) -> tuple[dict, list[str]]:
    """Valida uma correção humana sem inferir datas ou valores ausentes."""
    data_texto = campos.get("data", "").strip()
    data_linha = None
    if data_texto:
        try:
            data_linha = datetime.strptime(data_texto, "%d/%m/%Y").date()
        except ValueError:
            pass
    valor_texto = campos.get("valor", "").strip()
    valor = _converter_valor_preparado(valor_texto)
    tipo_texto = campos.get("tipo", "").strip().upper()
    tipo = tipo_texto if tipo_texto in {"C", "D"} else None
    conta = campos.get("conta_contabil", "").strip() or None
    descricao = campos.get("descricao", "").strip()
    filial = campos.get("filial", "").strip() or None
    pendencias: list[str] = []

    if data_texto and data_linha is None:
        pendencias.append("Data inválida; use DD/MM/AAAA.")
    if periodo and data_linha and data_linha.strftime("%Y-%m") != periodo:
        pendencias.append("Data fora do período do lote.")
    if valor_texto and valor is None:
        pendencias.append("Valor inválido.")
    if tipo_texto and tipo is None:
        pendencias.append("Tipo inválido; use C ou D.")
    if tipo_documento in {"extrato", "lancamentos"}:
        if data_linha is None:
            pendencias.append("Data obrigatória.")
        if valor is None:
            pendencias.append("Valor obrigatório.")
    if tipo_documento == "lancamentos":
        if not conta:
            pendencias.append("Conta contábil obrigatória.")
        if not tipo:
            pendencias.append("Tipo C/D obrigatório.")

    return {
        "data": data_linha,
        "descricao": descricao,
        "valor": valor,
        "tipo": tipo,
        "conta_contabil": conta,
        "filial": filial,
    }, list(dict.fromkeys(pendencias))


def validar_pre_import(df: pd.DataFrame) -> dict:
    erros: list[str] = []
    if df.empty:
        erros.append("Nenhum lançamento válido foi identificado.")
    for coluna in COLUNAS_OBRIGATORIAS:
        if coluna not in df.columns:
            erros.append(f"Coluna obrigatoria ausente: '{coluna}'.")
        elif df[coluna].isna().all():
            erros.append(f"Coluna '{coluna}' esta completamente vazia.")
        elif df[coluna].isna().any():
            erros.append(f"Coluna '{coluna}' contém linhas sem valor; revise o arquivo.")

    if "data" in df.columns and "periodo" in df.columns:
        if df["periodo"].dropna().empty:
            erros.append("Nenhuma data valida encontrada para determinar o periodo.")
        elif df["periodo"].nunique(dropna=True) != 1:
            erros.append("O arquivo contém mais de um período; separe ou revise os dados.")

    if "tipo" in df.columns and df["tipo"].notna().any():
        if not df["tipo"].dropna().isin(["C", "D"]).all():
            erros.append("O campo 'tipo' deve conter apenas C ou D.")

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
    avisos: list[str] = resultado_leitura.get("avisos", [])

    # Se o periodo nao foi determinado (arquivo 100% ambíguo),
    # retorna flag para que a interface solicite o periodo manualmente
    if resultado_leitura.get("periodo_necessario"):
        return {
            "sucesso": False,
            "periodo_necessario": True,
            "df": resultado_leitura.get("df"),
            "avisos": avisos,
        }

    if not resultado_leitura["sucesso"]:
        return {
            "sucesso": False,
            "erro": resultado_leitura.get("motivo_falha", "Falha desconhecida ao ler arquivo."),
            "avisos": avisos,
        }

    if resultado_leitura.get("linhas_descartadas", 0):
        return {
            "sucesso": False,
            "erro": (
                f"{resultado_leitura['linhas_descartadas']} linha(s) não puderam "
                "ser interpretadas. Revise o arquivo antes de importar."
            ),
            "avisos": avisos,
        }

    df = resultado_leitura["df"]

    return _executar_dataframe(df, nome_empresa, cnpj_empresa, arquivo, avisos)


def executar_importacao_por_caminho(
    caminho: str, empresa_id: int | None = None, periodo: str | None = None,
) -> dict:
    return _executar_importacao_confirmada(caminho, empresa_id, periodo, None)


def executar_importacao_confirmada(
    caminho: str, empresa_id: int, periodo: str, nome_arquivo: str,
) -> dict:
    """Confirma uma substituição preservando o nome do arquivo de origem."""
    return _executar_importacao_confirmada(caminho, empresa_id, periodo, nome_arquivo)


def _executar_importacao_confirmada(
    caminho: str, empresa_id: int | None, periodo: str | None,
    nome_arquivo_original: str | None,
) -> dict:
    try:
        if not empresa_id or not periodo:
            return {"sucesso": False, "erro": "Empresa e período são obrigatórios para substituir dados."}

        if caminho.endswith(".pkl"):
            df = pd.read_pickle(caminho)
            nome_arquivo = nome_arquivo_original or os.path.basename(caminho[:-4])
            avisos = []
        else:
            with open(caminho, "rb") as f:
                conteudo = f.read()
            buf = io.BytesIO(conteudo)
            buf.name = os.path.basename(caminho)

            resultado_leitura = ler_arquivo(buf)
            if not resultado_leitura.get("sucesso"):
                return resultado_leitura
            if resultado_leitura.get("linhas_descartadas", 0):
                return {
                    "sucesso": False,
                    "erro": "O arquivo contém linhas não interpretadas; a substituição foi cancelada.",
                    "avisos": resultado_leitura.get("avisos", []),
                }
            df = resultado_leitura["df"]
            nome_arquivo = nome_arquivo_original or os.path.basename(caminho)
            avisos = resultado_leitura.get("avisos", [])

        quantidade_original = len(df)
        df = limpar_dataframe(normalizar_colunas(df))
        if len(df) != quantidade_original:
            return {
                "sucesso": False,
                "erro": "Há linhas descartadas na validação; a substituição foi cancelada.",
                "avisos": avisos,
            }
        validacao = validar_pre_import(df)
        if not validacao["valido"]:
            return {"sucesso": False, "erro": "; ".join(validacao["erros"]), "avisos": avisos}
        if df["periodo"].iloc[0] != periodo:
            return {"sucesso": False, "erro": "O período confirmado difere dos dados do arquivo.", "avisos": avisos}

        df = injetar_sequencial_lote(df)
        df = df.copy()
        df["arquivo_origem"] = nome_arquivo
        verificar_periodo_existente(empresa_id, periodo)
        registros = substituir_lancamentos_do_periodo(df, empresa_id, periodo)
        if registros != len(df):
            return {"sucesso": False, "erro": "A quantidade gravada difere da quantidade validada.", "avisos": avisos}
        return {
            "sucesso": True, "registros_salvos": registros,
            "empresa_id": empresa_id, "periodo": periodo,
            "df": df, "avisos": avisos,
        }
    except Exception as exc:
        logger.error("Erro ao importar por caminho %s: %s", caminho, exc)
        return {"sucesso": False, "erro": f"Erro ao ler arquivo: {exc}"}
    finally:
        limpar_arquivo_temp(caminho)


def executar_importacao_dataframe(
    df: pd.DataFrame,
    nome_empresa: str,
    cnpj_empresa: str = None,
    nome_arquivo: str = "arquivo",
    avisos: list[str] | None = None,
) -> dict:
    if avisos is None:
        avisos = []

    return _executar_dataframe(df, nome_empresa, cnpj_empresa, nome_arquivo, avisos)


def _executar_dataframe(
    df: pd.DataFrame,
    nome_empresa: str,
    cnpj_empresa: str | None,
    arquivo_origem,
    avisos: list[str],
) -> dict:
    quantidade_original = len(df)
    df = limpar_dataframe(normalizar_colunas(df))
    if len(df) != quantidade_original:
        return {
            "sucesso": False,
            "erro": "Há linhas descartadas na validação; revise o arquivo.",
            "avisos": avisos,
        }

    # b. Validar
    validacao = validar_pre_import(df)
    if not validacao["valido"]:
        return {"sucesso": False, "erro": "; ".join(validacao["erros"]), "avisos": avisos}

    # c. Injetar sequencial
    df = injetar_sequencial_lote(df)

    # d. Determinar periodo
    periodos = sorted(df["periodo"].dropna().unique())
    if not periodos:
        return {
            "sucesso": False,
            "erro": "Nenhum periodo valido encontrado nos dados.",
            "avisos": avisos,
        }
    periodo = periodos[0]

    # e. Obter ou criar empresa
    try:
        empresa_id = obter_ou_criar_empresa(nome_empresa, cnpj_empresa)
    except Exception as exc:
        logger.error("Erro ao obter/criar empresa '%s': %s", nome_empresa, exc)
        return {
            "sucesso": False,
            "erro": f"Erro ao identificar empresa: {exc}",
            "avisos": avisos,
        }

    # f. Verificar duplicidade
    try:
        periodo_existente = verificar_periodo_existente(empresa_id, periodo)
    except Exception as exc:
        logger.error("Erro ao verificar periodo: %s", exc)
        return {
            "sucesso": False,
            "erro": f"Erro ao verificar periodo: {exc}",
            "avisos": avisos,
        }

    if periodo_existente:
        return {
            "requer_confirmacao": True,
            "empresa_id": empresa_id,
            "periodo": periodo,
            "df": df,
            "avisos": avisos,
        }

    # g. Salvar
    return _salvar_com_origem(df, empresa_id, arquivo_origem, avisos)


def confirmar_substituicao(
    empresa_id: int, periodo: str, df: pd.DataFrame,
    avisos: list[str] | None = None,
) -> dict:
    if avisos is None:
        avisos = []
    validacao = validar_pre_import(df)
    if not validacao["valido"]:
        return {"sucesso": False, "erro": "; ".join(validacao["erros"]), "avisos": avisos}
    if "sequencial_lote" not in df.columns:
        df = injetar_sequencial_lote(df)
    try:
        verificar_periodo_existente(empresa_id, periodo)
        registros = substituir_lancamentos_do_periodo(df, empresa_id, periodo)
        return {
            "sucesso": True, "registros_salvos": registros,
            "empresa_id": empresa_id, "periodo": periodo,
            "df": df, "avisos": avisos,
        }
    except Exception as exc:
        logger.error("Erro ao substituir período %s: %s", periodo, exc)
        return {"sucesso": False, "erro": f"Erro ao substituir período: {exc}", "avisos": avisos}


def _salvar(df: pd.DataFrame, empresa_id: int, avisos: list[str] | None = None) -> dict:
    if avisos is None:
        avisos = []
    try:
        registros = salvar_lancamentos(df, empresa_id)
        if registros != len(df) or registros == 0:
            raise RuntimeError("A gravação não confirmou todos os lançamentos do lote.")
        periodo = df["periodo"].iloc[0] if "periodo" in df.columns and not df["periodo"].empty else None
        return {
            "sucesso": True,
            "registros_salvos": registros,
            "empresa_id": empresa_id,
            "periodo": periodo,
            "df": df,
            "avisos": avisos,
        }
    except Exception as exc:
        logger.error("Erro ao salvar lancamentos: %s", exc)
        return {"sucesso": False, "erro": f"Erro ao salvar lancamentos: {exc}", "avisos": avisos}


def _salvar_com_origem(
    df: pd.DataFrame, empresa_id: int, arquivo: BinaryIO | str,
    avisos: list[str] | None = None,
) -> dict:
    if avisos is None:
        avisos = []
    nome_arquivo = (
        arquivo if isinstance(arquivo, str) else getattr(arquivo, "name", "arquivo")
    )
    df = df.copy()
    df["arquivo_origem"] = nome_arquivo
    return _salvar(df, empresa_id, avisos)
