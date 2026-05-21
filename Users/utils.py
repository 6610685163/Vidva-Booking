import logging
import threading
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Notification, UserProfile

logger = logging.getLogger(__name__)


def _send_email_async(subject, message, from_email, recipient_email, notification_id):
    """
    ส่งเมลในแยก thread เพื่อไม่ให้ user รอ
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        # อัพเดท notification ว่าส่งสำเร็จ
        Notification.objects.filter(id=notification_id).update(
            is_sent=True, sent_at=timezone.now(), error_message=""
        )
        logger.info(
            f"Email sent successfully to {recipient_email} (notification {notification_id})"
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(
            f"Error sending email to {recipient_email}: {error_msg}", exc_info=True
        )
        # บันทึก error message
        Notification.objects.filter(id=notification_id).update(
            is_sent=False, error_message=error_msg
        )


def send_booking_notification(booking, notification_type):
    """
    ฟังก์ชันสำหรับส่งอีเมลและบันทึกลง Notification Model
    อีเมลจะส่งแบบ async โดยไม่ให้ user รอ
    """
    subject = ""
    message = ""
    recipient_emails = []

    if notification_type == "new_booking":
        # แจ้งเตือน Admin เมื่อมีการจองใหม่ (FR-NOTI-01)
        subject = f"[ระบบจองห้อง TSE] มีคำขอจองห้องใหม่: {booking.room.room_name}"

        # ดึงอีเมลของ Admin ทั้งหมดในระบบ
        admins = UserProfile.objects.filter(role="admin", is_active=True)
        recipient_emails = [admin.email for admin in admins if admin.email]

        # ถ้าไม่มีอีเมล Admin ในระบบเลย ให้ใช้อีเมล Default จาก settings
        if not recipient_emails:
            recipient_emails = [getattr(settings, "ADMIN_EMAIL", "")]

        message = (
            f"เรียน เจ้าหน้าที่ (Admin),\n\n"
            f"มีการจองห้องใหม่รอการอนุมัติในระบบ ดังนี้:\n\n"
            f"ผู้จอง: {booking.booker.get_full_name() or booking.booker.username}\n"
            f"ห้อง: {booking.room.room_name} ({booking.room.room_code})\n"
            f"วันที่: {booking.start_date.strftime('%d/%m/%Y')} ถึง {booking.end_date.strftime('%d/%m/%Y')}\n"
            f"เวลา: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n\n"
            f"กรุณาเข้าสู่ระบบเพื่อตรวจสอบและอนุมัติ"
        )

    elif notification_type == "status_change":
        # แจ้งเตือนผู้จองเมื่อสถานะเปลี่ยน (FR-NOTI-02, FR-APPR-04)
        status_th = booking.get_status_display()
        subject = f"[ระบบจองห้อง TSE] อัปเดตสถานะการจองห้อง: {booking.room.room_name}"

        # ตรวจสอบว่าถ้ามีการกรอกอีเมลแจ้งเตือนแยกไว้ ให้ใช้เมลนั้นส่งหาอาจารย์ทันที
        if getattr(booking, "notification_email", None):
            recipient_emails = [booking.notification_email]
        else:
            recipient_emails = [booking.booker.email]

        message = (
            f"เรียน {booking.booker.get_full_name() or booking.booker.username},\n\n"
            f"คำขอจองห้องของคุณได้รับการพิจารณาแล้ว\n\n"
            f"ห้อง: {booking.room.room_name}\n"
            f"สถานะปัจจุบัน: **{status_th}**\n"
        )

        if booking.status == "rejected" and booking.rejection_reason:
            message += f"เหตุผลที่ไม่อนุมัติ: {booking.rejection_reason}\n"

        message += "\nขอบคุณครับ\nระบบจองห้องประชุมและห้องเรียน TSE"

    else:
        return False

    # บันทึก notification ทั้งหมดแล้วส่งเมลแบบ async
    for email in recipient_emails:
        if not email:  # ข้ามการส่งหากไม่มีที่อยู่อีเมล
            continue

        # สร้าง notification record ก่อน (pending)
        notification = Notification.objects.create(
            booking=booking,
            notification_type=notification_type,
            recipient_email=email,
            subject=subject,
            body=message,
            is_sent=False,  # ยังไม่ได้ส่ง
            error_message="",
        )

        # ส่งเมลแบบ async ใน background thread
        thread = threading.Thread(
            target=_send_email_async,
            args=(
                subject,
                message,
                getattr(settings, "DEFAULT_FROM_EMAIL", ""),
                email,
                notification.id,
            ),
            daemon=True,  # ให้ thread ทำงานเป็น daemon
        )
        thread.start()

    logger.info(
        f"Booking notification queued for {len(recipient_emails)} recipients (notification_type={notification_type})"
    )
    return True
