# Create your views here.
import json
import logging
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .models import Booking, Room
from .forms import BookingForm

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
    """แปลงข้อความ '28 พฤษภาคม 2569' -> object date(2026, 5, 28)"""
    try:
        parts = date_str.split()
        day = int(parts[0])
        month = THAI_MONTHS.get(parts[1], 1)
        year = int(parts[2]) - 543  # แปลง พ.ศ. เป็น ค.ศ.
        return date(year, month, day)
    except Exception:
        return date.today()


@login_required(login_url="login")
def booking_flow_view(request):
    if request.method == "POST":
        # 1. ถอดรหัสหาห้องจากชื่อเต็ม เช่น "ENG 406-3(ห้องประชุม 1)" -> "ENG 406-3"
        room_raw = request.POST.get("room_name", "")
        room_code = room_raw.split("(")[0].strip() if "(" in room_raw else room_raw
        room = Room.objects.filter(room_code=room_code).first()

        if not room:
            messages.error(request, "ไม่พบข้อมูลห้องที่เลือกในระบบ")
            return redirect("booking_flow")

        purpose = request.POST.get("purpose", "")
        booking_type = request.POST.get("booking_type", "daily")

        # ==========================================
        # CASE A: จัดการการจองแบบรายวัน (ดึงค่าจาก JSON)
        # ==========================================
        if booking_type != "semester":
            selected_data_str = request.POST.get("selected_data", "[]")
            try:
                slots = json.loads(selected_data_str)  # แกะกล่อง JSON ออกเป็น List
            except json.JSONDecodeError:
                messages.error(request, "รูปแบบข้อมูลวันเวลาไม่ถูกต้อง")
                return redirect("booking_flow")

            if not slots:
                messages.error(request, "กรุณาเลือกวันและเวลาอย่างน้อย 1 ช่วง")
                return redirect("booking_flow")

            # วนลูปตรวจสอบและบันทึกทีละช่วงเวลาที่เลือก
            for slot in slots:
                booking_date = parse_thai_date(slot.get("dateStr", ""))
                time_range = slot.get("timeStr", "").split("-")
                start_time_str = time_range[0].strip()
                end_time_str = time_range[1].strip()

                # แปลงเวลาเป็นออบเจกต์เพื่อนำไปใช้งาน
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
                day_num = str(booking_date.weekday())  # ดึงหมายเลขวัน (0=จันทร์)

                # ทำการตรวจเช็ค Conflict Detection ทันที
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
                        f"❌ ไม่สามารถจองได้ เนื่องจากห้อง {room.room_code} มีการจองทับซ้อนในวันที่ {slot.get('dateStr')}",
                    )
                    return redirect("booking_flow")

                # ถ้าผ่านด่านประเมิน ทำการบันทึกข้อมูลงฐานข้อมูล
                Booking.objects.create(
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
                )

            messages.success(
                request, "🎉 ส่งคำขอจองห้องแบบรายวันเรียบร้อยแล้ว (รอการอนุมัติ)"
            )
            return redirect("dashboard")

        # ==========================================
        # CASE B: จัดการการจองแบบทั้งเทอม
        # ==========================================
        else:
            days_list = request.POST.getlist("days")
            times_list = request.POST.getlist("times")

            if not days_list or not times_list:
                messages.error(
                    request, "กรุณาเลือกวันในสัปดาห์และช่วงเวลาที่ต้องการสอน"
                )
                return redirect("booking_flow")

            # แปลงชื่อวันภาษาไทย เช่น ["จันทร์", "พุธ"] -> "0,2"
            db_days = [THAI_DAYS.get(d) for d in days_list if d in THAI_DAYS]
            days_of_week_str = ",".join(db_days)

            # กำหนดขอบเขตเวลาของภาคการศึกษานั้นๆ (สมมุติระยะเวลาเทอม 4 เดือนนับจากวันนี้)
            start_semester = date.today()
            end_semester = start_semester + timedelta(days=120)

            for time_slot in times_list:
                time_range = time_slot.split("-")
                start_time = datetime.strptime(time_range[0].strip(), "%H:%M").time()
                end_time = datetime.strptime(time_range[1].strip(), "%H:%M").time()

                # ตรวจสอบเวลาทับซ้อนตลอดทั้งภาคการศึกษา
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
                        f"❌ ไม่สามารถจองทั้งเทอมได้ เนื่องจากช่วงเวลา {time_slot} ในวันที่เลือก มีวิชาอื่นจองอยู่ก่อนแล้ว",
                    )
                    return redirect("booking_flow")

                # บันทึกข้อมูลการจองระยะยาวลงฐานข้อมูล
                Booking.objects.create(
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
                )

            messages.success(
                request, "🎉 ส่งคำขอจองห้องสำหรับการเรียนการสอนทั้งเทอมเรียบร้อยแล้ว"
            )
            return redirect("dashboard")

    # สำหรับคำขอแบบ GET: แสดงหน้าจอเลือกห้องตามปกติ
    rooms = Room.objects.filter(is_active=True)

    # 🎯 ดึงคิวการจองทั้งหมดที่ยัง Active อยู่ มาแพ็กเป็น JSON ส่งให้ปฏิทิน
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
        "booked_data_json": json.dumps(booked_list),  # ส่งก้อนข้อมูลนี้ไปให้ Javascript
    }

    return render(request, "Booking/booking_flow.html", context)


# @login_required(login_url="login")
# def booking_flow_view(request):

#     rooms = Room.objects.filter(is_active=True)

#     context = {
#         "title": "จองห้อง",
#         "user": request.user,
#         "rooms": rooms,
#     }
#     return render(request, "Booking/booking_flow.html", context)


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def create_booking_view(request):
    """
    View for users to create a new booking
    """
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.booker = request.user  # FR-BOOK-07
            booking.days_of_week = ",".join(form.cleaned_data["selected_days"])

            # FR-BOOK-06 Conflict Detection
            conflicts = Booking.objects.filter(
                room=booking.room,
                status__in=["pending", "approved"],
                start_date__lte=booking.end_date,
                end_date__gte=booking.start_date,
                start_time__lt=booking.end_time,
                end_time__gt=booking.start_time,
            )

            # ตรวจสอบเพิ่มเติมว่าวันในสัปดาห์ทับซ้อนกันหรือไม่
            has_conflict = False
            for conf in conflicts:
                conf_days = set(conf.days_of_week.split(","))
                req_days = set(form.cleaned_data["selected_days"])
                if conf_days.intersection(req_days):
                    has_conflict = True
                    break

            if has_conflict:
                messages.error(
                    request, _("ห้องถูกจองในช่วงเวลาดังกล่าวแล้ว กรุณาเลือกเวลาอื่น")
                )
            else:
                booking.save()
                logger.info(
                    f"User {request.user.username} created booking for {booking.room}"
                )
                messages.success(request, _("บันทึกการจองสำเร็จ (รอการอนุมัติ)"))
                # หมายเหตุ: การส่งอีเมลแจ้ง Admin (FR-NOTI-01) จะนำมาใส่ตรงนี้ในอนาคต
                return redirect("dashboard")
    else:
        form = BookingForm()

    context = {
        "form": form,
        "title": _("สร้างการจองห้อง"),
    }
    return render(request, "Booking/create_booking.html", context)


@login_required(login_url="login")
def pending_bookings_view(request):
    """
    หน้าแสดงรายการจองที่รอการอนุมัติ (Admin Only)
    """
    # ตรวจสอบสิทธิ์ Admin
    if not request.user.profile.is_admin():
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect("dashboard")

    # ดึงรายการจองที่เป็น 'pending'
    bookings = Booking.objects.filter(status="pending").order_by("start_date")

    context = {
        "bookings": bookings,
        "title": "จัดการการจองที่รออนุมัติ",
    }
    return render(request, "Booking/pending_bookings.html", context)


@login_required(login_url="login")
@require_http_methods(["POST"])
def approve_booking(request, booking_id):
    """
    ฟังก์ชันสำหรับอนุมัติการจอง
    """
    if not request.user.profile.is_admin():
        return redirect("dashboard")

    booking = get_object_or_404(Booking, id=booking_id)
    booking.status = "approved"
    booking.save()

    # ตรงนี้สามารถเพิ่ม logic ส่ง Email แจ้งเตือนผู้จองได้ (FR-APPR-04)

    messages.success(
        request, f"อนุมัติการจองห้อง {booking.room.room_code} เรียบร้อยแล้ว"
    )
    return redirect("pending_bookings")


@login_required(login_url="login")
@require_http_methods(["POST"])
def reject_booking(request, booking_id):
    """
    ฟังก์ชันสำหรับปฏิเสธการจอง พร้อมระบุเหตุผล
    """
    if not request.user.profile.is_admin():
        return redirect("dashboard")

    booking = get_object_or_404(Booking, id=booking_id)
    reason = request.POST.get("rejection_reason", "")

    booking.status = "rejected"
    booking.rejection_reason = reason
    booking.save()

    messages.warning(request, f"ปฏิเสธการจองห้อง {booking.room.room_code} แล้ว")
    return redirect("pending_bookings")


@login_required(login_url="login")
@require_http_methods(["GET"])
def my_bookings_view(request):
    """
    หน้าแสดงประวัติการจองห้องของ User แต่ละคน
    """
    my_bookings = Booking.objects.filter(booker=request.user).order_by("-created_at")

    context = {
        "title": "ประวัติการจองของฉัน",
        "my_bookings": my_bookings,
    }
    return render(request, "Booking/my_bookings.html", context)
