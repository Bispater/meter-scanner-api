from django.db import models


class Building(models.Model):
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
    tower = models.ForeignKey(Tower, on_delete=models.CASCADE, related_name='apartments')
    number = models.CharField(max_length=20)
    floor = models.IntegerField(default=1)
    meter_id = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['floor', 'number']
        unique_together = ['tower', 'number']

    def __str__(self):
        return f'{self.tower} · Depto {self.number}'
