#!/usr/bin/env python
"""
Test script to check TU REST API response format
"""
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Tse_Booking.settings')
django.setup()

from django.conf import settings

def test_tu_api():
    """Test TU REST API with dummy credentials to see response format"""
    
    api_endpoint = settings.TU_API_ENDPOINT
    api_key = settings.TU_API_KEY
    
    print(f"API Endpoint: {api_endpoint}")
    print(f"API Key: {api_key[:20]}...")
    print()
    
    # Try with test credentials
    test_cases = [
        {"username": "6610685163", "password": "test123"},
        # Add more test cases if needed
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing with username: {test_case['username']}")
        print('='*60)
        
        headers = {
            "Content-Type": "application/json",
            "Application-Key": api_key,
        }
        
        payload = {
            "UserName": test_case['username'],
            "PassWord": test_case['password']
        }
        
        try:
            print(f"\nRequest headers: {headers}")
            print(f"Request payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                api_endpoint,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            print(f"\nResponse Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            response_data = response.json()
            print(f"\nResponse Data:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            
            # Check if data exists
            if "data" in response_data and isinstance(response_data["data"], list) and response_data["data"]:
                user_data = response_data["data"][0]
                print(f"\nFirst user object keys: {list(user_data.keys())}")
                print(f"\nFirst user object:")
                print(json.dumps(user_data, indent=2, ensure_ascii=False))
                
        except requests.exceptions.RequestException as e:
            print(f"\nRequest Error: {str(e)}")
        except json.JSONDecodeError as e:
            print(f"\nJSON Decode Error: {str(e)}")
            print(f"Response Text: {response.text}")
        except Exception as e:
            print(f"\nUnexpected Error: {str(e)}")

if __name__ == "__main__":
    test_tu_api()
