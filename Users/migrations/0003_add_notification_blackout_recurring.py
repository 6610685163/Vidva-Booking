import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Users", "0002_booking"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="is_recurring",
            field=models.BooleanField(
                default=False,
                verbose_name="การจองแบบซ้ำ",
                help_text="True = recurring booking ที่มี pattern วันในสัปดาห์",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="parent_booking",
            field=models.ForeignKey(
                to="Users.booking",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recurring_instances",
                null=True,
                blank=True,
                verbose_name="การจองหลัก (Recurring)",
            ),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "notification_type",
                    models.CharField(
                        max_length=30,
                        choices=[
                            ("new_booking", "มีการจองใหม่ (แจ้ง Admin)"),  # FR-NOTI-01
                            (
                                "status_change",
                                "สถานะการจองเปลี่ยน (แจ้งผู้จอง)",
                            ),  # FR-NOTI-02
                            ("reminder", "แจ้งเตือนล่วงหน้า 1 วัน"),  # FR-NOTI-03
                        ],
                        verbose_name="ประเภทการแจ้งเตือน",
                    ),
                ),
                ("recipient_email", models.EmailField(verbose_name="อีเมลผู้รับ")),
                ("subject", models.CharField(max_length=255, verbose_name="หัวข้ออีเมล")),
                ("body", models.TextField(verbose_name="เนื้อหาอีเมล")),
                ("is_sent", models.BooleanField(default=False, verbose_name="ส่งแล้ว")),
                (
                    "sent_at",
                    models.DateTimeField(null=True, blank=True, verbose_name="เวลาที่ส่ง"),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, verbose_name="ข้อผิดพลาด (ถ้ามี)"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "booking",
                    models.ForeignKey(
                        to="Users.booking",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        verbose_name="การจองที่เกี่ยวข้อง",
                    ),
                ),
            ],
            options={
                "verbose_name": "การแจ้งเตือน",
                "verbose_name_plural": "การแจ้งเตือน",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="BlackoutPeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=200, verbose_name="ชื่อช่วงปิด เช่น ปิดเทอม"),
                ),
                ("start_date", models.DateField(verbose_name="วันเริ่มต้น")),
                ("end_date", models.DateField(verbose_name="วันสิ้นสุด")),
                ("is_active", models.BooleanField(default=True, verbose_name="ใช้งาน")),
                (
                    "created_by",
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        on_delete=django.db.models.deletion.SET_NULL,
                        null=True,
                        related_name="blackout_periods",
                        verbose_name="สร้างโดย",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "rooms",
                    models.ManyToManyField(
                        to="Users.room",
                        blank=True,
                        related_name="blackout_periods",
                        verbose_name="ห้องที่ปิด (ว่าง = ทุกห้อง)",
                    ),
                ),
            ],
            options={
                "verbose_name": "ช่วงเวลาปิดใช้งาน",
                "verbose_name_plural": "ช่วงเวลาปิดใช้งาน",
                "ordering": ["start_date"],
            },
        ),
    ]
