from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('buildings', '0003_building_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='apartment',
            name='reading_layout',
            field=models.CharField(
                choices=[('A', 'Tipo A (5 enteros + 4 esferas)'), ('B', 'Tipo B (8 rodillos + 1 esfera)')],
                default='A',
                help_text='Disposición de la lectura de 9 dígitos (A o B).',
                max_length=1,
            ),
        ),
    ]
