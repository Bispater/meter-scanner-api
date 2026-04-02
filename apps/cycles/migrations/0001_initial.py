from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('buildings', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeasurementCycle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('year', models.IntegerField()),
                ('month', models.IntegerField()),
                ('scheduled_date', models.DateField(help_text='Fecha programada para realizar las mediciones')),
                ('deadline', models.DateField(help_text='Fecha límite para completar el ciclo')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendiente'),
                        ('in_progress', 'En Curso'),
                        ('completed', 'Completado'),
                        ('closed', 'Cerrado'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('building', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='cycles',
                    to='buildings.building',
                )),
            ],
            options={
                'ordering': ['-year', '-month'],
                'unique_together': {('building', 'year', 'month')},
            },
        ),
    ]
