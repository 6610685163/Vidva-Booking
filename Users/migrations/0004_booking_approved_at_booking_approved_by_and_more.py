import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Users", "0003_add_notification_blackout_recurring"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="approved_bookings",
                to=settings.AUTH_USER_MODEL,
                verbose_name="อนุมัติ/ปฏิเสธโดย",
            ),
        ),
        migrations.AlterField(
            model_name="blackoutperiod",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="blackout_periods",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="blackoutperiod",
            name="end_date",
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name="blackoutperiod",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="blackoutperiod",
            name="start_date",
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name="blackoutperiod",
            name="title",
            field=models.CharField(max_length=200, verbose_name="ชื่อช่วงปิด"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="is_recurring",
            field=models.BooleanField(default=False, verbose_name="การจองแบบซ้ำ"),
        ),
        migrations.AlterField(
            model_name="notification",
            name="body",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="notification",
            name="booking",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="Users.booking",
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="error_message",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="notification",
            name="is_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("new_booking", "มีการจองใหม่ (แจ้ง Admin)"),
                    ("status_change", "สถานะการจองเปลี่ยน (แจ้งผู้จอง)"),
                    ("reminder", "แจ้งเตือนล่วงหน้า 1 วัน"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="recipient_email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name="notification",
            name="sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="notification",
            name="subject",
            field=models.CharField(max_length=255),
        ),
    ]
