#!/usr/bin/env python
"""
Management command to test TU API response and update user data
Usage: python manage.py test_tu_api_response 6610685163
"""
import os
import sys
import django
import requests
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Tse_Booking.settings')
django.setup()

from Users.models import UserProfile
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Test TU REST API response and show available fields'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='TU Username to test')
        parser.add_argument('password', type=str, help='TU Password')
        parser.add_argument('--update', action='store_true', help='Update user data in database if valid')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        
        self.stdout.write(f"\nTesting TU REST API for username: {username}")
        self.stdout.write("="*70)
        
        # Call TU API
        api_endpoint = settings.TU_API_ENDPOINT
        api_key = settings.TU_API_KEY
        
        if not api_key:
            raise CommandError("TU_API_KEY not configured in settings")
        
        headers = {
            "Content-Type": "application/json",
            "Application-Key": api_key,
        }
        
        payload = {
            "UserName": username,
            "PassWord": password
        }
        
        try:
            self.stdout.write(f"API Endpoint: {api_endpoint}")
            self.stdout.write(f"API Key: {api_key[:20]}...")
            self.stdout.write(f"\nSending request...\n")
            
            response = requests.post(
                api_endpoint,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            self.stdout.write(f"Response Status: {response.status_code}")
            
            response_data = response.json()
            self.stdout.write(f"\nFull API Response:")
            self.stdout.write(json.dumps(response_data, indent=2, ensure_ascii=False))
            
            # Check if authentication was successful
            if response_data.get("status") in [1, True] or response_data.get("valid"):
                self.stdout.write("\n✅ Authentication SUCCESSFUL\n")
                
                # Extract user data
                data_list = response_data.get("data", [])
                if data_list and isinstance(data_list, list):
                    user_data = data_list[0]
                    self.stdout.write("User Data Fields:")
                    self.stdout.write("-"*70)
                    
                    for key, value in user_data.items():
                        self.stdout.write(f"  {key}: {value}")
                    
                    self.stdout.write("\n" + "="*70)
                    
                    # Try to extract email and full name
                    email_found = False
                    name_found = False
                    
                    email_keys = ["Email", "email", "EMAIL", "EmailAddress", "email_address", "EmailTU"]
                    for key in email_keys:
                        if key in user_data and user_data[key]:
                            self.stdout.write(f"\n📧 Email found in key '{key}': {user_data[key]}")
                            email_found = True
                            break
                    
                    if not email_found:
                        self.stdout.write("\n❌ No email field found. Check available fields above.")
                    
                    name_keys_first = ["First_Name_Th", "FirstNameTh", "FirstName", "first_name"]
                    name_keys_last = ["Last_Name_Th", "LastNameTh", "LastName", "last_name"]
                    
                    first_name = None
                    last_name = None
                    
                    for key in name_keys_first:
                        if key in user_data and user_data[key]:
                            first_name = user_data[key]
                            break
                    
                    for key in name_keys_last:
                        if key in user_data and user_data[key]:
                            last_name = user_data[key]
                            break
                    
                    if first_name or last_name:
                        full_name = f"{first_name or ''} {last_name or ''}".strip()
                        self.stdout.write(f"👤 Full Name: {full_name}")
                        name_found = True
                    
                    if not name_found:
                        self.stdout.write("❌ No name fields found. Check available fields above.")
                    
                    # Update user if requested and found
                    if options['update'] and email_found:
                        email = None
                        for key in email_keys:
                            if key in user_data and user_data[key]:
                                email = user_data[key]
                                break
                        
                        full_name = None
                        for key in name_keys_first:
                            if key in user_data and user_data[key]:
                                first_name = user_data[key]
                                break
                        for key in name_keys_last:
                            if key in user_data and user_data[key]:
                                last_name = user_data[key]
                                break
                        
                        if first_name or last_name:
                            full_name = f"{first_name or ''} {last_name or ''}".strip()
                        
                        try:
                            user_profile = UserProfile.objects.get(tu_username=username)
                            django_user = user_profile.user
                            
                            old_email = django_user.email
                            old_name = user_profile.full_name
                            
                            if email:
                                django_user.email = email
                                user_profile.email = email
                            if full_name:
                                user_profile.full_name = full_name
                            
                            django_user.save()
                            user_profile.save()
                            
                            self.stdout.write("\n✅ User updated successfully!")
                            self.stdout.write(f"  Email: {old_email} → {django_user.email}")
                            self.stdout.write(f"  Name: {old_name} → {user_profile.full_name}")
                        except UserProfile.DoesNotExist:
                            self.stdout.write(f"\n❌ User {username} not found in database")
            else:
                self.stdout.write("\n❌ Authentication FAILED")
                
        except requests.exceptions.RequestException as e:
            raise CommandError(f"Request Error: {str(e)}")
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON Decode Error: {str(e)}")
        except Exception as e:
            raise CommandError(f"Unexpected Error: {str(e)}")
