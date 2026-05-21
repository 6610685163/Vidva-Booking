"""
models.py — Vidva Booking System
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
# from django.core.exceptions import ValidationError

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

