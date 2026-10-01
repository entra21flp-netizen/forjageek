from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("dioramas_novo", "0003_cenarios_super_herois"),
        ("inventario", "0013_remove_diorama_legado"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dioramageradonovo",
            options={
                "ordering": ["-data_criacao"],
                "verbose_name": "Diorama criado pelo usuário",
                "verbose_name_plural": "Dioramas criados pelos usuários",
            },
        ),
        migrations.AlterModelOptions(
            name="dioramapresetnovo",
            options={
                "ordering": ["nome"],
                "verbose_name": "Diorama padrão",
                "verbose_name_plural": "Dioramas padrão",
            },
        ),
        migrations.AlterModelTable(
            name="dioramageradonovo",
            table="dioramas_ia",
        ),
        migrations.AlterModelTable(
            name="dioramapresetnovo",
            table="dioramas_padrao",
        ),
    ]
