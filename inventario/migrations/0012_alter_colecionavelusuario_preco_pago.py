from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0011_itemestante_diorama_novo_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="colecionavelusuario",
            name="preco_pago",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True),
        ),
    ]
