@echo off
REM Script สำหรับรัน Scheduler ส่งเมลแจ้งเตือน (Windows)

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║     Booking System - Reminder Email Scheduler              ║
echo ║     จะส่งเมลแจ้งเตือนทุกวันเวลา 08:00 น.                ║
echo ║     กด Ctrl+C เพื่อหยุด                                   ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM ตรวจสอบว่า virtual environment มีอยู่
if not exist ".venv\Scripts\activate.bat" (
    echo ✗ Virtual environment ไม่พบ
    echo ทำการติดตั้ง: python -m venv .venv
    python -m venv .venv
    echo ✓ สร้าง virtual environment แล้ว
)

REM เปิดใช้งาน virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ✗ ไม่สามารถเปิดใช้งาน virtual environment
    exit /b 1
)

REM ติดตั้ง/อัปเดต dependencies
echo.
echo ⏳ ตรวจสอบและติดตั้ง dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ✗ ไม่สามารถติดตั้ง dependencies
    exit /b 1
)
echo ✓ Dependencies ติดตั้งแล้ว

REM รัน scheduler
echo.
echo ⏳ เริ่มต้น Scheduler...
echo.
python run_reminders_scheduler.py
pause
