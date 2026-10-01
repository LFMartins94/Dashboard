from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TentativaLogin",
            fields=[
                (
                    "chave_hash",
                    models.CharField(max_length=64, primary_key=True, serialize=False),
                ),
                ("tentativas", models.PositiveSmallIntegerField(default=0)),
                ("janela_iniciada_em", models.DateTimeField()),
                ("bloqueado_ate", models.DateTimeField(blank=True, null=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "tentativa de login",
                "verbose_name_plural": "tentativas de login",
                "db_table": "django_tentativas_login",
            },
        ),
        migrations.AddIndex(
            model_name="tentativalogin",
            index=models.Index(
                fields=["bloqueado_ate"], name="idx_login_bloqueio"
            ),
        ),
    ]
