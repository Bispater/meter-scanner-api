from django.contrib import admin
from django.utils.html import format_html
from .models import Measurement


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = [
        'apartment', 'reading_value', 'ocr_value', 'modified_by_user',
        'unit', 'status', 'operator', 'photo_thumbnail', 'captured_at',
    ]
    list_filter = ['status', 'meter_type', 'modified_by_user', 'apartment__tower__building']
    search_fields = ['apartment__number', 'apartment__meter_id']
    date_hierarchy = 'captured_at'
    readonly_fields = ['photo_preview', 'ocr_value', 'modified_by_user']

    @admin.display(description='Foto')
    def photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height:40px; border-radius:4px;" />',
                obj.photo.url,
            )
        return '-'

    @admin.display(description='Vista previa')
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height:300px; border-radius:8px;" />',
                obj.photo.url,
            )
        return '-'
