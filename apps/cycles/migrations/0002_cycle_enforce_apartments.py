from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('buildings', '0001_initial'),
        ('cycles', '0001_initial'),
    ]

    operations = [
        # Remove the unique_together constraint so multiple cycles
        # can exist for the same building+year+month.
        migrations.AlterUniqueTogether(
            name='measurementcycle',
            unique_together=set(),
        ),
        # Per-cycle enforcement flag.
        migrations.AddField(
            model_name='measurementcycle',
            name='enforce',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'Si es True, solo se aceptan mediciones para los departamentos '
                    'asignados a este ciclo mientras esté in_progress.'
                ),
            ),
        ),
        # M2M: specific apartments assigned to a cycle.
        # If empty, all apartments from the building are considered.
        migrations.AddField(
            model_name='measurementcycle',
            name='apartments',
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    'Departamentos incluidos en este ciclo. '
                    'Si vacío, se consideran todos los del edificio.'
                ),
                related_name='cycles',
                to='buildings.apartment',
            ),
        ),
    ]
