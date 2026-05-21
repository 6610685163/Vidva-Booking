#!/bin/bash
# Script สำหรับรัน Scheduler ส่งเมลแจ้งเตือน (Linux/Mac)

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Booking System - Reminder Email Scheduler              ║"
echo "║     จะส่งเมลแจ้งเตือนทุกวันเวลา 08:00 น.                ║"
echo "║     กด Ctrl+C เพื่อหยุด                                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ตรวจสอบว่า virtual environment มีอยู่
if [ ! -d ".venv" ]; then
    echo "✗ Virtual environment ไม่พบ"
    echo "ทำการติดตั้ง: python -m venv .venv"
    python -m venv .venv
    echo "✓ สร้าง virtual environment แล้ว"
fi

# เปิดใช้งาน virtual environment
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "✗ ไม่สามารถเปิดใช้งาน virtual environment"
    exit 1
fi

# ติดตั้ง/อัปเดต dependencies
echo ""
echo "⏳ ตรวจสอบและติดตั้ง dependencies..."
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "✗ ไม่สามารถติดตั้ง dependencies"
    exit 1
fi
echo "✓ Dependencies ติดตั้งแล้ว"

# รัน scheduler
echo ""
echo "⏳ เริ่มต้น Scheduler..."
echo ""
python run_reminders_scheduler.py
