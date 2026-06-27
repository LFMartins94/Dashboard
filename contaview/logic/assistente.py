import json
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI | None:
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        logger.warning("OPENAI_API_KEY não encontrada em os.getenv")
        try:
            import reflex as rx
            chave = rx.config.get("openai_api_key", "")
        except Exception:
            pass
    if not chave:
        logger.error(
            "OPENAI_API_KEY não configurada em nenhuma fonte. "
            "Verifique as secrets no painel da Reflex Cloud."
        )
        return None
    return OpenAI(api_key=chave)


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
    from contaview.logic.assistente_ferramentas import TOOL_SCHEMAS, MAP_FERRAMENTAS

    historico = [{"role": "system", "content": _SISTEMA}] + mensagens
    client = _get_client()
    if not client:
        return "Assistente indisponivel. Verifique a chave da API."

    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=historico,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        msg = resposta.choices[0].message

        if not msg.tool_calls:
            return msg.content or ""

        historico.append(msg)

        for tc in msg.tool_calls:
            nome = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            funcao = MAP_FERRAMENTAS.get(nome)
            if funcao:
                try:
                    resultado = funcao(**args)
                except Exception as exc:
                    resultado = {"erro": str(exc)}
            else:
                resultado = {"erro": f"Funcao '{nome}' desconhecida."}

            historico.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })

        resposta_final = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=historico,
            tools=TOOL_SCHEMAS,
            tool_choice="none",
        )
        return resposta_final.choices[0].message.content or ""

    except Exception as exc:
        logger.error("Erro ao chamar OpenAI: %s", exc)
        return "Nao foi possivel obter uma resposta. Tente novamente."


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
