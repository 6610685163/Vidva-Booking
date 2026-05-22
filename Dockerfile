# ใช้ Python เวอร์ชั่น 3.13 (เวอร์ชั่นเล็กและเบา)
FROM python:3.13-slim

# ตั้งค่าไม่ให้ Python สร้างไฟล์ .pyc และให้แสดง Log ทันที
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# สร้างโฟลเดอร์ /app ใน Container และย้ายเข้าไปทำงานในนั้น
WORKDIR /app

# ก๊อปปี้ไฟล์ requirements.txt เข้าไปก่อน เพื่อติดตั้งไลบรารี
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# ก๊อปปี้โค้ดโปรเจกต์ทั้งหมดของเราตามเข้าไป
COPY . /app/

# เปิด Port 8000 ให้คนภายนอกเข้าถึงได้
EXPOSE 8000

# คำสั่งสำหรับรันเซิร์ฟเวอร์เมื่อ Container เริ่มทำงาน
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]