from django.db import migrations


TABELAS_INTERNAS = (
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
    "django_content_type",
    "django_migrations",
    "django_session",
    "django_tentativas_login",
)


def proteger_tabelas(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    nomes = ", ".join(f'"{nome}"' for nome in TABELAS_INTERNAS)
    with schema_editor.connection.cursor() as cursor:
        for tabela in TABELAS_INTERNAS:
            cursor.execute(f'ALTER TABLE "{tabela}" ENABLE ROW LEVEL SECURITY')
        cursor.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                    EXECUTE 'REVOKE ALL ON TABLE {nomes} FROM anon';
                END IF;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                    EXECUTE 'REVOKE ALL ON TABLE {nomes} FROM authenticated';
                END IF;
            END
            $$;
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("nucleo", "0001_tentativa_login"),
        ("sessions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(proteger_tabelas, reverse_code=migrations.RunPython.noop),
    ]
