from django.db import models


class MeasurementCycle(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        IN_PROGRESS = 'in_progress', 'En Curso'
        COMPLETED = 'completed', 'Completado'
        CLOSED = 'closed', 'Cerrado'

    name = models.CharField(max_length=100)
    building = models.ForeignKey(
        'buildings.Building',
        on_delete=models.PROTECT,
        related_name='cycles',
    )
    year = models.IntegerField()
    month = models.IntegerField()
    scheduled_date = models.DateField(help_text='Fecha programada para realizar las mediciones')
    deadline = models.DateField(help_text='Fecha límite para completar el ciclo')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    enforce = models.BooleanField(
        default=False,
        help_text='Si es True, solo se aceptan mediciones para los departamentos '
                  'asignados a este ciclo mientras esté in_progress.',
    )
    apartments = models.ManyToManyField(
        'buildings.Apartment',
        blank=True,
        related_name='cycles',
        help_text='Departamentos incluidos en este ciclo. '
                  'Si vacío, se consideran todos los del edificio.',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-month']

    def __str__(self):
        return f'{self.name} — {self.building.name}'

    @property
    def month_name(self):
        months = [
            '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
        ]
        return months[self.month] if 1 <= self.month <= 12 else str(self.month)

    def get_target_apartments(self):
        """Return apartments in this cycle: explicit list, or all from building."""
        if self.apartments.exists():
            return self.apartments.all()
        from apps.buildings.models import Apartment
        return Apartment.objects.filter(tower__building=self.building)
