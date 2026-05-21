from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Booking.models import Booking
from Users.utils import send_booking_notification
import sys


class Command(BaseCommand):
    help = "ทดสอบการส่งเมลแจ้งเตือน (Reminder)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--booking-id',
            type=int,
            help='ID ของการจอง (ถ้าไม่ระบุจะใช้การจองแรกที่สถานะเป็น approved)',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='ส่งไปยังเมลนี้แทน (สำหรับทดสอบ)',
        )

    def handle(self, *args, **options):
        booking_id = options.get('booking_id')
        email = options.get('email')

        # หารายการจอง
        if booking_id:
            try:
                booking = Booking.objects.get(id=booking_id)
            except Booking.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"✗ ไม่พบการจอง ID: {booking_id}"))
                sys.exit(1)
        else:
            # หารายการจองแรกที่สถานะเป็น approved
            booking = Booking.objects.filter(status="approved").first()
            if not booking:
                self.stdout.write(
                    self.style.WARNING(
                        "✗ ไม่มีการจองที่สถานะ 'approved' ในระบบ\n"
                        "กรุณาอนุมัติการจองบางรายการก่อน"
                    )
                )
                sys.exit(1)

        # แสดงข้อมูล
        self.stdout.write(
            self.style.SUCCESS("\n📋 ข้อมูลการจอง:")
        )
        self.stdout.write(f"  ID: {booking.id}")
        self.stdout.write(f"  ห้อง: {booking.room.room_name}")
        self.stdout.write(f"  ผู้จอง: {booking.booker.get_full_name() or booking.booker.username}")
        self.stdout.write(f"  เมล: {booking.booker.email}")
        self.stdout.write(f"  วันที่จอง: {booking.start_date.strftime('%d/%m/%Y')}")
        self.stdout.write(f"  เวลา: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}")

        # ส่งเมล
        self.stdout.write("\n📧 กำลังส่งเมลแจ้งเตือน...")
        try:
            # สำหรับทดสอบ สามารถเปลี่ยน email ไป
            if email:
                original_email = booking.booker.email
                booking.booker.email = email
                self.stdout.write(self.style.WARNING(f"  (เปลี่ยนเมล: {original_email} → {email})"))

            send_booking_notification(booking, "reminder")
            
            self.stdout.write(
                self.style.SUCCESS("\n✓ ส่งเมลแจ้งเตือนแล้ว!")
            )
            self.stdout.write("  ตรวจสอบ Email เพื่อยืนยัน\n")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n✗ เกิดข้อผิดพลาด: {e}\n")
            )
            sys.exit(1)

        # แสดงข้อมูล Notification ที่สร้างขึ้น
        from Booking.models import Notification
        latest_notif = Notification.objects.filter(
            booking=booking, notification_type="reminder"
        ).order_by('-created_at').first()

        if latest_notif:
            self.stdout.write(self.style.SUCCESS("📦 Notification Record:"))
            self.stdout.write(f"  Status: {'✓ ส่งสำเร็จ' if latest_notif.is_sent else '✗ ส่งไม่สำเร็จ'}")
            self.stdout.write(f"  Recipient: {latest_notif.recipient_email}")
            self.stdout.write(f"  Subject: {latest_notif.subject}")
            self.stdout.write(f"  Sent At: {latest_notif.sent_at or 'รอการส่ง'}")
            if latest_notif.error_message:
                self.stdout.write(f"  Error: {latest_notif.error_message}\n")
