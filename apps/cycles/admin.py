from django.contrib import admin
from .models import MeasurementCycle


@admin.register(MeasurementCycle)
class MeasurementCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'building', 'year', 'month', 'scheduled_date', 'deadline', 'status']
    list_filter = ['status', 'building', 'year']
    ordering = ['-year', '-month']
