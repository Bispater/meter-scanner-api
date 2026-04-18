# Generated manually for MeasurementAuditLog

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('measurements', '0004_measurement_deleted_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeasurementAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(max_length=64)),
                ('old_value', models.TextField(blank=True)),
                ('new_value', models.TextField(blank=True)),
                ('note', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('edited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='measurement_audit_edits', to=settings.AUTH_USER_MODEL)),
                ('measurement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='measurements.measurement')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
