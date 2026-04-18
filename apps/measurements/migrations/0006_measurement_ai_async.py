# Generated manually for async AI analysis

from django.db import migrations, models


def mark_existing_complete(apps, schema_editor):
    Measurement = apps.get_model('measurements', 'Measurement')
    Measurement.objects.all().update(ai_analysis_status='complete')


class Migration(migrations.Migration):

    dependencies = [
        ('measurements', '0005_measurement_audit_log'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='ai_analysis_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pendiente'),
                    ('processing', 'Procesando'),
                    ('complete', 'Completo'),
                    ('failed', 'Falló'),
                    ('skipped', 'Omitido'),
                ],
                default='skipped',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='measurement',
            name='ai_agrees_with_operator',
            field=models.BooleanField(
                blank=True,
                help_text='Si hubo lectura manual e IA: True si coinciden, False si no, null si no aplica.',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='measurement',
            name='reading_value',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.RunPython(mark_existing_complete, migrations.RunPython.noop),
    ]
