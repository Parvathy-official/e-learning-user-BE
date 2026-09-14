from django.contrib import admin
from .models import AdminActivityLog


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'action', 'target_model', 'target_id', 'ip_address', 'created_at')
    list_filter = ('action', 'target_model', 'created_at')
    search_fields = ('admin_user__email', 'admin_user__name', 'action', 'target_model', 'target_id')
    readonly_fields = ('admin_user', 'action', 'target_model', 'target_id', 'details', 'ip_address', 'created_at')
