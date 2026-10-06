"""Confere, somente em leitura, as migrações e o RLS do corte Django."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from configurar_ambiente_railway import url_direta_supabase


RAIZ = Path(__file__).resolve().parents[1]
MIGRACOES_NUCLEO = {f"000{numero}_" for numero in range(1, 10)}
TABELAS_PROTEGIDAS = (
    "django_tentativas_login",
    "django_competencias_trabalho",
    "django_itens_checklist_trabalho",
    "django_arquivos_entrada_temporarios",
    "django_modelos_mapeamento_entrada",
    "django_revisoes_conciliacao",
    "django_estados_ocorrencias_auditoria",
    "django_classificacoes_dre",
    "django_perfis_exportacao",
    "django_geracoes_relatorios",
    "django_modelos_documentos_esperados",
    "django_perfis_origem_entrada",
    "django_tarefas_automacao",
    "django_registros_consultas_assistente",
)


def principal() -> None:
    load_dotenv(RAIZ / ".env")
    url_local = os.getenv("DATABASE_URL", "")
    if not url_local:
        raise SystemExit("DATABASE_URL não foi encontrada no arquivo .env.")

    motor = create_engine(url_direta_supabase(url_local), connect_args={"connect_timeout": 10})
    nomes_sql = ", ".join(f"'{nome}'" for nome in TABELAS_PROTEGIDAS)
    with motor.connect() as conexao:
        aplicadas = {
            linha[0]
            for linha in conexao.execute(
                text("SELECT name FROM django_migrations WHERE app = 'nucleo'")
            )
        }
        tabelas = {
            linha[0]: linha[1]
            for linha in conexao.execute(
                text(
                    "SELECT tablename, rowsecurity FROM pg_tables "
                    f"WHERE schemaname = 'public' AND tablename IN ({nomes_sql})"
                )
            )
        }

    faltam_migracoes = sorted(
        prefixo for prefixo in MIGRACOES_NUCLEO if not any(nome.startswith(prefixo) for nome in aplicadas)
    )
    faltam_tabelas = sorted(set(TABELAS_PROTEGIDAS) - set(tabelas))
    rls_desativado = sorted(nome for nome, ativo in tabelas.items() if not ativo)
    if faltam_migracoes or faltam_tabelas or rls_desativado:
        if faltam_migracoes:
            print("Migrações ausentes:", ", ".join(faltam_migracoes))
        if faltam_tabelas:
            print("Tabelas ausentes:", ", ".join(faltam_tabelas))
        if rls_desativado:
            print("RLS desativado:", ", ".join(rls_desativado))
        raise SystemExit("A verificação de corte falhou.")

    print(f"Migrações do núcleo confirmadas: {len(aplicadas)}")
    print(f"Tabelas protegidas com RLS confirmado: {len(tabelas)}")


if __name__ == "__main__":
    principal()
