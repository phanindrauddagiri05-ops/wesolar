
from django.contrib.auth.models import User
from solar_management.models import UserProfile
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wesolar_web.settings')
django.setup()

print("Existing Users:")
for u in User.objects.all():
    try:
        profile = u.userprofile
        print(f"User: {u.username}, Role: {profile.role}, Mobile: {profile.mobile_number}, Approved: {profile.is_approved}, Is Staff: {u.is_staff}")
    except:
        print(f"User: {u.username} (No Profile), Is Staff: {u.is_staff}")
