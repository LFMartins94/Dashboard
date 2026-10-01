"""Valores seguros compartilhados pelos templates."""


def contexto_requisicao(requisicao):
    return {
        "requisicao_id": getattr(requisicao, "id_requisicao", "indisponível"),
        "contexto_atual": getattr(requisicao, "contexto_trabalho", None),
    }
