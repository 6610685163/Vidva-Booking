"""
URL configuration for Tse_Booking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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
    path("dashboard/", dashboard_view, name="dashboard"),
    path("booking/create/", create_booking_view, name="create_booking"),  # เพิ่มบรรทัดนี้
    path("users/", users_management_view, name="users_management"),
    path("bookings/pending/", pending_bookings_view, name="pending_bookings"),
    path("bookings/<int:booking_id>/approve/", approve_booking, name="approve_booking"),
    path("bookings/<int:booking_id>/reject/", reject_booking, name="reject_booking"),
    path('booking/', include('Booking.urls')),
]
