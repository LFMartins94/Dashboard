from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def proteger_revisoes_conciliacao(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            'ALTER TABLE "django_revisoes_conciliacao" ADD CONSTRAINT '
            '"fk_django_revisoes_conciliacao_empresa" FOREIGN KEY ("empresa_id") '
            'REFERENCES empresas(id) ON DELETE RESTRICT'
        )
        cursor.execute('ALTER TABLE "django_revisoes_conciliacao" ENABLE ROW LEVEL SECURITY')
        cursor.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    EXECUTE 'REVOKE ALL ON TABLE django_revisoes_conciliacao FROM anon';
                    EXECUTE 'REVOKE ALL ON SEQUENCE django_revisoes_conciliacao_id_seq FROM anon';
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    EXECUTE 'REVOKE ALL ON TABLE django_revisoes_conciliacao FROM authenticated';
                    EXECUTE 'REVOKE ALL ON SEQUENCE django_revisoes_conciliacao_id_seq FROM authenticated';
                END IF;
            END
            $$;
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("nucleo", "0004_entrada_generica"),
    ]

    operations = [
        migrations.CreateModel(
            name="RevisaoConciliacao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("empresa_id", models.PositiveIntegerField()),
                ("competencia", models.CharField(max_length=7)),
                ("lote_extrato_id", models.BigIntegerField()),
                ("lote_referencia_id", models.BigIntegerField()),
                ("linha_extrato_id", models.BigIntegerField()),
                ("linha_referencia_id", models.BigIntegerField()),
                ("decisao", models.CharField(choices=[("confirmada", "Confirmada"), ("rejeitada", "Rejeitada"), ("manual", "Ajuste manual")], max_length=15)),
                ("justificativa", models.CharField(blank=True, max_length=500)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("decidido_por", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="revisoes_conciliacao", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "revisão de conciliação", "verbose_name_plural": "revisões de conciliação", "db_table": "django_revisoes_conciliacao"},
        ),
        migrations.AddConstraint(model_name="revisaoconciliacao", constraint=models.UniqueConstraint(fields=("empresa_id", "competencia", "lote_extrato_id", "lote_referencia_id", "linha_extrato_id", "linha_referencia_id"), name="uq_rev_conc_linhas")),
        migrations.AddConstraint(model_name="revisaoconciliacao", constraint=models.CheckConstraint(condition=models.Q(("empresa_id__gt", 0)), name="ck_rev_conc_empresa_pos")),
        migrations.AddConstraint(model_name="revisaoconciliacao", constraint=models.CheckConstraint(condition=models.Q(("competencia__regex", "^[0-9]{4}-(0[1-9]|1[0-2])$")), name="ck_rev_conc_periodo")),
        migrations.AddConstraint(model_name="revisaoconciliacao", constraint=models.CheckConstraint(condition=models.Q(("decisao__in", ["confirmada", "rejeitada", "manual"])), name="ck_rev_conc_decisao")),
        migrations.AddIndex(model_name="revisaoconciliacao", index=models.Index(fields=["empresa_id", "competencia", "lote_extrato_id", "lote_referencia_id"], name="idx_rev_conc_contexto")),
        migrations.RunPython(proteger_revisoes_conciliacao, reverse_code=migrations.RunPython.noop),
    ]
