from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    """Tenant entity. Each building and user belongs to one organization."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom user with role and phone."""

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        OPERATOR = 'operator', 'Operador'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OPERATOR)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    # Primary organization (all users belong to exactly one org)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )

    # Admins can additionally manage other organizations
    extra_organizations = models.ManyToManyField(
        Organization,
        blank=True,
        related_name='extra_admins',
        help_text='Additional organizations this admin can manage',
    )

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
