from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
import csv
import io
import logging

from .forms import TULoginForm, UserRoleAssignmentForm
from .models import UserProfile, SystemSettings

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    User login view using TU REST API authentication
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = TULoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # ยืนยันตัวตนผ่านระบบ TU REST API
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                logger.info(f"User {username} logged in successfully")
                messages.success(request, _("เข้าสู่ระบบสำเร็จ"))
                return redirect("dashboard")
            else:
                logger.warning(f"Login failed for user: {username}")
                messages.error(
                    request,
                    _(
                        "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง หรือเซิร์ฟเวอร์ API ไม่พร้อมใช้งาน"
                    ),
                )
    else:
        form = TULoginForm()

    context = {
        "form": form,
        "title": _("เข้าสู่ระบบ"),
    }
    return render(request, "Users/login.html", context)


@require_http_methods(["POST"])
def logout_view(request):
    username = request.user.username if request.user.is_authenticated else "Unknown"
    logout(request)
    logger.info(f"User {username} logged out")
    messages.success(request, _("ออกจากระบบสำเร็จ"))
    return redirect("login")


@login_required(login_url="login")
@require_http_methods(["GET"])
def dashboard_view(request):
    """
    Main dashboard view after successful login
    """
    if not request.user.is_authenticated:
        return redirect("login")

    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        logout(request)
        return redirect("login")

    # ส่งข้อความแจ้งเตือนหลัง login (เฉพาะครั้งแรก)
    if not request.session.get("welcome_shown"):
        messages.success(request, _("ยินดีต้อนรับ! คุณเข้าสู่ระบบสำเร็จแล้ว"))
        request.session["welcome_shown"] = True

    # แยกหน้าจอตาม Role
    if user_profile.role == "lecturer":
        from Booking.models import Booking  # ป้องกันการหมุนวน Import

        # ดึงประวัติการจองไปแสดงที่หน้า Dashboard อาจารย์
        my_bookings = Booking.objects.filter(booker=request.user).order_by(
            "-created_at"
        )

        context = {
            "title": _("แดชบอร์ด - อาจารย์"),
            "user_role": _("อาจารย์"),
            "my_bookings": my_bookings,
        }
        return render(request, "Users/dashboard_lecturer.html", context)

    elif user_profile.role == "admin":
        context = {
            "title": _("แดชบอร์ด - เจ้าหน้าที่"),
            "user_role": _("เจ้าหน้าที่"),
        }
        return render(request, "Users/dashboard_admin.html", context)
    else:
        messages.error(request, _("บทบาทของผู้ใช้งานไม่ชัดเจน"))
        return redirect("logout")


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def assign_user_role_view(request, user_id):
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _("คุณไม่มีสิทธิ์ในการทำงานนี้"))
            return redirect("dashboard")
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        return redirect("login")

    try:
        target_user = User.objects.get(id=user_id)
        user_profile = target_user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, _("ไม่พบผู้ใช้งานที่ระบุ"))
        return redirect("dashboard")

    if request.method == "POST":
        form = UserRoleAssignmentForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            form.save()
            logger.info(
                f"Admin {request.user.username} assigned role {user_profile.role} to user {target_user.username}"
            )
            messages.success(request, _(f"กำหนดบทบาทให้ {target_user.username} สำเร็จ"))
            return redirect("users_management")
    else:
        form = UserRoleAssignmentForm(user_profile=user_profile)

    context = {
        "form": form,
        "target_user": target_user,
        "user_profile": user_profile,
        "title": _("กำหนดบทบาทผู้ใช้งาน"),
    }
    return render(request, "Users/assign_role.html", context)


@login_required(login_url="login")
@require_http_methods(["GET"])
def users_management_view(request):
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _("คุณไม่มีสิทธิ์ในการทำงานนี้"))
            return redirect("dashboard")
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        return redirect("login")

    users = UserProfile.objects.all().order_by("-created_at")
    context = {
        "users": users,
        "title": _("จัดการผู้ใช้งาน"),
    }
    return render(request, "Users/users_management.html", context)


# ==========================================
# ระบบ Report และ Admin Dashboard
# ==========================================


def _count_sessions_in_range(booking, report_from, report_to):
    """
    นับจำนวนครั้งที่ booking เกิดขึ้นในช่วง [report_from, report_to]
    โดยพิจารณา days_of_week ของ booking (recurring pattern)
    """
    overlap_start = max(booking.start_date, report_from)
    overlap_end = min(booking.end_date, report_to)
    if overlap_start > overlap_end:
        return 0

    try:
        days_set = {
            int(d.strip())
            for d in booking.days_of_week.split(",")
            if d.strip().isdigit()
        }
    except (AttributeError, ValueError):
        days_set = set()

    if not days_set:
        return 0

    count = 0
    cur = overlap_start
    while cur <= overlap_end:
        # Python weekday(): 0=Monday ... 6=Sunday — ตรงกับ convention ของระบบ (0=จันทร์)
        if cur.weekday() in days_set:
            count += 1
        cur += timedelta(days=1)
    return count


def _hours_per_session(booking):
    """คำนวณชั่วโมงต่อ session (ปัดทศนิยม 2 ตำแหน่ง)"""
    start_dt = datetime.combine(date.today(), booking.start_time)
    end_dt = datetime.combine(date.today(), booking.end_time)
    delta = end_dt - start_dt
    return round(delta.total_seconds() / 3600, 2)


@login_required(login_url="login")
@require_http_methods(["GET"])
def room_report_view(request):
    """
    รายงานสถิติการใช้ห้อง (FR-RPT-01, FR-RPT-02, FR-RPT-04)
    GET params:
      date_from (YYYY-MM-DD)
      date_to   (YYYY-MM-DD)
    """
    # ตรวจสอบสิทธิ์
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _("คุณไม่มีสิทธิ์ในการทำงานนี้"))
            return redirect("dashboard")
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        return redirect("login")

    from Booking.models import Booking, Room  # ป้องกัน circular import

    # อ่านช่วงวันที่ — ถ้าไม่ส่งมา ใช้ค่า default = 30 วันที่ผ่านมา
    today = date.today()
    date_from_str = request.GET.get("date_from", "")
    date_to_str = request.GET.get("date_to", "")

    try:
        date_from = (
            datetime.strptime(date_from_str, "%Y-%m-%d").date()
            if date_from_str
            else today - timedelta(days=30)
        )
    except ValueError:
        date_from = today - timedelta(days=30)

    try:
        date_to = (
            datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else today
        )
    except ValueError:
        date_to = today

    if date_from > date_to:
        date_from, date_to = date_to, date_from

    # ดึง bookings ทั้งหมดที่ overlap กับช่วงรายงาน (เฉพาะ approved)
    bookings = Booking.objects.filter(
        status="approved",
        start_date__lte=date_to,
        end_date__gte=date_from,
    ).select_related("room")

    # ชั่วโมงทำงานต่อวันสำหรับคำนวณ Utilization Rate
    AVAILABLE_HOURS_PER_DAY = 9

    # นับจำนวนวันทั้งหมดในช่วง report range (รวมเสาร์-อาทิตย์ ไม่ตัดออก)
    total_days = (date_to - date_from).days + 1
    available_hours_total = total_days * AVAILABLE_HOURS_PER_DAY

    # คำนวณสถิติต่อห้อง
    rows = []
    grand_total_count = 0
    grand_total_hours = 0.0

    for room in Room.objects.all().order_by("room_code"):
        room_bookings = [b for b in bookings if b.room_id == room.id]

        room_count = 0
        room_hours = 0.0
        class_count = class_hours = 0
        training_count = training_hours = 0
        curriculum_stats = {
            "regular": {"count": 0, "hours": 0.0},
            "master": {"count": 0, "hours": 0.0},
            "tep_tepe": {"count": 0, "hours": 0.0},
            "tu_pine": {"count": 0, "hours": 0.0},
        }

        for b in room_bookings:
            sessions = _count_sessions_in_range(b, date_from, date_to)
            if sessions == 0:
                continue
            hrs_per = _hours_per_session(b)
            total_hrs = sessions * hrs_per

            room_count += sessions
            room_hours += total_hrs

            if b.purpose_type == "training":
                training_count += sessions
                training_hours += total_hrs
            else:
                class_count += sessions
                class_hours += total_hrs

            if b.curriculum and b.curriculum in curriculum_stats:
                curriculum_stats[b.curriculum]["count"] += sessions
                curriculum_stats[b.curriculum]["hours"] += total_hrs

        # Utilization Rate (%)
        if available_hours_total > 0:
            utilization = round((room_hours / available_hours_total) * 100, 1)
        else:
            utilization = 0.0

        # รวม international (TEP-TEPE + TU-PINE) เป็นกลุ่ม "หลักสูตรนานาชาติ" ตาม template
        regular_count = (
            curriculum_stats["regular"]["count"] + curriculum_stats["master"]["count"]
        )
        regular_hours = (
            curriculum_stats["regular"]["hours"] + curriculum_stats["master"]["hours"]
        )
        intl_count = (
            curriculum_stats["tep_tepe"]["count"] + curriculum_stats["tu_pine"]["count"]
        )
        intl_hours = (
            curriculum_stats["tep_tepe"]["hours"] + curriculum_stats["tu_pine"]["hours"]
        )

        rows.append(
            {
                "room": room,
                "count": room_count,
                "hours": round(room_hours, 1),
                "utilization": utilization,
                "class_count": class_count,
                "class_hours": round(class_hours, 1),
                "training_count": training_count,
                "training_hours": round(training_hours, 1),
                "regular_count": regular_count,
                "regular_hours": round(regular_hours, 1),
                "intl_count": intl_count,
                "intl_hours": round(intl_hours, 1),
            }
        )

        grand_total_count += room_count
        grand_total_hours += room_hours

    # ----- Export CSV (FR-RPT-03) -----
    if request.GET.get("export") == "csv":
        buffer = io.StringIO()
        # UTF-8 BOM ให้ Excel แสดงภาษาไทยถูกต้อง
        buffer.write("﻿")
        writer = csv.writer(buffer)
        writer.writerow(
            [
                f"รายงานสถิติการใช้ห้อง: {date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}"
            ]
        )
        writer.writerow([])
        writer.writerow(
            [
                "รหัสห้อง",
                "ชื่อห้อง",
                "ประเภท",
                "สถานะ",
                "จำนวนครั้ง",
                "ชั่วโมงรวม",
                "Utilization (%)",
                "เรียนการสอน-ครั้ง",
                "เรียนการสอน-ชม.",
                "อบรม/ประชุม-ครั้ง",
                "อบรม/ประชุม-ชม.",
                "ภาคปกติ/โท-ครั้ง",
                "ภาคปกติ/โท-ชม.",
                "นานาชาติ-ครั้ง",
                "นานาชาติ-ชม.",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r["room"].room_code,
                    r["room"].room_name,
                    r["room"].get_room_type_display(),
                    "เปิดใช้งาน" if r["room"].is_active else "ปิดใช้งาน",
                    r["count"],
                    r["hours"],
                    r["utilization"],
                    r["class_count"],
                    r["class_hours"],
                    r["training_count"],
                    r["training_hours"],
                    r["regular_count"],
                    r["regular_hours"],
                    r["intl_count"],
                    r["intl_hours"],
                ]
            )
        writer.writerow([])
        writer.writerow(
            ["รวมทั้งหมด", "", "", "", grand_total_count, round(grand_total_hours, 1)]
        )

        filename = f"room_report_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.csv"
        response = HttpResponse(
            buffer.getvalue(), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    context = {
        "title": _("รายงานสถิติการใช้ห้อง"),
        "rows": rows,
        "date_from": date_from,
        "date_to": date_to,
        "date_from_str": date_from.strftime("%Y-%m-%d"),
        "date_to_str": date_to.strftime("%Y-%m-%d"),
        "grand_total_count": grand_total_count,
        "grand_total_hours": round(grand_total_hours, 1),
        "available_hours_total": available_hours_total,
    }
    return render(request, "Users/room_report.html", context)


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def room_management_view(request):
    """
    จัดการห้องและช่วงเวลาปิดใช้งาน (FR-ADM-01, FR-ADM-03)
    POST actions: add_room, edit_room, toggle_room, add_blackout, delete_blackout
    """
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _("คุณไม่มีสิทธิ์ในการทำงานนี้"))
            return redirect("dashboard")
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        return redirect("login")

    from Booking.models import Room, BlackoutPeriod

    if request.method == "POST":
        action = request.POST.get("action_type", "")

        # ----- เพิ่มห้องใหม่ -----
        if action == "add_room":
            room_code = request.POST.get("room_code", "").strip()
            room_name = request.POST.get("room_name", "").strip()
            room_type = request.POST.get("room_type", "classroom").strip()
            capacity_raw = request.POST.get("capacity", "0").strip()
            is_active = request.POST.get("is_active", "true") == "true"

            room_image = request.FILES.get("image")

            if not room_code or not room_name:
                messages.error(request, _("กรุณาระบุรหัสห้องและชื่อห้องให้ครบ"))
                return redirect("room_management")

            try:
                capacity = int(capacity_raw)
                if capacity < 1:
                    raise ValueError
            except ValueError:
                messages.error(request, _("ความจุต้องเป็นจำนวนเต็มบวก"))
                return redirect("room_management")

            if room_type not in ("meeting", "classroom"):
                room_type = "classroom"

            if Room.objects.filter(room_code=room_code).exists():
                messages.error(request, _(f"รหัสห้อง {room_code} มีอยู่แล้วในระบบ"))
                return redirect("room_management")

            Room.objects.create(
                room_code=room_code,
                room_name=room_name,
                room_type=room_type,
                capacity=capacity,
                is_active=is_active,
                image=room_image,
            )
            logger.info(f"Admin {request.user.username} added room {room_code}")
            messages.success(request, _(f"เพิ่มห้อง {room_code} เรียบร้อยแล้ว"))
            return redirect("room_management")

        # ----- แก้ไขห้อง -----
        elif action == "edit_room":
            room_id = request.POST.get("room_id")
            try:
                room = Room.objects.get(id=room_id)
            except (Room.DoesNotExist, ValueError, TypeError):
                messages.error(request, _("ไม่พบห้องที่ระบุ"))
                return redirect("room_management")

            room.room_name = request.POST.get("room_name", room.room_name).strip()
            room_type = request.POST.get("room_type", room.room_type).strip()
            if room_type in ("meeting", "classroom"):
                room.room_type = room_type
            try:
                room.capacity = int(request.POST.get("capacity", room.capacity))
            except ValueError:
                pass
            room.is_active = request.POST.get("is_active", "true") == "true"

            uploaded_image = request.FILES.get("image")
            if uploaded_image:
                room.image = uploaded_image

            room.save()
            logger.info(f"Admin {request.user.username} edited room {room.room_code}")
            messages.success(
                request, _(f"อัปเดตข้อมูลห้อง {room.room_code} เรียบร้อยแล้ว")
            )
            return redirect("room_management")

        # ----- เปิด/ปิดใช้งานห้อง -----
        elif action == "toggle_room":
            room_id = request.POST.get("room_id")
            try:
                room = Room.objects.get(id=room_id)
            except (Room.DoesNotExist, ValueError, TypeError):
                messages.error(request, _("ไม่พบห้องที่ระบุ"))
                return redirect("room_management")

            room.is_active = not room.is_active
            room.save()
            log_status = "Active" if room.is_active else "Inactive"
            logger.info(
                f"Admin {request.user.username} toggled room {room.room_code} to {log_status}"
            )
            status_text = "เปิดใช้งาน" if room.is_active else "ปิดใช้งาน"
            messages.success(
                request, _(f"เปลี่ยนสถานะห้อง {room.room_code} เป็น {status_text}")
            )
            return redirect("room_management")

        # ----- เพิ่ม Blackout Period -----
        elif action == "add_blackout":
            title = request.POST.get("reason", "").strip()
            start_date_str = request.POST.get("start_date", "")
            end_date_str = request.POST.get("end_date", "")
            target_room = request.POST.get("target_room", "all").strip()

            if not title:
                messages.error(request, _("กรุณาระบุสาเหตุ/หมายเหตุของการล็อกห้อง"))
                return redirect("room_management")

            try:
                blk_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                blk_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, _("รูปแบบวันที่ไม่ถูกต้อง"))
                return redirect("room_management")

            if blk_start > blk_end:
                messages.error(request, _("วันเริ่มต้นต้องไม่หลังวันสิ้นสุด"))
                return redirect("room_management")

            blackout = BlackoutPeriod.objects.create(
                title=title,
                start_date=blk_start,
                end_date=blk_end,
                is_active=True,
                created_by=request.user,
            )
            if target_room and target_room != "all":
                room = Room.objects.filter(room_code=target_room).first()
                if room:
                    blackout.rooms.add(room)
            logger.info(f"Admin {request.user.username} added blackout '{title}'")
            messages.success(request, _(f"บันทึกช่วงปิดใช้งาน '{title}' เรียบร้อยแล้ว"))
            return redirect("room_management")

        # ----- ลบ Blackout (ตั้งเป็น inactive) -----
        elif action == "delete_blackout":
            blackout_id = request.POST.get("blackout_id")
            try:
                blackout = BlackoutPeriod.objects.get(id=blackout_id)
            except (BlackoutPeriod.DoesNotExist, ValueError, TypeError):
                messages.error(request, _("ไม่พบช่วงปิดใช้งานที่ระบุ"))
                return redirect("room_management")

            blackout.delete()
            logger.info(
                f"Admin {request.user.username} deleted blackout #{blackout_id}"
            )
            messages.success(request, _("ปลดล็อกช่วงเวลาเรียบร้อยแล้ว"))
            return redirect("room_management")

        else:
            messages.error(request, _("คำสั่งไม่ถูกต้อง"))
            return redirect("room_management")

    # ----- GET: แสดงรายการห้องและ Blackout ทั้งหมด -----
    rooms = Room.objects.all().order_by("room_code")
    blackouts = (
        BlackoutPeriod.objects.filter(is_active=True)
        .prefetch_related("rooms")
        .order_by("-start_date")
    )

    context = {
        "title": _("จัดการห้อง"),
        "rooms": rooms,
        "blackouts": blackouts,
    }
    return render(request, "Users/room_management.html", context)


@login_required(login_url="login")
@require_http_methods(["GET"])
def admin_calendar_view(request):
    """
    ปฏิทินภาพรวมการใช้ห้องสำหรับ Admin (FR-CAL admin view)
    ส่ง bookings + blackouts เป็น JSON ให้ JS ฝั่ง client ใช้ render
    """
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _("คุณไม่มีสิทธิ์ในการทำงานนี้"))
            return redirect("dashboard")
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        return redirect("login")

    import json
    from Booking.models import Booking, Room, BlackoutPeriod

    rooms = Room.objects.filter(is_active=True).order_by("room_code")

    # ดึง bookings ที่ active (pending + approved) ล่วงหน้า ±6 เดือน
    today = date.today()
    horizon_start = today - timedelta(days=180)
    horizon_end = today + timedelta(days=180)

    booking_qs = Booking.objects.filter(
        status__in=["pending", "approved"],
        start_date__lte=horizon_end,
        end_date__gte=horizon_start,
    ).select_related("room", "booker")

    bookings_data = []
    for b in booking_qs:
        try:
            days_list = [
                int(d.strip()) for d in b.days_of_week.split(",") if d.strip().isdigit()
            ]
        except AttributeError:
            days_list = []
        title = b.subject_name or b.topic or "(ไม่ระบุ)"
        if b.subject_code:
            title = f"{b.subject_code} {title}"
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
                "rooms": affected_rooms,  # ถ้า [] = ทุกห้อง
            }
        )

    context = {
        "title": _("ปฏิทินตรวจสอบการใช้งานห้อง"),
        "rooms": rooms,
        "bookings_json": json.dumps(bookings_data),
        "blackouts_json": json.dumps(blackouts_data),
    }
    return render(request, "Users/admin_calendar.html", context)


@login_required(login_url="login")
def system_settings_view(request):
    if not request.user.profile.is_admin():
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect("dashboard")

    # ดึงค่า Settings จากฐานข้อมูล
    settings = SystemSettings.get_settings()

    if request.method == "POST":
        # ดักจับว่าบันทึกจากฟอร์มไหน (เพราะมี 3 ฟอร์ม)
        if "semester_name" in request.POST:
            settings.semester_name = request.POST.get("semester_name")
            start = request.POST.get("start_date")
            end = request.POST.get("end_date")
            if start:
                settings.start_date = datetime.strptime(start, "%Y-%m-%d").date()
            if end:
                settings.end_date = datetime.strptime(end, "%Y-%m-%d").date()
            settings.allow_break_booking = (
                request.POST.get("allow_break_booking") == "on"
            )
            messages.success(request, "บันทึกข้อมูลภาคการศึกษาสำเร็จ")

        elif "max_advance_days" in request.POST:
            settings.max_advance_days = int(request.POST.get("max_advance_days", 30))
            settings.max_hours = int(request.POST.get("max_hours", 4))
            # settings.auto_approve_lecturer = (
            #     request.POST.get("auto_approve_lecturer") == "on"
            # )
            settings.allow_weekend = request.POST.get("allow_weekend") == "on"
            messages.success(request, "บันทึกเงื่อนไขการจองสำเร็จ")

        elif "admin_email" in request.POST:
            settings.admin_email = request.POST.get("admin_email")
            settings.enable_email_notification = (
                request.POST.get("enable_email_notification") == "on"
            )
            messages.success(request, "บันทึกการตั้งค่าแจ้งเตือนสำเร็จ")

        settings.save()
        return redirect("system_settings")

    return render(
        request,
        "Users/system_settings.html",
        {"settings": settings, "title": "การตั้งค่าระบบ"},
    )
