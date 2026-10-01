"""Marcadores usados pelos middlewares globais."""


def contexto_nao_obrigatorio(view_func):
    view_func.contexto_obrigatorio = False
    return view_func
