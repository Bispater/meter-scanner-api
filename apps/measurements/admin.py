from django.contrib import admin
from .models import Measurement


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['apartment', 'reading_value', 'unit', 'status', 'operator', 'captured_at']
    list_filter = ['status', 'meter_type', 'apartment__tower__building']
    search_fields = ['apartment__number', 'apartment__meter_id']
    date_hierarchy = 'captured_at'
