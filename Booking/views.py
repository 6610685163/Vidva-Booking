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
from .models import (
    Booking,
    Room,
    # AcademicSemester,
    BlackoutPeriod,
)  # นำเข้าครบทุก Model ทั้ง Semester และ Blackout
from .forms import BookingForm
from Users.models import SystemSettings

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


def _blackout_blocking_for_date(room, target_date):
    """
    ตรวจสอบว่ามี BlackoutPeriod ใดบล็อกห้องนี้ในวันที่กำหนดหรือไม่
    Returns BlackoutPeriod instance ถ้าโดนบล็อก, ไม่งั้น None
    """
    blackouts = BlackoutPeriod.objects.filter(
        is_active=True,
        start_date__lte=target_date,
        end_date__gte=target_date,
    ).prefetch_related("rooms")
    for blk in blackouts:
        # ถ้า rooms ว่าง = ปิดทุกห้อง; ถ้ามีระบุ = เช็คว่าห้องนี้อยู่ในนั้นไหม
        if not blk.rooms.exists() or blk.rooms.filter(id=room.id).exists():
            return blk
    return None


def _blackout_blocking_in_range(room, start_dt, end_dt, days_set):
    """
    ตรวจสอบว่ามี BlackoutPeriod ใดบล็อกห้องนี้ในช่วง [start_dt, end_dt]
    โดยพิจารณาเฉพาะวันที่ weekday ตรงกับ days_set (Mon=0..Sun=6)
    Returns tuple (BlackoutPeriod, conflict_date) ถ้าเจอ, ไม่งั้น (None, None)
    """
    cur = start_dt
    while cur <= end_dt:
        if cur.weekday() in days_set:
            blk = _blackout_blocking_for_date(room, cur)
            if blk:
                return blk, cur
        cur += timedelta(days=1)
    return None, None


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
        # ฟอร์มส่งเป็น "ENG 406-3(...)" แต่ DB เก็บ "406-3" → ต้องตัด prefix
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

                # 🛡️ Blackout Detection (FR-ADM-03) สำหรับรายวัน
                blocking_blackout = _blackout_blocking_for_date(room, booking_date)
                if blocking_blackout:
                    messages.error(
                        request,
                        f"❌ ไม่สามารถจองได้ในวันที่ {slot.get('dateStr')} เนื่องจากอยู่ในช่วงปิดใช้งาน '{blocking_blackout.title}' "
                        f"({blocking_blackout.start_date.strftime('%d/%m/%Y')} - {blocking_blackout.end_date.strftime('%d/%m/%Y')})",
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
            purpose_type_raw = request.POST.get("purpose_type", "class").strip()
            subject_code_raw = request.POST.get("subject_code", "").strip()
            subject_name_raw = request.POST.get("subject_name", "").strip()
            curriculum_raw = request.POST.get("curriculum", "").strip()
            topic_raw = request.POST.get("topic", "").strip()

            if not days_list or not times_list:
                messages.error(
                    request, "กรุณาเลือกวันในสัปดาห์และช่วงเวลาที่ต้องการสอน"
                )
                return redirect("booking_flow")

            if purpose_type_raw == "class" and (
                not subject_code_raw or not subject_name_raw
            ):
                messages.error(request, "กรุณาระบุรหัสวิชาและชื่อวิชาสำหรับการสอน")
                return redirect("booking_flow")

            if purpose_type_raw == "training" and not topic_raw:
                messages.error(request, "กรุณาระบุชื่อเรื่องสำหรับการจัดอบรม/จัดติว")
                return redirect("booking_flow")

            # ดึงข้อมูลเทอมการศึกษาปัจจุบันจาก Admin (ถ้ามี)
            settings = SystemSettings.get_settings()

            if settings.start_date and settings.end_date:
                start_semester = settings.start_date
                end_semester = settings.end_date
            else:
                # Fallback: ถ้า Admin ยังไม่ได้ตั้งภาคการศึกษาหน้าเว็บ
                start_semester = date.today()
                end_semester = start_semester + timedelta(days=120)
                logger.warning(
                    "SystemSettings ยังไม่ได้ตั้งค่า start_date/end_date — ใช้ค่า fallback start=today end=today+120days"
                )

            # if active_semester:
            #     start_semester = active_semester.start_date
            #     end_semester = active_semester.end_date
            # else:
            #     # Fallback: ถ้า Admin ยังไม่ได้ตั้งภาคการศึกษา → ใช้ค่า default (วันนี้ + 120 วัน)
            #     start_semester = date.today()
            #     end_semester = start_semester + timedelta(days=120)
            #     logger.warning(
            #         "ไม่พบ AcademicSemester ที่ active — ใช้ค่า fallback start=today end=today+120days"
            #     )

            db_days = [THAI_DAYS.get(d) for d in days_list if d in THAI_DAYS]
            days_of_week_str = ",".join(db_days)

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

                # 🛡️ Blackout Detection (FR-ADM-03) สำหรับทั้งเทอม
                days_set_int = {int(d) for d in db_days if d and d.isdigit()}
                blocking_blackout, blocked_date = _blackout_blocking_in_range(
                    room, start_semester, end_semester, days_set_int
                )
                if blocking_blackout:
                    messages.error(
                        request,
                        f"❌ ไม่สามารถจองทั้งเทอมได้ เนื่องจากตรงกับช่วงปิดใช้งานห้อง '{blocking_blackout.title}' "
                        f"(ตรงกับวันที่ {blocked_date.strftime('%d/%m/%Y')}). "
                        f"กรุณาแจ้งเจ้าหน้าที่หรือเลือกช่วงเวลาอื่น",
                    )
                    return redirect("booking_flow")

                # บันทึกลงฐานข้อมูล
                create_kwargs = dict(
                    room=room,
                    booker=request.user,
                    purpose_type=purpose_type_raw,
                    start_date=start_semester,
                    end_date=end_semester,
                    start_time=start_time,
                    end_time=end_time,
                    days_of_week=days_of_week_str,
                    status="pending",
                    notification_email=notification_email,
                )
                if purpose_type_raw == "class":
                    create_kwargs["subject_code"] = subject_code_raw
                    create_kwargs["subject_name"] = subject_name_raw
                    create_kwargs["curriculum"] = (
                        curriculum_raw if curriculum_raw else None
                    )
                else:
                    create_kwargs["topic"] = topic_raw

                booking = Booking.objects.create(**create_kwargs)

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
                "end_date": b.end_date.strftime("%Y-%m-%d"),
                "days_of_week": b.days_of_week if b.days_of_week else "",
                "start_time": b.start_time.strftime("%H:%M"),
                "end_time": b.end_time.strftime("%H:%M"),
            }
        )

    # 🌟 [เพิ่มโค้ดส่วนนี้] ดึงข้อมูลช่วงเวลาปิดใช้งานห้อง (Blackout)
    blackouts_data = []
    for blk in BlackoutPeriod.objects.filter(is_active=True).prefetch_related("rooms"):
        affected_rooms = [r.room_code for r in blk.rooms.all()]
        blackouts_data.append({
            "id": blk.id,
            "title": blk.title,
            "start_date": blk.start_date.strftime("%Y-%m-%d"),
            "end_date": blk.end_date.strftime("%Y-%m-%d"),
            "affected_rooms": affected_rooms,
        })

    context = {
        "rooms": rooms,
        "booked_data_json": json.dumps(booked_list),
        "blackouts_json": json.dumps(blackouts_data), # 🌟 [เพิ่มตัวแปรนี้]
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
@require_http_methods(["POST"])
def cancel_booking(request, booking_id):
    """
    ผู้จองยกเลิกการจองของตัวเอง (FR-BOOK-08)
    เงื่อนไข: ต้องเป็นเจ้าของ booking และ status ต้องเป็น pending หรือ approved
    และวันจองยังไม่ถึง
    """
    booking = get_object_or_404(Booking, id=booking_id)

    # เช็คเจ้าของ
    if booking.booker_id != request.user.id:
        messages.error(request, "คุณไม่มีสิทธิ์ยกเลิกการจองนี้")
        return redirect("my_bookings")

    # เช็คสถานะ
    if booking.status not in ("pending", "approved"):
        messages.warning(
            request,
            f"การจองนี้อยู่ในสถานะ '{booking.get_status_display()}' ยกเลิกไม่ได้",
        )
        return redirect("my_bookings")

    # เช็คว่าวันสิ้นสุดยังไม่ผ่าน
    if booking.end_date < date.today():
        messages.warning(request, "การจองนี้ผ่านวันใช้งานไปแล้ว ยกเลิกไม่ได้")
        return redirect("my_bookings")

    booking.status = "cancelled"
    booking.save()
    logger.info(f"User {request.user.username} cancelled booking #{booking.id}")
    messages.success(
        request,
        f"ยกเลิกการจองห้อง {booking.room.room_code} เรียบร้อยแล้ว",
    )
    return redirect("my_bookings")


@login_required(login_url="login")
def booking_calendar_view(request):
    """
    ปฏิทินภาพรวมการใช้ห้องสำหรับ user (ดูก่อนจองว่าวันไหน/ห้องไหน เต็ม/ว่าง)
    ส่ง bookings (ทุกคน) + blackouts เป็น JSON ให้ JS render
    โครงสร้างเหมือน admin_calendar เพื่อให้ผู้ใช้ตรวจสอบสถานะห้องก่อนสร้างการจอง
    """
    today = date.today()
    horizon_start = today - timedelta(days=180)
    horizon_end = today + timedelta(days=365)

    rooms = Room.objects.filter(is_active=True).order_by("room_code")

    # ดึง booking ของ "ทุกคน" ที่ active (pending + approved) ในช่วง horizon
    booking_qs = (
        Booking.objects.filter(
            status__in=["pending", "approved"],
            start_date__lte=horizon_end,
            end_date__gte=horizon_start,
        )
        .select_related("room", "booker")
        .order_by("start_date", "start_time")
    )

    bookings_data = []
    for b in booking_qs:
        try:
            days_list = [
                int(d.strip())
                for d in (b.days_of_week or "").split(",")
                if d.strip().isdigit()
            ]
        except AttributeError:
            days_list = []

        # ประกอบ title ที่จะโชว์
        title = b.subject_name or b.topic or "(ไม่ระบุ)"
        if b.subject_code:
            title = f"{b.subject_code} {title}"

        # ระบุว่าเป็นการจองของผู้ใช้คนนี้ไหม (ใช้ไฮไลต์ฝั่ง JS)
        is_mine = b.booker_id == request.user.id

        bookings_data.append(
            {
                "id": b.id,
                "room_code": b.room.room_code,
                "start_date": b.start_date.strftime("%Y-%m-%d"),
                "end_date": b.end_date.strftime("%Y-%m-%d"),
                "start_time": b.start_time.strftime("%H:%M"),
                "end_time": b.end_time.strftime("%H:%M"),
                "days_of_week": days_list,
                "status": b.status,
                "title": title,
                "booker": b.booker.get_full_name() or b.booker.username,
                "is_mine": is_mine,
            }
        )

    # ดึง blackouts ที่ active
    blackouts_data = []
    for blk in BlackoutPeriod.objects.filter(is_active=True).prefetch_related("rooms"):
        affected_rooms = [r.room_code for r in blk.rooms.all()]
        blackouts_data.append(
            {
                "id": blk.id,
                "title": blk.title,
                "start_date": blk.start_date.strftime("%Y-%m-%d"),
                "end_date": blk.end_date.strftime("%Y-%m-%d"),
                "rooms": affected_rooms,  # [] = ทุกห้อง
            }
        )

    context = {
        "title": "ปฏิทินตรวจสอบห้องว่าง",
        "rooms": rooms,
        "bookings_json": json.dumps(bookings_data),
        "blackouts_json": json.dumps(blackouts_data),
    }
    return render(request, "Booking/booking_calendar.html", context)



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
