from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        # รับค่าจากฟอร์ม UI
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # TODO: ส่วนนี้คือที่ที่คุณจะเขียนโค้ดเชื่อมต่อกับ TU REST API
        # เช่น requests.post('https://api.tu.ac.th/...', data={...})
        
        # สมมติว่าล็อกอินไม่ผ่าน (ตัวอย่างการส่ง Error กลับไปที่ UI)
        messages.error(request, 'Username หรือ Password ไม่ถูกต้อง (TU API Error)')
        return render(request, 'accounts/login.html')
        
    return render(request, 'Users/login.html')