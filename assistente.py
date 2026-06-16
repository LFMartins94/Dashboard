import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    import streamlit as st
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


_SISTEMA = (
    "Você é uma assistente contábil especializada chamada ContaView. "
    "Responda sempre em português brasileiro. "
    "Você pode responder qualquer dúvida contábil, fiscal, tributária ou "
    "financeira, além de perguntas gerais. "
    "Seja objetiva, clara e profissional. "
    "Quando não souber algo, diga claramente que não sabe. "
    "Não invente legislação, normas ou valores."
)


def perguntar_ao_assistente(mensagens: list[dict]) -> str:
    historio_completo = [{"role": "system", "content": _SISTEMA}] + mensagens
    try:
        client = _get_client()
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=historio_completo,
        )
        return resposta.choices[0].message.content
    except Exception as exc:
        logger.error("Erro ao chamar OpenAI: %s", exc)
        return "Não foi possível obter uma resposta. Tente novamente."


def gerar_titulo_conversa(primeira_mensagem: str) -> str:
    prompt = (
        f"Gere um título curto (máximo 5 palavras) para uma conversa que começa com:"
        f" '{primeira_mensagem}'. Responda apenas o título, sem aspas."
    )
    try:
        client = _get_client()
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return resposta.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Erro ao gerar título: %s", exc)
        return primeira_mensagem[:40]
