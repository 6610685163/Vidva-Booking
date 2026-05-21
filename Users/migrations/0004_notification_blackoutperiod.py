# Generated migration to add Notification and BlackoutPeriod models

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0003_alter_booking_curriculum_alter_booking_days_of_week_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('new_booking', 'มีการจองใหม่ (แจ้ง Admin)'), ('status_change', 'สถานะการจองเปลี่ยน (แจ้งผู้จอง)'), ('reminder', 'แจ้งเตือนล่วงหน้า 1 วัน')], max_length=30)),
                ('recipient_email', models.EmailField(max_length=254)),
                ('subject', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('is_sent', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='Users.booking')),
            ],
            options={
                'verbose_name': 'การแจ้งเตือน',
                'verbose_name_plural': 'การแจ้งเตือน',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BlackoutPeriod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(verbose_name='วันเริ่มต้น')),
                ('end_date', models.DateField(verbose_name='วันสิ้นสุด')),
                ('reason', models.CharField(max_length=255, verbose_name='เหตุผล')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blackout_periods', to='Users.room', verbose_name='ห้อง')),
            ],
            options={
                'verbose_name': 'ช่วงเวลาปิดห้อง',
                'verbose_name_plural': 'ช่วงเวลาปิดห้อง',
                'ordering': ['-start_date'],
            },
        ),
    ]
