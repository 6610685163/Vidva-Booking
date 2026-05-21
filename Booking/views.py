import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from Users.models import Room, Booking
from Users.utils import send_booking_notification

THAI_MONTHS = [
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]


def parse_thai_date(date_str):
    """แปลงข้อความ '22 พฤษภาคม 2569' เป็นวัตถุเวลาในระบบ Python"""
    parts = date_str.split()
    day = int(parts[0])
    month = THAI_MONTHS.index(parts[1]) + 1
    year = int(parts[2]) - 543  # แปลงปี พ.ศ. เป็น ค.ศ.
    return datetime(year, month, day).date()


@login_required(login_url="login")
def booking_flow_view(request):
    if request.method == "POST":
        booking_type = request.POST.get("booking_type", "daily")
        room_name_raw = request.POST.get("room_name", "")
        purpose = request.POST.get("purpose", "")

        # ดึงค่าอีเมลแจ้งเตือนที่ผู้ใช้ระบุเอง
        notification_email = request.POST.get("notification_email", "").strip()

        if not notification_email:
            messages.error(request, "กรุณาระบุอีเมลสำหรับรับการแจ้งเตือนผล")
            return redirect("booking_flow")

        # ค้นหา Object ห้องจากชื่อที่ส่งมาจากหน้าเว็บ
        room = None
        for r in Room.objects.filter(is_active=True):
            if r.room_code in room_name_raw:
                room = r
                break

        if not room:
            messages.error(request, "ไม่พบห้องที่เลือกในระบบฐานข้อมูล")
            return redirect("booking_flow")

        # --- 1. กรณีจองรายวัน (คลิกเลือกวันจากปฏิทิน) ---
        if booking_type != "semester":
            selected_data_json = request.POST.get("selected_data", "[]")
            try:
                slots = json.loads(selected_data_json)
                if not slots:
                    messages.error(request, "กรุณาเลือกวันและเวลาอย่างน้อย 1 ช่วงเวลา")
                    return redirect("booking_flow")

                for slot in slots:
                    date_obj = parse_thai_date(slot["dateStr"])
                    time_range = slot["timeStr"].split(" - ")
                    start_time = datetime.strptime(
                        time_range[0].strip(), "%H:%M"
                    ).time()
                    end_time = datetime.strptime(time_range[1].strip(), "%H:%M").time()
                    day_of_week_num = str(date_obj.weekday())

                    booking = Booking.objects.create(
                        room=room,
                        booker=request.user,
                        purpose_type="training",
                        topic=purpose,
                        start_date=date_obj,
                        end_date=date_obj,
                        start_time=start_time,
                        end_time=end_time,
                        days_of_week=day_of_week_num,
                        notification_email=notification_email,  # บันทึกอีเมล
                        status="pending",
                    )
                    send_booking_notification(booking, "new_booking")

                messages.success(request, "ส่งคำขอจองห้องเรียบร้อยแล้ว!")
                return redirect("dashboard")

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
                return redirect("booking_flow")

        # --- 2. กรณีจองทั้งเทอม (เลือกวันจันทร์-ศุกร์) ---
        else:
            days = request.POST.getlist("days")
            times = request.POST.getlist("times")

            if not days or not times:
                messages.error(request, "กรุณาเลือกวันในสัปดาห์และช่วงเวลา")
                return redirect("booking_flow")

            day_mapping = {
                "จันทร์": "0",
                "อังคาร": "1",
                "พุธ": "2",
                "พฤหัสบดี": "3",
                "ศุกร์": "4",
                "เสาร์": "5",
                "อาทิตย์": "6",
            }
            days_numeric = [day_mapping[d] for d in days if d in day_mapping]

            # สมมุติเวลาเปิดเทอม (120 วัน)
            start_semester = datetime.now().date()
            end_semester = start_semester + timedelta(days=120)

            try:
                for time_str in times:
                    time_range = time_str.split(" - ")
                    start_time = datetime.strptime(
                        time_range[0].strip(), "%H:%M"
                    ).time()
                    end_time = datetime.strptime(time_range[1].strip(), "%H:%M").time()

                    booking = Booking.objects.create(
                        room=room,
                        booker=request.user,
                        purpose_type="class",
                        subject_name=purpose,
                        subject_code=(
                            purpose.split()[0] if len(purpose.split()) > 0 else ""
                        ),
                        start_date=start_semester,
                        end_date=end_semester,
                        start_time=start_time,
                        end_time=end_time,
                        days_of_week=",".join(days_numeric),
                        notification_email=notification_email,  # บันทึกอีเมล
                        status="pending",
                    )
                    send_booking_notification(booking, "new_booking")

                messages.success(
                    request, "ส่งคำขอจองห้องเรียนแบบประจำทั้งเทอมสำเร็จแล้ว!"
                )
                return redirect("dashboard")
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
                return redirect("booking_flow")

    # สำหรับโหลดหน้าเว็บปกติ (GET)
    context = {
        "title": "จองห้อง",
        "user": request.user,
    }
    return render(request, "Booking/booking_flow.html", context)
