from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='login')
def booking_flow_view(request):
    context = {
        'title': 'จองห้อง',
        'user': request.user,
    }
    return render(request, 'Booking/booking_flow.html', context)

@login_required
def my_bookings_view(request):
    # ดึงข้อมูลจาก Database ทีหลังได้
    return render(request, 'Booking/my_bookings.html')

def booking_calendar_view(request):
    return render(request, 'Booking/booking_calendar.html')