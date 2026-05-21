#!/usr/bin/env python
"""
Script สำหรับตั้งค่า scheduler ให้รัน send_reminders command ทุกวันเวลา 08:00 น.
สำหรับ Windows: ให้ใช้ Task Scheduler
สำหรับ Linux/Mac: ให้ใช้ crontab หรือ systemd timer
"""

import os
import sys
import django
from datetime import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# ตั้งค่า Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Tse_Booking.settings')
django.setup()

from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def send_reminders_job():
    """ฟังก์ชันที่จะเรียก management command"""
    try:
        call_command('send_reminders')
        logger.info("✓ ส่งเมลแจ้งเตือนเรียบร้อยแล้ว")
    except Exception as e:
        logger.error(f"✗ เกิดข้อผิดพลาดในการส่งเมลแจ้งเตือน: {e}")


def start_scheduler():
    """เริ่มต้น APScheduler"""
    scheduler = BackgroundScheduler()
    
    # ตั้งให้รัน ทุกวันเวลา 08:00 น.
    scheduler.add_job(
        send_reminders_job,
        trigger=CronTrigger(hour=8, minute=0),
        id='send_reminders_daily',
        name='ส่งเมลแจ้งเตือนทุกวันเวลา 08:00',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✓ Scheduler เริ่มต้นแล้ว - จะรันทุกวันเวลา 08:00 น.")
    
    try:
        # ให้ scheduler ทำงานต่อเนื่อง
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("✗ Scheduler หยุดแล้ว")


if __name__ == '__main__':
    # ตั้งค่า logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scheduler.log'),
            logging.StreamHandler()
        ]
    )
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║   Scheduler สำหรับส่งเมลแจ้งเตือนการจองห้อง              ║
    ║   จะรันทุกวันเวลา 08:00 น.                             ║
    ║   กด Ctrl+C เพื่อหยุด                                   ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        start_scheduler()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
