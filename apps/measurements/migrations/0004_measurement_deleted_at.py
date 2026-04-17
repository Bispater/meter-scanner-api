from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('measurements', '0003_measurement_cycle'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='deleted_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text='Si está definido, la medición está en papelera (soft delete).',
                null=True,
            ),
        ),
    ]
