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
            rx.vstack(
                rx.callout(
                    DadosState.import_mensagem,
                    icon="check",
                    color_scheme="green",
                    width="100%",
                ),
                rx.link("Conferir dados preparados", href="/lancamentos"),
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


def _campo_mapeamento(titulo: str, valor, ao_alterar) -> rx.Component:
    return rx.vstack(
        rx.text(titulo, font_size="13px"),
        rx.select(
            DadosState.preparacao_opcoes,
            value=valor,
            on_change=ao_alterar,
            width="100%",
            style=_input_style(),
        ),
        width="100%",
        align="start",
        spacing="1",
    )


def _previa_preparacao() -> rx.Component:
    return rx.cond(
        DadosState.preparacao_cabecalhos,
        rx.vstack(
            rx.text("Conferir arquivo", font_size="18px", font_weight="600"),
            rx.text(DadosState.preparacao_nome_arquivo, font_size="13px"),
            rx.select(
                DadosState.preparacao_abas,
                value=DadosState.preparacao_aba,
                on_change=DadosState.set_preparacao_aba,
                width="100%",
                style=_input_style(),
            ),
            rx.hstack(
                rx.input(
                    placeholder="Linha do cabeçalho (0 = sem cabeçalho)",
                    value=DadosState.preparacao_linha_cabecalho,
                    on_change=DadosState.set_preparacao_linha_cabecalho,
                    width="250px",
                    style=_input_style(),
                ),
                rx.button(
                    "Aplicar cabeçalho", variant="soft",
                    on_click=DadosState.aplicar_linha_cabecalho,
                ),
                align="center",
            ),
            rx.text(
                "A prévia mostra até 15 linhas. As linhas de dados após o cabeçalho "
                "selecionado serão preservadas na preparação.",
                font_size="12px",
            ),
            rx.box(
                rx.data_table(
                    data=DadosState.preparacao_linhas_preview,
                    columns=DadosState.preparacao_cabecalhos,
                    pagination=True,
                ),
                width="100%",
                overflow_x="auto",
            ),
            rx.text("Tipo de documento", font_size="13px"),
            rx.select(
                ["Extrato bancário", "Folha de pagamento", "Notas", "Lançamentos", "Outro"],
                placeholder="Escolha o destino dos dados",
                value=DadosState.preparacao_tipo_documento,
                on_change=DadosState.set_preparacao_tipo_documento,
                width="100%",
                style=_input_style(),
            ),
            rx.input(
                placeholder="Período opcional (MM/AAAA)",
                value=DadosState.preparacao_periodo,
                on_change=DadosState.set_preparacao_periodo,
                width="100%",
                style=_input_style(),
            ),
            rx.text("Mapeamento de colunas", font_size="16px", font_weight="600"),
            rx.grid(
                _campo_mapeamento(
                    "Data", DadosState.preparacao_mapa_data,
                    DadosState.set_preparacao_mapa_data,
                ),
                _campo_mapeamento(
                    "Valor", DadosState.preparacao_mapa_valor,
                    DadosState.set_preparacao_mapa_valor,
                ),
                _campo_mapeamento(
                    "Descrição", DadosState.preparacao_mapa_descricao,
                    DadosState.set_preparacao_mapa_descricao,
                ),
                _campo_mapeamento(
                    "Tipo C/D", DadosState.preparacao_mapa_tipo,
                    DadosState.set_preparacao_mapa_tipo,
                ),
                _campo_mapeamento(
                    "Conta contábil", DadosState.preparacao_mapa_conta,
                    DadosState.set_preparacao_mapa_conta,
                ),
                _campo_mapeamento(
                    "Filial", DadosState.preparacao_mapa_filial,
                    DadosState.set_preparacao_mapa_filial,
                ),
                columns="2",
                gap="12px",
                width="100%",
            ),
            rx.hstack(
                rx.button(
                    "Cancelar",
                    variant="soft",
                    on_click=DadosState.cancelar_preparacao,
                ),
                rx.button(
                    "Salvar para conferência",
                    on_click=DadosState.confirmar_preparacao,
                ),
                justify="end",
                width="100%",
            ),
            width="100%",
            spacing="3",
            padding="16px",
            border="1px solid",
            border_color=rx.cond(
                TemaState.tema_escuro, ECLIPSE["border"], MINERAL["border"]
            ),
            border_radius="10px",
        ),
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
                        on_click=DadosState.cancelar_periodo_manual,
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
                    "Selecione a empresa e envie uma planilha para conferência.",
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
                            placeholder="Empresa obrigatória",
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
                                "ou arraste uma planilha XLSX, CSV ou XLS XML para cá",
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
                        id="planilha_importacao",
                        on_drop=DadosState.handle_upload_previa(
                            rx.upload_files(upload_id="planilha_importacao")
                        ),
                        accept={
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                            "text/csv": [".csv"],
                            "application/vnd.ms-excel": [".xls"],
                        },
                        max_files=1,
                        max_size=20 * 1024 * 1024,
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
                    spacing="4",
                    width="100%",
                    max_width="720px",
                ),
                _previa_preparacao(),
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
