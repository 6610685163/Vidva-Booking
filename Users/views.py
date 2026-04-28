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
from django.db.models import Q
from .forms import BookingForm
from .models import Booking
from django.shortcuts import get_object_or_404
from .models import Booking

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
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TULoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Authenticate using TU REST API backend
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Create session (Requirement: FR-AUTH-03)
                login(request, user)
                logger.info(f"User {username} logged in successfully")
                messages.success(request, _('เข้าสู่ระบบสำเร็จ'))
                return redirect('dashboard')
            else:
                logger.warning(f"Login failed for user: {username}")
                messages.error(
                    request,
                    _('ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง หรือเซิร์ฟเวอร์ API ไม่พร้อมใช้งาน')
                )
    else:
        form = TULoginForm()
    
    context = {
        'form': form,
        'title': _('เข้าสู่ระบบ'),
    }
    return render(request, 'Users/login.html', context)


@require_http_methods(["POST"])
def logout_view(request):
    """
    User logout view - destroy session
    """
    username = request.user.username if request.user.is_authenticated else 'Unknown'
    logout(request)  # Destroy session
    logger.info(f"User {username} logged out")
    messages.success(request, _('ออกจากระบบสำเร็จ'))
    return redirect('login')


@login_required(login_url='login')
@require_http_methods(["GET"])
def dashboard_view(request):
    """
    Main dashboard view after successful login
    Shows different content based on user role
    """
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        messages.error(request, _('ไม่พบข้อมูลผู้ใช้งาน'))
        logout(request)
        return redirect('login')
    
    # Check if role has been assigned
    if user_profile.role == 'lecturer':
        context = {
            'title': _('แดชบอร์ด - อาจารย์'),
            'user_role': _('อาจารย์'),
        }
        return render(request, 'Users/dashboard_lecturer.html', context)
    elif user_profile.role == 'admin':
        context = {
            'title': _('แดชบอร์ด - เจ้าหน้าที่'),
            'user_role': _('เจ้าหน้าที่'),
        }
        return render(request, 'Users/dashboard_admin.html', context)
    else:
        messages.error(request, _('บทบาทของผู้ใช้งานไม่ชัดเจน'))
        return redirect('logout')


@login_required(login_url='login')
@require_http_methods(["GET", "POST"])
def assign_user_role_view(request, user_id):
    """
    Admin view to assign roles to users on first login
    Only accessible by admins
    """
    # Check if current user is admin
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _('คุณไม่มีสิทธิ์ในการทำงานนี้'))
            return redirect('dashboard')
    except UserProfile.DoesNotExist:
        messages.error(request, _('ไม่พบข้อมูลผู้ใช้งาน'))
        return redirect('login')
    
    # Get user to assign role
    try:
        target_user = User.objects.get(id=user_id)
        user_profile = target_user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, _('ไม่พบผู้ใช้งานที่ระบุ'))
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRoleAssignmentForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            form.save()
            logger.info(
                f"Admin {request.user.username} assigned role "
                f"{user_profile.role} to user {target_user.username}"
            )
            messages.success(
                request,
                _(f'กำหนดบทบาทให้ {target_user.username} สำเร็จ')
            )
            return redirect('dashboard')
    else:
        form = UserRoleAssignmentForm(user_profile=user_profile)
    
    context = {
        'form': form,
        'target_user': target_user,
        'user_profile': user_profile,
        'title': _('กำหนดบทบาทผู้ใช้งาน'),
    }
    return render(request, 'Users/assign_role.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def users_management_view(request):
    """
    Admin view to manage users and their roles
    """
    try:
        if not request.user.profile.is_admin():
            messages.error(request, _('คุณไม่มีสิทธิ์ในการทำงานนี้'))
            return redirect('dashboard')
    except UserProfile.DoesNotExist:
        messages.error(request, _('ไม่พบข้อมูลผู้ใช้งาน'))
        return redirect('login')

    # Get all user profiles
    users = UserProfile.objects.all().order_by('-created_at')

    context = {
        'users': users,
        'title': _('จัดการผู้ใช้งาน'),
    }
    return render(request, 'Users/users_management.html', context)


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
                messages.error(request, _("ห้องถูกจองในช่วงเวลาดังกล่าวแล้ว กรุณาเลือกเวลาอื่น"))
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
    return render(request, "Users/create_booking.html", context)


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
    return render(request, "Users/pending_bookings.html", context)


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

    messages.success(request, f"อนุมัติการจองห้อง {booking.room.room_code} เรียบร้อยแล้ว")
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
