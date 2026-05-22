"""
models.py — Vidva Booking System
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("lecturer", _("อาจารย์")),
        ("admin", _("เจ้าหน้าที่")),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    tu_username = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )  # TU REST API username
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


class SystemSettings(models.Model):
    # Tab 1: ภาคการศึกษา
    semester_name = models.CharField(max_length=50, default="1/2569")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    allow_break_booking = models.BooleanField(default=False)

    # Tab 2: เงื่อนไขการจอง
    max_advance_days = models.IntegerField(default=30)
    max_hours = models.IntegerField(default=4)
    # auto_approve_lecturer = models.BooleanField(default=True)
    allow_weekend = models.BooleanField(default=True)

    # Tab 3: การแจ้งเตือน
    admin_email = models.EmailField(default="admin.tse@thammasat.ac.th")
    enable_email_notification = models.BooleanField(default=True)

    class Meta:
        verbose_name = "การตั้งค่าระบบ"
        verbose_name_plural = "การตั้งค่าระบบ"

    # เทคนิคบังคับให้มี Settings แค่แถวเดียว (ID=1) เสมอ
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
