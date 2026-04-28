from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Users.models import UserProfile, Room


class Command(BaseCommand):
    help = "ใส่ข้อมูลเริ่มต้นสำหรับระบบจองห้อง (ห้อง 5 ห้อง และ Admin User)"

    def handle(self, *args, **kwargs):

        ROOMS = [
            {
                "room_code": "406-3",
                "room_name": "ห้องประชุม 1",
                "room_type": "meeting",
                "capacity": 60,
                "description": "ห้องประชุมขนาดใหญ่ ชั้น 4 อาคาร 406",
            },
            {
                "room_code": "406-5",
                "room_name": "ห้องประชุม 2",
                "room_type": "meeting",
                "capacity": 15,
                "description": "ห้องประชุมขนาดกลาง ชั้น 4 อาคาร 406",
            },
            {
                "room_code": "408-1",
                "room_name": "ห้องประชุม 3",
                "room_type": "meeting",
                "capacity": 10,
                "description": "ห้องประชุมขนาดเล็ก ชั้น 4 อาคาร 408",
            },
            {
                "room_code": "408-2/1",
                "room_name": "ห้องบรรยาย 1",
                "room_type": "classroom",
                "capacity": 20,
                "description": "ห้องเรียนบรรยาย ชั้น 4 อาคาร 408",
            },
            {
                "room_code": "408-2/2",
                "room_name": "ห้องบรรยาย 2",
                "room_type": "classroom",
                "capacity": 20,
                "description": "ห้องเรียนบรรยาย ชั้น 4 อาคาร 408",
            },
        ]

        created_rooms = 0
        for r in ROOMS:
            obj, created = Room.objects.get_or_create(
                room_code=r["room_code"],
                defaults={
                    "room_name": r["room_name"],
                    "room_type": r["room_type"],
                    "capacity": r["capacity"],
                    "description": r["description"],
                    "is_active": True,
                },
            )
            if created:
                created_rooms += 1
                self.stdout.write(self.style.SUCCESS(f"  [+] สร้างห้อง: {obj}"))
            else:
                self.stdout.write(f"  [=] มีอยู่แล้ว: {obj}")

        self.stdout.write(f"\nห้อง: สร้างใหม่ {created_rooms} ห้อง\n")

        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "admin1234"  # ⚠ เปลี่ยนทันทีหลัง deploy
        ADMIN_EMAIL = "admin@example.com"  # ⚠ ใส่อีเมลจริง
        ADMIN_FULL_NAME = "ผู้ดูแลระบบ"

        user, user_created = User.objects.get_or_create(
            username=ADMIN_USERNAME,
            defaults={
                "email": ADMIN_EMAIL,
                "first_name": ADMIN_FULL_NAME,
                "is_staff": True,
                "is_superuser": True,  # แนะนำให้เพิ่มสิทธิ์นี้เพื่อให้เข้าหน้า /admin ของ Django ได้
            },
        )

        if user_created:
            user.set_password(ADMIN_PASSWORD)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"[+] สร้าง Django User: {ADMIN_USERNAME}")
            )
        else:
            self.stdout.write(f"[=] มี Django User อยู่แล้ว: {ADMIN_USERNAME}")

        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "tu_username": ADMIN_USERNAME,
                "role": "admin",
                "full_name": ADMIN_FULL_NAME,
                "email": ADMIN_EMAIL,
                "is_active": True,
            },
        )

        if profile_created:
            self.stdout.write(
                self.style.SUCCESS(f"[+] สร้าง UserProfile (admin): {profile}")
            )
        else:
            self.stdout.write(f"[=] มี UserProfile อยู่แล้ว: {profile}")

        self.stdout.write(self.style.SUCCESS("\n✅ Seed data เสร็จสมบูรณ์"))
        self.stdout.write(
            self.style.WARNING(
                "⚠️  อย่าลืมเปลี่ยนรหัสผ่าน admin และ ADMIN_EMAIL ก่อน deploy จริง"
            )
        )
