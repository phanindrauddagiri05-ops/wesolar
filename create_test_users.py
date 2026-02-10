
from django.contrib.auth.models import User
from solar_management.models import UserProfile

def create_user(mobile, role, password="password123"):
    user, created = User.objects.get_or_create(username=mobile)
    user.set_password(password)
    user.save()
    
    profile, created = UserProfile.objects.get_or_create(user=user, defaults={'mobile_number': mobile, 'role': role})
    profile.mobile_number = mobile
    profile.role = role
    profile.is_approved = True
    profile.save()
    print(f"User {mobile} ({role}) created/updated.")

create_user('9999999991', 'Field Engineer')
create_user('9999999992', 'Installer')
create_user('9999999993', 'Office')
