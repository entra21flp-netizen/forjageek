from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0012_alter_colecionavelusuario_preco_pago"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="diorama",
            name="uniq_diorama_por_posicao",
        ),
        migrations.DeleteModel(
            name="Diorama",
        ),
    ]
