MINERAL = {
    "sidebar_bg": "#2C3540",
    "sidebar_text": "#8FA0AE",
    "sidebar_active": "#7EB8C4",
    "content_bg": "#F2F0EA",
    "card_bg": "#FFFFFF",
    "border": "#E0DDD5",
    "text_primary": "#1A1916",
    "text_secondary": "#7A7870",
    "accent": "#7EB8C4",
    "positive": "#2D8C5E",
    "negative": "#C94B3C",
    "warning": "#BA7517",
    "info": "#3A7DBF",
}

ECLIPSE = {
    "sidebar_bg": "#090B0F",
    "sidebar_text": "#4A5260",
    "sidebar_active": "#00C9A0",
    "content_bg": "#0F1117",
    "card_bg": "#161920",
    "border": "#1E2128",
    "text_primary": "#E8E8E8",
    "text_secondary": "#4A5260",
    "accent": "#00C9A0",
    "positive": "#00C9A0",
    "negative": "#FF6B5B",
    "warning": "#F0A840",
    "info": "#5BA8E8",
}


def cor(tema_escuro: bool, token: str) -> str:
    return (ECLIPSE if tema_escuro else MINERAL)[token]
