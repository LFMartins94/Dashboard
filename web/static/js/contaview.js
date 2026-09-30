const raiz = document.documentElement;
const botaoTema = document.querySelector("#botao-tema");
const botaoMenu = document.querySelector("#botao-menu");
const barraLateral = document.querySelector("#barra-lateral");

function atualizarBotaoTema() {
    if (!botaoTema) return;
    const escuro = raiz.dataset.theme === "escuro";
    botaoTema.setAttribute("aria-pressed", String(escuro));
    botaoTema.querySelector("span").textContent = escuro ? "Modo claro" : "Modo escuro";
}

botaoTema?.addEventListener("click", () => {
    const proximo = raiz.dataset.theme === "escuro" ? "claro" : "escuro";
    raiz.dataset.theme = proximo;
    localStorage.setItem("contaview-tema", proximo);
    atualizarBotaoTema();
});

botaoMenu?.addEventListener("click", () => {
    const aberto = barraLateral?.classList.toggle("aberta") ?? false;
    botaoMenu.setAttribute("aria-expanded", String(aberto));
});

document.addEventListener("click", (evento) => {
    if (window.innerWidth > 760 || !barraLateral?.classList.contains("aberta")) return;
    if (!barraLateral.contains(evento.target) && !botaoMenu?.contains(evento.target)) {
        barraLateral.classList.remove("aberta");
        botaoMenu?.setAttribute("aria-expanded", "false");
    }
});

document.body.addEventListener("htmx:responseError", () => {
    const alvo = document.querySelector(".cabecalho-status");
    if (alvo) alvo.innerHTML = '<span class="status-sistema indisponivel"><span></span>Falha na atualização</span>';
});

atualizarBotaoTema();
