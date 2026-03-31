from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with role and phone."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        OPERATOR = 'operator', 'Operador'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    # Apartments assigned to this operator (M2M through Building app)
    assigned_apartments = models.ManyToManyField(
        'buildings.Apartment',
        blank=True,
        related_name='assigned_operators',
    )

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'
