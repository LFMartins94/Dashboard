import reflex as rx
from contaview.components.sidebar import sidebar
from contaview.components.filtros import filtros
from contaview.state.tema_state import TemaState
from contaview.state.dados_state import DadosState
from contaview.utils.auth import pagina_protegida
from contaview.styles import MINERAL, ECLIPSE


def _campo_edicao(rotulo: str, valor, ao_alterar) -> rx.Component:
    return rx.vstack(
        rx.text(rotulo, font_size="13px"),
        rx.input(value=valor, on_change=ao_alterar, width="100%"),
        width="100%",
        align="start",
        spacing="1",
    )


def _dialog_edicao() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Corrigir linha preparada"),
            rx.text("Confira os valores com o arquivo de origem antes de salvar."),
            rx.grid(
                _campo_edicao(
                    "Data (DD/MM/AAAA)", DadosState.linha_edicao_data,
                    DadosState.set_linha_edicao_data,
                ),
                _campo_edicao(
                    "Valor", DadosState.linha_edicao_valor,
                    DadosState.set_linha_edicao_valor,
                ),
                _campo_edicao(
                    "Descrição", DadosState.linha_edicao_descricao,
                    DadosState.set_linha_edicao_descricao,
                ),
                _campo_edicao(
                    "Tipo C/D", DadosState.linha_edicao_tipo,
                    DadosState.set_linha_edicao_tipo,
                ),
                _campo_edicao(
                    "Conta contábil", DadosState.linha_edicao_conta,
                    DadosState.set_linha_edicao_conta,
                ),
                _campo_edicao(
                    "Filial", DadosState.linha_edicao_filial,
                    DadosState.set_linha_edicao_filial,
                ),
                columns="2",
                gap="12px",
                width="100%",
            ),
            rx.hstack(
                rx.button(
                    "Cancelar", variant="soft",
                    on_click=DadosState.cancelar_edicao_linha,
                ),
                rx.button("Salvar correção", on_click=DadosState.salvar_edicao_linha),
                justify="end",
                margin_top="16px",
                width="100%",
            ),
            max_width="640px",
        ),
        open=DadosState.linha_edicao_aberta,
    )


def _tabela_preparados() -> rx.Component:
    return rx.cond(
        DadosState.lote_selecionado_id > 0,
        rx.vstack(
            rx.hstack(
                rx.text("Linhas preparadas", font_size="18px", font_weight="600"),
                rx.spacer(),
                rx.button(
                    "Exportar CSV", variant="outline",
                    on_click=DadosState.exportar_lote_csv,
                ),
                rx.button(
                    "Exportar Excel", variant="outline",
                    on_click=DadosState.exportar_lote_xlsx,
                ),
                width="100%",
            ),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Linha"),
                            rx.table.column_header_cell("Data"),
                            rx.table.column_header_cell("Descrição"),
                            rx.table.column_header_cell("Valor"),
                            rx.table.column_header_cell("Tipo"),
                            rx.table.column_header_cell("Conta"),
                            rx.table.column_header_cell("Situação"),
                            rx.table.column_header_cell("Pendências"),
                            rx.table.column_header_cell("Ação"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DadosState.linhas_preparadas,
                            lambda linha: rx.table.row(
                                rx.table.cell(linha["numero_linha"]),
                                rx.table.cell(linha["data_exibicao"]),
                                rx.table.cell(linha["descricao"]),
                                rx.table.cell(linha["valor_exibicao"]),
                                rx.table.cell(linha["tipo"]),
                                rx.table.cell(linha["conta_contabil"]),
                                rx.table.cell(linha["status"]),
                                rx.table.cell(linha["pendencias_exibicao"]),
                                rx.table.cell(
                                    rx.button(
                                        "Corrigir", size="1", variant="soft",
                                        on_click=lambda: DadosState.abrir_edicao_linha(linha["id"]),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                width="100%",
                overflow_x="auto",
            ),
            rx.hstack(
                rx.button(
                    "Anterior", variant="soft",
                    on_click=DadosState.pagina_anterior_preparada,
                ),
                rx.text(DadosState.pagina_linhas_preparadas + 1),
                rx.button(
                    "Próxima", variant="soft",
                    on_click=DadosState.proxima_pagina_preparada,
                ),
                justify="end",
                width="100%",
            ),
            width="100%",
            spacing="3",
        ),
    )


def lancamentos() -> rx.Component:
    return pagina_protegida(
        rx.hstack(
            sidebar(),
            rx.vstack(
                rx.text(
                    "Dados preparados",
                    font_size="22px",
                    font_weight="600",
                    color=rx.cond(
                        TemaState.tema_escuro,
                        ECLIPSE["text_primary"],
                        MINERAL["text_primary"],
                    ),
                ),
                filtros(),
                rx.cond(
                    DadosState.erro_preparacao != "",
                    rx.callout(DadosState.erro_preparacao, color_scheme="red"),
                ),
                rx.text("Arquivos em conferência", font_size="18px", font_weight="600"),
                rx.cond(
                    DadosState.lotes_preparados,
                    rx.vstack(
                        rx.foreach(
                            DadosState.lotes_preparados,
                            lambda lote: rx.button(
                                rx.hstack(
                                    rx.text(lote["nome_arquivo"]),
                                    rx.text(lote["tipo_documento"]),
                                    rx.text(lote["periodo_exibicao"]),
                                    rx.text(lote["total_linhas"]),
                                    justify="between",
                                    width="100%",
                                ),
                                on_click=lambda: DadosState.selecionar_lote_preparacao(lote["id"]),
                                variant="outline",
                                width="100%",
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("Selecione uma empresa para ver seus arquivos preparados."),
                ),
                _tabela_preparados(),
                _dialog_edicao(),
                rx.text("Lançamentos classificados", font_size="18px", font_weight="600"),
                rx.cond(
                    DadosState.carregando,
                    rx.spinner(),
                    rx.data_table(
                        data=DadosState.lancamentos_tabela,
                        columns=DadosState.colunas_tabela,
                        pagination=True,
                        sort=True,
                    ),
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
