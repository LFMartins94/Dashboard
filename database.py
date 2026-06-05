"""
database.py
===========
Módulo de persistência SQLite para o Dashboard Financeiro.
Gerencia criação do schema, leitura e escrita de registros financeiros.
"""

import sqlite3
import time
import logging
from contextlib import contextmanager
from datetime import date
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
DB_PATH: str = "financeiro.db"
MAX_RETRIES: int = 5
RETRY_DELAY: float = 0.3  # segundos entre tentativas

# Schema da tabela principal
DDL_GASTOS: str = """
CREATE TABLE IF NOT EXISTS gastos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    data        TEXT    NOT NULL,
    categoria   TEXT    NOT NULL,
    valor       REAL    NOT NULL,
    origem      TEXT    NOT NULL DEFAULT 'manual',
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


# ---------------------------------------------------------------------------
# Context manager com retry para concorrência de escrita
# ---------------------------------------------------------------------------
@contextmanager
def _get_connection(db_path: str = DB_PATH):
    """
    Abre uma conexão SQLite com política de retry para evitar
    bloqueios de escrita (SQLITE_BUSY).

    Args:
        db_path: Caminho para o arquivo .db.

    Yields:
        sqlite3.Connection: Conexão ativa.

    Raises:
        sqlite3.OperationalError: Se esgotar todas as tentativas.
    """
    conn: Optional[sqlite3.Connection] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            if conn:
                conn.rollback()
            if attempt == MAX_RETRIES:
                logger.error("SQLite bloqueado após %d tentativas: %s", MAX_RETRIES, exc)
                raise
            logger.warning(
                "SQLite ocupado (tentativa %d/%d). Aguardando %.1fs...",
                attempt, MAX_RETRIES, RETRY_DELAY,
            )
            time.sleep(RETRY_DELAY)
        finally:
            if conn:
                conn.close()


# ---------------------------------------------------------------------------
# Inicialização do banco
# ---------------------------------------------------------------------------
def inicializar_banco(db_path: str = DB_PATH) -> None:
    """
    Cria o banco de dados e a tabela `gastos` caso não existam.

    Args:
        db_path: Caminho para o arquivo SQLite.
    """
    with _get_connection(db_path) as conn:
        conn.execute(DDL_GASTOS)
    logger.info("Banco inicializado em '%s'.", db_path)


# ---------------------------------------------------------------------------
# Operações de escrita
# ---------------------------------------------------------------------------
def salvar_registro(
    data: date | str,
    categoria: str,
    valor: float,
    origem: str = "manual",
    db_path: str = DB_PATH,
) -> None:
    """
    Persiste um único registro financeiro no SQLite.

    Args:
        data:      Data da despesa (date ou string ISO 'YYYY-MM-DD').
        categoria: Categoria da despesa.
        valor:     Valor monetário com até 2 casas decimais.
        origem:    Fonte do registro ('manual', 'excel', 'csv', 'pdf', 'pptx').
        db_path:   Caminho para o banco.
    """
    data_str = data.isoformat() if isinstance(data, date) else str(data)
    sql = "INSERT INTO gastos (data, categoria, valor, origem) VALUES (?, ?, ?, ?)"
    with _get_connection(db_path) as conn:
        conn.execute(sql, (data_str, categoria, round(valor, 2), origem))
    logger.info("Registro salvo: data=%s, categoria=%s, valor=%.2f", data_str, categoria, valor)


def salvar_dataframe(
    df: pd.DataFrame,
    origem: str = "arquivo",
    db_path: str = DB_PATH,
) -> int:
    """
    Persiste um DataFrame inteiro no SQLite, linha a linha, ignorando
    registros com campos obrigatórios ausentes.

    O DataFrame deve conter, ao menos, as colunas:
        - 'data'      (str ou date)
        - 'categoria' (str)
        - 'valor'     (float)

    Campos ausentes são preenchidos com 'NÃO ENCONTRADO' / 0.0.

    Args:
        df:      DataFrame com os dados a serem persistidos.
        origem:  Rótulo de origem para todos os registros do lote.
        db_path: Caminho para o banco.

    Returns:
        int: Número de registros efetivamente salvos.
    """
    colunas_obrigatorias = {"data", "categoria", "valor"}
    colunas_presentes = {c.lower() for c in df.columns}

    # Normaliza nomes de colunas para lowercase
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # Preenche colunas ausentes com sentinela
    for col in colunas_obrigatorias:
        if col not in df.columns:
            df[col] = "NÃO ENCONTRADO" if col != "valor" else 0.0
            logger.warning("Coluna '%s' ausente no DataFrame — preenchida com sentinela.", col)

    salvos = 0
    sql = "INSERT INTO gastos (data, categoria, valor, origem) VALUES (?, ?, ?, ?)"

    with _get_connection(db_path) as conn:
        for idx, row in df.iterrows():
            try:
                data_val = row["data"]
                if isinstance(data_val, date):
                    data_val = data_val.isoformat()
                else:
                    data_val = str(data_val)

                valor_val = float(row["valor"]) if row["valor"] != "NÃO ENCONTRADO" else 0.0
                conn.execute(sql, (data_val, str(row["categoria"]), round(valor_val, 2), origem))
                salvos += 1
            except (ValueError, TypeError) as exc:
                logger.warning("Linha %d ignorada por erro de conversão: %s", idx, exc)

    logger.info("%d/%d registros salvos do DataFrame (origem=%s).", salvos, len(df), origem)
    return salvos


# ---------------------------------------------------------------------------
# Operações de leitura
# ---------------------------------------------------------------------------
def carregar_todos_os_gastos(db_path: str = DB_PATH) -> pd.DataFrame:
    """
    Retorna todos os registros da tabela `gastos` como um DataFrame.

    Colunas retornadas:
        id, data, categoria, valor, origem, criado_em

    Args:
        db_path: Caminho para o banco.

    Returns:
        pd.DataFrame: Dados históricos completos, ordenados por data DESC.
                      DataFrame vazio se não houver registros.
    """
    sql = "SELECT id, data, categoria, valor, origem, criado_em FROM gastos ORDER BY data DESC, id DESC"
    try:
        with _get_connection(db_path) as conn:
            df = pd.read_sql_query(sql, conn)
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
            df["valor"] = df["valor"].round(2)
        return df
    except Exception as exc:
        logger.error("Falha ao carregar dados do banco: %s", exc)
        return pd.DataFrame(columns=["id", "data", "categoria", "valor", "origem", "criado_em"])
