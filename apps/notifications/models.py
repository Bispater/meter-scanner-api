from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notificaciones in-app dirigidas a un usuario (por ahora sin push real)."""

    class Type(models.TextChoices):
        MEASUREMENT_REJECTED = 'measurement_rejected', 'Medición rechazada'
        MEASUREMENT_VALIDATED = 'measurement_validated', 'Medición validada'
        GENERIC = 'generic', 'Genérica'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    type = models.CharField(max_length=40, choices=Type.choices, default=Type.GENERIC)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default='')
    measurement = models.ForeignKey(
        'measurements.Measurement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    payload = models.JSONField(blank=True, default=dict)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f'#{self.pk} {self.type} → {self.recipient_id}'
