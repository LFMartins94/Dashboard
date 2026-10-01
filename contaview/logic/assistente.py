import json
import logging
import os
import re

from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI | None:
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        logger.error(
            "OPENAI_API_KEY não configurada em nenhuma fonte. "
            "Verifique as secrets no painel da Reflex Cloud."
        )
        return None
    return OpenAI(api_key=chave)


def _ocultar_documentos(texto: str) -> str:
    texto = re.sub(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[CPF oculto]", texto)
    texto = re.sub(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", "[CNPJ oculto]", texto)
    texto = re.sub(r"(?<!\d)\d{14}(?!\d)", "[CNPJ oculto]", texto)
    texto = re.sub(r"(?<!\d)\d{11}(?!\d)", "[CPF oculto]", texto)
    return texto


def _sanitizar_resultado_ferramenta(resultado):
    """Retira identificadores e registros nominais antes de voltar à IA."""
    if not isinstance(resultado, dict):
        return resultado
    seguro = {}
    for chave, valor in resultado.items():
        if chave.lower() in {"cpf", "cnpj", "nome", "razao_social"}:
            continue
        if chave == "lancamentos" and isinstance(valor, list):
            seguro["quantidade_lancamentos"] = len(valor)
            continue
        seguro[chave] = _sanitizar_resultado_ferramenta(valor) if isinstance(valor, dict) else valor
    return seguro


_SISTEMA = (
    "Você é uma assistente contábil especializada chamada ContaView. "
    "Responda sempre em português brasileiro. "
    "Você pode responder qualquer dúvida contábil, fiscal, tributária ou "
    "financeira, além de perguntas gerais. "
    "Seja objetiva, clara e profissional. "
    "Quando não souber algo, diga claramente que não sabe. "
    "Não invente legislação, normas ou valores."
)


def perguntar_ao_assistente(
    mensagens: list[dict], empresa_permitida: str | None = None,
    periodo_permitido: str | None = None,
) -> str:
    from contaview.logic.assistente_ferramentas import TOOL_SCHEMAS, MAP_FERRAMENTAS

    instrucao = _SISTEMA
    if empresa_permitida or periodo_permitido:
        instrucao += (
            f" Consulte somente a empresa '{empresa_permitida}' e a competência "
            f"'{periodo_permitido}'. Se a pergunta pedir outro contexto, informe que "
            "é necessário trocar o contexto de trabalho primeiro."
        )
    historico = [{"role": "system", "content": instrucao}] + [
        {**mensagem, "content": _ocultar_documentos(mensagem.get("content", ""))}
        for mensagem in mensagens
    ]
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
            empresa_pedida = args.get("empresa")
            periodo_pedido = args.get("periodo")
            contexto_bloqueado = (
                (empresa_permitida and empresa_pedida and empresa_pedida.strip().casefold() != empresa_permitida.strip().casefold())
                or (periodo_permitido and periodo_pedido and periodo_pedido not in {periodo_permitido, f"{periodo_permitido[5:]}/{periodo_permitido[:4]}"})
            )
            if contexto_bloqueado:
                resultado = {"erro": "Consulta fora do contexto de trabalho selecionado."}
            elif funcao:
                try:
                    resultado = funcao(**args)
                except Exception as exc:
                    resultado = {"erro": str(exc)}
            else:
                resultado = {"erro": f"Funcao '{nome}' desconhecida."}

            historico.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(_sanitizar_resultado_ferramenta(resultado), ensure_ascii=False),
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
    palavras = _ocultar_documentos(primeira_mensagem).strip().split()
    return " ".join(palavras[:5])[:80] or "Nova conversa"
