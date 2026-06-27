def formatar_moeda(valor: float) -> str:
    s = f"R$ {valor:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
