
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wesolar_web.settings')
django.setup()

from django.contrib.auth.models import User
from solar_management.models import UserProfile

mobile = '2222222222'
password = 'password123'
role = 'Installer'

print(f"Creating user {mobile} with role {role}...")

try:
    user, created = User.objects.get_or_create(username=mobile)
    user.set_password(password)
    user.save()
    
    profile, created = UserProfile.objects.get_or_create(user=user, defaults={'mobile_number': mobile, 'role': role})
    profile.mobile_number = mobile
    profile.role = role
    profile.is_approved = True  # Auto-approve for testing
    profile.save()
    
    print(f"User {mobile} created/updated successfully.")
    print(f"Password set to: {password}")
    
except Exception as e:
    print(f"Error: {e}")
