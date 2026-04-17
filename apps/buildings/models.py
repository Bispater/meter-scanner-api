from django.db import models


class Building(models.Model):
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='buildings',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=400)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Tower(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='towers')
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']
        unique_together = ['building', 'name']

    def __str__(self):
        return f'{self.building.name} — {self.name}'


class Apartment(models.Model):
    class ReadingLayout(models.TextChoices):
        A = 'A', 'Tipo A (5 enteros + 4 esferas)'
        B = 'B', 'Tipo B (8 rodillos + 1 esfera)'

    tower = models.ForeignKey(Tower, on_delete=models.CASCADE, related_name='apartments')
    number = models.CharField(max_length=20)
    floor = models.IntegerField(default=1)
    meter_id = models.CharField(max_length=50, blank=True, default='')
    reading_layout = models.CharField(
        max_length=1,
        choices=ReadingLayout.choices,
        default=ReadingLayout.A,
        help_text='Disposición de la lectura de 9 dígitos (A o B).',
    )
    qr_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text='Identificador único del departamento para QR. Formato: NúmeroTorre (ej: 1409A)',
    )

    class Meta:
        ordering = ['floor', 'number']
        unique_together = ['tower', 'number']

    def _generate_qr_code(self):
        """Build qr_code from apartment number + tower short name (strips 'Torre '/'Torre ')."""
        short = self.tower.name.replace('Torre ', '').replace('torre ', '').strip()
        return f'{self.number}{short}'

    def save(self, *args, **kwargs):
        if self.tower_id:
            need_qr = not self.qr_code
            if self.pk:
                try:
                    prev = Apartment.objects.get(pk=self.pk)
                    if prev.number != self.number or prev.tower_id != self.tower_id:
                        need_qr = True
                except Apartment.DoesNotExist:
                    need_qr = need_qr or not self.qr_code
            if need_qr:
                self.qr_code = self._generate_qr_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.tower} · Depto {self.number} [{self.qr_code}]'
