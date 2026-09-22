"""
database.py (Versão PostgreSQL Otimizada para Supabase Pooler)
============================================================
Módulo de persistência em nuvem utilizando SQLAlchemy e PostgreSQL.
Focado em alta performance (Bulk Insert) e segurança para dados contábeis.
Faz fallback automatico entre pooler (6543) e conexão direta (5432)
para compatibilidade com Supavisor.
"""

import os
import re
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


def _tentar_criar_engine(url: str):
    """Tenta criar engine com uma URL. Retorna engine ou None."""
    try:
        eng = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        # Testa conexao
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Engine do banco criada com sucesso.")
        return eng
    except Exception:
        logger.warning("Falha ao conectar ao banco de dados com a configuração recebida.")
        return None


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine

    if not os.getenv("DATABASE_URL"):
        from dotenv import load_dotenv
        load_dotenv()

    url = os.getenv("DATABASE_URL")
    if not url:
        logger.warning("Variável DATABASE_URL não encontrada. Verifique o .env ou secrets.")
        raise RuntimeError("DATABASE_URL não configurada")

    url = url.replace("postgres://", "postgresql://", 1)

    _engine = _tentar_criar_engine(url)
    if _engine is not None:
        return _engine

    # Fallback: se URL usa pooler (porta 6543), tenta conexão direta na 5432
    logger.info("Tentando fallback para conexao direta (porta 5432)...")
    # Extrai project ref do username no formato postgres.<project_ref>
    m_ref = re.search(r"postgres\.([a-z0-9]{20})", url)
    if m_ref:
        project_ref = m_ref.group(1)
        # Extrai a senha: tudo entre o último ':' e '@' antes do host
        auth_part = url.split("@")[0]                     # postgresql://user:pass
        password = auth_part.rsplit(":", 1)[-1]           # pass
        # Reconstrói a URL para conexão direta:
        #   pooler:  postgres.<ref>:<pass>@<region>.pooler.supabase.com:6543/postgres
        #   direct:  postgres:<pass>@db.<ref>.supabase.co:5432/postgres
        url_fb = (
            f"postgresql://postgres:{password}"
            f"@db.{project_ref}.supabase.co:5432/postgres"
        )
        if "sslmode=" not in url_fb:
            url_fb += "?sslmode=require"
        logger.info("Fallback URL: postgresql://postgres:***@db.%s.supabase.co:5432/postgres", project_ref)
    else:
        # Fallback simples: só troca a porta
        url_fb = url.replace(":6543/", ":5432/")
    _engine = _tentar_criar_engine(url_fb)
    if _engine is not None:
        return _engine

    logger.critical("Todas as tentativas de conexao falharam.")
    raise RuntimeError("Não foi possível conectar ao banco de dados.")


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
   atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
   favorito BOOLEAN NOT NULL DEFAULT FALSE
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
CREATE INDEX IF NOT EXISTS idx_conciliacoes_empresa ON conciliacoes(empresa_id);
CREATE INDEX IF NOT EXISTS idx_ocorrencias_auditoria_empresa
    ON ocorrencias_auditoria(empresa_id);
CREATE INDEX IF NOT EXISTS idx_ocorrencias_auditoria_lancamento
    ON ocorrencias_auditoria(lancamento_id);
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


_MIGRACOES = [
    "ALTER TABLE conversas ADD COLUMN IF NOT EXISTS favorito BOOLEAN NOT NULL DEFAULT FALSE;",
]


# Migração separada: executar após revisar e preservar os dados de produção.
# As tabelas existentes continuam disponíveis durante a transição.
MIGRACAO_PREPARACAO = """
CREATE TABLE IF NOT EXISTS lotes_importacao (
    id BIGSERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    nome_arquivo VARCHAR(255) NOT NULL,
    arquivo_sha256 CHAR(64) NOT NULL,
    conteudo_original BYTEA NOT NULL,
    aba VARCHAR(255) NOT NULL,
    tipo_documento VARCHAR(30) NOT NULL,
    periodo VARCHAR(7),
    mapeamento JSONB NOT NULL DEFAULT '{}'::jsonb,
    total_linhas INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'em_revisao',
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id, empresa_id),
    CHECK (total_linhas > 0),
    CHECK (periodo IS NULL OR periodo ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    CHECK (status IN ('em_revisao', 'concluido', 'cancelado'))
);

CREATE TABLE IF NOT EXISTS linhas_preparadas (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    numero_linha INTEGER NOT NULL,
    dados_brutos JSONB NOT NULL,
    data DATE,
    descricao TEXT,
    valor NUMERIC(14,2),
    tipo CHAR(1),
    conta_contabil VARCHAR(50),
    filial VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'pendente',
    pendencias JSONB NOT NULL DEFAULT '[]'::jsonb,
    alterado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lote_id, empresa_id)
        REFERENCES lotes_importacao(id, empresa_id),
    UNIQUE (lote_id, numero_linha),
    CHECK (numero_linha > 0),
    CHECK (tipo IS NULL OR tipo IN ('C', 'D')),
    CHECK (status IN ('pendente', 'validado'))
);

CREATE TABLE IF NOT EXISTS historico_alteracoes (
    id BIGSERIAL PRIMARY KEY,
    tabela VARCHAR(40) NOT NULL,
    registro_id BIGINT NOT NULL,
    empresa_id INTEGER NOT NULL,
    operacao VARCHAR(10) NOT NULL,
    dados_anteriores JSONB,
    dados_posteriores JSONB,
    usuario VARCHAR(200) NOT NULL,
    alterado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lotes_importacao_empresa
    ON lotes_importacao(empresa_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_linhas_preparadas_empresa
    ON linhas_preparadas(empresa_id, lote_id, status);
CREATE INDEX IF NOT EXISTS idx_historico_alteracoes_registro
    ON historico_alteracoes(tabela, registro_id, alterado_em DESC);
CREATE INDEX IF NOT EXISTS idx_historico_alteracoes_empresa
    ON historico_alteracoes(empresa_id, alterado_em DESC);

ALTER TABLE lotes_importacao ENABLE ROW LEVEL SECURITY;
ALTER TABLE linhas_preparadas ENABLE ROW LEVEL SECURITY;
ALTER TABLE historico_alteracoes ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.registrar_historico_alteracoes()
RETURNS TRIGGER AS $$
DECLARE
    registro_atual JSONB;
    registro_anterior JSONB;
    identificador BIGINT;
    empresa INTEGER;
BEGIN
    IF TG_OP = 'DELETE' THEN
        registro_anterior := to_jsonb(OLD) - 'dados_brutos';
        identificador := OLD.id;
        empresa := OLD.empresa_id;
    ELSE
        registro_atual := to_jsonb(NEW) - 'dados_brutos';
        identificador := NEW.id;
        empresa := NEW.empresa_id;
        IF TG_OP = 'UPDATE' THEN
            registro_anterior := to_jsonb(OLD) - 'dados_brutos';
        END IF;
    END IF;

    INSERT INTO public.historico_alteracoes (
        tabela, registro_id, empresa_id, operacao,
        dados_anteriores, dados_posteriores, usuario
    ) VALUES (
        TG_TABLE_NAME, identificador, empresa, TG_OP,
        registro_anterior, registro_atual,
        COALESCE(NULLIF(current_setting('app.usuario', true), ''), current_user)
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog;

REVOKE ALL ON FUNCTION public.registrar_historico_alteracoes()
    FROM PUBLIC, anon, authenticated, service_role;

DROP TRIGGER IF EXISTS historico_linhas_preparadas ON linhas_preparadas;
CREATE TRIGGER historico_linhas_preparadas
    AFTER INSERT OR UPDATE OR DELETE ON linhas_preparadas
    FOR EACH ROW EXECUTE FUNCTION public.registrar_historico_alteracoes();

DROP TRIGGER IF EXISTS historico_lancamentos ON lancamentos;
CREATE TRIGGER historico_lancamentos
    AFTER INSERT OR UPDATE OR DELETE ON lancamentos
    FOR EACH ROW EXECUTE FUNCTION public.registrar_historico_alteracoes();
"""


# O Reflex acessa o PostgreSQL somente no servidor. As funções da Data API
# (anon/authenticated/service_role) não têm acesso direto a estas tabelas ou
# sequências.
# RLS continua habilitada para impedir exposição acidental por novos grants.
SEGURANCA_RLS = """
DO $$
DECLARE
    nome_tabela TEXT;
    nome_sequencia TEXT;
BEGIN
    FOREACH nome_tabela IN ARRAY ARRAY[
        'empresas', 'lancamentos', 'conciliacoes',
        'ocorrencias_auditoria', 'conversas', 'mensagens',
        'lotes_importacao', 'linhas_preparadas', 'historico_alteracoes',
        'gastos'
    ] LOOP
        IF to_regclass(format('public.%I', nome_tabela)) IS NOT NULL THEN
            EXECUTE format(
                'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', nome_tabela
            );
            EXECUTE format(
                'REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role',
                nome_tabela
            );
            nome_sequencia := pg_get_serial_sequence(
                format('public.%I', nome_tabela), 'id'
            );
            IF nome_sequencia IS NOT NULL THEN
                EXECUTE format(
                    'REVOKE ALL ON SEQUENCE %s FROM PUBLIC, anon, authenticated, service_role',
                    nome_sequencia
                );
            END IF;
        END IF;
    END LOOP;

    IF to_regprocedure('public.registrar_historico_alteracoes()') IS NOT NULL THEN
        EXECUTE 'ALTER FUNCTION public.registrar_historico_alteracoes() SECURITY INVOKER';
        EXECUTE 'ALTER FUNCTION public.registrar_historico_alteracoes() SET search_path = pg_catalog';
        EXECUTE 'REVOKE ALL ON FUNCTION public.registrar_historico_alteracoes() FROM PUBLIC, anon, authenticated, service_role';
    END IF;
END;
$$;

-- Restringe novos objetos criados pelo mesmo papel que aplica a migração.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated, service_role;
-- EXECUTE para PUBLIC é um privilégio padrão global do PostgreSQL. A
-- revogação limitada ao schema não remove esse privilégio herdado.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated, service_role;
"""


def configurar_seguranca_banco() -> None:
    """Habilita RLS e fecha a Data API nas tabelas do ContaView."""
    with _get_engine().begin() as conn:
        conn.execute(text(SEGURANCA_RLS))


def migrar_preparacao() -> None:
    """Instala a área de preparação e a trilha de alterações em transação."""
    with _get_engine().begin() as conn:
        conn.exec_driver_sql(MIGRACAO_PREPARACAO)
        conn.execute(text(SEGURANCA_RLS))


def inicializar_banco() -> None:
    """Garante que todas as tabelas, índices e políticas RLS existam no PostgreSQL."""
    try:
        with _get_engine().begin() as conn:
            conn.execute(text(DDL))
            for migracao in _MIGRACOES:
                conn.execute(text(migracao))
            conn.execute(text(SEGURANCA_RLS))
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
            return bool(result)
    except SQLAlchemyError as exc:
        logger.error(f"Erro ao verificar período {periodo} para empresa {empresa_id}: {exc}")
        raise


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


def _preparar_lancamentos(df: pd.DataFrame, empresa_id: int, origem: str) -> pd.DataFrame:
    df_insert = df.copy()
    df_insert['empresa_id'] = empresa_id
    df_insert['origem'] = origem

    # Garante que as colunas estão na ordem correta da tabela
    colunas_tabela = [
        'empresa_id', 'data', 'conta_contabil', 'valor', 'tipo', 'historico', 
        'filial', 'periodo', 'sequencial_lote', 'origem', 'arquivo_origem'
    ]
    return df_insert[colunas_tabela]


def _inserir_lancamentos(conn, df_insert: pd.DataFrame) -> int:
    df_insert.to_sql(
        name="lancamentos",
        con=conn,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )
    return len(df_insert)


def _definir_usuario_auditoria(conn) -> None:
    if conn.dialect.name == "postgresql":
        conn.execute(
            text("SELECT set_config('app.usuario', :usuario, true)"),
            {"usuario": os.getenv("APP_USUARIO", "contadora")},
        )


def salvar_lancamentos(df: pd.DataFrame, empresa_id: int, origem: str = 'arquivo') -> int:
    """Salva lançamentos em uma transação e propaga falhas ao chamador."""
    if df.empty:
        return 0

    df_insert = _preparar_lancamentos(df, empresa_id, origem)

    try:
        with _get_engine().begin() as conn:
            _definir_usuario_auditoria(conn)
            registros_salvos = _inserir_lancamentos(conn, df_insert)
        logger.info(f"{registros_salvos} lançamentos salvos com sucesso para empresa {empresa_id}.")
        return registros_salvos
    except SQLAlchemyError as exc:
        logger.error(f"Falha no bulk insert para empresa {empresa_id}: {exc}")
        raise


def substituir_lancamentos_do_periodo(
    df: pd.DataFrame, empresa_id: int, periodo: str, origem: str = 'arquivo'
) -> int:
    """Substitui um período inteiro sem expor um estado parcialmente gravado."""
    if df.empty or "periodo" not in df or df["periodo"].isna().any():
        raise ValueError("O lote não contém um período válido para substituição.")
    if set(df["periodo"].astype(str)) != {periodo}:
        raise ValueError("O lote contém lançamentos de outro período.")

    df_insert = _preparar_lancamentos(df, empresa_id, origem)
    with _get_engine().begin() as conn:
        _definir_usuario_auditoria(conn)
        # A linha da empresa serializa substituições concorrentes da mesma empresa.
        bloqueio = " FOR UPDATE" if conn.dialect.name == "postgresql" else ""
        empresa = conn.execute(
            text(f"SELECT id FROM empresas WHERE id = :empresa_id{bloqueio}"),
            {"empresa_id": empresa_id},
        ).scalar_one_or_none()
        if empresa is None:
            raise ValueError("Empresa não encontrada para substituição.")

        parametros = {"empresa_id": empresa_id, "periodo": periodo}
        conn.execute(text("""
            DELETE FROM ocorrencias_auditoria
            WHERE empresa_id = :empresa_id
              AND lancamento_id IN (
                  SELECT id FROM lancamentos
                  WHERE empresa_id = :empresa_id AND periodo = :periodo
              )
        """), parametros)
        conn.execute(text("""
            DELETE FROM conciliacoes
            WHERE empresa_id = :empresa_id AND periodo = :periodo
        """), parametros)
        conn.execute(text("""
            DELETE FROM lancamentos
            WHERE empresa_id = :empresa_id AND periodo = :periodo
        """), parametros)
        registros_salvos = _inserir_lancamentos(conn, df_insert)

    logger.info(
        "%d lançamentos substituídos para empresa %d / %s.",
        registros_salvos, empresa_id, periodo,
    )
    return registros_salvos


def salvar_lote_preparacao(
    empresa_id: int, nome_arquivo: str, arquivo_sha256: str,
    conteudo_original: bytes, aba: str, tipo_documento: str,
    periodo: str | None, mapeamento: dict, linhas: list[dict],
) -> dict:
    """Grava arquivo e linhas de revisão em uma única transação."""
    import json

    if not linhas:
        raise ValueError("Nenhuma linha foi encontrada para preparação.")
    if tipo_documento not in {"extrato", "folha", "notas", "lancamentos", "outro"}:
        raise ValueError("Tipo de documento inválido.")
    mapeamento_json = json.dumps(mapeamento, ensure_ascii=False, sort_keys=True)

    with _get_engine().begin() as conn:
        _definir_usuario_auditoria(conn)
        empresa = conn.execute(
            text("SELECT id FROM empresas WHERE id = :empresa_id FOR UPDATE"),
            {"empresa_id": empresa_id},
        ).scalar_one_or_none()
        if empresa is None:
            raise ValueError("Empresa não encontrada para importação.")

        duplicado = conn.execute(text("""
            SELECT id FROM lotes_importacao
            WHERE empresa_id = :empresa_id AND arquivo_sha256 = :arquivo_sha256
              AND aba = :aba AND tipo_documento = :tipo_documento
              AND COALESCE(periodo, '') = COALESCE(:periodo, '')
              AND mapeamento = CAST(:mapeamento AS jsonb)
              AND status <> 'cancelado'
            ORDER BY id DESC LIMIT 1
        """), {
            "empresa_id": empresa_id, "arquivo_sha256": arquivo_sha256,
            "aba": aba, "tipo_documento": tipo_documento, "periodo": periodo,
            "mapeamento": mapeamento_json,
        }).scalar_one_or_none()
        if duplicado is not None:
            return {"duplicado": True, "lote_id": int(duplicado)}

        lote_id = conn.execute(text("""
            INSERT INTO lotes_importacao (
                empresa_id, nome_arquivo, arquivo_sha256, conteudo_original,
                aba, tipo_documento, periodo, mapeamento, total_linhas
            ) VALUES (
                :empresa_id, :nome_arquivo, :arquivo_sha256, :conteudo_original,
                :aba, :tipo_documento, :periodo, CAST(:mapeamento AS jsonb), :total_linhas
            ) RETURNING id
        """), {
            "empresa_id": empresa_id, "nome_arquivo": nome_arquivo,
            "arquivo_sha256": arquivo_sha256,
            "conteudo_original": conteudo_original,
            "aba": aba, "tipo_documento": tipo_documento,
            "periodo": periodo,
            "mapeamento": mapeamento_json,
            "total_linhas": len(linhas),
        }).scalar_one()

        parametros = [
            {
                "lote_id": lote_id,
                "empresa_id": empresa_id,
                "numero_linha": linha["numero_linha"],
                "dados_brutos": json.dumps(linha["dados_brutos"], ensure_ascii=False),
                "data": linha.get("data"),
                "descricao": linha.get("descricao"),
                "valor": linha.get("valor"),
                "tipo": linha.get("tipo"),
                "conta_contabil": linha.get("conta_contabil"),
                "filial": linha.get("filial"),
                "status": linha.get("status", "pendente"),
                "pendencias": json.dumps(linha.get("pendencias", []), ensure_ascii=False),
            }
            for linha in linhas
        ]
        conn.execute(text("""
            INSERT INTO linhas_preparadas (
                lote_id, empresa_id, numero_linha, dados_brutos, data,
                descricao, valor, tipo, conta_contabil, filial, status, pendencias
            ) VALUES (
                :lote_id, :empresa_id, :numero_linha, CAST(:dados_brutos AS jsonb),
                :data, :descricao, :valor, :tipo, :conta_contabil, :filial,
                :status, CAST(:pendencias AS jsonb)
            )
        """), parametros)

    return {"duplicado": False, "lote_id": int(lote_id), "total_linhas": len(linhas)}


def listar_lotes_preparacao(empresa_id: int, periodo: str | None = None) -> list[dict]:
    sql = """
        SELECT lote.id, lote.nome_arquivo, lote.aba, lote.tipo_documento,
               lote.periodo, lote.total_linhas, lote.status, lote.criado_em,
               (SELECT COUNT(*) FROM linhas_preparadas linha
                WHERE linha.lote_id = lote.id AND linha.status = 'pendente') AS pendentes
        FROM lotes_importacao lote WHERE lote.empresa_id = :empresa_id
    """
    parametros = {"empresa_id": empresa_id}
    if periodo:
        sql += " AND lote.periodo = :periodo"
        parametros["periodo"] = periodo
    sql += " ORDER BY lote.criado_em DESC, lote.id DESC"
    with _get_engine().connect() as conn:
        return [dict(linha._mapping) for linha in conn.execute(text(sql), parametros)]


def listar_periodos_preparacao(empresa_id: int) -> list[str]:
    with _get_engine().connect() as conn:
        resultado = conn.execute(text("""
            SELECT DISTINCT periodo FROM lotes_importacao
            WHERE empresa_id = :empresa_id AND periodo IS NOT NULL
            ORDER BY periodo DESC
        """), {"empresa_id": empresa_id})
        return [linha[0] for linha in resultado]


def carregar_linhas_preparadas(
    empresa_id: int, lote_id: int, limite: int = 100, deslocamento: int = 0,
) -> list[dict]:
    with _get_engine().connect() as conn:
        resultado = conn.execute(text("""
            SELECT id, lote_id, numero_linha, dados_brutos, data, descricao,
                   valor, tipo, conta_contabil, filial, status, pendencias
            FROM linhas_preparadas
            WHERE empresa_id = :empresa_id AND lote_id = :lote_id
            ORDER BY numero_linha
            LIMIT :limite OFFSET :deslocamento
        """), {
            "empresa_id": empresa_id, "lote_id": lote_id,
            "limite": limite, "deslocamento": deslocamento,
        })
        return [dict(linha._mapping) for linha in resultado]


def carregar_linhas_para_exportacao(empresa_id: int, lote_id: int) -> list[dict]:
    with _get_engine().connect() as conn:
        resultado = conn.execute(text("""
            SELECT id, numero_linha, dados_brutos, data, descricao, valor, tipo,
                   conta_contabil, filial, status
            FROM linhas_preparadas
            WHERE empresa_id = :empresa_id AND lote_id = :lote_id
            ORDER BY numero_linha
        """), {"empresa_id": empresa_id, "lote_id": lote_id})
        return [dict(linha._mapping) for linha in resultado]


def atualizar_linha_preparada(
    empresa_id: int, linha_id: int, campos: dict, pendencias: list[str],
) -> None:
    import json

    permitidos = {
        "data", "descricao", "valor", "tipo", "conta_contabil", "filial"
    }
    if set(campos) != permitidos:
        raise ValueError("Campos de edição incompletos ou desconhecidos.")
    parametros = {
        **campos,
        "empresa_id": empresa_id,
        "linha_id": linha_id,
        "status": "pendente" if pendencias else "validado",
        "pendencias": json.dumps(pendencias, ensure_ascii=False),
    }
    with _get_engine().begin() as conn:
        _definir_usuario_auditoria(conn)
        resultado = conn.execute(text("""
            UPDATE linhas_preparadas
            SET data = :data, descricao = :descricao, valor = :valor,
                tipo = :tipo, conta_contabil = :conta_contabil,
                filial = :filial, status = :status,
                pendencias = CAST(:pendencias AS jsonb),
                alterado_em = CURRENT_TIMESTAMP
            WHERE id = :linha_id AND empresa_id = :empresa_id
        """), parametros)
        if resultado.rowcount != 1:
            raise ValueError("Linha não encontrada para esta empresa.")

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


def renomear_empresa(empresa_id: int, novo_nome: str) -> None:
    sql = text("UPDATE empresas SET nome = :nome WHERE id = :id")
    try:
        with _get_engine().begin() as conn:
            conn.execute(sql, {"id": empresa_id, "nome": novo_nome})
        logger.info("Empresa %d renomeada para '%s'.", empresa_id, novo_nome)
    except SQLAlchemyError as exc:
        logger.error("Erro ao renomear empresa %d: %s", empresa_id, exc)
        raise exc


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
        "SELECT id, titulo, atualizado_em, favorito "
        "FROM conversas ORDER BY favorito DESC, atualizado_em DESC"
    )
    try:
        with _get_engine().connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [
            {"id": row[0], "titulo": row[1], "atualizado_em": row[2], "favorito": row[3]}
            for row in rows
        ]
    except SQLAlchemyError as exc:
        logger.error("Erro ao listar conversas: %s", exc)
        return []


def favoritar_conversa(conversa_id: int, favorito: bool) -> None:
    sql = text("UPDATE conversas SET favorito = :favorito WHERE id = :id")
    try:
        with _get_engine().begin() as conn:
            conn.execute(sql, {"id": conversa_id, "favorito": favorito})
    except SQLAlchemyError as exc:
        logger.error("Erro ao favoritar conversa %d: %s", conversa_id, exc)
        raise exc


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
