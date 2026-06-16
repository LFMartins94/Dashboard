import streamlit as st


def verificar_login(usuario: str, senha: str) -> bool:
    usuario_valido = st.secrets.get("APP_USUARIO", "")
    senha_valida = st.secrets.get("APP_SENHA", "")
    return usuario == usuario_valido and senha == senha_valida


def logout() -> None:
    st.session_state.pop("autenticado", None)
    st.session_state.pop("usuario", None)
    st.rerun()


def exibir_tela_login() -> None:
    st.markdown(
        """
        <style>
        .stApp { background-color: #F2F0EA; }
        .login-box {
            max-width: 360px;
            margin: 80px auto 0;
            padding: 40px 32px;
            background: #FFFFFF;
            border-radius: 10px;
            border: 1px solid #E0DDD5;
        }
        .login-box h1 {
            font-size: 28px;
            font-weight: 700;
            color: #1A1916;
            text-align: center;
            margin-bottom: 4px;
        }
        .login-box p {
            font-size: 14px;
            color: #7A7870;
            text-align: center;
            margin-bottom: 24px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("<h1>ContaView</h1>", unsafe_allow_html=True)
    st.markdown("<p>Acesso restrito</p>", unsafe_allow_html=True)

    usuario = st.text_input("Usuário", key="login_usuario")
    senha = st.text_input("Senha", type="password", key="login_senha")

    if st.button("Entrar", type="primary", use_container_width=True):
        if verificar_login(usuario, senha):
            st.session_state.autenticado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

    st.markdown("</div>", unsafe_allow_html=True)
