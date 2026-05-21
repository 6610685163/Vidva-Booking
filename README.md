# Vidva Booking

**ระบบจองห้องประชุมและห้องเรียน ภาควิชาวิศวกรรมไฟฟ้าและคอมพิวเตอร์ (TSE)**
ระบบเว็บแอปพลิเคชันสำหรับบริหารจัดการการจองห้องเรียนและห้องประชุมจำนวน 5 ห้อง พัฒนาด้วย Django Framework โดยรองรับการยืนยันตัวตนผ่านระบบของมหาวิทยาลัยธรรมศาสตร์

## ขอบเขตของระบบ
ระบบถูกออกแบบมาเพื่ออำนวยความสะดวกในการจองห้องพักภายในภาควิชาฯ โดยมีระบบตรวจสอบความขัดแย้งของเวลา (Conflict Detection) การแสดงผลผ่านปฏิทิน และการอนุมัติการจองโดยเจ้าหน้าที่

### รายชื่อห้องในระบบ
| รหัสห้อง | ชื่อห้อง | ประเภท | จำนวนที่นั่ง |
| :--- | :--- | :--- | :--- |
| **406-3** | ห้องประชุม 1 | ห้องประชุม | 60 |
| **406-5** | ห้องประชุม 2 | ห้องประชุม | 15 |
| **408-1** | ห้องประชุม 3 | ห้องประชุม | 10 |
| **408-2/1** | ห้องบรรยาย 1 | ห้องเรียน | 20 |
| **408-2/2** | ห้องบรรยาย 2 | ห้องเรียน | 20 |

## ฟีเจอร์หลัก
* **Authentication:** เข้าสู่ระบบผ่าน TU REST API (Username/Password เดียวกับ TU-WiFi)
* **Role Management:** แบ่งสิทธิ์ผู้ใช้เป็น อาจารย์ (จอง/ดูปฏิทิน) และ เจ้าหน้าที่ (อนุมัติ/จัดการห้อง/ดูรายงาน)
* **Booking System:** ระบุวัตถุประสงค์การใช้งาน (การเรียนการสอน หรือ จัดอบรม) และรองรับการจองแบบซ้ำ (Recurring)
* **Calendar:** ตรวจสอบความว่างของห้องผ่านปฏิทินรายสัปดาห์และรายเดือน
* **Notification:** แจ้งเตือนสถานะการจองผ่าน Email โดยอัตโนมัติ

## เทคโนโลยีที่ใช้
* **Backend:** Python / Django 6.0.4
* **Database:** SQLite (Development) / PostgreSQL (Production)
* **API:** TU REST API Integration
* **UI:** Responsive Design (CSS Grid)

## ขั้นตอนการติดตั้งและตั้งค่า

1. **Clone โปรเจค และสร้าง Virtual Environment:**
   ```bash
   git clone <repository-url>
   cd TSE-Room-Booking
   python -m venv .venv
   .\venv\Scripts\activate # สำหรับ Windows  
   ```

2. **ติดตั้ง Library:**
   ```bash
   pip install -r requirements.txt
   ```

3. **ตั้งค่า Environment Variables:**
   สร้างไฟล์ `.env` โดยคัดลอกข้อมูลจาก `.env.example` และระบุค่า `TU_API_KEY` (Application-Key)

4. **เตรียมฐานข้อมูล (สำคัญ):**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **เพิ่มข้อมูลห้องตั้งต้น (Initial Data):**
   เพื่อให้ระบบมีข้อมูลห้อง 5 ห้องตามเงื่อนไข ให้เข้าสู่ระบบ Django Admin หรือใช้คำสั่ง SQL ดังนี้:
   ```sql
   INSERT INTO Users_room (room_code, room_name, room_type, capacity, is_active) VALUES
   ('406-3', 'ห้องประชุม 1', 'meeting', 60, TRUE),
   ('406-5', 'ห้องประชุม 2', 'meeting', 15, TRUE),
   ('408-1', 'ห้องประชุม 3', 'meeting', 10, TRUE),
   ('408-2/1', 'ห้องบรรยาย 1', 'classroom', 20, TRUE),
   ('408-2/2', 'ห้องบรรยาย 2', 'classroom', 20, TRUE);
   ```

6. **สร้าง Admin User (สำหรับเข้าไปจัดการห้องและสิทธิ์):**
   ```bash
   python manage.py createsuperuser
   ```

7. **เริ่มระบบ:**
   ```bash
   python manage.py runserver
   ```
   
---
**หมายเหตุ:** สำหรับผู้ใช้ใหม่ที่ Login ครั้งแรก เจ้าหน้าที่ (Admin) จะเป็นผู้กำหนดสิทธิ์การใช้งาน (Role) ให้ในระบบจัดการผู้ใช้
