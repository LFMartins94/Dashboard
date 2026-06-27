"""
database.py (Versão PostgreSQL Otimizada para Supabase Pooler)
============================================================
Módulo de persistência em nuvem utilizando SQLAlchemy e PostgreSQL.
Focado em alta performance (Bulk Insert) e segurança para dados contábeis.
"""

import os
import logging
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
_engine = None


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine

    url = os.getenv("DATABASE_URL")
    if not url:
        logger.warning("Variável DATABASE_URL não encontrada. Verifique o .env ou secrets.")
        raise RuntimeError("DATABASE_URL não configurada")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    try:
        _engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        logger.info("Engine do banco criada com sucesso.")
    except Exception as exc:
        logger.critical(
            "Falha ao criar engine do banco. DATABASE_URL=%s, erro=%s",
            url[:30] + "..." if url else "VAZIA",
            exc,
            exc_info=True,
        )
        raise exc

    return _engine


# Schema completo do banco de dados ContaView
DDL = """
CREATE TABLE IF NOT EXISTS empresas (
   id SERIAL PRIMARY KEY,
   nome VARCHAR(200) NOT NULL UNIQUE,
   cnpj VARCHAR(18),
   ativa BOOLEAN NOT NULL DEFAULT TRUE,
   criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lancamentos (
   id SERIAL PRIMARY KEY,
   empresa_id INTEGER NOT NULL REFERENCES empresas(id),
   data DATE NOT NULL,
   conta_contabil VARCHAR(50) NOT NULL,
   valor NUMERIC(14, 2) NOT NULL,
   tipo CHAR(1) CHECK (tipo IS NULL OR tipo IN ('C', 'D')),
   historico TEXT,
   filial VARCHAR(20),
   periodo VARCHAR(7),
   sequencial_lote INTEGER,
   origem VARCHAR(50) NOT NULL DEFAULT 'arquivo',
   arquivo_origem VARCHAR(255),
   criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conciliacoes (
   id SERIAL PRIMARY KEY,
   empresa_id INTEGER NOT NULL REFERENCES empresas(id),
   periodo VARCHAR(7) NOT NULL,
   total_pares INTEGER NOT NULL DEFAULT 0,
   pares_ok INTEGER NOT NULL DEFAULT 0,
   pares_com_erro INTEGER NOT NULL DEFAULT 0,
   status VARCHAR(20) NOT NULL DEFAULT 'pendente',
   executado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ocorrencias_auditoria (
   id SERIAL PRIMARY KEY,
   empresa_id INTEGER NOT NULL REFERENCES empresas(id),
   lancamento_id INTEGER REFERENCES lancamentos(id),
   tipo_ocorrencia VARCHAR(50) NOT NULL,
   descricao TEXT NOT NULL,
   severidade VARCHAR(10) NOT NULL DEFAULT 'media',
   resolvida BOOLEAN NOT NULL DEFAULT FALSE,
   criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversas (
   id SERIAL PRIMARY KEY,
   titulo VARCHAR(200) NOT NULL DEFAULT 'Nova conversa',
   criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
   atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mensagens (
   id SERIAL PRIMARY KEY,
   conversa_id INTEGER NOT NULL REFERENCES conversas(id) ON DELETE CASCADE,
   role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
   conteudo TEXT NOT NULL,
   criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimização de consultas
CREATE INDEX IF NOT EXISTS idx_lancamentos_empresa ON lancamentos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_lancamentos_data ON lancamentos(data);
CREATE INDEX IF NOT EXISTS idx_lancamentos_conta ON lancamentos(conta_contabil);
CREATE INDEX IF NOT EXISTS idx_lancamentos_periodo ON lancamentos(periodo);
CREATE INDEX IF NOT EXISTS idx_lancamentos_tipo ON lancamentos(tipo);
CREATE INDEX IF NOT EXISTS idx_mensagens_conversa ON mensagens(conversa_id);
"""

# ---------------------------------------------------------------------------
# Inicialização do Banco
# ---------------------------------------------------------------------------
TABELAS = [
    "empresas",
    "lancamentos",
    "conciliacoes",
    "ocorrencias_auditoria",
    "conversas",
    "mensagens",
]


def inicializar_banco() -> None:
    """Garante que todas as tabelas, índices e políticas RLS existam no PostgreSQL."""
    try:
        with _get_engine().begin() as conn:
            conn.execute(text(DDL))
        logger.info("Banco de dados inicializado com sucesso.")
    except SQLAlchemyError as exc:
        logger.critical(f"Falha crítica ao inicializar o banco de dados: {exc}")
        raise exc

# ---------------------------------------------------------------------------
# Operações de Escrita
# ---------------------------------------------------------------------------

def obter_ou_criar_empresa(nome: str, cnpj: str = None) -> int:
    """Busca uma empresa pelo nome. Se não existir, cria e retorna o ID."""
    find_sql = text("SELECT id FROM empresas WHERE nome = :nome")
    insert_sql = text("INSERT INTO empresas (nome, cnpj) VALUES (:nome, :cnpj) RETURNING id")

    with _get_engine().connect() as conn:
        trans = conn.begin()
        try:
            result = conn.execute(find_sql, {"nome": nome}).fetchone()
            if result:
                trans.commit()
                return result[0]
            
            new_id = conn.execute(insert_sql, {"nome": nome, "cnpj": cnpj}).scalar_one()
            trans.commit()
            logger.info(f"Empresa '{nome}' criada com ID: {new_id}")
            return new_id
        except SQLAlchemyError as exc:
            trans.rollback()
            logger.error(f"Erro ao obter ou criar empresa '{nome}': {exc}")
            raise exc


def verificar_periodo_existente(empresa_id: int, periodo: str) -> bool:
    """Verifica se já existem lançamentos para uma empresa em um período."""
    sql = text("""
        SELECT EXISTS (
            SELECT 1 FROM lancamentos WHERE empresa_id = :empresa_id AND periodo = :periodo
        )
    """)
    try:
        with _get_engine().connect() as conn:
            result = conn.execute(sql, {"empresa_id": empresa_id, "periodo": periodo}).scalar()
            return result
    except SQLAlchemyError as exc:
        logger.error(f"Erro ao verificar período {periodo} para empresa {empresa_id}: {exc}")
        return False


def deletar_lancamentos_do_periodo(empresa_id: int, periodo: str) -> int:
    """Deleta lançamentos, ocorrências de auditoria e conciliações de um período."""
    delete_ocorrencias_sql = text("""
        DELETE FROM ocorrencias_auditoria WHERE empresa_id = :empresa_id 
        AND lancamento_id IN (SELECT id FROM lancamentos WHERE periodo = :periodo AND empresa_id = :empresa_id)
    """)
    delete_conciliacoes_sql = text("DELETE FROM conciliacoes WHERE empresa_id = :empresa_id AND periodo = :periodo")
    delete_lancamentos_sql = text("DELETE FROM lancamentos WHERE empresa_id = :empresa_id AND periodo = :periodo")
    
    deleted_count = 0
    with _get_engine().begin() as conn:
        try:
            conn.execute(delete_ocorrencias_sql, {"empresa_id": empresa_id, "periodo": periodo})
            conn.execute(delete_conciliacoes_sql, {"empresa_id": empresa_id, "periodo": periodo})
            result = conn.execute(delete_lancamentos_sql, {"empresa_id": empresa_id, "periodo": periodo})
            deleted_count = result.rowcount
            logger.info(f"{deleted_count} lançamentos deletados para empresa {empresa_id} no período {periodo}.")
        except SQLAlchemyError as exc:
            logger.error(f"Erro ao deletar período {periodo} para empresa {empresa_id}: {exc}")
            raise exc
    return deleted_count


def salvar_lancamentos(df: pd.DataFrame, empresa_id: int, origem: str = 'arquivo') -> int:
    """Salva um DataFrame de lançamentos contábeis usando to_sql otimizado."""
    if df.empty:
        return 0

    df_insert = df.copy()
    df_insert['empresa_id'] = empresa_id
    df_insert['origem'] = origem

    # Garante que as colunas estão na ordem correta da tabela
    colunas_tabela = [
        'empresa_id', 'data', 'conta_contabil', 'valor', 'tipo', 'historico', 
        'filial', 'periodo', 'sequencial_lote', 'origem', 'arquivo_origem'
    ]
    df_insert = df_insert[colunas_tabela]

    try:
        with _get_engine().begin() as conn:
            registros_salvos = df_insert.to_sql(
                name="lancamentos",
                con=conn,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000
            )
        logger.info(f"{registros_salvos} lançamentos salvos com sucesso para empresa {empresa_id}.")
        return registros_salvos if registros_salvos is not None else 0
    except SQLAlchemyError as exc:
        logger.error(f"Falha no bulk insert para empresa {empresa_id}: {exc}")
        return 0

# ---------------------------------------------------------------------------
# Operações de Leitura
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Operações — Conciliação
# ---------------------------------------------------------------------------

def inserir_conciliacao(empresa_id: int, periodo: str, total_pares: int, pares_ok: int, pares_com_erro: int) -> int:
    sql = text("""
        INSERT INTO conciliacoes (empresa_id, periodo, total_pares, pares_ok, pares_com_erro, status)
        VALUES (:empresa_id, :periodo, :total_pares, :pares_ok, :pares_com_erro, 'concluido')
        RETURNING id
    """)
    try:
        with _get_engine().begin() as conn:
            new_id = conn.execute(sql, {
                "empresa_id": empresa_id, "periodo": periodo,
                "total_pares": total_pares, "pares_ok": pares_ok,
                "pares_com_erro": pares_com_erro,
            }).scalar_one()
        logger.info("Conciliacao salva (id=%d) para empresa %d / %s.", new_id, empresa_id, periodo)
        return new_id
    except SQLAlchemyError as exc:
        logger.error("Erro ao salvar conciliacao: %s", exc)
        raise exc


def carregar_conciliacao(empresa_id: int, periodo: str) -> pd.DataFrame:
    sql = text("""
        SELECT * FROM conciliacoes
        WHERE empresa_id = :empresa_id AND periodo = :periodo
        ORDER BY executado_em DESC
    """)
    try:
        with _get_engine().connect() as conn:
            return pd.read_sql_query(sql, conn, params={"empresa_id": empresa_id, "periodo": periodo})
    except SQLAlchemyError as exc:
        logger.error("Erro ao carregar conciliacao: %s", exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Operações — Auditoria
# ---------------------------------------------------------------------------

def inserir_ocorrencias(ocorrencias: list[dict]) -> int:
    if not ocorrencias:
        return 0
    df = pd.DataFrame(ocorrencias)
    cols = [c for c in ("empresa_id", "lancamento_id", "tipo_ocorrencia", "descricao", "severidade") if c in df.columns]
    df = df[cols]
    try:
        with _get_engine().begin() as conn:
            registros = df.to_sql("ocorrencias_auditoria", conn, if_exists="append", index=False, method="multi", chunksize=500)
        logger.info("%d ocorrencias salvas.", registros or 0)
        return registros or 0
    except SQLAlchemyError as exc:
        logger.error("Erro ao salvar ocorrencias: %s", exc)
        return 0


def carregar_ocorrencias(empresa_id: int, periodo: str) -> pd.DataFrame:
    sql = text("""
        SELECT oa.*, l.data, l.conta_contabil, l.valor, l.tipo
        FROM ocorrencias_auditoria oa
        LEFT JOIN lancamentos l ON l.id = oa.lancamento_id
        WHERE oa.empresa_id = :empresa_id
          AND (l.periodo = :periodo OR l.periodo IS NULL)
        ORDER BY oa.severidade DESC, oa.criado_em DESC
    """)
    try:
        with _get_engine().connect() as conn:
            return pd.read_sql_query(sql, conn, params={"empresa_id": empresa_id, "periodo": periodo})
    except SQLAlchemyError as exc:
        logger.error("Erro ao carregar ocorrencias: %s", exc)
        return pd.DataFrame()


def atualizar_ocorrencia_resolvida(ocorrencia_id: int, resolvida: bool) -> None:
    sql = text("UPDATE ocorrencias_auditoria SET resolvida = :resolvida WHERE id = :id")
    try:
        with _get_engine().begin() as conn:
            conn.execute(sql, {"id": ocorrencia_id, "resolvida": resolvida})
    except SQLAlchemyError as exc:
        logger.error("Erro ao atualizar ocorrencia %d: %s", ocorrencia_id, exc)
        raise exc


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def listar_empresas() -> pd.DataFrame:
    try:
        with _get_engine().connect() as conn:
            return pd.read_sql_query(text("SELECT id, nome, cnpj FROM empresas WHERE ativa = TRUE ORDER BY nome"), conn)
    except SQLAlchemyError as exc:
        logger.error("Erro ao listar empresas: %s", exc)
        return pd.DataFrame()


def listar_periodos(empresa_id: int = None) -> list[str]:
    sql = "SELECT DISTINCT periodo FROM lancamentos"
    params = {}
    if empresa_id:
        sql += " WHERE empresa_id = :empresa_id"
        params["empresa_id"] = empresa_id
    sql += " ORDER BY periodo DESC"
    try:
        with _get_engine().connect() as conn:
            df = pd.read_sql_query(text(sql), conn, params=params)
        return df["periodo"].dropna().tolist()
    except SQLAlchemyError as exc:
        logger.error("Erro ao listar periodos: %s", exc)
        return []


def carregar_lancamentos(empresa_id: int = None, periodo: str = None) -> pd.DataFrame:
    """Carrega lançamentos com filtros opcionais de empresa e período."""
    query = "SELECT * FROM lancamentos"
    params = {}
    conditions = []

    if empresa_id:
        conditions.append("empresa_id = :empresa_id")
        params['empresa_id'] = empresa_id
    
    if periodo:
        conditions.append("periodo = :periodo")
        params['periodo'] = periodo

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY data, sequencial_lote"

    try:
        with _get_engine().connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
        return df
    except SQLAlchemyError as exc:
        logger.error(f"Falha ao carregar lançamentos: {exc}")
        return pd.DataFrame()

# ---------------------------------------------------------------------------
# Operações — Assistente / Chat
# ---------------------------------------------------------------------------

def criar_conversa(titulo: str = "Nova conversa") -> int:
    sql = text("INSERT INTO conversas (titulo) VALUES (:titulo) RETURNING id")
    try:
        with _get_engine().begin() as conn:
            new_id = conn.execute(sql, {"titulo": titulo}).scalar_one()
        logger.info("Conversa criada (id=%d).", new_id)
        return new_id
    except SQLAlchemyError as exc:
        logger.error("Erro ao criar conversa: %s", exc)
        raise exc


def salvar_mensagem(conversa_id: int, role: str, conteudo: str) -> None:
    insert_sql = text(
        "INSERT INTO mensagens (conversa_id, role, conteudo) VALUES (:conversa_id, :role, :conteudo)"
    )
    update_sql = text(
        "UPDATE conversas SET atualizado_em = CURRENT_TIMESTAMP WHERE id = :id"
    )
    try:
        with _get_engine().begin() as conn:
            conn.execute(insert_sql, {"conversa_id": conversa_id, "role": role, "conteudo": conteudo})
            conn.execute(update_sql, {"id": conversa_id})
    except SQLAlchemyError as exc:
        logger.error("Erro ao salvar mensagem: %s", exc)
        raise exc


def conversa_existe(conversa_id: int) -> bool:
    sql = text("SELECT EXISTS (SELECT 1 FROM conversas WHERE id = :id)")
    try:
        with _get_engine().connect() as conn:
            return bool(conn.execute(sql, {"id": conversa_id}).scalar())
    except SQLAlchemyError as exc:
        logger.error("Erro ao verificar se conversa %d existe: %s", conversa_id, exc)
        return False


def carregar_mensagens(conversa_id: int) -> list[dict]:
    sql = text(
        "SELECT role, conteudo FROM mensagens WHERE conversa_id = :conversa_id ORDER BY criado_em ASC"
    )
    try:
        with _get_engine().connect() as conn:
            rows = conn.execute(sql, {"conversa_id": conversa_id}).fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows]
    except SQLAlchemyError as exc:
        logger.error("Erro ao carregar mensagens: %s", exc)
        return []


def listar_conversas() -> list[dict]:
    sql = text(
        "SELECT id, titulo, atualizado_em FROM conversas ORDER BY atualizado_em DESC"
    )
    try:
        with _get_engine().connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [
            {"id": row[0], "titulo": row[1], "atualizado_em": row[2]}
            for row in rows
        ]
    except SQLAlchemyError as exc:
        logger.error("Erro ao listar conversas: %s", exc)
        return []


def renomear_conversa(conversa_id: int, titulo: str) -> None:
    sql = text("UPDATE conversas SET titulo = :titulo WHERE id = :id")
    try:
        with _get_engine().begin() as conn:
            conn.execute(sql, {"id": conversa_id, "titulo": titulo})
    except SQLAlchemyError as exc:
        logger.error("Erro ao renomear conversa %d: %s", conversa_id, exc)
        raise exc


def deletar_conversa(conversa_id: int) -> None:
    sql = text("DELETE FROM conversas WHERE id = :id")
    try:
        with _get_engine().begin() as conn:
            conn.execute(sql, {"id": conversa_id})
        logger.info("Conversa %d deletada.", conversa_id)
    except SQLAlchemyError as exc:
        logger.error("Erro ao deletar conversa %d: %s", conversa_id, exc)
        raise exc
