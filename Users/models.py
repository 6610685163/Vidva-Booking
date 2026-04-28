from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class UserProfile(models.Model):
    """
    Extended user profile to store additional information and role assignment
    Requirement: FR-AUTH-05 - Role (Lecturer / Admin) assignment
    """
    ROLE_CHOICES = [
        ('lecturer', _('อาจารย์')),  # Lecturer
        ('admin', _('เจ้าหน้าที่')),    # Admin/Staff
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tu_username = models.CharField(max_length=100, unique=True)  # TU REST API username
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='lecturer')
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('ผู้ใช้งาน')
        verbose_name_plural = _('ผู้ใช้งาน')
    
    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_lecturer(self):
        return self.role == 'lecturer'


class Room(models.Model):
    """
    Room model for the 5 rooms mentioned in SRS
    Section 2.3: ข้อมูลห้อง (Room Information)
    """
    ROOM_TYPE_CHOICES = [
        ('meeting', _('ห้องประชุม')),      # Meeting room
        ('classroom', _('ห้องเรียน')),      # Classroom
    ]

    room_code = models.CharField(max_length=20, unique=True)      # 406-3, 406-5, etc.
    room_name = models.CharField(max_length=100)                   # Name in Thai
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    capacity = models.IntegerField()                               # Number of seats
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
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
        return f"{self.room.room_code} - {self.booker.username} ({self.start_date} to {self.end_date})"

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("วันที่เริ่มต้นต้องไม่มากกว่าวันที่สิ้นสุด"))
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(_("เวลาเริ่มต้นต้องน้อยกว่าเวลาสิ้นสุด"))
