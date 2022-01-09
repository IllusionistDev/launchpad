from django.contrib import admin

from .models import Session, LaunchedApp


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'expires_at', 'created', 'modified')


@admin.register(LaunchedApp)
class LaunchedAppAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'created_by', 'url', 'status',
        'status_updated_at', 'launched_at', 'modified'
    )
