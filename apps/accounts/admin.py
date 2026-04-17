from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'organization', 'is_active']
    list_filter = ['role', 'is_active', 'organization']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('HydroScan', {'fields': ('role', 'phone', 'organization', 'extra_organizations', 'assigned_apartments')}),
    )
