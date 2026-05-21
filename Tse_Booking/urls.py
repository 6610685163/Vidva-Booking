from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from Users.views import (
    login_view,
    logout_view,
    dashboard_view,
    assign_user_role_view,
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
    # ดึงเส้นทางจากแอป Booking สำหรับระบบปฏิทินและการจองของอาจารย์
    path("booking/", include("Booking.urls")),
]
