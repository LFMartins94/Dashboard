import logging

import google.generativeai as genai
import pandas as pd

from conciliacao import conciliar_partidas
from database import carregar_lancamentos, carregar_ocorrencias, listar_periodos

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração da API Gemini
# ---------------------------------------------------------------------------
_CHAVE_API = None

def _configurar_api():
    global _CHAVE_API
    if _CHAVE_API is not None:
        return
    try:
        import streamlit as st
        _CHAVE_API = st.secrets.get("LLM_API_KEY")
    except Exception:
        pass
    if not _CHAVE_API:
        import os
        _CHAVE_API = os.getenv("LLM_API_KEY")
    if _CHAVE_API:
        genai.configure(api_key=_CHAVE_API)
    else:
        logger.warning("LLM_API_KEY nao configurada.")


def _fmt_brl(valor: float) -> str:
    s = f"R$ {valor:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def montar_contexto_resumido(empresa_id: int, periodo: str, empresa_nome: str = None) -> str:
    """
    Monta resumo textual dos dados para enviar à IA.
    Nunca envia dados brutos — apenas agregados.
    """
    if not empresa_nome:
        from database import listar_empresas
        df_emp = listar_empresas()
        row = df_emp[df_emp["id"] == empresa_id]
        empresa_nome = row["nome"].iloc[0] if not row.empty else f"ID {empresa_id}"

    # Lançamentos
    df = carregar_lancamentos(empresa_id, periodo)
    if df.empty:
        return (
            f"Empresa: {empresa_nome} | Período: {periodo}\n"
            f"Nenhum lançamento encontrado para este período."
        )

    total_lancamentos = len(df)
    total_debitos = df[df["tipo"] == "D"]["valor"].sum()
    total_creditos = df[df["tipo"] == "C"]["valor"].sum()

    # Top 5 contas
    top5 = (
        df.groupby("conta_contabil")["valor"]
        .agg(lambda s: s.abs().sum())
        .sort_values(ascending=False)
        .head(5)
    )
    top5_str = ", ".join(
        f"{conta} ({_fmt_brl(valor)})"
        for conta, valor in top5.items()
    )

    # Ocorrências de auditoria
    ocorrencias_df = carregar_ocorrencias(empresa_id, periodo)
    if not ocorrencias_df.empty:
        alta = len(ocorrencias_df[ocorrencias_df["severidade"] == "alta"])
        media = len(ocorrencias_df[ocorrencias_df["severidade"] == "media"])
        baixa = len(ocorrencias_df[ocorrencias_df["severidade"] == "baixa"])
        auditoria_str = f"{alta} altas, {media} medias, {baixa} baixas"
    else:
        auditoria_str = "Nenhuma"

    # Conciliação
    try:
        conc_result = conciliar_partidas(df)
        conciliacao_str = (
            f"{conc_result['pares_ok']} pares OK, {conc_result['sem_par']} sem par"
        )
    except Exception:
        conciliacao_str = "Nao foi possivel calcular"

    linhas = [
        f"Empresa: {empresa_nome} | Periodo: {periodo}",
        f"Total de lancamentos: {total_lancamentos}",
        f"Total debitos: {_fmt_brl(total_debitos)} | Total creditos: {_fmt_brl(total_creditos)}",
    ]

    if not df.empty:
        linhas.append(f"Periodo contabil: de {df['data'].min()} a {df['data'].max()}")

    linhas.append(f"Top contas: {top5_str}")
    linhas.append(f"Auditoria: {auditoria_str}")
    linhas.append(f"Conciliacao: {conciliacao_str}")

    return "\n".join(linhas)


_SISTEMA = (
    "Voce e um assistente contabil especializado. Responda em portugues brasileiro. "
    "Seja objetivo e preciso. Baseie suas respostas apenas nos dados fornecidos. "
    "Nao invente valores ou informacoes que nao estejam no contexto."
)


def perguntar_ao_assistente(pergunta: str, contexto: str, historico: list) -> str:
    """
    Envia pergunta + contexto para o Gemini e retorna a resposta.
    historico: lista de dicts [{"role": "user"/"assistant", "content": str}]
    """
    _configurar_api()
    if not _CHAVE_API:
        return (
            "Chave da API nao configurada. "
            "Defina LLM_API_KEY no arquivo .env ou nos secrets do Streamlit."
        )

    try:
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        chat = model.start_chat(history=[])

        # Mensagem do sistema + contexto
        prompt_inicial = f"{_SISTEMA}\n\nContexto dos dados:\n{contexto}"
        chat.send_message(prompt_inicial)

        # Reenvia o histórico da conversa atual
        for msg in historico:
            chat.send_message(f"{msg['role']}: {msg['content']}")

        resposta = chat.send_message(pergunta)
        return resposta.text

    except Exception as exc:
        logger.error("Erro ao chamar Gemini API: %s", exc)
        return f"Erro ao consultar o assistente: {exc}"
