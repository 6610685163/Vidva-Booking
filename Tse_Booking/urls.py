from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from Booking import views
from Users.views import (
    admin_calendar_view,
    login_view,
    logout_view,
    dashboard_view,
    assign_user_role_view,
    room_management_view,
    room_report_view,
    system_settings_view,
    users_management_view,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # ระบบ Users และหน้า Dashboard
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("users/", users_management_view, name="users_management"),
    path("users/<int:user_id>/role/", assign_user_role_view, name="assign_role"),
    
    # ระบบ Booking (ดึงจากไฟล์ของแอป Booking ที่เราทำไว้สมบูรณ์แล้ว)
    path('booking/', include('Booking.urls')),

    # ฟีเจอร์ใหม่ของเพื่อน (ระบบ Report และ Admin Dashboard)
    path('room-report/', room_report_view, name='room_report'),
    path('admin-dashboard/rooms/', room_management_view, name='room_management'),
    path('admin-dashboard/calendar/', admin_calendar_view, name='admin_calendar'),
    path('admin-dashboard/settings/', system_settings_view, name='system_settings'),
]