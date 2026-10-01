from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


TABELAS_TRABALHO = (
    "django_competencias_trabalho",
    "django_itens_checklist_trabalho",
)
SEQUENCIAS_TRABALHO = (
    "django_competencias_trabalho_id_seq",
    "django_itens_checklist_trabalho_id_seq",
)


def proteger_tabelas_trabalho(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    nomes = ", ".join(f'"{nome}"' for nome in TABELAS_TRABALHO)
    sequencias = ", ".join(f'"{nome}"' for nome in SEQUENCIAS_TRABALHO)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE "django_competencias_trabalho"
            ADD CONSTRAINT "fk_comp_trabalho_empresa"
            FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE RESTRICT
            """
        )
        for tabela in TABELAS_TRABALHO:
            cursor.execute(f'ALTER TABLE "{tabela}" ENABLE ROW LEVEL SECURITY')
        cursor.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    EXECUTE 'REVOKE ALL ON TABLE {nomes} FROM anon';
                    EXECUTE 'REVOKE ALL ON SEQUENCE {sequencias} FROM anon';
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    EXECUTE 'REVOKE ALL ON TABLE {nomes} FROM authenticated';
                    EXECUTE 'REVOKE ALL ON SEQUENCE {sequencias} FROM authenticated';
                END IF;
            END
            $$;
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("nucleo", "0002_proteger_tabelas_django"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompetenciaTrabalho",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("empresa_id", models.PositiveIntegerField()),
                ("competencia", models.CharField(max_length=7)),
                ("estado", models.CharField(choices=[("aguardando", "Aguardando"), ("recebido", "Recebido"), ("em_conferencia", "Em conferência"), ("com_divergencia", "Com divergência"), ("revisado", "Revisado"), ("entregue", "Entregue")], default="aguardando", max_length=20)),
                ("prazo_entrega", models.DateField(blank=True, null=True)),
                ("iniciado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("iniciado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="competencias_iniciadas", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "competência de trabalho", "verbose_name_plural": "competências de trabalho", "db_table": "django_competencias_trabalho"},
        ),
        migrations.CreateModel(
            name="ItemChecklistTrabalho",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=160)),
                ("categoria", models.CharField(choices=[("documento", "Documento"), ("conferencia", "Conferência"), ("divergencia", "Divergência"), ("entrega", "Entrega")], max_length=20)),
                ("estado", models.CharField(choices=[("aguardando", "Aguardando"), ("recebido", "Recebido"), ("em_conferencia", "Em conferência"), ("com_divergencia", "Com divergência"), ("revisado", "Revisado"), ("entregue", "Entregue")], default="aguardando", max_length=20)),
                ("ordem", models.PositiveSmallIntegerField(default=0)),
                ("obrigatorio", models.BooleanField(default=True)),
                ("rota_destino", models.CharField(max_length=80)),
                ("concluido_em", models.DateTimeField(blank=True, null=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("atualizado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="itens_checklist_atualizados", to=settings.AUTH_USER_MODEL)),
                ("competencia_trabalho", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="itens", to="nucleo.competenciatrabalho")),
            ],
            options={"verbose_name": "item do checklist", "verbose_name_plural": "itens do checklist", "db_table": "django_itens_checklist_trabalho"},
        ),
        migrations.AddConstraint(model_name="competenciatrabalho", constraint=models.UniqueConstraint(fields=("empresa_id", "competencia"), name="uq_comp_empresa_periodo")),
        migrations.AddConstraint(model_name="competenciatrabalho", constraint=models.CheckConstraint(condition=models.Q(("empresa_id__gt", 0)), name="ck_comp_empresa_pos")),
        migrations.AddConstraint(model_name="competenciatrabalho", constraint=models.CheckConstraint(condition=models.Q(("competencia__regex", "^[0-9]{4}-(0[1-9]|1[0-2])$")), name="ck_comp_periodo")),
        migrations.AddConstraint(model_name="competenciatrabalho", constraint=models.CheckConstraint(condition=models.Q(("estado__in", ["aguardando", "recebido", "em_conferencia", "com_divergencia", "revisado", "entregue"])), name="ck_comp_estado")),
        migrations.AddIndex(model_name="competenciatrabalho", index=models.Index(fields=["empresa_id", "estado", "competencia"], name="idx_comp_empresa_estado")),
        migrations.AddConstraint(model_name="itemchecklisttrabalho", constraint=models.UniqueConstraint(fields=("competencia_trabalho", "titulo"), name="uq_item_comp_titulo")),
        migrations.AddConstraint(model_name="itemchecklisttrabalho", constraint=models.CheckConstraint(condition=models.Q(("categoria__in", ["documento", "conferencia", "divergencia", "entrega"])), name="ck_item_categoria")),
        migrations.AddConstraint(model_name="itemchecklisttrabalho", constraint=models.CheckConstraint(condition=models.Q(("estado__in", ["aguardando", "recebido", "em_conferencia", "com_divergencia", "revisado", "entregue"])), name="ck_item_estado")),
        migrations.AddConstraint(model_name="itemchecklisttrabalho", constraint=models.CheckConstraint(condition=models.Q(("rota_destino__in", ["nucleo:entradas", "nucleo:conferencia", "nucleo:entregas"])), name="ck_item_rota")),
        migrations.AddIndex(model_name="itemchecklisttrabalho", index=models.Index(fields=["competencia_trabalho", "estado", "ordem"], name="idx_item_comp_estado")),
        migrations.RunPython(proteger_tabelas_trabalho, reverse_code=migrations.RunPython.noop),
    ]
