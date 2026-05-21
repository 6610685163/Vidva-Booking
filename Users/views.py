"""
Views for authentication and user management
"""

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from .forms import TULoginForm, UserRoleAssignmentForm
from .models import UserProfile
import logging
from Booking.models import Booking

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """
    User login view using TU REST API authentication
    GET: Display login form
    POST: Authenticate user and create session
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = TULoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            # Authenticate using TU REST API backend
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Create session (Requirement: FR-AUTH-03)
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
    """
    User logout view - destroy session
    """
    username = request.user.username if request.user.is_authenticated else "Unknown"
    logout(request)  # Destroy session
    logger.info(f"User {username} logged out")
    messages.success(request, _("ออกจากระบบสำเร็จ"))
    return redirect("login")


@login_required(login_url="login")
@require_http_methods(["GET"])
def dashboard_view(request):
    """
    Main dashboard view after successful login
    Shows different content based on user role
    """
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        logout(request)
        return redirect("login")

    # Check if role has been assigned
    if user_profile.role == "lecturer":
        from Booking.models import Booking  # ป้องกันการหมุนวน Import

        my_bookings = Booking.objects.filter(booker=request.user).order_by(
            "-created_at"
        )

        context = {
            "title": _("แดชบอร์ด - อาจารย์"),
            "user_role": _("อาจารย์"),
            "my_bookings": my_bookings,  # 🔥 2. ส่งประวัติการจองเข้าไปที่หน้าเว็บอาจารย์
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
    """
    Admin view to assign roles to users on first login
    Only accessible by admins
    """
    # Check if current user is admin
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _("คุณไม่มีสิทธิ์ในการทำงานนี้"))
            return redirect("dashboard")
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        return redirect("login")

    # Get user to assign role
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
                f"Admin {request.user.username} assigned role "
                f"{user_profile.role} to user {target_user.username}"
            )
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
    """
    Admin view to manage users and their roles
    """
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _("คุณไม่มีสิทธิ์ในการทำงานนี้"))
            return redirect("dashboard")
    except UserProfile.DoesNotExist:
        messages.error(request, _("ไม่พบข้อมูลผู้ใช้งาน"))
        return redirect("login")

    # Get all user profiles
    users = UserProfile.objects.all().order_by("-created_at")

    context = {
        "users": users,
        "title": _("จัดการผู้ใช้งาน"),
    }
    return render(request, "Users/users_management.html", context)
