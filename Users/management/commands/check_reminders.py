from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Booking.models import Notification


class Command(BaseCommand):
    help = "ดูประวัติการส่งเมลแจ้งเตือน"

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='reminder',
            help='ประเภทการแจ้งเตือน (reminder/status_change/new_booking)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='ดูประวัติย้อนหลัง N วัน (default: 7)',
        )
        parser.add_argument(
            '--status',
            type=str,
            default='all',
            help='สถานะ (sent/failed/all)',
        )

    def handle(self, *args, **options):
        notification_type = options['type']
        days = options['days']
        status = options['status']

        # กรองข้อมูล
        notifications = Notification.objects.filter(
            notification_type=notification_type,
            created_at__gte=timezone.now() - timedelta(days=days)
        )

        if status == 'sent':
            notifications = notifications.filter(is_sent=True)
        elif status == 'failed':
            notifications = notifications.filter(is_sent=False)

        # แสดงผล
        self.stdout.write(
            self.style.SUCCESS(f"\n📧 ประวัติการแจ้งเตือน ({notification_type}) - {days} วันที่ผ่านมา\n")
        )

        if not notifications.exists():
            self.stdout.write(self.style.WARNING("ไม่มีข้อมูล"))
            return

        self.stdout.write(
            f"{'Status':<10} {'Email':<30} {'Subject':<50} {'Sent At':<20}"
        )
        self.stdout.write("-" * 110)

        for notif in notifications:
            status_icon = "✓" if notif.is_sent else "✗"
            sent_at = notif.sent_at.strftime('%Y-%m-%d %H:%M') if notif.sent_at else "รอการส่ง"
            
            self.stdout.write(
                f"{status_icon:<10} {notif.recipient_email:<30} {notif.subject[:50]:<50} {sent_at:<20}"
            )

        # สรุป
        total = notifications.count()
        sent = notifications.filter(is_sent=True).count()
        failed = notifications.filter(is_sent=False).count()

        self.stdout.write("\n" + "=" * 110)
        self.stdout.write(
            self.style.SUCCESS(
                f"รวม: {total} | ✓ ส่งสำเร็จ: {sent} | ✗ ล้มเหลว: {failed}"
            )
        )
