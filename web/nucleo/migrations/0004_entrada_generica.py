import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


TABELAS_ENTRADA = (
    "django_arquivos_entrada_temporarios",
    "django_modelos_mapeamento_entrada",
)
SEQUENCIAS_ENTRADA = ("django_modelos_mapeamento_entrada_id_seq",)


def proteger_tabelas_entrada(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    nomes = ", ".join(f'"{nome}"' for nome in TABELAS_ENTRADA)
    sequencias = ", ".join(f'"{nome}"' for nome in SEQUENCIAS_ENTRADA)
    with schema_editor.connection.cursor() as cursor:
        for tabela, coluna in (
            ("django_arquivos_entrada_temporarios", "empresa_id"),
            ("django_modelos_mapeamento_entrada", "empresa_id"),
        ):
            cursor.execute(
                f'ALTER TABLE "{tabela}" ADD CONSTRAINT "fk_{tabela}_empresa" '
                f'FOREIGN KEY ("{coluna}") REFERENCES empresas(id) ON DELETE RESTRICT'
            )
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
        ("nucleo", "0003_trabalho_operacional"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArquivoEntradaTemporario",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("empresa_id", models.PositiveIntegerField()),
                ("competencia", models.CharField(max_length=7)),
                ("nome_original", models.CharField(max_length=255)),
                ("extensao", models.CharField(max_length=5)),
                ("tamanho_bytes", models.PositiveIntegerField()),
                ("arquivo_sha256", models.CharField(max_length=64)),
                ("conteudo", models.BinaryField()),
                ("inspecao", models.JSONField(default=dict)),
                ("status", models.CharField(choices=[("recebido", "Recebido"), ("em_mapeamento", "Em mapeamento"), ("preparado", "Preparado"), ("descartado", "Descartado")], default="recebido", max_length=20)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="arquivos_entrada_temporarios", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "arquivo temporário de entrada", "verbose_name_plural": "arquivos temporários de entrada", "db_table": "django_arquivos_entrada_temporarios"},
        ),
        migrations.CreateModel(
            name="ModeloMapeamentoEntrada",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("empresa_id", models.PositiveIntegerField()),
                ("assinatura_estrutura", models.CharField(max_length=64)),
                ("tipo_documento", models.CharField(max_length=20)),
                ("aba", models.CharField(max_length=255)),
                ("linha_cabecalho", models.PositiveIntegerField(default=0)),
                ("mapeamento", models.JSONField(default=dict)),
                ("vezes_utilizado", models.PositiveIntegerField(default=1)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                ("confirmado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="modelos_mapeamento_confirmados", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "modelo de mapeamento de entrada", "verbose_name_plural": "modelos de mapeamento de entrada", "db_table": "django_modelos_mapeamento_entrada"},
        ),
        migrations.AddConstraint(model_name="arquivoentradatemporario", constraint=models.CheckConstraint(condition=models.Q(("empresa_id__gt", 0)), name="ck_arq_ent_empresa_pos")),
        migrations.AddConstraint(model_name="arquivoentradatemporario", constraint=models.CheckConstraint(condition=models.Q(("competencia__regex", "^[0-9]{4}-(0[1-9]|1[0-2])$")), name="ck_arq_ent_periodo")),
        migrations.AddConstraint(model_name="arquivoentradatemporario", constraint=models.CheckConstraint(condition=models.Q(("extensao__in", ("xlsx", "xls", "csv"))), name="ck_arq_ent_extensao")),
        migrations.AddConstraint(model_name="arquivoentradatemporario", constraint=models.CheckConstraint(condition=models.Q(("status__in", ["recebido", "em_mapeamento", "preparado", "descartado"])), name="ck_arq_ent_status")),
        migrations.AddIndex(model_name="arquivoentradatemporario", index=models.Index(fields=["usuario", "empresa_id", "competencia", "status"], name="idx_arq_ent_contexto")),
        migrations.AddIndex(model_name="arquivoentradatemporario", index=models.Index(fields=["empresa_id", "arquivo_sha256"], name="idx_arq_ent_hash")),
        migrations.AddConstraint(model_name="modelomapeamentoentrada", constraint=models.UniqueConstraint(fields=("empresa_id", "assinatura_estrutura", "tipo_documento"), name="uq_mod_map_empresa_estrutura_tipo")),
        migrations.AddConstraint(model_name="modelomapeamentoentrada", constraint=models.CheckConstraint(condition=models.Q(("empresa_id__gt", 0)), name="ck_mod_map_empresa_pos")),
        migrations.AddConstraint(model_name="modelomapeamentoentrada", constraint=models.CheckConstraint(condition=models.Q(("tipo_documento__in", ("extrato", "folha", "notas", "lancamentos", "outro"))), name="ck_mod_map_tipo")),
        migrations.AddIndex(model_name="modelomapeamentoentrada", index=models.Index(fields=["empresa_id", "assinatura_estrutura"], name="idx_mod_map_estrutura")),
        migrations.RunPython(proteger_tabelas_entrada, reverse_code=migrations.RunPython.noop),
    ]
