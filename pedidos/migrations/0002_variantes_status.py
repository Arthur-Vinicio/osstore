import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0001_initial'),
        ('produtos', '0003_variantes_galeria_descricao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pedido',
            name='status',
            field=models.CharField(choices=[('novo', 'Pendente'), ('pago', 'Pago'), ('enviado', 'Enviado'), ('entregue', 'Entregue'), ('cancelado', 'Cancelado')], default='novo', max_length=20),
        ),
        migrations.AddField(
            model_name='itempedido',
            name='variante',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='produtos.variante'),
        ),
        migrations.AddField(
            model_name='itempedido',
            name='descricao_variante',
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
