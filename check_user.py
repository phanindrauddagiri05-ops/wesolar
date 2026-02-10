
from django.contrib.auth.models import User
from solar_management.models import UserProfile

mobile = '2222222222'
print(f"Checking user with mobile: {mobile}")

try:
    user = User.objects.get(username=mobile)
    print(f"User found: {user.username}")
    print(f"Is active: {user.is_active}")
    
    try:
        profile = user.userprofile
        print(f"Profile found.")
        print(f"Role: {profile.role}")
        print(f"Is approved: {profile.is_approved}")
        print(f"Mobile in profile: {profile.mobile_number}")
    except UserProfile.DoesNotExist:
        print("UserProfile NOT found for this user.")
        
except User.DoesNotExist:
    print("User NOT found.")
