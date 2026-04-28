import requests
import json
import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)


class TURestAPIBackend(ModelBackend):
    """
    Custom authentication backend for TU REST API
    Authenticates against https://restapi.tu.ac.th/api/v1/auth/Ad/verify
    """

    TU_API_ENDPOINT = "https://restapi.tu.ac.th/api/v1/auth/Ad/verify"

    def authenticate(self, request, username=None, password=None):
        """
        Authenticate user against TU REST API

        Args:
            request: HTTP request object
            username: TU username
            password: TU password

        Returns:
            User object if authentication successful, None otherwise
        """
        if not username or not password:
            return None

        # Step 1: Verify credentials with TU REST API
        # ปรับให้รับค่ากลับมาเป็น tuple (สถานะ, ข้อมูลผู้ใช้)
        is_valid, user_data = self._verify_tu_credentials(username, password)

        if not is_valid:
            logger.warning(f"TU REST API authentication failed for user: {username}")
            return None

        # กำหนดค่าเริ่มต้น (Fallback) หาก API ไม่ส่งข้อมูลบางอย่างมา
        api_email = f"{username}@dome.tu.ac.th"
        api_full_name = username

        if user_data:
            # 1. พยายามดึง Email จริงจาก API โดยตรวจสอบ Key หลายรูปแบบ
            email_keys = [
                "Email",
                "email",
                "EMAIL",
                "EmailAddress",
                "tu_email",
                "EmailTU",
            ]
            for key in email_keys:
                if user_data.get(key):
                    api_email = user_data[key]
                    break

            # 2. พยายามดึงชื่อ-นามสกุลจริงภาษาไทย
            first_name = (
                user_data.get("First_Name_Th")
                or user_data.get("FirstNameTh")
                or user_data.get("first_name")
                or ""
            )
            last_name = (
                user_data.get("Last_Name_Th")
                or user_data.get("LastNameTh")
                or user_data.get("last_name")
                or ""
            )

            if first_name or last_name:
                api_full_name = f"{first_name} {last_name}".strip()

        # Step 2: Get or create user in local database
        try:
            user_profile = UserProfile.objects.get(tu_username=username)
            user = user_profile.user

            # อัปเดตข้อมูลให้เป็นปัจจุบันเสมอเมื่อมีการล็อกอินใหม่
            user.email = api_email
            user.is_active = True
            user.save()

            user_profile.full_name = api_full_name
            user_profile.email = api_email
            user_profile.save()

            logger.info(f"User {username} authenticated and updated successfully")
            return user

        except UserProfile.DoesNotExist:
            # กรณีล็อกอินครั้งแรก - สร้าง User และ UserProfile ใหม่
            logger.info(f"Creating new user profile for {username}")
            try:
                # สร้าง Django User
                user = User.objects.create_user(username=username, email=api_email)

                # สร้าง UserProfile (Role เริ่มต้นจะเป็น lecturer)
                UserProfile.objects.create(
                    user=user,
                    tu_username=username,
                    full_name=api_full_name,
                    email=api_email,
                    role="lecturer",
                )

                logger.info(
                    f"New user profile created for {username} with email: {api_email}"
                )
                return user

            except Exception as e:
                logger.error(f"Error creating user profile for {username}: {str(e)}")
                return None

    def _verify_tu_credentials(self, username, password):
        """
        Verify credentials against TU REST API
        Requirement: FR-AUTH-02

        Returns:
            (Boolean, Dictionary/None): (สถานะการยืนยัน, ข้อมูลผู้ใช้จาก API)
        """
        try:
            application_key = settings.TU_API_KEY
            if not application_key:
                logger.error("TU_API_KEY not configured in settings")
                return False, None

            headers = {
                "Content-Type": "application/json",
                "Application-Key": application_key,
            }

            payload = {"UserName": username, "PassWord": password}

            # ส่งคำขอไปยัง TU REST API
            response = requests.post(
                self.TU_API_ENDPOINT, json=payload, headers=headers, timeout=10
            )

            if response.status_code == 200:
                response_data = response.json()

                # ตรวจสอบสถานะความสำเร็จจาก API
                if response_data.get("status") in [
                    1,
                    True,
                    "Success",
                ] or response_data.get("valid"):
                    logger.info(f"TU REST API verification successful for {username}")

                    # ดึงข้อมูลผู้ใช้จาก Array 'data'
                    user_data = None
                    data_list = response_data.get("data", [])
                    if data_list and isinstance(data_list, list):
                        user_data = data_list[0]

                    return True, user_data
                else:
                    logger.warning(
                        f"TU REST API returned invalid status for {username}"
                    )
                    return False, None
            else:
                logger.warning(f"TU REST API returned status {response.status_code}")
                return False, None

        except requests.exceptions.RequestException as e:
            logger.error(f"TU REST API request error: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error during TU authentication: {str(e)}")
            return False, None

    def get_user(self, user_id):
        """
        Get user by ID
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
