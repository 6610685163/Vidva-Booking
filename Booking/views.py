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