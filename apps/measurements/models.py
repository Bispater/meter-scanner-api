from django.db import models
from django.conf import settings


class MeasurementQuerySet(models.QuerySet):
    def active_only(self):
        return self.filter(deleted_at__isnull=True)


class ActiveMeasurementManager(models.Manager):
    """Solo mediciones no eliminadas (eliminación lógica)."""

    def get_queryset(self):
        return MeasurementQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


class AllMeasurementsManager(models.Manager):
    """Incluye eliminadas (papelera / restauración)."""

    def get_queryset(self):
        return MeasurementQuerySet(self.model, using=self._db)


class Measurement(models.Model):
    class Status(models.TextChoices):
        VERIFIED = 'verified', 'Validado'
        PENDING_REVIEW = 'pending_review', 'Pendiente'
        REJECTED = 'rejected', 'Rechazado'

    class MeterType(models.TextChoices):
        ANALOG = 'analog', 'Analógico'
        DIGITAL_DRUM = 'digital_drum', 'Digital Tambor'
        DIGITAL = 'digital', 'Digital'

    apartment = models.ForeignKey(
        'buildings.Apartment',
        on_delete=models.CASCADE,
        related_name='measurements',
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='measurements',
    )
    reading_value = models.DecimalField(max_digits=12, decimal_places=3)
    ocr_value = models.CharField(max_length=50, blank=True, default='',
                                 help_text='Valor original detectado por OCR/IA')
    modified_by_user = models.BooleanField(default=False,
                                           help_text='True si el operador editó el valor OCR')
    unit = models.CharField(max_length=10, default='m³')
    photo = models.ImageField(upload_to='measurements/%Y/%m/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW)
    meter_type = models.CharField(max_length=20, choices=MeterType.choices, default=MeterType.ANALOG)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    cycle = models.ForeignKey(
        'cycles.MeasurementCycle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='measurements',
    )
    captured_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Si está definido, la medición está en papelera (soft delete).',
    )

    objects = ActiveMeasurementManager()
    all_objects = AllMeasurementsManager()

    class Meta:
        ordering = ['-captured_at']

    def __str__(self):
        return f'{self.apartment} — {self.reading_value} {self.unit} ({self.captured_at:%d/%m/%Y})'


class MeasurementAuditLog(models.Model):
    """Historial de cambios hechos por administradores (p. ej. lectura corregida)."""

    measurement = models.ForeignKey(
        Measurement,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='measurement_audit_edits',
    )
    field_name = models.CharField(max_length=64)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.measurement_id} {self.field_name} @ {self.created_at:%Y-%m-%d %H:%M}'
