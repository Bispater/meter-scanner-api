from django.db import models
from django.conf import settings


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
    captured_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-captured_at']

    def __str__(self):
        return f'{self.apartment} — {self.reading_value} {self.unit} ({self.captured_at:%d/%m/%Y})'
