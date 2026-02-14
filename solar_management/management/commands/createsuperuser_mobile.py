"""
Custom management command to create a superuser with mobile number, email, and password.
Usage: python manage.py createsuperuser_mobile
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from solar_management.models import UserProfile
from django.db import transaction


class Command(BaseCommand):
    help = 'Create a superuser with mobile number, email, and password'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Create Superuser with Mobile Number ===\n'))
        
        # Get mobile number
        while True:
            mobile_number = input('Mobile number: ').strip()
            if not mobile_number:
                self.stdout.write(self.style.ERROR('Mobile number cannot be empty'))
                continue
            if UserProfile.objects.filter(mobile_number=mobile_number).exists():
                self.stdout.write(self.style.ERROR(f'Mobile number {mobile_number} already exists'))
                continue
            if len(mobile_number) < 10:
                self.stdout.write(self.style.ERROR('Mobile number must be at least 10 digits'))
                continue
            break
        
        # Get email
        while True:
            email = input('Email address: ').strip()
            if not email:
                self.stdout.write(self.style.ERROR('Email cannot be empty'))
                continue
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.ERROR(f'Email {email} already exists'))
                continue
            if '@' not in email:
                self.stdout.write(self.style.ERROR('Invalid email address'))
                continue
            break
        
        # Get password
        while True:
            password = input('Password: ')
            if not password:
                self.stdout.write(self.style.ERROR('Password cannot be empty'))
                continue
            if len(password) < 6:
                self.stdout.write(self.style.ERROR('Password must be at least 6 characters'))
                continue
            password_confirm = input('Password (again): ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match'))
                continue
            break
        
        # Get full name (optional)
        full_name = input('Full name (optional): ').strip()
        
        # Create superuser
        try:
            with transaction.atomic():
                # Use mobile number as username
                username = mobile_number
                
                # Create User
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                
                # Set full name if provided
                if full_name:
                    name_parts = full_name.split(' ', 1)
                    user.first_name = name_parts[0]
                    if len(name_parts) > 1:
                        user.last_name = name_parts[1]
                    user.save()
                
                # Create UserProfile
                UserProfile.objects.create(
                    user=user,
                    mobile_number=mobile_number,
                    role='Admin',
                    is_approved=True
                )
                
                self.stdout.write(self.style.SUCCESS(f'\n✅ Superuser created successfully!'))
                self.stdout.write(self.style.SUCCESS(f'   Username: {username}'))
                self.stdout.write(self.style.SUCCESS(f'   Mobile: {mobile_number}'))
                self.stdout.write(self.style.SUCCESS(f'   Email: {email}'))
                self.stdout.write(self.style.SUCCESS(f'   Role: Admin'))
                self.stdout.write(self.style.SUCCESS(f'   Superuser: Yes'))
                self.stdout.write(self.style.SUCCESS(f'   Staff: Yes'))
                self.stdout.write(self.style.SUCCESS(f'\nYou can now login with mobile number: {mobile_number}\n'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error creating superuser: {str(e)}\n'))
            raise
