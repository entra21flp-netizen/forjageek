from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("inventario", "0002_initial")]

    operations = [
        migrations.AddField(
            model_name="estantevirtual",
            name="quantidade_dioramas",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.CreateModel(
            name="Diorama",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(default="Meu diorama", max_length=100)),
                ("descricao", models.CharField(blank=True, max_length=180)),
                ("ordem", models.PositiveSmallIntegerField()),
                ("estante", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dioramas", to="inventario.estantevirtual")),
            ],
            options={"ordering": ["ordem"]},
        ),
        migrations.AddConstraint(
            model_name="diorama",
            constraint=models.UniqueConstraint(fields=("estante", "ordem"), name="uniq_diorama_por_posicao"),
        ),
    ]
