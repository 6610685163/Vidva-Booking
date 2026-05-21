from django.urls import path
from . import views

urlpatterns = [
    path("", views.booking_flow_view, name="booking_flow"),
    # 🎯 หน้าฟอร์มจองห้อง (หน้าที่เรากำลังจะเข้า)
    path("create/", views.create_booking_view, name="create_booking"),
    # หน้าจัดการของ Admin (อนุมัติ/ปฏิเสธ)
    path("pending/", views.pending_bookings_view, name="pending_bookings"),
    path("<int:booking_id>/approve/", views.approve_booking, name="approve_booking"),
    path("<int:booking_id>/reject/", views.reject_booking, name="reject_booking"),
    path("history/", views.my_bookings_view, name="my_bookings"),
]
