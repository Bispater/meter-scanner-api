import django.db.models.deletion
from django.db import migrations, models


def _assign_buildings_to_default_org(apps, schema_editor):
    Organization = apps.get_model('accounts', 'Organization')
    Building = apps.get_model('buildings', 'Building')

    org = Organization.objects.filter(slug='default').first()
    if org:
        Building.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ('buildings', '0002_apartment_qr_code'),
        ('accounts', '0002_organization_user_org'),
    ]

    operations = [
        migrations.AddField(
            model_name='building',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='buildings',
                to='accounts.organization',
            ),
        ),
        migrations.RunPython(
            code=_assign_buildings_to_default_org,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
