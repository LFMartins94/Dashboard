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
from datetime import date, datetime
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
SENTINEL: str = "NÃO ENCONTRADO"

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
    Gerenciador de contexto que fornece uma conexão SQLite com política de retry
    para mitigar erros de travamento por concorrência (SQLITE_BUSY).
    """
    conn = sqlite3.connect(db_path, timeout=5.0)
    
    # Hardening: Ativa o modo WAL (Write-Ahead Logging) para melhorar concorrência
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.Error:
        pass
        
    try:
        retries = 0
        while retries < MAX_RETRIES:
            try:
                yield conn
                conn.commit()
                break
            except sqlite3.OperationalError as exc:
                if "database is locked" in str(exc).lower():
                    retries += 1
                    logger.warning(
                        "Banco travado. Tentativa %d/%d aguardando %.2fs...",
                        retries, MAX_RETRIES, RETRY_DELAY
                    )
                    time.sleep(RETRY_DELAY)
                else:
                    conn.rollback()
                    raise exc
            except Exception as exc:
                conn.rollback()
                raise exc
        else:
            conn.rollback()
            raise sqlite3.OperationalError(
                f"Falha ao adquirir trava no banco após {MAX_RETRIES} tentativas."
            )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Inicialização do Banco
# ---------------------------------------------------------------------------
def inicializar_banco(db_path: str = DB_PATH) -> None:
    """
    Cria o arquivo de banco de dados e executa o DDL para garantir
    a existência da tabela gastos com os índices necessários.
    """
    try:
        with _get_connection(db_path) as conn:
            conn.execute(DDL_GASTOS)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_data ON gastos(data);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_categoria ON gastos(categoria);")
        logger.info("Banco de dados inicializado com sucesso em '%s'.", db_path)
    except Exception as exc:
        logger.critical("Falha crítica ao inicializar o banco de dados: %s", exc)
        raise exc


# ---------------------------------------------------------------------------
# Funções Auxiliares de Normalização e Sanitização (Hardening)
# ---------------------------------------------------------------------------
def _normalizar_data(d) -> str:
    """Normaliza diferentes tipos de entrada de data para string no padrão YYYY-MM-DD."""
    if pd.isna(d) or d == SENTINEL:
        return SENTINEL
    if isinstance(d, (date, datetime)):
        return d.strftime("%Y-%m-%d")
    if isinstance(d, pd.Timestamp):
        return d.strftime("%Y-%m-%d")
    
    d_str = str(d).strip()
    try:
        parsed_dt = pd.to_datetime(d_str, errors="coerce")
        if pd.notna(parsed_dt):
            return parsed_dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return d_str if d_str else SENTINEL


def _normalizar_valor(v) -> float:
    """Normaliza valores financeiros garantindo precisão numérica de 2 casas decimais."""
    if pd.isna(v) or v == SENTINEL:
        return 0.0
    try:
        if isinstance(v, str):
            v = v.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return round(float(v), 2)
    except (ValueError, TypeError):
        return 0.0


# ---------------------------------------------------------------------------
# Operações de Escrita
# ---------------------------------------------------------------------------
def salvar_registro(data_val, categoria: str, valor_val, origem: str = "manual", db_path: str = DB_PATH) -> bool:
    """
    Salva um único registro no banco utilizando consultas parametrizadas (Anti-SQLi).
    """
    data_str = _normalizar_data(data_val)
    valor = _normalizar_valor(valor_val)
    categoria_clean = str(categoria).strip()[:100]

    if data_str == SENTINEL or not categoria_clean:
        logger.warning("Registro manual ignorado devido a campos obrigatórios inválidos.")
        return False

    sql = "INSERT INTO gastos (data, categoria, valor, origem) VALUES (?, ?, ?, ?)"
    try:
        with _get_connection(db_path) as conn:
            conn.execute(sql, (data_str, categoria_clean, valor, str(origem)))
        return True
    except Exception as exc:
        logger.error("Erro ao salvar registro individual: %s", exc)
        return False


def salvar_dataframe_otimizado(df: pd.DataFrame, origem: str = "arquivo", db_path: str = DB_PATH) -> int:
    """
    Refatoração de Alta Performance (Bulk Insert).
    Persiste os dados em lote único usando executemany dentro de uma transação.
    """
    if df.empty:
        return 0

    colunas_obrigatorias = ["data", "categoria", "valor"]
    for col in colunas_obrigatorias:
        if col not in df.columns:
            logger.error("Coluna obrigatória ausente no DataFrame enviado: %s", col)
            return 0

    df_clean = df.copy()
    df_clean["data_norm"] = df_clean["data"].apply(_normalizar_data)
    df_clean["valor_norm"] = df_clean["valor"].apply(_normalizar_valor)
    
    df_filtrado = df_clean[
        (df_clean["data_norm"] != SENTINEL) & 
        (df_clean["categoria"].notna()) & 
        (df_clean["categoria"] != "") &
        (df_clean["categoria"] != SENTINEL)
    ]
    
    if df_filtrado.empty:
        logger.warning("Nenhum registro válido restou após a higienização do DataFrame.")
        return 0

    registros_para_banco = [
        (
            str(row["data_norm"]),
            str(row["categoria"]).strip()[:100],
            float(row["valor_norm"]),
            str(origem)
        )
        for _, row in df_filtrado.iterrows()
    ]

    sql = "INSERT INTO gastos (data, categoria, valor, origem) VALUES (?, ?, ?, ?)"
    
    try:
        with _get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, registros_para_banco)
            salvos = cursor.rowcount
        logger.info("Bulk Insert concluído: %d/%d registros salvos com sucesso.", salvos, len(df))
        return salvos
    except sqlite3.Error as exc:
        logger.error("Falha crítica na transação em lote (Bulk Insert): %s", exc)
        return 0


# ---------------------------------------------------------------------------
# Operações de Leitura
# ---------------------------------------------------------------------------
def carregar_todos_os_gastos(db_path: str = DB_PATH) -> pd.DataFrame:
    """
    Retorna todos os registros da tabela `gastos` como um DataFrame do Pandas.
    """
    sql = "SELECT id, data, categoria, valor, origem, criado_em FROM gastos ORDER BY data DESC, id DESC"
    try:
        with _get_connection(db_path) as conn:
            df = pd.read_sql_query(sql, conn)
        
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
            df["valor"] = df["valor"].round(2)
        else:
            return pd.DataFrame(columns=["id", "data", "categoria", "valor", "origem", "criado_em"])
            
        return df
    except Exception as exc:
        logger.error("Falha ao carregar dados do banco de dados: %s", exc)
        return pd.DataFrame(columns=["id", "data", "categoria", "valor", "origem", "criado_em"])
