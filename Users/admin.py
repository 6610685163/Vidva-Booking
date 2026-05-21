from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile
    Requirement: FR-AUTH-05 - Role assignment
    """
    list_display = ('full_name', 'tu_username', 'role', 'email', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('tu_username', 'full_name', 'email')
    readonly_fields = ('tu_username', 'created_at', 'updated_at')
    fieldsets = (
        (_('ข้อมูลพื้นฐาน'), {
            'fields': ('user', 'tu_username', 'full_name', 'email')
        }),
        (_('บทบาท'), {
            'fields': ('role',)
        }),
        (_('สถานะ'), {
            'fields': ('is_active',)
        }),
        (_('วันที่'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            # Log role change
            import logging
            logger = logging.getLogger('Users.admin')
            logger.info(
                f"Admin {request.user.username} changed {obj.tu_username} role to {obj.role}"
            )


