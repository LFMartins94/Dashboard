"""
database.py (Versão PostgreSQL Otimizada para Supabase Pooler)
============================================================
Módulo de persistência em nuvem utilizando SQLAlchemy e PostgreSQL.
Focado em alta performance (Bulk Insert) e segurança para dados contábeis.
"""

import os
import logging
from datetime import date, datetime
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ---------------------------------------------------------------------------
# Configuração de logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gerenciamento Seguro de Conexão (Hardening via Environment Variables)
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback de segurança caso rode localmente sem a variável configurada
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///financeiro.db"

# Correção automática de dialeto exigida pelo SQLAlchemy moderno
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# CRIAÇÃO DA ENGINE COM ADAPTAÇÃO PARA O POOLER DO SUPABASE (PORTA 6543)
# - pool_size e max_overflow: controlam a concorrência dentro do limite do plano.
# - pool_recycle: Fecha conexões ociosas a cada 30 min, evitando a queda do pooler.
# - pool_pre_ping: Garante resiliência testando a conexão antes de executar o SQL.
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_pre_ping=True
)

SENTINEL: str = "NÃO ENCONTRADO"

# Schema adaptado para PostgreSQL (com tipos de dados nativos mais eficientes)
DDL_GASTOS_POSTGRES = """
CREATE TABLE IF NOT EXISTS gastos (
    id          SERIAL PRIMARY KEY,
    data        DATE NOT NULL,
    categoria   VARCHAR(100) NOT NULL,
    valor       NUMERIC(12, 2) NOT NULL,
    origem      VARCHAR(50) NOT NULL DEFAULT 'manual',
    criado_em   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gastos_data ON gastos(data);
CREATE INDEX IF NOT EXISTS idx_gastos_categoria ON gastos(categoria);
"""

# ---------------------------------------------------------------------------
# Inicialização do Banco
# ---------------------------------------------------------------------------
def inicializar_banco() -> None:
    """Garante que a tabela e os índices existam no PostgreSQL remoto."""
    try:
        with engine.begin() as conn:
            conn.execute(text(DDL_GASTOS_POSTGRES))
        logger.info("Banco de dados PostgreSQL/SQLAlchemy inicializado com sucesso.")
    except SQLAlchemyError as exc:
        logger.critical(f"Falha crítica ao inicializar o banco de dados: {exc}")
        raise exc

# ---------------------------------------------------------------------------
# Funções Auxiliares de Normalização
# ---------------------------------------------------------------------------
def _normalizar_data(d):
    if pd.isna(d) or d == SENTINEL:
        return None
    try:
        return pd.to_datetime(d).date()
    except Exception:
        return None

def _normalizar_valor(v) -> float:
    if pd.isna(v) or v == SENTINEL:
        return 0.0
    try:
        if isinstance(v, str):
            v = v.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return round(float(v), 2)
    except (ValueError, TypeError):
        return 0.0

# ---------------------------------------------------------------------------
# Operações de Escrita (Alta Performance Contábil)
# ---------------------------------------------------------------------------
def salvar_registro(data_val, categoria: str, valor_val, origem: str = "manual") -> bool:
    """Salva um único registro manual de forma parametrizada (Anti-SQLi)."""
    data_clean = _normalizar_data(data_val)
    valor_clean = _normalizar_valor(valor_val)
    categoria_clean = str(categoria).strip()[:100]

    if not data_clean or not categoria_clean:
        return False

    sql = text("INSERT INTO gastos (data, categoria, valor, origem) VALUES (:data, :categoria, :valor, :origem)")
    try:
        with engine.begin() as conn:
            conn.execute(sql, {"data": data_clean, "categoria": categoria_clean, "valor": valor_clean, "origem": origem})
        return True
    except SQLAlchemyError as exc:
        logger.error(f"Erro ao salvar registro individual: {exc}")
        return False

def salvar_dataframe_otimizado(df: pd.DataFrame, origem: str = "arquivo") -> int:
    """
    BULK INSERT CONTÁBIL DE ALTA PERFORMANCE.
    Utiliza o método nativo altamente otimizado do Pandas acoplado ao SQLAlchemy
    para empurrar milhares de linhas de reconciliação de uma vez só para o Postgres.
    """
    if df.empty:
        return 0

    colunas_obrigatorias = ["data", "categoria", "valor"]
    for col in colunas_obrigatorias:
        if col not in df.columns:
            logger.error(f"Coluna obrigatória ausente: {col}")
            return 0

    # Preparação veloz dos dados
    df_clean = df.copy()
    df_clean["data"] = df_clean["data"].apply(_normalizar_data)
    df_clean["valor"] = df_clean["valor"].apply(_normalizar_valor)
    df_clean["categoria"] = df_clean["categoria"].astype(str).str.strip().str[:100]
    df_clean["origem"] = str(origem)

    # Remove registros inválidos antes de enviar à nuvem para poupar banda e processamento
    df_filtrado = df_clean[df_clean["data"].notna() & (df_clean["categoria"] != "")]
    
    if df_filtrado.empty:
        return 0

    # Seleciona apenas as colunas que batem com o banco de dados
    df_final = df_filtrado[["data", "categoria", "valor", "origem"]]

    try:
        # O 'to_sql' com a engine do SQLAlchemy realiza a inserção em blocos na nuvem de forma atômica
        with engine.begin() as conn:
            df_final.to_sql(
                name="gastos",
                con=conn,
                if_exists="append",
                index=False,
                幕method="multi", # Agrupa múltiplas linhas por comando INSERT (Velocidade Máxima)
                chunksize=1000  # Envia de 1000 em 1000 linhas por bloco
            )
        return len(df_final)
    except SQLAlchemyError as exc:
        logger.error(f"Falha crítica no Bulk Insert contábil: {exc}")
        return 0

# ---------------------------------------------------------------------------
# Operações de Leitura
# ---------------------------------------------------------------------------
def carregar_todos_os_gastos() -> pd.DataFrame:
    """Carrega todo o histórico contábil do PostgreSQL para análise no Streamlit."""
    sql = text("SELECT id, data, categoria, valor, origem, criado_em FROM gastos ORDER BY data DESC, id DESC")
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(sql, conn)
        
        if not df.empty:
            df["data"] = pd.to_datetime(df["data"]).dt.date
            df["valor"] = df["valor"].astype(float).round(2)
        else:
            return pd.DataFrame(columns=["id", "data", "categoria", "valor", "origem", "criado_em"])
        return df
    except SQLAlchemyError as exc:
        logger.error(f"Falha ao carregar dados do PostgreSQL: {exc}")
        return pd.DataFrame(columns=["id", "data", "categoria", "valor", "origem", "criado_em"])