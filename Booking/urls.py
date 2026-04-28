from django.urls import path
from . import views

urlpatterns = [
    path('', views.booking_flow_view, name='booking_flow'),
]