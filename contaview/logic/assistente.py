"""Chamada isolada ao modelo de linguagem, sem acesso direto ao banco."""

from __future__ import annotations

import logging
import os
import re

from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI | None:
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        logger.error("OPENAI_API_KEY não configurada.")
        return None
    return OpenAI(api_key=chave)


def sanitizar_texto_assistente(texto: str) -> str:
    """Oculta identificadores e referências nominais antes de persistir ou enviar."""
    seguro = texto or ""
    seguro = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[CPF oculto]", seguro)
    seguro = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", "[CNPJ oculto]", seguro)
    seguro = re.sub(r"(?<!\d)\d{14}(?!\d)", "[CNPJ oculto]", seguro)
    seguro = re.sub(r"(?<!\d)\d{11}(?!\d)", "[CPF oculto]", seguro)
    seguro = re.sub(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", "[e-mail oculto]", seguro)
    seguro = re.sub(
        r"(?i)\b(cliente|fornecedor|favorecido|funcion[áa]rio|colaborador)"
        r"\s*[:=-]?\s+([A-ZÀ-ÖØ-Ý][\wÀ-ÖØ-öø-ÿ'’-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÖØ-öø-ÿ'’-]*){0,3})",
        r"\1 [terceiro oculto]",
        seguro,
    )
    return re.sub(
        r"\b(?:[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ'’-]{1,}(?:\s+(?:da|de|do|das|dos))?\s+){1,3}"
        r"[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ'’-]{1,}\b",
        "[terceiro oculto]",
        seguro,
    )


_SISTEMA = (
    "Você é a assistente contábil ContaView. Responda em português brasileiro, "
    "de forma objetiva e profissional. Não invente legislação, normas ou valores. "
    "Nunca execute alterações, aprovações ou decisões contábeis."
)


def perguntar_ao_assistente(
    mensagens: list[dict],
    empresa_permitida: str | None = None,
    periodo_permitido: str | None = None,
    dados_consulta: dict | None = None,
) -> str:
    """Responde usando apenas o resumo agregado que o serviço já autorizou."""
    instrucao = _SISTEMA
    if empresa_permitida or periodo_permitido:
        instrucao += (
            " O contexto de trabalho é restrito à empresa e competência já "
            "selecionadas; solicite a troca do contexto para qualquer outro caso."
        )
    if dados_consulta is not None:
        instrucao += (
            " Use exclusivamente os dados agregados autorizados abaixo para perguntas "
            "sobre registros. Se uma fonte indicar ausência de dados, informe isso e não "
            "estime totais. Cite a origem dos números na resposta. Dados autorizados: "
            f"{dados_consulta!r}"
        )
    else:
        instrucao += (
            " Nenhum dado contábil foi autorizado nesta conversa. Para valores ou "
            "registros, informe que é necessário selecionar um contexto com dados."
        )
    historico = [{"role": "system", "content": instrucao}] + [
        {**mensagem, "content": sanitizar_texto_assistente(mensagem.get("content", ""))}
        for mensagem in mensagens
        if mensagem.get("role") in {"user", "assistant"}
    ]
    client = _get_client()
    if not client:
        return "Assistente indisponível. Verifique a configuração da chave de acesso."

    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=historico,
        )
        return resposta.choices[0].message.content or ""
    except Exception:
        logger.exception("Erro ao chamar o Assistente")
        return "Não foi possível obter uma resposta agora. Tente novamente em instantes."


def gerar_titulo_conversa(primeira_mensagem: str) -> str:
    palavras = sanitizar_texto_assistente(primeira_mensagem).strip().split()
    return " ".join(palavras[:5])[:80] or "Nova conversa"
