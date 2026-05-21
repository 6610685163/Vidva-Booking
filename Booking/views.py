import json
import logging
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.http import JsonResponse
from .models import Booking, Room
from .forms import BookingForm

# นำเข้าฟังก์ชันส่งแจ้งเตือนของเพื่อน
from Users.utils import send_booking_notification

logger = logging.getLogger(__name__)

THAI_MONTHS = {
    "มกราคม": 1,
    "กุมภาพันธ์": 2,
    "มีนาคม": 3,
    "เมษายน": 4,
    "พฤษภาคม": 5,
    "มิถุนายน": 6,
    "กรกฎาคม": 7,
    "สิงหาคม": 8,
    "กันยายน": 9,
    "ตุลาคม": 10,
    "พฤศจิกายน": 11,
    "ธันวาคม": 12,
}

THAI_DAYS = {
    "จันทร์": "0",
    "อังคาร": "1",
    "พุธ": "2",
    "พฤหัสบดี": "3",
    "ศุกร์": "4",
    "เสาร์": "5",
    "อาทิตย์": "6",
}


def parse_thai_date(date_str):
    try:
        parts = date_str.split()
        day = int(parts[0])
        month = THAI_MONTHS.get(parts[1], 1)
        year = int(parts[2]) - 543
        return date(year, month, day)
    except Exception:
        return date.today()


@login_required(login_url="login")
def booking_flow_view(request):
    if request.method == "POST":
        room_raw = request.POST.get("room_name", "")
        room_code = room_raw.split("(")[0].strip() if "(" in room_raw else room_raw
        room_code = room_code.replace("ENG ", "").strip()
        room = Room.objects.filter(room_code=room_code).first()

        if not room:
            messages.error(request, "ไม่พบข้อมูลห้องที่เลือกในระบบ")
            return redirect("booking_flow")

        purpose = request.POST.get("purpose", "")
        booking_type = request.POST.get("booking_type", "daily")

        # 🎯 รับค่าอีเมลแจ้งเตือน (ฟีเจอร์ของเพื่อน)
        notification_email = request.POST.get("notification_email", "").strip()
        if not notification_email:
            notification_email = (
                request.user.email
            )  # ถ้าไม่กรอก ให้ใช้อีเมลของ User แทน

        # ==========================================
        # 1. จองแบบรายวัน
        # ==========================================
        if booking_type != "semester":
            selected_data_str = request.POST.get("selected_data", "[]")
            try:
                slots = json.loads(selected_data_str)
            except json.JSONDecodeError:
                messages.error(request, "รูปแบบข้อมูลวันเวลาไม่ถูกต้อง")
                return redirect("booking_flow")

            if not slots:
                messages.error(request, "กรุณาเลือกวันและเวลาอย่างน้อย 1 ช่วง")
                return redirect("booking_flow")

            for slot in slots:
                booking_date = parse_thai_date(slot.get("dateStr", ""))

                # ป้องกันบั๊กเรื่องการเว้นวรรค
                time_str_clean = slot.get("timeStr", "").replace(" - ", "-")
                time_range = time_str_clean.split("-")

                start_time_str = time_range[0].strip()
                end_time_str = time_range[1].strip()

                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
                day_num = str(booking_date.weekday())

                # Conflict Detection
                conflict_exists = Booking.objects.filter(
                    room=room,
                    status__in=["pending", "approved"],
                    start_date__lte=booking_date,
                    end_date__gte=booking_date,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                    days_of_week__contains=day_num,
                ).exists()

                if conflict_exists:
                    messages.error(
                        request,
                        f"❌ ไม่สามารถจองได้ เนื่องจากห้องมีการจองทับซ้อนในวันที่ {slot.get('dateStr')}",
                    )
                    return redirect("booking_flow")

                # บันทึกลงฐานข้อมูล
                booking = Booking.objects.create(
                    room=room,
                    booker=request.user,
                    purpose_type="training" if "ติว" in purpose else "class",
                    topic=purpose,
                    start_date=booking_date,
                    end_date=booking_date,
                    start_time=start_time,
                    end_time=end_time,
                    days_of_week=day_num,
                    status="pending",
                    notification_email=notification_email,
                )

                # ส่ง Email แจ้งเตือน
                try:
                    send_booking_notification(booking, "new_booking")
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")

            messages.success(
                request, "🎉 ส่งคำขอจองห้องแบบรายวันเรียบร้อยแล้ว (รอการอนุมัติ)"
            )
            return redirect("dashboard")

        # ==========================================
        # 2. จองแบบทั้งเทอม
        # ==========================================
        else:
            days_list = request.POST.getlist("days")
            times_list = request.POST.getlist("times")

            if not days_list or not times_list:
                messages.error(
                    request, "กรุณาเลือกวันในสัปดาห์และช่วงเวลาที่ต้องการสอน"
                )
                return redirect("booking_flow")

            db_days = [THAI_DAYS.get(d) for d in days_list if d in THAI_DAYS]
            days_of_week_str = ",".join(db_days)

            start_semester = date.today()
            end_semester = start_semester + timedelta(days=120)

            for time_slot in times_list:
                time_str_clean = time_slot.replace(" - ", "-")
                time_range = time_str_clean.split("-")

                start_time = datetime.strptime(time_range[0].strip(), "%H:%M").time()
                end_time = datetime.strptime(time_range[1].strip(), "%H:%M").time()

                # 🛡️ Conflict Detection
                conflict_query = (
                    Q(room=room)
                    & Q(status__in=["pending", "approved"])
                    & Q(start_date__lte=end_semester)
                    & Q(end_date__gte=start_semester)
                    & Q(start_time__lt=end_time)
                    & Q(end_time__gt=start_time)
                )

                conflicts = Booking.objects.filter(conflict_query)
                has_conflict = False
                for conf in conflicts:
                    conf_days = set(conf.days_of_week.split(","))
                    if conf_days.intersection(set(db_days)):
                        has_conflict = True
                        break

                if has_conflict:
                    messages.error(
                        request,
                        f"❌ ไม่สามารถจองทั้งเทอมได้ เนื่องจากช่วงเวลา {time_slot} มีวิชาอื่นจองอยู่แล้ว",
                    )
                    return redirect("booking_flow")

                # บันทึกลงฐานข้อมูล
                booking = Booking.objects.create(
                    room=room,
                    booker=request.user,
                    purpose_type="class",
                    subject_code=(
                        purpose.split()[0] if len(purpose.split()) > 0 else purpose
                    ),
                    subject_name=purpose,
                    start_date=start_semester,
                    end_date=end_semester,
                    start_time=start_time,
                    end_time=end_time,
                    days_of_week=days_of_week_str,
                    status="pending",
                    notification_email=notification_email,
                )

                # 🎯 ส่ง Email แจ้งเตือน
                try:
                    send_booking_notification(booking, "new_booking")
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")

            messages.success(
                request, "🎉 ส่งคำขอจองห้องสำหรับการเรียนการสอนทั้งเทอมเรียบร้อยแล้ว"
            )
            return redirect("dashboard")

    # ==========================================
    # GET: โหลดหน้าเว็บปฏิทินและข้อมูลห้อง
    # ==========================================
    rooms = Room.objects.filter(is_active=True)
    active_bookings = Booking.objects.filter(status__in=["pending", "approved"])
    booked_list = []

    for b in active_bookings:
        booked_list.append(
            {
                "room_code": b.room.room_code,
                "start_date": b.start_date.strftime("%Y-%m-%d"),
                "start_time": b.start_time.strftime("%H:%M"),
                "end_time": b.end_time.strftime("%H:%M"),
            }
        )

    context = {
        "rooms": rooms,
        "booked_data_json": json.dumps(booked_list),
        "title": "จองห้องเรียน/ห้องประชุม",
    }
    return render(request, "Booking/booking_flow.html", context)


# ==========================================
# Views อื่นๆ ของระบบ
# ==========================================


@login_required(login_url="login")
def pending_bookings_view(request):
    if not request.user.profile.is_admin():
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect("dashboard")

    bookings = Booking.objects.filter(status="pending").order_by("start_date")
    return render(
        request,
        "Booking/pending_bookings.html",
        {"bookings": bookings, "title": "จัดการการจองที่รออนุมัติ"},
    )



@login_required(login_url="login")
@require_http_methods(["POST"])
def approve_booking(request, booking_id):
    if not request.user.profile.is_admin():
        return redirect("dashboard")

    booking = get_object_or_404(Booking, id=booking_id)

    booking.status = "approved"
    booking.save()

    # ส่งเมลแจ้ง user ว่าอนุมัติแล้ว
    send_booking_notification(booking, "status_change")

    messages.success(
        request,
        f"อนุมัติการจองห้อง {booking.room.room_code} เรียบร้อยแล้ว",
    )

    return redirect("pending_bookings")


@login_required(login_url="login")
@require_http_methods(["POST"])
def reject_booking(request, booking_id):
    if not request.user.profile.is_admin():
        return redirect("dashboard")

    booking = get_object_or_404(Booking, id=booking_id)

    reason = request.POST.get("rejection_reason", "")

    booking.status = "rejected"
    booking.rejection_reason = reason
    booking.save()

    # ส่งเมลแจ้ง user ว่าถูกปฏิเสธ
    send_booking_notification(booking, "status_change")

    messages.warning(
        request,
        f"ปฏิเสธการจองห้อง {booking.room.room_code} แล้ว",
    )

    return redirect("pending_bookings")


@login_required(login_url="login")
@require_http_methods(["GET"])
def my_bookings_view(request):
    my_bookings = Booking.objects.filter(booker=request.user).order_by("-created_at")
    return render(
        request,
        "Booking/my_bookings.html",
        {"title": "ประวัติการจองของฉัน", "my_bookings": my_bookings},
    )


@login_required(login_url="login")
def booking_calendar_view(request):
    return render(request, "Booking/booking_calendar.html")


# ==========================================
# Chatbot API View
# ==========================================
@login_required(login_url="login")
def chatbot_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message", "").strip().lower()

            # Rule-based Logic (เช็ค Keyword)
            if any(word in user_message for word in ["สวัสดี", "ดีจ้า", "ทักทาย"]):
                reply = f"สวัสดีครับคุณ {request.user.first_name or request.user.username}! ผมคือผู้ช่วย Vidva Booking มีอะไรให้ผมช่วยไหมครับ?"

            elif any(word in user_message for word in ["ว่าง", "ห้องว่าง", "เช็คห้อง"]):
                reply = "คุณสามารถเช็คห้องว่างได้ที่หน้า 'ปฏิทินตารางห้อง' หรือกดเลือกเวลาในเมนู 'จองห้องใหม่' ระบบจะตรวจสอบให้ทันทีครับ 📅"

            elif any(word in user_message for word in ["จอง", "วิธีจอง", "อยากจอง"]):
                reply = "การจองห้องทำได้ง่ายๆ:\n1. ไปที่เมนู 'จองห้องใหม่'\n2. เลือกห้องและวัตถุประสงค์\n3. เลือกวัน-เวลาที่ต้องการ\n4. กดยืนยันเพื่อรอเจ้าหน้าที่อนุมัติครับ 📝"

            elif any(word in user_message for word in ["ยกเลิก", "ไม่จองแล้ว"]):
                reply = "หากต้องการยกเลิก ให้ไปที่เมนู 'รายการจองของฉัน' แล้วกดปุ่มยกเลิกในรายการที่ยังไม่ถึงวันใช้งานได้เลยครับ ❌"

            elif any(word in user_message for word in ["อนุมัติ", "สถานะ", "รอนานไหม"]):
                reply = "ปกติเจ้าหน้าที่จะใช้เวลาพิจารณาอนุมัติภายใน 1-2 วันทำการ หากได้รับการอนุมัติจะมี Email แจ้งเตือนส่งไปให้ครับ 📧"

            # เมนูคำสั่งทั้งหมด
            elif any(
                word in user_message
                for word in ["เมนู", "ช่วยเหลือ", "คำสั่ง", "ทำอะไรได้บ้าง"]
            ):
                reply = (
                    "นี่คือคำสั่งที่ผมสามารถช่วยได้ครับ กดพิมพ์คำเหล่านี้มาได้เลย:\n"
                    "- 📅 **'วิธีจอง'** (ดูขั้นตอนการจอง)\n"
                    "- 🔍 **'เช็คห้อง'** (วิธีดูตารางว่าง)\n"
                    "- ❌ **'ยกเลิก'** (วิธียกเลิกการจอง)\n"
                    "- ⏳ **'สถานะ'** (ระยะเวลาอนุมัติ)"
                )

            # ข้อความเมื่อบอทไม่เข้าใจ (Fallback)
            else:
                reply = (
                    "ขออภัยครับ ผมยังไม่ค่อยเข้าใจคำถามนี้ 😅\n"
                    "ลองพิมพ์คำสั่งสั้นๆ เช่น 'วิธีจอง', 'เช็คห้อง', หรือพิมพ์ 'เมนู' เพื่อดูว่าผมช่วยอะไรได้บ้างนะครับ"
                )

            return JsonResponse({"reply": reply})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request method"}, status=405)
