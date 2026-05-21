from django.urls import path
from . import views

urlpatterns = [
    path('', views.booking_flow_view, name='booking_flow'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('my-calendar/', views.booking_calendar_view, name='booking_calendar'),
]