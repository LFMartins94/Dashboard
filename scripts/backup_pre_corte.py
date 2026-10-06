"""Gera um backup nativo do schema público antes do corte em produção."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


RAIZ = Path(__file__).resolve().parents[1]
PASTA_BACKUPS = RAIZ / "temp" / "corte"


def localizar_pg_dump() -> str | None:
    configurado = os.getenv("PG_DUMP")
    candidatos = [configurado, shutil.which("pg_dump"), shutil.which("pg_dump.exe")]
    candidatos.extend(str(caminho) for caminho in (RAIZ / "temp").glob("postgresql*/bin/pg_dump.exe"))
    return next((caminho for caminho in candidatos if caminho and Path(caminho).is_file()), None)


def localizar_pg_restore(executavel_pg_dump: str) -> str | None:
    configurado = os.getenv("PG_RESTORE")
    candidato_irmao = Path(executavel_pg_dump).with_name("pg_restore.exe")
    candidatos = [
        configurado,
        str(candidato_irmao),
        shutil.which("pg_restore"),
        shutil.which("pg_restore.exe"),
    ]
    return next((caminho for caminho in candidatos if caminho and Path(caminho).is_file()), None)


def validar_url(url: str) -> None:
    partes = urlparse(url.replace("postgresql+psycopg2://", "postgresql://", 1))
    if partes.scheme not in {"postgres", "postgresql"} or not partes.hostname:
        raise SystemExit("DATABASE_URL não aponta para um PostgreSQL válido.")
    if partes.port == 6543:
        raise SystemExit(
            "Use a conexão direta do PostgreSQL (porta 5432) para o backup; "
            "a porta de pool não é adequada para pg_dump."
        )


def gerar_backup(url: str, executavel: str, executavel_restore: str) -> tuple[Path, Path]:
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    instante = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arquivo = PASTA_BACKUPS / f"backup_publico_pre_corte_{instante}.dump"
    comando = [
        executavel,
        f"--dbname={url}",
        "--format=custom",
        "--schema=public",
        "--no-owner",
        "--no-privileges",
        f"--file={arquivo}",
    ]
    subprocess.run(comando, check=True)
    if not arquivo.is_file() or arquivo.stat().st_size == 0:
        raise SystemExit("O pg_dump terminou sem criar um arquivo de backup válido.")
    subprocess.run(
        [executavel_restore, "--list", str(arquivo)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    checksum = hashlib.sha256(arquivo.read_bytes()).hexdigest()
    manifesto = arquivo.with_suffix(".json")
    manifesto.write_text(
        json.dumps(
            {
                "gerado_em": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "arquivo": arquivo.name,
                "sha256": checksum,
                "bytes": arquivo.stat().st_size,
                "schema": "public",
                "validado_pg_restore": True,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return arquivo, manifesto


def principal() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executar", action="store_true", help="Confirma a criação do backup remoto.")
    argumentos = parser.parse_args()
    load_dotenv(RAIZ / ".env", override=False)
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise SystemExit("DATABASE_URL não configurada.")
    validar_url(url)
    executavel = localizar_pg_dump()
    if not executavel:
        raise SystemExit("pg_dump não encontrado. Defina PG_DUMP com o caminho do executável.")
    executavel_restore = localizar_pg_restore(executavel)
    if not executavel_restore:
        raise SystemExit("pg_restore não encontrado. Defina PG_RESTORE com o caminho do executável.")
    if not argumentos.executar:
        print("Pré-requisitos aprovados. Execute novamente com --executar para criar o backup.")
        return
    arquivo, manifesto = gerar_backup(url, executavel, executavel_restore)
    print(f"Backup criado em {arquivo.relative_to(RAIZ)}")
    print(f"Manifesto criado em {manifesto.relative_to(RAIZ)}")


if __name__ == "__main__":
    principal()
