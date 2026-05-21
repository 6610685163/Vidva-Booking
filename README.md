# Vidva Booking

**ระบบจองห้องประชุมและห้องเรียน ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์ (TSE)**

ระบบเว็บแอปพลิเคชันสำหรับบริหารจัดการการจองห้องเรียนและห้องประชุมจำนวน 5 ห้อง พัฒนาด้วย Django Framework โดยรองรับการยืนยันตัวตนผ่านระบบของมหาวิทยาลัยธรรมศาสตร์

---

# ขอบเขตของระบบ

ระบบถูกออกแบบมาเพื่ออำนวยความสะดวกในการจองห้องพักภายในภาควิชาฯ โดยมีระบบตรวจสอบความขัดแย้งของเวลา (Conflict Detection) การแสดงผลผ่านปฏิทิน และการอนุมัติการจองโดยเจ้าหน้าที่

## รายชื่อห้องในระบบ

| รหัสห้อง | ชื่อห้อง | ประเภท | จำนวนที่นั่ง |
| :--- | :--- | :--- | :--- |
| **406-3** | ห้องประชุม 1 | ห้องประชุม | 60 |
| **406-5** | ห้องประชุม 2 | ห้องประชุม | 15 |
| **408-1** | ห้องประชุม 3 | ห้องประชุม | 10 |
| **408-2/1** | ห้องบรรยาย 1 | ห้องเรียน | 20 |
| **408-2/2** | ห้องบรรยาย 2 | ห้องเรียน | 20 |

---

# ฟีเจอร์หลัก

- **Authentication:** เข้าสู่ระบบผ่าน TU REST API (Username/Password เดียวกับ TU-WiFi)
- **Role Management:** แบ่งสิทธิ์ผู้ใช้เป็น อาจารย์ (จอง/ดูปฏิทิน) และ เจ้าหน้าที่ (อนุมัติ/จัดการห้อง/ดูรายงาน)
- **Booking System:** ระบุวัตถุประสงค์การใช้งาน (การเรียนการสอน หรือ จัดอบรม) และรองรับการจองแบบซ้ำ (Recurring)
- **Calendar:** ตรวจสอบความว่างของห้องผ่านปฏิทินรายสัปดาห์และรายเดือน
- **Notification:** แจ้งเตือนสถานะการจองผ่าน Email โดยอัตโนมัติ

---

# เทคโนโลยีที่ใช้

- **Backend:** Python / Django
- **Database:** SQLite (Development) / PostgreSQL (Production)
- **API:** TU REST API Integration
- **UI:** Responsive Design (CSS Grid)

---

# ขั้นตอนการติดตั้งและตั้งค่า

## 1. Clone โปรเจค และสร้าง Virtual Environment

```bash
git clone <repository-url>

cd TSE-Room-Booking

python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows CMD

```cmd
.venv\Scripts\activate.bat
```

---

## 2. ติดตั้ง Library

```bash
pip install -r requirements.txt
```

---

## 3. ตั้งค่า Environment Variables

สร้างไฟล์ `.env`

```env
SECRET_KEY=your-secret-key

TU_API_KEY=your-tu-api-key

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True

EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

DEFAULT_FROM_EMAIL=your-email@gmail.com
ADMIN_EMAIL=admin@gmail.com
```

---

## 4. สร้าง Database และ Apply Migration

```bash
python manage.py makemigrations

python manage.py migrate
```

---

## 5. เพิ่มข้อมูลเริ่มต้นของระบบ

```bash
python manage.py seed_data
```

---

## 6. สร้าง Admin User

```bash
python manage.py createsuperuser
```

---

## 7. เริ่มระบบ

```bash
python manage.py runserver
```

---

# ระบบ Notification

ระบบสามารถส่ง Email อัตโนมัติในกรณีดังต่อไปนี้

- ส่ง Email หา Admin เมื่อมีการจองใหม่
- ส่ง Email หา User เมื่อการจองถูกอนุมัติ
- ส่ง Email หา User เมื่อการจองถูกปฏิเสธ

---

# หมายเหตุ

- ผู้ใช้ใหม่ที่ Login ครั้งแรก จะต้องรอให้เจ้าหน้าที่กำหนดสิทธิ์การใช้งาน (Role)
- หากใช้ Gmail สำหรับส่ง Email จำเป็นต้องใช้ Google App Password แทนรหัสผ่านปกติ
- SQLite ใช้สำหรับ Development เท่านั้น แนะนำ PostgreSQL สำหรับ Production