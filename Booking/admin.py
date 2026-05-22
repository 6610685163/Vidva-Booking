from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Room, Booking, Notification, BlackoutPeriod

# Register your models here.
admin.site.register(Booking)
admin.site.register(Notification)
admin.site.register(BlackoutPeriod)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """
    Admin interface for Room management
    Requirement: FR-ADM-01 - Room management
    """

    list_display = ("room_code", "room_name", "room_type", "capacity", "is_active")
    list_filter = ("room_type", "is_active")
    search_fields = ("room_code", "room_name")
    fieldsets = (
        (
            _("ข้อมูลห้อง"),
            {"fields": ("room_code", "room_name", "room_type", "capacity")},
        ),
        (_("รายละเอียด"), {"fields": ("description",), "classes": ("collapse",)}),
        (_("สถานะ"), {"fields": ("is_active",)}),
    )
    readonly_fields = ("created_at", "updated_at")


# @admin.register(AcademicSemester)
# class AcademicSemesterAdmin(admin.ModelAdmin):
#     list_display = ("name", "start_date", "end_date", "is_active")
#     list_editable = ("is_active",)
