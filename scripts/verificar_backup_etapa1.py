"""Compara o banco remoto com a restauração local da Etapa 1."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


RAIZ = Path(__file__).resolve().parents[1]
DUMP = RAIZ / "temp" / "etapa1" / "backup_public.dump"
RELATORIO = RAIZ / "docs" / "verificacao_backup_etapa1.md"
URL_LOCAL = "postgresql://postgres@127.0.0.1:55432/contaview_restore"


def coletar(url: str) -> dict[str, Any]:
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    with engine.connect() as conn:
        tabelas = list(
            conn.execute(
                text(
                    "select table_name from information_schema.tables "
                    "where table_schema='public' and table_type='BASE TABLE' order by table_name"
                )
            ).scalars()
        )
        contagens = {
            tabela: conn.execute(text(f'SELECT count(*) FROM public."{tabela}"')).scalar_one()
            for tabela in tabelas
        }
        colunas = {
            tabela: [
                tuple(linha)
                for linha in conn.execute(
                    text(
                        "select column_name, data_type, udt_name, is_nullable "
                        "from information_schema.columns where table_schema='public' "
                        "and table_name=:tabela order by ordinal_position"
                    ),
                    {"tabela": tabela},
                )
            ]
            for tabela in tabelas
        }
        indices = {
            tuple(linha)
            for linha in conn.execute(
                text(
                    "select tablename,indexname from pg_indexes "
                    "where schemaname='public' order by tablename,indexname"
                )
            )
        }
        gatilhos = {
            tuple(linha)
            for linha in conn.execute(
                text(
                    "select event_object_table,trigger_name,event_manipulation,action_timing "
                    "from information_schema.triggers where trigger_schema='public' "
                    "order by event_object_table,trigger_name,event_manipulation"
                )
            )
        }
        constraints = {
            tuple(tuple(valor) if isinstance(valor, list) else valor for valor in linha)
            for linha in conn.execute(
                text(
                    "select conrelid::regclass::text,conname,contype,convalidated,conkey, "
                    "confrelid::regclass::text,confkey,confupdtype,confdeltype "
                    "from pg_constraint where connamespace='public'::regnamespace "
                    "order by conrelid,conname"
                )
            )
        }
        rls = {
            tuple(linha)
            for linha in conn.execute(
                text(
                    "select c.relname,c.relrowsecurity,c.relforcerowsecurity "
                    "from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                    "where n.nspname='public' and c.relkind='r' order by c.relname"
                )
            )
        }
        politicas = conn.execute(
            text("select count(*) from pg_policies where schemaname='public'")
        ).scalar_one()
    engine.dispose()
    return {
        "tabelas": tabelas,
        "contagens": contagens,
        "colunas": colunas,
        "indices": indices,
        "gatilhos": gatilhos,
        "constraints": constraints,
        "rls": rls,
        "politicas": politicas,
    }


def gerar() -> None:
    load_dotenv(RAIZ / ".env", override=False)
    url_remota = os.getenv("DATABASE_URL")
    if not url_remota:
        raise SystemExit("DATABASE_URL não configurada")
    if not DUMP.exists():
        raise SystemExit(f"Dump não encontrado: {DUMP}")

    remoto = coletar(url_remota)
    local = coletar(URL_LOCAL)
    verificacoes = {
        "Tabelas": remoto["tabelas"] == local["tabelas"],
        "Totais de linhas": remoto["contagens"] == local["contagens"],
        "Colunas e tipos": remoto["colunas"] == local["colunas"],
        "Índices": remoto["indices"] == local["indices"],
        "Triggers": remoto["gatilhos"] == local["gatilhos"],
        "Constraints": remoto["constraints"] == local["constraints"],
        "Configuração RLS": remoto["rls"] == local["rls"],
        "Quantidade de políticas RLS": remoto["politicas"] == local["politicas"],
    }
    sucesso = all(verificacoes.values())
    hash_dump = hashlib.sha256(DUMP.read_bytes()).hexdigest()
    agora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    linhas = [
        "# Verificação do backup — Etapa 1",
        "",
        f"Executada em `{agora}`.",
        "",
        "## Procedimento",
        "",
        "1. O `pg_dump` 17.11 gerou um arquivo custom a partir do schema `public` do PostgreSQL remoto 17.6.",
        "2. Um PostgreSQL 17.11 portátil foi inicializado localmente em `127.0.0.1:55432`.",
        "3. O dump foi restaurado no banco isolado `contaview_restore`, dentro de uma única transação e com parada no primeiro erro.",
        "4. `ANALYZE` foi executado no banco restaurado.",
        "5. Estrutura e totais foram comparados com o banco remoto por consultas somente leitura.",
        "",
        "## Resultado",
        "",
        f"**{'Aprovado' if sucesso else 'Reprovado'}**",
        "",
        "| Verificação | Resultado |",
        "|---|:---:|",
    ]
    linhas.extend(
        f"| {nome} | {'OK' if resultado else 'DIVERGENTE'} |"
        for nome, resultado in verificacoes.items()
    )
    linhas.extend(
        [
            "",
            "## Totais conferidos",
            "",
            "| Tabela | Remoto | Restaurado |",
            "|---|---:|---:|",
        ]
    )
    linhas.extend(
        f"| `{tabela}` | {remoto['contagens'][tabela]} | {local['contagens'][tabela]} |"
        for tabela in remoto["tabelas"]
    )
    linhas.extend(
        [
            "",
            "## Artefato",
            "",
            f"- Arquivo local ignorado pelo Git: `{DUMP.relative_to(RAIZ)}`.",
            f"- Tamanho: `{DUMP.stat().st_size}` bytes.",
            f"- SHA-256: `{hash_dump}`.",
            "- O dump contém dados reais e deve permanecer fora do repositório.",
        ]
    )
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    if not sucesso:
        divergentes = [nome for nome, resultado in verificacoes.items() if not resultado]
        raise SystemExit(f"Restauração divergente: {', '.join(divergentes)}")
    print(f"Backup verificado com sucesso: {RELATORIO}")


if __name__ == "__main__":
    gerar()
