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
    users_management_view,
    create_booking_view,
    pending_bookings_view,
    approve_booking,
    reject_booking,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("users/", users_management_view, name="users_management"),
    path("users/<int:user_id>/role/", assign_user_role_view, name="assign_role"),
    path("booking/create/", create_booking_view, name="create_booking"),
    path("bookings/pending/", pending_bookings_view, name="pending_bookings"),
    path("bookings/<int:booking_id>/approve/", approve_booking, name="approve_booking"),
    path("bookings/<int:booking_id>/reject/", reject_booking, name="reject_booking"),
    path('booking/', include('Booking.urls')),
    path('room-report/', room_report_view, name='room_report'),
    path('admin-dashboard/rooms/', room_management_view, name='room_management'),
    path('admin-dashboard/calendar/', admin_calendar_view, name='admin_calendar'),
]
