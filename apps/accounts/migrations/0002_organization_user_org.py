import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _create_default_org_and_assign_users(apps, schema_editor):
    Organization = apps.get_model('accounts', 'Organization')
    User = apps.get_model('accounts', 'User')

    org, _ = Organization.objects.get_or_create(
        slug='default',
        defaults={'name': 'Organización Principal'},
    )
    User.objects.filter(organization__isnull=True).update(organization=org)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('buildings', '0002_apartment_qr_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=80, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='user',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='accounts.organization',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='extra_organizations',
            field=models.ManyToManyField(
                blank=True,
                help_text='Additional organizations this admin can manage',
                related_name='extra_admins',
                to='accounts.organization',
            ),
        ),
        migrations.RunPython(
            code=_create_default_org_and_assign_users,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
