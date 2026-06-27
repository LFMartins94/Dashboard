import reflex as rx


def alerta_auditoria(ocorrencia: dict) -> rx.Component:
    return rx.callout(
        ocorrencia["descricao"],
        color_scheme=rx.cond(
            ocorrencia["severidade"] == "alta",
            "red",
            rx.cond(ocorrencia["severidade"] == "media", "amber", "blue"),
        ),
        size="2",
    )
