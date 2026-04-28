"""
models.py — Vidva Booking System
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("lecturer", _("อาจารย์")),
        ("admin", _("เจ้าหน้าที่")),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    tu_username = models.CharField(max_length=100, unique=True)  # TU REST API username
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="lecturer")
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("ผู้ใช้งาน")
        verbose_name_plural = _("ผู้ใช้งาน")

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    def is_admin(self):
        return self.role == "admin"

    def is_lecturer(self):
        return self.role == "lecturer"


class Room(models.Model):
    ROOM_TYPE_CHOICES = [
        ("meeting", _("ห้องประชุม")),
        ("classroom", _("ห้องเรียน")),
    ]

    room_code = models.CharField(max_length=20, unique=True)      # 406-3, 406-5, etc.
    room_name = models.CharField(max_length=100)                   # Name in Thai
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    capacity = models.IntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)  # FR-ADM-01
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('ห้อง')
        verbose_name_plural = _('ห้อง')
        ordering = ['room_code']

    def __str__(self):
        return f"{self.room_code} - {self.room_name}"


class Booking(models.Model):
    """
    Booking model
    Requirement: FR-BOOK-01 to FR-BOOK-07
    """

    PURPOSE_CHOICES = [
        ("class", _("สอนปกติ/ชดเชย/เสริม")),
        ("training", _("จัดอบรม/จัดติว")),
    ]

    CURRICULUM_CHOICES = [
        ("regular", _("ปริญญาตรีภาคปกติ")),
        ("master", _("ปริญญาโท")),
        ("tep_tepe", _("TEP-TEPE")),
        ("tu_pine", _("TU-PINE")),
    ]

    STATUS_CHOICES = [
        ("pending", _("รอการอนุมัติ")),
        ("approved", _("อนุมัติแล้ว")),
        ("rejected", _("ปฏิเสธ")),
        ("cancelled", _("ยกเลิก")),
    ]

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="bookings", verbose_name=_("ห้อง")
    )
    booker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    purpose_type = models.CharField(
        max_length=20, choices=PURPOSE_CHOICES, verbose_name=_("วัตถุประสงค์")
    )

    # สำหรับ สอนปกติ/ชดเชย/เสริม
    subject_code = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("รหัสวิชา")
    )
    subject_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("ชื่อวิชา")
    )
    curriculum = models.CharField(
        max_length=20,
        choices=CURRICULUM_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("หลักสูตร"),
    )

    # สำหรับ จัดอบรม/จัดติว
    topic = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("ชื่อเรื่อง")
    )

    # วันและเวลา
    start_date = models.DateField(verbose_name=_("ตั้งแต่วันที่"))
    end_date = models.DateField(verbose_name=_("ถึงวันที่"))
    start_time = models.TimeField(verbose_name=_("ตั้งแต่เวลา"))
    end_time = models.TimeField(verbose_name=_("ถึงเวลา"))
    days_of_week = models.CharField(
        max_length=50, verbose_name=_("วันในสัปดาห์")
    )  # เก็บเป็น string เช่น "0,1,2" (0=จันทร์)

    # สถานะ
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    rejection_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("การจองห้อง")
        verbose_name_plural = _("การจองห้อง")
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.room} | {self.booker.get_full_name()} | {self.start_date}"

    def clean(self):
        """Basic validation — conflict detection done in view (FR-BOOK-06)"""
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("วันเริ่มต้นต้องไม่หลังวันสิ้นสุด"))
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(_("เวลาเริ่มต้นต้องก่อนเวลาสิ้นสุด"))


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ("new_booking", _("มีการจองใหม่ (แจ้ง Admin)")),  # FR-NOTI-01
        ("status_change", _("สถานะการจองเปลี่ยน (แจ้งผู้จอง)")),  # FR-NOTI-02
        ("reminder", _("แจ้งเตือนล่วงหน้า 1 วัน")),  # FR-NOTI-03
    ]

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="notifications"
    )
    notification_type = models.CharField(
        max_length=30, choices=NOTIFICATION_TYPE_CHOICES
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("การแจ้งเตือน")
        verbose_name_plural = _("การแจ้งเตือน")
        ordering = ["-created_at"]

    def __str__(self):
        status = "✓" if self.is_sent else "✗"
        return f"{status} [{self.get_notification_type_display()}] → {self.recipient_email}"


class BlackoutPeriod(models.Model):
    """
    ช่วงเวลาที่ห้องไม่พร้อมใช้งาน เช่น ปิดเทอม, ซ่อมบำรุง
    ถ้า rooms ว่าง = ปิดทุกห้อง
    """

    title = models.CharField(max_length=200, verbose_name=_("ชื่อช่วงปิด"))
    start_date = models.DateField()
    end_date = models.DateField()
    rooms = models.ManyToManyField(
        Room,
        blank=True,
        related_name="blackout_periods",
        verbose_name=_("ห้องที่ปิด (ว่าง = ทุกห้อง)"),
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="blackout_periods"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("ช่วงเวลาปิดใช้งาน")
        verbose_name_plural = _("ช่วงเวลาปิดใช้งาน")
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.title} ({self.start_date} – {self.end_date})"

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("วันเริ่มต้นต้องไม่หลังวันสิ้นสุด"))
