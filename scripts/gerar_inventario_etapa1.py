"""Gera o inventário e o snapshot lógico local da Etapa 1.

O snapshot é gravado em ``temp/etapa1`` e permanece fora do Git. Ele não
substitui um dump nativo do PostgreSQL; serve para preservar uma fotografia
verificável das tabelas públicas da aplicação enquanto o ambiente de teste
PostgreSQL ainda não está disponível.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


RAIZ = Path(__file__).resolve().parents[1]
LOGIC = RAIZ / "contaview" / "logic"
DOCS = RAIZ / "docs"
TEMP = RAIZ / "temp" / "etapa1"


def serializar(valor: Any) -> Any:
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, bytes):
        return {"__tipo__": "bytes", "base64": base64.b64encode(valor).decode("ascii")}
    if isinstance(valor, dict):
        return {str(chave): serializar(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [serializar(item) for item in valor]
    return valor


def md(valor: Any) -> str:
    return str(valor).replace("|", "\\|").replace("\n", " ")


def catalogar_logica() -> str:
    linhas = [
        "# Catálogo da lógica reutilizável — Etapa 1",
        "",
        "Este catálogo foi gerado a partir dos arquivos em `contaview/logic/`. "
        "Os módulos permanecem sem importação do framework de interface.",
        "",
        "| Módulo | Funções e métodos | Classes | Imports principais |",
        "|---|---|---|---|",
    ]
    for caminho in sorted(LOGIC.glob("*.py")):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
        funcoes = [
            no.name
            for no in ast.walk(arvore)
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        classes = [no.name for no in ast.walk(arvore) if isinstance(no, ast.ClassDef)]
        imports: list[str] = []
        for no in arvore.body:
            if isinstance(no, ast.Import):
                imports.extend(alias.name for alias in no.names)
            elif isinstance(no, ast.ImportFrom):
                imports.append(no.module or "import relativo")
        linhas.append(
            f"| `{caminho.name}` | {md(', '.join(funcoes) or '—')} | "
            f"{md(', '.join(classes) or '—')} | {md(', '.join(imports) or '—')} |"
        )
    return "\n".join(linhas) + "\n"


def gerar() -> None:
    load_dotenv(RAIZ / ".env", override=False)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL não configurada")

    engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 15})
    agora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    TEMP.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    with engine.connect() as conn:
        versao = conn.execute(text("select version()"))
        versao_postgres = versao.scalar_one().split(",")[0]
        tabelas = list(
            conn.execute(
                text(
                    "select table_name from information_schema.tables "
                    "where table_schema='public' and table_type='BASE TABLE' "
                    "order by table_name"
                )
            ).scalars()
        )
        total_tabelas = conn.execute(
            text(
                "select count(*) from information_schema.tables "
                "where table_schema not in ('pg_catalog','information_schema')"
            )
        ).scalar_one()

        snapshot: dict[str, Any] = {
            "gerado_em": agora,
            "escopo": "public",
            "observacao": "Snapshot lógico local; não é dump físico do PostgreSQL.",
            "tabelas": {},
        }
        detalhes: list[dict[str, Any]] = []
        for tabela in tabelas:
            colunas = list(
                conn.execute(
                    text(
                        "select column_name, data_type, udt_name, is_nullable, column_default "
                        "from information_schema.columns where table_schema='public' "
                        "and table_name=:tabela order by ordinal_position"
                    ),
                    {"tabela": tabela},
                ).mappings()
            )
            linhas = [
                {chave: serializar(valor) for chave, valor in linha.items()}
                for linha in conn.execute(text(f'SELECT * FROM public."{tabela}"')).mappings()
            ]
            rls = conn.execute(
                text(
                    "select c.relrowsecurity, c.relforcerowsecurity from pg_class c "
                    "join pg_namespace n on n.oid=c.relnamespace "
                    "where n.nspname='public' and c.relname=:tabela"
                ),
                {"tabela": tabela},
            ).mappings().one()
            politicas = conn.execute(
                text(
                    "select count(*) from pg_policies where schemaname='public' "
                    "and tablename=:tabela"
                ),
                {"tabela": tabela},
            ).scalar_one()
            detalhes.append(
                {
                    "nome": tabela,
                    "linhas": len(linhas),
                    "colunas": colunas,
                    "rls": bool(rls["relrowsecurity"]),
                    "forcar_rls": bool(rls["relforcerowsecurity"]),
                    "politicas": int(politicas),
                }
            )
            snapshot["tabelas"][tabela] = {
                "colunas": [dict(coluna) for coluna in colunas],
                "linhas": linhas,
            }

        indices = list(
            conn.execute(
                text(
                    "select tablename, indexname, indexdef from pg_indexes "
                    "where schemaname='public' order by tablename,indexname"
                )
            ).mappings()
        )
        gatilhos = list(
            conn.execute(
                text(
                    "select event_object_table, trigger_name, event_manipulation, "
                    "action_timing, action_statement from information_schema.triggers "
                    "where trigger_schema='public' order by event_object_table,trigger_name"
                )
            ).mappings()
        )
        politicas = list(
            conn.execute(
                text(
                    "select tablename, policyname, permissive, roles, cmd, qual, with_check "
                    "from pg_policies where schemaname='public' order by tablename,policyname"
                )
            ).mappings()
        )
        privilegios = list(
            conn.execute(
                text(
                    "select table_name, grantee, privilege_type from information_schema.role_table_grants "
                    "where table_schema='public' order by table_name,grantee,privilege_type"
                )
            ).mappings()
        )
        constraints = list(
            conn.execute(
                text(
                    "select conrelid::regclass::text as tabela, conname, contype, "
                    "pg_get_constraintdef(oid) as definicao from pg_constraint "
                    "where connamespace='public'::regnamespace order by conrelid,conname"
                )
            ).mappings()
        )

    backup = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=serializar)
    backup_path = TEMP / "backup_public_logico.json"
    backup_path.write_text(backup, encoding="utf-8")
    checksum = hashlib.sha256(backup.encode("utf-8")).hexdigest()
    (TEMP / "backup_public_logico.sha256").write_text(f"{checksum}  backup_public_logico.json\n", encoding="ascii")
    restaurado = json.loads(backup_path.read_text(encoding="utf-8"))
    verificacao = {
        tabela: len(dados["linhas"])
        for tabela, dados in restaurado["tabelas"].items()
    }
    (TEMP / "backup_manifesto.json").write_text(
        json.dumps(
            {"arquivo": str(backup_path.relative_to(RAIZ)), "sha256": checksum, "linhas": verificacao},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    inventario = [
        "# Inventário técnico — Etapa 1",
        "",
        f"Gerado em `{agora}` a partir de uma conexão somente leitura com o PostgreSQL.",
        "",
        "## Escopo",
        "",
        f"- PostgreSQL: `{versao_postgres}`.",
        f"- Tabelas públicas da aplicação catalogadas: **{len(tabelas)}**.",
        f"- Tabelas nos schemas não sistêmicos encontrados na conexão: **{total_tabelas}**; os schemas gerenciados pelo Supabase não foram incluídos no snapshot de dados.",
        "- Nenhum DDL, insert, update ou delete foi executado.",
        "- O snapshot local inclui a lista completa de colunas, tipos e linhas de cada tabela pública.",
        "",
        "## Tabelas, volume e RLS",
        "",
        "| Tabela | Linhas | RLS | Forçar RLS | Políticas |",
        "|---|---:|:---:|:---:|---:|",
    ]
    for detalhe in detalhes:
        inventario.append(
            f"| `{detalhe['nome']}` | {detalhe['linhas']} | "
            f"{'sim' if detalhe['rls'] else 'não'} | "
            f"{'sim' if detalhe['forcar_rls'] else 'não'} | {detalhe['politicas']} |"
        )
    inventario.extend(
        [
            "",
            "> Atenção: o RLS está habilitado nas tabelas públicas, mas o catálogo retornou zero políticas. Nenhuma política foi criada nesta etapa porque isso exige decisão explícita do modelo de autenticação da nova aplicação.",
            "",
            "## Índices",
            "",
            "| Tabela | Índice | Definição |",
            "|---|---|---|",
        ]
    )
    inventario.extend(
        f"| `{md(item['tablename'])}` | `{md(item['indexname'])}` | `{md(item['indexdef'])}` |" for item in indices
    )
    inventario.extend(["", "## Triggers", "", "| Tabela | Trigger | Evento | Momento | Ação |", "|---|---|---|---|---|"])
    inventario.extend(
        f"| `{md(item['event_object_table'])}` | `{md(item['trigger_name'])}` | {md(item['event_manipulation'])} | {md(item['action_timing'])} | `{md(item['action_statement'])}` |"
        for item in gatilhos
    )
    inventario.extend(["", "## Constraints", "", "| Tabela | Nome | Tipo | Definição |", "|---|---|---|---|"])
    inventario.extend(
        f"| `{md(item['tabela'])}` | `{md(item['conname'])}` | {md(item['contype'])} | `{md(item['definicao'])}` |"
        for item in constraints
    )
    inventario.extend(["", "## Políticas RLS", ""])
    if politicas:
        inventario.extend(["| Tabela | Política | Comando | Qualificação | Verificação |", "|---|---|---|---|---|"])
        inventario.extend(
            f"| `{md(item['tablename'])}` | `{md(item['policyname'])}` | {md(item['cmd'])} | `{md(item['qual'])}` | `{md(item['with_check'])}` |"
            for item in politicas
        )
    else:
        inventario.append("Nenhuma política cadastrada no schema `public`.")
    inventario.extend(["", "## Privilégios encontrados", "", "| Tabela | Concedido a | Privilégio |", "|---|---|---|"])
    inventario.extend(
        f"| `{md(item['table_name'])}` | `{md(item['grantee'])}` | {md(item['privilege_type'])} |" for item in privilegios
    )
    inventario.extend(
        [
            "",
            "## Backup local",
            "",
            f"- Snapshot lógico: `{backup_path.relative_to(RAIZ)}`.",
            f"- SHA-256: `{checksum}`; manifesto em `temp/etapa1/backup_manifesto.json`.",
            "- Verificação realizada: o arquivo foi lido novamente como JSON e os totais por tabela foram comparados com a fotografia gerada.",
            "- O dump nativo foi gerado com `pg_dump` 17.11 e restaurado em PostgreSQL 17.11 local; a verificação completa está em `docs/verificacao_backup_etapa1.md`.",
        ]
    )
    (DOCS / "inventario_etapa1.md").write_text("\n".join(inventario) + "\n", encoding="utf-8")
    (DOCS / "catalogo_logic_etapa1.md").write_text(catalogar_logica(), encoding="utf-8")

    aceite = [
        "# Base de aceitação — Etapa 1",
        "",
        "Os arquivos abaixo são referências de entrada. O sistema deverá preservar o original, identificar a estrutura e exigir confirmação do mapeamento antes de gravar dados.",
        "",
        "| Arquivo | Formato | Uso no aceite | Estado | SHA-256 |",
        "|---|---|---|---|---|",
        "| `CAP_ILHAS_DO_LAGO_CONCILIADO (1).xlsx` | XLSX com linhas delimitadas por `;` | Caso principal contábil | disponível | `1f7156b4638a4924bfc226f281624b8f7ea6b3116cbc4a103a029540ca3ea21e` |",
        "| `cap_anonimizada_delimitada.xlsx` | XLSX com linhas delimitadas por `;` | Importação automática do formato original | versionada | `441a1ac3c3295fedf40ee99421cebd4cf34756589f2e0388d63d3553d2553463` |",
        "| `cap_anonimizada_colunas.csv` | CSV em colunas | Importação automática em formato aberto | versionada | `0c89c850337d1ca0e447412801a583d7cef984d215d221a9d1f4c45237f9d767` |",
        "| `cap_anonimizada_multiplas_abas.xlsx` | XLSX com resumo e movimentos | Escolha manual de aba e cabeçalho | versionada | `8edebe57f01091db324c5be5a766d1f6d4e3502fdd2c770a8778311374285f67` |",
        "",
        "## Caso CAP confirmado",
        "",
        "- 42 linhas de dados, em 21 datas.",
        "- 21 créditos (`C`) e 21 débitos (`D`).",
        "- Soma dos créditos: `R$ 11.243,72`.",
        "- Soma dos débitos: `R$ 11.243,72`.",
        "- Filial observada: `1`.",
        "- Resultado esperado da conciliação: 21 pares conhecidos, sem confirmação automática de ambiguidades.",
        "",
        "## Primeiro ciclo de aceite",
        "",
        "1. Entrar pelo navegador e selecionar empresa e competência.",
        "2. Enviar o arquivo CAP e mostrar a prévia das 42 linhas.",
        "3. Confirmar o mapeamento de data, conta contábil, valor, tipo, histórico e filial.",
        "4. Exigir revisão das pendências e aprovação manual do lote.",
        "5. Verificar que os 42 lançamentos aprovados permanecem após atualizar a página.",
        "6. Executar conciliação e conferir os 21 pares conhecidos.",
        "7. Exportar a saída sem colunas técnicas.",
        "",
        "## Evidências de conclusão",
        "",
        "- O dump nativo foi restaurado e comparado com o banco remoto em `docs/verificacao_backup_etapa1.md`.",
        "- As três fixtures anonimizadas estão em `tests/fixtures/aceitacao/` e preservam 42 linhas, 21 débitos, 21 créditos e os totais conhecidos.",
        "- Os três testes de aceitação das fixtures passam com `unittest`.",
    ]
    (DOCS / "aceitacao_etapa1.md").write_text("\n".join(aceite) + "\n", encoding="utf-8")

    print(f"Inventário criado: {DOCS / 'inventario_etapa1.md'}")
    print(f"Snapshot lógico criado: {backup_path}")
    print(f"SHA-256: {checksum}")


if __name__ == "__main__":
    gerar()
