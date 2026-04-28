#!/usr/bin/env python
"""
Check existing user data in database
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Tse_Booking.settings')
django.setup()

from Users.models import UserProfile
from django.contrib.auth.models import User

print("="*60)
print("Existing Users in Database")
print("="*60)

users = User.objects.all()
for user in users:
    print(f"\nDjango User: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  First Name: {user.first_name}")
    print(f"  Last Name: {user.last_name}")
    
    try:
        profile = UserProfile.objects.get(user=user)
        print(f"  UserProfile:")
        print(f"    TU Username: {profile.tu_username}")
        print(f"    Full Name: {profile.full_name}")
        print(f"    Email: {profile.email}")
        print(f"    Role: {profile.role}")
    except UserProfile.DoesNotExist:
        print(f"  No UserProfile associated")

print("\n" + "="*60)
print(f"Total users: {users.count()}")
print("="*60)
