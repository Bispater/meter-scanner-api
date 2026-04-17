from django.db import migrations, models


def _populate_qr_codes(apps, schema_editor):
    Apartment = apps.get_model('buildings', 'Apartment')
    for apt in Apartment.objects.select_related('tower').all():
        short = apt.tower.name.replace('Torre ', '').replace('torre ', '').strip()
        apt.qr_code = f'{apt.number}{short}'
        apt.save(update_fields=['qr_code'])


class Migration(migrations.Migration):

    dependencies = [
        ('buildings', '0001_initial'),
    ]

    operations = [
        # Remove unique constraint from meter_id and make it optional
        migrations.AlterField(
            model_name='apartment',
            name='meter_id',
            field=models.CharField(blank=True, default='', max_length=50),
        ),
        # Add qr_code field (initially blank=True so existing rows don't fail)
        migrations.AddField(
            model_name='apartment',
            name='qr_code',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Identificador único del departamento para QR. Formato: NúmeroTorre (ej: 1409A)",
                max_length=50,
            ),
        ),
        # Populate qr_code for existing rows via a data migration
        migrations.RunPython(
            code=_populate_qr_codes,
            reverse_code=migrations.RunPython.noop,
        ),
        # Now enforce uniqueness
        migrations.AlterField(
            model_name='apartment',
            name='qr_code',
            field=models.CharField(
                blank=True,
                help_text="Identificador único del departamento para QR. Formato: NúmeroTorre (ej: 1409A)",
                max_length=50,
                unique=True,
            ),
        ),
    ]
