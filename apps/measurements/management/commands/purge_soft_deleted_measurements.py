"""
Elimina físicamente mediciones en papelera más antiguas que RETENTION_DAYS.
Ejecutar diario vía cron: python manage.py purge_soft_deleted_measurements
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.measurements.models import Measurement

RETENTION_DAYS = 30


class Command(BaseCommand):
    help = 'Borra definitivamente mediciones soft-deleted hace más de 30 días.'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=RETENTION_DAYS)
        qs = Measurement.all_objects.filter(deleted_at__isnull=False, deleted_at__lt=cutoff)
        count = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(f'Eliminadas {count} medición(es) expiradas de la papelera.'))
