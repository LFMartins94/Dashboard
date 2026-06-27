import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.state.tema_state import TemaState
from contaview.state.dados_state import DadosState
from contaview.utils.auth import pagina_protegida
from contaview.styles import MINERAL, ECLIPSE


def _input_style() -> dict:
    return {
        "color": rx.cond(TemaState.tema_escuro, ECLIPSE["text_primary"], MINERAL["text_primary"]),
        "background_color": rx.cond(
            TemaState.tema_escuro,
            "#1E2530",
            "#FFFFFF",
        ),
        "border": rx.cond(
            TemaState.tema_escuro,
            "1px solid #3A4150",
            "1px solid #E0DDD5",
        ),
        "placeholder_color": rx.cond(
            TemaState.tema_escuro,
            ECLIPSE["text_secondary"],
            MINERAL["text_secondary"],
        ),
    }


def _feedback_importacao() -> rx.Component:
    return rx.vstack(
        rx.cond(
            DadosState.import_status == "sucesso",
            rx.callout(
                DadosState.import_mensagem,
                icon="check",
                color_scheme="green",
                width="100%",
            ),
        ),
        rx.cond(
            (DadosState.import_status == "sucesso") & DadosState.import_avisos,
            rx.callout(
                rx.vstack(
                    rx.foreach(
                        DadosState.import_avisos,
                        lambda msg: rx.text(msg, font_size="13px"),
                    ),
                    spacing="1",
                    width="100%",
                ),
                icon="info",
                color_scheme="blue",
                width="100%",
            ),
        ),
        rx.cond(
            DadosState.import_status == "erro",
            rx.callout(
                DadosState.import_mensagem,
                icon="triangle_alert",
                color_scheme="red",
                width="100%",
            ),
        ),
        spacing="2",
        width="100%",
    )


def _dialog_periodo_manual() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Periodo nao identificado"),
            rx.alert_dialog.description(
                "Nao foi possivel determinar o periodo contabil deste arquivo "
                "automaticamente. Informe o periodo manualmente no formato MM/AAAA."
            ),
            rx.input(
                placeholder="MM/AAAA (ex: 05/2026)",
                value=DadosState.periodo_manual_input,
                on_change=DadosState.set_periodo_manual_input,
                width="100%",
                style=_input_style(),
            ),
            rx.text(
                DadosState.import_mensagem,
                font_size="13px",
                color=rx.cond(
                    TemaState.tema_escuro, ECLIPSE.get("text_secondary"),
                    MINERAL.get("text_secondary"),
                ),
                margin_top="8px",
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancelar",
                        variant="soft",
                        on_click=DadosState.set_dialog_periodo_aberto,
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Confirmar periodo",
                        on_click=DadosState.definir_periodo_manual,
                    ),
                ),
                spacing="3",
                justify="end",
                margin_top="16px",
            ),
        ),
        open=DadosState.dialog_periodo_aberto,
    )


def _dialog_substituicao() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Período já existente"),
            rx.alert_dialog.description(
                "Já existem lançamentos para este período. "
                "Deseja substituir os dados existentes?"
            ),
            rx.flex(
                rx.alert_dialog.cancel(
                    rx.button(
                        "Cancelar",
                        variant="soft",
                        on_click=DadosState.cancelar_substituicao,
                    ),
                ),
                rx.alert_dialog.action(
                    rx.button(
                        "Substituir",
                        color_scheme="red",
                        on_click=DadosState.confirmar_substituicao,
                    ),
                ),
                spacing="3",
                justify="end",
            ),
        ),
        open=DadosState.alert_dialog_open,
    )


def importar() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.text(
                    "Importar",
                    font_size="22px",
                    font_weight="600",
                    color=rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["text_primary"],
                        MINERAL["text_primary"],
                    ),
                ),
                rx.text(
                    "Faça upload de arquivos .xlsx ou .csv com lançamentos contábeis.",
                    font_size="14px",
                    color=rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["text_secondary"],
                        MINERAL["text_secondary"],
                    ),
                    margin_bottom="16px",
                ),
                rx.vstack(
                    rx.cond(
                        DadosState.empresas_disponiveis,
                        rx.select(
                            DadosState.empresas_disponiveis,
                            placeholder="Selecione uma empresa",
                            value=DadosState.importar_empresa,
                            on_change=DadosState.set_importar_empresa,
                            width="100%",
                            style=_input_style(),
                        ),
                    ),
                    rx.cond(
                        DadosState.mostrar_nova_empresa,
                        rx.input(
                            placeholder="Nome da nova empresa",
                            value=DadosState.nova_empresa_nome,
                            on_change=DadosState.set_nova_empresa_nome,
                            width="100%",
                            style=_input_style(),
                        ),
                        rx.button(
                            "Nova empresa",
                            variant="ghost",
                            on_click=DadosState.toggle_nova_empresa,
                            width="100%",
                        ),
                    ),
                    rx.input(
                        placeholder="CNPJ (opcional)",
                        value=DadosState.importar_cnpj,
                        on_change=DadosState.set_importar_cnpj,
                        width="100%",
                        style=_input_style(),
                    ),
                    rx.upload(
                        rx.vstack(
                            rx.button(
                                "Selecionar arquivo",
                                type="button",
                                variant="soft",
                            ),
                            rx.text(
                                "ou arraste o arquivo .xlsx ou .csv para cá",
                                font_size="12px",
                                color=rx.cond(
                                    TemaState.tema_escuro,
                                    ECLIPSE["text_secondary"],
                                    MINERAL["text_secondary"],
                                ),
                            ),
                            spacing="2",
                            align="center",
                            padding="32px 16px",
                        ),
                        on_drop=DadosState.handle_upload_import,
                        accept={
                            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ".csv": "text/csv",
                        },
                        max_files=1,
                        multiple=False,
                        border="2px dashed",
                        border_color=rx.cond(
                            TemaState.tema_escuro,
                            ECLIPSE["border"],
                            MINERAL["border"],
                        ),
                        background_color=rx.cond(
                            TemaState.tema_escuro,
                            ECLIPSE["card_bg"],
                            MINERAL["card_bg"],
                        ),
                        border_radius="10px",
                        width="100%",
                    ),
                    _feedback_importacao(),
                    _dialog_substituicao(),
                    _dialog_periodo_manual(),
                    spacing="4",
                    width="100%",
                    max_width="500px",
                ),
                width="100%",
                height="100vh",
                padding="24px",
                background=rx.cond(
                    TemaState.tema_escuro,
                    ECLIPSE["content_bg"],
                    MINERAL["content_bg"],
                ),
                overflow_y="auto",
            ),
            spacing="0",
        ),
    )
