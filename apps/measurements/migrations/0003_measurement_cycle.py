from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('measurements', '0002_measurement_ocr_fields'),
        ('cycles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='cycle',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='measurements',
                to='cycles.measurementcycle',
            ),
        ),
    ]
