from django.contrib import admin
from .models import Building, Tower, Apartment


class TowerInline(admin.TabularInline):
    model = Tower
    extra = 0


class ApartmentInline(admin.TabularInline):
    model = Apartment
    extra = 0


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'created_at']
    search_fields = ['name', 'address']
    inlines = [TowerInline]


@admin.register(Tower)
class TowerAdmin(admin.ModelAdmin):
    list_display = ['name', 'building']
    list_filter = ['building']
    inlines = [ApartmentInline]


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = ['number', 'floor', 'meter_id', 'tower']
    list_filter = ['tower__building', 'tower']
    search_fields = ['number', 'meter_id']
