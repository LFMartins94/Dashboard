from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def preparar_auditoria_postgres(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
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
            CREATE INDEX IF NOT EXISTS idx_historico_alteracoes_registro
                ON historico_alteracoes(tabela, registro_id, alterado_em DESC);
            CREATE INDEX IF NOT EXISTS idx_historico_alteracoes_empresa
                ON historico_alteracoes(empresa_id, alterado_em DESC);
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

            DROP TRIGGER IF EXISTS historico_linhas_preparadas ON linhas_preparadas;
            CREATE TRIGGER historico_linhas_preparadas
                AFTER INSERT OR UPDATE OR DELETE ON linhas_preparadas
                FOR EACH ROW EXECUTE FUNCTION public.registrar_historico_alteracoes();
            DROP TRIGGER IF EXISTS historico_lancamentos ON lancamentos;
            CREATE TRIGGER historico_lancamentos
                AFTER INSERT OR UPDATE OR DELETE ON lancamentos
                FOR EACH ROW EXECUTE FUNCTION public.registrar_historico_alteracoes();

            ALTER TABLE django_estados_ocorrencias_auditoria ENABLE ROW LEVEL SECURITY;
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    EXECUTE 'REVOKE ALL ON TABLE historico_alteracoes, django_estados_ocorrencias_auditoria FROM anon';
                    EXECUTE 'REVOKE ALL ON SEQUENCE django_estados_ocorrencias_auditoria_id_seq FROM anon';
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    EXECUTE 'REVOKE ALL ON TABLE historico_alteracoes, django_estados_ocorrencias_auditoria FROM authenticated';
                    EXECUTE 'REVOKE ALL ON SEQUENCE django_estados_ocorrencias_auditoria_id_seq FROM authenticated';
                END IF;
            END $$;
            REVOKE ALL ON FUNCTION public.registrar_historico_alteracoes()
                FROM PUBLIC;
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("nucleo", "0005_revisoes_conciliacao"),
    ]

    operations = [
        migrations.CreateModel(
            name="EstadoOcorrenciaAuditoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ocorrencia_id", models.BigIntegerField(unique=True)),
                ("empresa_id", models.PositiveIntegerField()),
                ("competencia", models.CharField(max_length=7)),
                ("resolvida", models.BooleanField(default=False)),
                ("justificativa", models.CharField(blank=True, max_length=500)),
                ("resolvida_em", models.DateTimeField(blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("resolvida_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ocorrencias_auditoria_resolvidas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "estado de ocorrência de auditoria", "verbose_name_plural": "estados de ocorrências de auditoria", "db_table": "django_estados_ocorrencias_auditoria"},
        ),
        migrations.AddConstraint(model_name="estadoocorrenciaauditoria", constraint=models.CheckConstraint(condition=models.Q(("empresa_id__gt", 0)), name="ck_est_aud_empresa_pos")),
        migrations.AddConstraint(model_name="estadoocorrenciaauditoria", constraint=models.CheckConstraint(condition=models.Q(("competencia__regex", "^[0-9]{4}-(0[1-9]|1[0-2])$")), name="ck_est_aud_periodo")),
        migrations.AddIndex(model_name="estadoocorrenciaauditoria", index=models.Index(fields=["empresa_id", "competencia", "resolvida"], name="idx_est_aud_contexto")),
        migrations.RunPython(preparar_auditoria_postgres, reverse_code=migrations.RunPython.noop),
    ]
