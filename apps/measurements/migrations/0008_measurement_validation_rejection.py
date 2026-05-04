import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('measurements', '0007_alter_measurement_reading_value_decimals'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='measurement',
            name='validated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='validated_measurements',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='measurement',
            name='validated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='rejected_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rejected_measurements',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='measurement',
            name='rejected_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='measurement',
            name='rejection_category',
            field=models.CharField(
                blank=True,
                choices=[('photo', 'Foto'), ('reading', 'Medición manual incorrecta')],
                default='',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='measurement',
            name='rejection_reason',
            field=models.TextField(blank=True, default=''),
        ),
    ]
