from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Booking.models import Booking
from Users.utils import send_booking_notification


class Command(BaseCommand):
    help = "ส่งอีเมลแจ้งเตือนล่วงหน้า 1 วัน สำหรับการจองที่ได้รับการอนุมัติแล้ว"

    def handle(self, *args, **kwargs):
        # หาวันพรุ่งนี้
        tomorrow = timezone.now().date() + timedelta(days=1)

        # ดึงการจองที่จะเกิดขึ้นในวันพรุ่งนี้ และสถานะเป็น 'approved'
        upcoming_bookings = Booking.objects.filter(
            start_date=tomorrow, status="approved"
        ).distinct()

        count = 0
        for booking in upcoming_bookings:
            # ตรวจสอบว่าไม่ได้ส่งแจ้งเตือนนี้ไปแล้ว
            from Booking.models import Notification
            existing_reminder = Notification.objects.filter(
                booking=booking,
                notification_type="reminder",
                is_sent=True
            ).exists()
            
            if not existing_reminder:
                send_booking_notification(booking, "reminder")
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"ส่งการแจ้งเตือนแล้วสำหรับการจอง ID: {booking.id}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"ข้ามการจอง ID: {booking.id} (แจ้งเตือนส่งไปแล้ว)")
                )

        self.stdout.write(
            self.style.SUCCESS(f"ส่งอีเมลแจ้งเตือนทั้งหมด {count} รายการ")
        )
