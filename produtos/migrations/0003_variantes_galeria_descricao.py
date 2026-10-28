import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0002_produto_imagem'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='descricao',
            field=models.TextField(blank=True, verbose_name='descrição'),
        ),
        migrations.AddField(
            model_name='produto',
            name='caracteristicas',
            field=models.TextField(blank=True, help_text='Uma característica por linha.', verbose_name='características'),
        ),
        migrations.AddField(
            model_name='produto',
            name='material',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='produto',
            name='tabela_medidas',
            field=models.TextField(blank=True, help_text='Uma linha por tamanho, colunas separadas por | . A primeira linha é o cabeçalho. Ex.: Tamanho | Altura | Peso. Deixe vazio se o produto não usa tabela.', verbose_name='tabela de medidas'),
        ),
        migrations.AddField(
            model_name='produto',
            name='criado_em',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.CreateModel(
            name='ImagemProduto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagem', models.ImageField(upload_to='produtos/galeria/')),
                ('legenda', models.CharField(blank=True, max_length=120)),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='imagens', to='produtos.produto')),
            ],
            options={
                'verbose_name': 'imagem da galeria',
                'verbose_name_plural': 'imagens da galeria',
                'ordering': ['ordem', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='Variante',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tamanho', models.CharField(blank=True, max_length=20)),
                ('cor', models.CharField(blank=True, max_length=40)),
                ('estoque', models.PositiveIntegerField(default=0)),
                ('ativo', models.BooleanField(default=True)),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variantes', to='produtos.produto')),
            ],
            options={
                'ordering': ['ordem', 'tamanho', 'cor'],
            },
        ),
        migrations.AddConstraint(
            model_name='variante',
            constraint=models.UniqueConstraint(fields=('produto', 'tamanho', 'cor'), name='variante_unica_por_produto'),
        ),
    ]
