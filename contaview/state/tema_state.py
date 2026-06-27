import reflex as rx


class TemaState(rx.State):
    tema_escuro: bool = False

    def alternar_tema(self):
        self.tema_escuro = not self.tema_escuro
        from contaview.state.dados_state import DadosState
        return DadosState.set_tema(self.tema_escuro)
