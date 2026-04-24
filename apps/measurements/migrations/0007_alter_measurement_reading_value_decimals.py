from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("measurements", "0006_measurement_ai_async"),
    ]

    operations = [
        migrations.AlterField(
            model_name="measurement",
            name="reading_value",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Lectura del operador (hasta 4 decimales, alineado con cara 5+4); si está vacía puede completarse con la estimación por IA.",
                max_digits=12,
                null=True,
            ),
        ),
    ]
