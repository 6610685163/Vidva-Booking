# ระบบส่งเมลแจ้งเตือนการจองห้อง

ระบบนี้จะส่งเมลแจ้งเตือนให้ผู้ใช้ล่วงหน้า **1 วัน** ก่อนวันที่พวกเขาทำการจองห้อง

## ฟังก์ชันการทำงาน

1. **เมลแจ้งเตือนใหม่** (Reminder) ส่งไปให้ผู้จองหน้า:
   - ชื่อห้อง
   - วันและเวลาที่จอง
   - วัตถุประสงค์ (วิชา/หัวข้อ)
   - เตือนให้มาตรงเวลา

2. **ส่งเฉพาะการจองที่**:
   - สถานะ = "อนุมัติแล้ว" (approved)
   - วันจอง = พรุ่งนี้
   - ยังไม่ได้ส่งแจ้งเตือนไปแล้ว

## การใช้งาน

### วิธีที่ 1: รันด้วยตนเองทีละครั้ง
```bash
python manage.py send_reminders
```

### วิธีที่ 2: ใช้ Scheduler (อนุญาต 24/7)

#### ก. บน Linux/Mac - ใช้ crontab

1. เปิด crontab editor:
```bash
crontab -e
```

2. เพิ่มบรรทัดนี้เพื่อรันทุกวันเวลา 08:00 น.:
```bash
0 8 * * * cd /path/to/Vidva-Booking && /path/to/.venv/bin/python manage.py send_reminders >> logs/reminders.log 2>&1
```

#### ข. บน Windows - ใช้ Task Scheduler

1. เปิด Task Scheduler
2. Create Basic Task:
   - ชื่อ: "Send Booking Reminders"
   - เลือก "Daily" และตั้งเวลา 08:00
   - Action: Start a program
     - Program: `C:\path\to\.venv\Scripts\python.exe`
     - Arguments: `manage.py send_reminders`
     - Start in: `C:\Dev\Projects\Vidva-Booking`

#### ค. ใช้ APScheduler (Python):

```bash
pip install apscheduler
python run_reminders_scheduler.py
```

แล้วให้ process นี้รันอยู่เบื้องหลัง (ใช้ supervisor หรือ systemd)

#### ง. ใช้ Celery Beat (สำหรับ Production)

```bash
pip install celery celery-beat redis
celery -A Tse_Booking beat --loglevel=info
```

## การตั้งค่าเอกสาร

### ตัวแปร Environment (.env)

```env
# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
ADMIN_EMAIL=661068513@student.tu.ac.th
```

### การทดสอบการส่งเมล

```bash
python manage.py shell
>>> from Booking.models import Booking
>>> from Users.utils import send_booking_notification
>>> booking = Booking.objects.first()
>>> send_booking_notification(booking, "reminder")
```

## ประวัติการแจ้งเตือน

ทุกการส่งเมลแจ้งเตือนจะบันทึกลงใน Notification table:
- `notification_type` = "reminder"
- `is_sent` = True (ถ้าส่งสำเร็จ)
- `sent_at` = timestamp ของการส่ง
- `error_message` = ข้อความ error (ถ้ามี)

ดูประวัติได้ที่ Django Admin:
```
/admin/booking/notification/
```

## Troubleshooting

### เมลไม่ส่งออกไป

1. ตรวจสอบ Email Configuration ใน `.env`
2. ดูลอก: `logs/tse_booking.log` และ `logs/authentication.log`
3. ตรวจสอบว่า Booking มี status = "approved"
4. ตรวจสอบ email address ของผู้จอง

### Scheduler ไม่ทำงาน

1. ตรวจสอบ permission ของ logs directory
2. ดูว่า Python process ยังทำงานอยู่หรือไม่
3. ใช้ `ps aux | grep python` (Linux/Mac)

### Duplicate แจ้งเตือน

- Scheduler ตรวจสอบว่า notification นี้ส่งไปแล้วหรือไม่
- ไม่ควรส่ง reminder ซ้ำ เว้นแต่ delete record เก่า
