# ระบบส่งเมลแจ้งเตือนการจองห้อง - คู่มือเริ่มต้นใช้งาน

## 📋 ข้อมูลทั่วไป

ระบบนี้จะส่งเมลแจ้งเตือนให้ผู้ใช้ **1 วัน ก่อนวันที่พวกเขาทำการจองห้อง** 

### ตัวอย่าง:
- ผู้ใช้จองห้องสำหรับวันที่ **25 พฤษภาคม**
- ระบบจะส่งเมลแจ้งเตือนให้พวกเขาวันที่ **24 พฤษภาคม**

## 🚀 ขั้นตอนการตั้งค่า

### 1. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า Email ใน .env

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

> **หมายเหตุ สำหรับ Gmail**: ใช้ [Google App Password](https://myaccount.google.com/apppasswords) แทนรหัสผ่านทั่วไป

### 3. ทดสอบการส่งเมล

```bash
python manage.py test_reminder
```

หรือทดสอบกับการจองที่ระบุ:
```bash
python manage.py test_reminder --booking-id 5
```

## ▶️ วิธีการรัน

### วิธีที่ 1: รันด้วยตนเองทีละครั้ง (Manual)

```bash
python manage.py send_reminders
```

### วิธีที่ 2: รันอัตโนมัติทุกวี (Automatic)

#### 💻 บน Windows

1. **ใช้ Batch Script:**
```bash
run_scheduler.bat
```
- Script นี้จะตั้ง virtual environment และรัน scheduler
- Scheduler จะรันทุกวันเวลา 08:00 น.
- ให้เปิด Command Prompt ไว้ตลอด

2. **ใช้ Task Scheduler (Windows):**

ดับเบิลคลิก `run_scheduler.bat` หรือตั้ง Task Scheduler:

```
Program: C:\path\to\.venv\Scripts\pythonw.exe
Arguments: C:\path\to\Vidva-Booking\run_reminders_scheduler.py
Start in: C:\path\to\Vidva-Booking
```

#### 🐧 บน Linux/Mac

1. **ใช้ Shell Script:**
```bash
chmod +x run_scheduler.sh
./run_scheduler.sh
```

2. **ใช้ Crontab (ทางการดี):**

```bash
crontab -e
```

เพิ่มบรรทัดนี้:
```bash
0 8 * * * cd /path/to/Vidva-Booking && /path/to/.venv/bin/python manage.py send_reminders >> logs/reminders.log 2>&1
```

3. **ใช้ systemd service (Production):**

สร้างไฟล์ `/etc/systemd/system/booking-reminders.service`:

```ini
[Unit]
Description=Booking System Reminder Scheduler
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Vidva-Booking
ExecStart=/path/to/.venv/bin/python run_reminders_scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

จากนั้นรัน:
```bash
sudo systemctl enable booking-reminders
sudo systemctl start booking-reminders
sudo systemctl status booking-reminders
```

## 📊 ตรวจสอบประวัติการแจ้งเตือน

### ดูประวัติการส่งเมล:

```bash
# ดูเมลแจ้งเตือนทั้งหมดใน 7 วันที่ผ่านมา
python manage.py check_reminders

# ดูเฉพาะเมลที่ส่งสำเร็จ
python manage.py check_reminders --status sent

# ดูเฉพาะเมลที่ล้มเหลว
python manage.py check_reminders --status failed

# ดูประวัติ 30 วัน
python manage.py check_reminders --days 30

# ดูประวัติเมลอื่นๆ (status_change, new_booking)
python manage.py check_reminders --type status_change
```

### ดูใน Django Admin:

ไปที่ `/admin/booking/notification/` เพื่อดูบันทึกการแจ้งเตือนทั้งหมด

## 📝 ตัวอย่างเมลที่ส่ง

```
Subject: [ระบบจองห้อง TSE] ชำระการจองห้องพรุ่งนี้: ENG 406-3

เรียน [ชื่อผู้ใช้],

แจ้งเตือน: คุณมีการจองห้องในวันพรุ่งนี้

รายละเอียด:
ห้อง: ENG 406-3 (ห้องประชุม 1)
วันที่: 25/05/2026
เวลา: 08:00 - 10:00
วิชา: Advanced Programming (365234)

โปรดเตรียมตัวและมาตรงเวลา
ขอบคุณครับ
ระบบจองห้องประชุมและห้องเรียน TSE
```

## 🐛 Troubleshooting

### ปัญหา: Reminder ไม่ส่ง

**ตรวจสอบ:**
1. ตรวจสอบ Email Configuration ใน `.env`
2. ตรวจสอบว่า Booking มี `status = "approved"`
3. ตรวจสอบ Email address ของผู้จอง
4. ดูลอก: `logs/tse_booking.log`

```bash
tail -f logs/tse_booking.log
```

### ปัญหา: Scheduler ไม่ทำงาน

```bash
# ตรวจสอบว่า Process ยังรันอยู่
ps aux | grep python

# ตรวจสอบ Log
tail -f logs/scheduler.log
```

### ปัญหา: Duplicate Reminders

ระบบป้องกัน duplicate reminders อัตโนมัติ แต่ถ้าเกิดขึ้น:

```bash
python manage.py shell
>>> from Booking.models import Notification
>>> Notification.objects.filter(notification_type="reminder", is_sent=False).delete()
```

## 📞 ความช่วยเหลือเพิ่มเติม

สำหรับข้อมูลเพิ่มเติม ดู:
- [REMINDER_SYSTEM.md](REMINDER_SYSTEM.md) - เอกสารทางเทคนิค
- [README.md](README.md) - ข้อมูลระบบทั่วไป
- Django Admin: `/admin/booking/notification/`

---

**ติดตั้งเสร็จแล้ว! ระบบส่งเมลแจ้งเตือนพร้อมใช้งาน ✓**
