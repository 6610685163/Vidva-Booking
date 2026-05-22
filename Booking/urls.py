from django.urls import path
from . import views

urlpatterns = [
    path("", views.booking_flow_view, name="booking_flow"),
    # หน้าจัดการของ Admin (อนุมัติ/ปฏิเสธ)
    path("pending/", views.pending_bookings_view, name="pending_bookings"),
    path("<int:booking_id>/approve/", views.approve_booking, name="approve_booking"),
    path("<int:booking_id>/reject/", views.reject_booking, name="reject_booking"),
    path("<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("history/", views.my_bookings_view, name="my_bookings"),
    # path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path("my-calendar/", views.booking_calendar_view, name="booking_calendar"),
    path("api/chatbot/", views.chatbot_api, name="chatbot_api"),
]
