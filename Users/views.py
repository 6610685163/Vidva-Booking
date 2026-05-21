from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
import logging

from .forms import TULoginForm, UserRoleAssignmentForm
from .models import UserProfile

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
                    _("ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง หรือเซิร์ฟเวอร์ API ไม่พร้อมใช้งาน"),
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
    if not request.session.get('welcome_shown'):
        messages.success(request, _("ยินดีต้อนรับ! คุณเข้าสู่ระบบสำเร็จแล้ว"))
        request.session['welcome_shown'] = True

    # แยกหน้าจอตาม Role
    if user_profile.role == "lecturer":
        from Booking.models import Booking  # ป้องกันการหมุนวน Import

        # ดึงประวัติการจองไปแสดงที่หน้า Dashboard อาจารย์
        my_bookings = Booking.objects.filter(booker=request.user).order_by("-created_at")

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
            logger.info(f"Admin {request.user.username} assigned role {user_profile.role} to user {target_user.username}")
            messages.success(request, _(f"กำหนดบทบาทให้ {target_user.username} สำเร็จ"))
            return redirect("dashboard")
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
# ฟีเจอร์ใหม่ของเพื่อน (ระบบ Report และ Admin Dashboard)
# เก็บไว้เพื่อให้ urls.py เรียกใช้ได้ปกติ
# ==========================================
@login_required
def room_report_view(request):
    return render(request, 'Users/room_report.html')

@login_required
def room_management_view(request):
    return render(request, 'Users/room_management.html')

@login_required
def admin_calendar_view(request):
    return render(request, 'Users/admin_calendar.html')