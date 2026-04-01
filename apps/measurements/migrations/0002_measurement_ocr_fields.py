from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('measurements', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='ocr_value',
            field=models.CharField(blank=True, default='', help_text='Valor original detectado por OCR/IA', max_length=50),
        ),
        migrations.AddField(
            model_name='measurement',
            name='modified_by_user',
            field=models.BooleanField(default=False, help_text='True si el operador editó el valor OCR'),
        ),
    ]
