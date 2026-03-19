import csv
import io
import re
import openpyxl
from openpyxl.styles import Font
import sys
import zipfile
import os
from datetime import datetime
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User

from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry, SiteSettings, InstallationPhoto, SurveyMedia, ProfileMedia
from .forms import SurveyForm, InstallationForm, BankDetailsForm, SignUpForm, LoginForm, EnquiryForm, OfficeStatusForm, FEUpdateForm, OfficeBankDetailsForm
import json

from django.core.mail import send_mail
from django.conf import settings

# ==========================================
# 0. AUTHENTICATION & LANDING
# ==========================================

# def landing_page(request):
#     """Landing page with 3 options: Field Engineer, Installer, Office."""
#     if request.user.is_authenticated:
#         return redirect('dashboard')
#     return render(request, 'solar/landing.html')

def custom_login_view(request):
    """Unified login view for Field Engineer, Installer, and Office."""
    if request.user.is_authenticated:
         # Redirect if already logged in based on role
         try:
             # Try to find profile role
            profile = request.user.userprofile
            if profile.role == 'Admin' or request.user.is_superuser:
                return redirect('admin_dashboard')
            elif 'Field Engineer' in profile.role:
                return redirect('dashboard')
            elif 'Installer' in profile.role:
                return redirect('dashboard')
            elif 'Office' in profile.role:
                return redirect('office_dashboard')
            elif 'Loan' in profile.role:
                return redirect('loan_dashboard')
         except:
             pass 
         
         # Fallback for staff/superuser without profile
         if request.user.is_superuser or request.user.is_staff:
             return redirect('admin_dashboard')

         return redirect('dashboard') # Default fallback

    # Pre-select dropdown if role checks fail or coming from specific link
    initial_data = {}
    role_param = request.GET.get('role', '')
    if role_param:
        initial_data['login_type'] = role_param
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_type = form.cleaned_data['login_type']
            mobile = form.cleaned_data['mobile_number']
            password = form.cleaned_data['password']
            
            user = None
            profile = None
            
            # --- 1. Authenticate User ---
            # Try finding user by Profile first (Mobile -> User -> Auth)
            try:
                profile = UserProfile.objects.select_related('user').get(mobile_number=mobile)
                user = authenticate(username=profile.user.username, password=password)
            except UserProfile.DoesNotExist:
                # Fallback: Try direct mobile auth (for Superusers/Office who might use mobile as username)
                user = authenticate(username=mobile, password=password)

            if user:
                 # --- 2. Role Validation ---
                
                # A. ADMIN LOGIN (Formerly Office)
                if login_type == 'admin':
                    # Staff/Superusers OR Users with 'Admin' role
                    if user.is_staff or (profile and profile.role == 'Admin'):
                        login(request, user)
                        return redirect('admin_dashboard')
                    else:
                         messages.error(request, "Access Denied: You do not have Admin permissions.")

                # B. OFFICE LOGIN (New Role)
                elif login_type == 'office':
                    if profile and profile.role == 'Office':
                        if profile.is_approved:
                            login(request, user)
                            return redirect('office_dashboard')
                        else:
                            messages.error(request, "Account pending admin approval.")
                    else:
                        messages.error(request, "This account is not registered as Office Staff.")

                # B. FIELD ENGINEER LOGIN
                elif login_type == 'field_engineer':
                    if profile and 'Field Engineer' in profile.role:
                        if profile.is_approved:
                            login(request, user)
                            return redirect('dashboard')
                        else:
                            messages.error(request, "Account pending admin approval.")
                    else:
                        messages.error(request, "This account is not registered as a Field Engineer.")

                # C. INSTALLER LOGIN
                elif login_type == 'installer':
                    if profile and 'Installer' in profile.role:
                        if profile.is_approved:
                            login(request, user)
                            return redirect('dashboard')
                        else:
                            messages.error(request, "Account pending admin approval.")
                    else:
                        messages.error(request, "This account is not registered as an Installer.")

                # D. LOAN LOGIN
                elif login_type == 'loan':
                    if profile and profile.role == 'Loan':
                        if profile.is_approved:
                            login(request, user)
                            return redirect('loan_dashboard')
                        else:
                            messages.error(request, "Account pending admin approval.")
                    else:
                        messages.error(request, "This account is not registered as a Loan Officer.")
                
                else:
                    messages.error(request, "Invalid login type selected.")

            else:
                messages.error(request, "Invalid mobile number or password.")
    else:
        form = LoginForm(initial=initial_data)
    
    return render(request, 'solar/login.html', {'form': form, 'hide_toast': True})

def admin_login_view(request):
    """Dedicated login view for Office/Admin users only."""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile_number']
            password = form.cleaned_data['password']
            
            # Authentication Logic
            user = None
            profile = None
            
            # 1. Try direct auth (for Superusers who use username/mobile directly)
            user = authenticate(username=mobile, password=password)
            
            # 2. If valid superuser, let them in immediately
            if user and user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')

            # 3. If not, try looking up via UserProfile (for regular Office staff)
            try:
                profile = UserProfile.objects.select_related('user').get(mobile_number=mobile)
                user = authenticate(username=profile.user.username, password=password)
            except UserProfile.DoesNotExist:
                pass
                
            if user:
                # STRICT Admin Check
                if user.is_staff or (profile and profile.role == 'Admin'):
                        login(request, user)
                        return redirect('admin_dashboard')
                else:
                        messages.error(request, "Access Denied: This portal is for Admins only.")
            else:
                messages.error(request, "Invalid credentials.")
    else:
        form = LoginForm()
        
    return render(request, 'solar/admin_login.html', {'form': form, 'hide_toast': True})
    
    return render(request, 'solar/login.html', {'form': form, 'role_name': role_name, 'role_slug': role})

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST, request.FILES)
        if form.is_valid():
            # Create User
            user = User.objects.create_user(
                username=form.cleaned_data['mobile_number'], # Using mobile as username
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            
            # Create Profile
            profile = UserProfile.objects.create(
                user=user,
                mobile_number=form.cleaned_data['mobile_number'],
                role=form.cleaned_data['role'],
                is_approved=False,
                plain_password=form.cleaned_data['password'],
            )

            # Handle multi-uploads for profile
            media_map = {
                'aadhar_photo': 'aadhar',
                'pan_card_photo': 'pan_card',
            }
            for field, m_type in media_map.items():
                files = form.cleaned_data.get(field) or []
                for f in files:
                    ProfileMedia.objects.create(profile=profile, file=f, media_type=m_type)

            # Send Email Notification
            subject = 'Welcome to WeSolar - Account Created'
            message = f"""
            Hi {user.first_name},

            Thank you for registering with WeSolar.
            
            Your account has been created successfully and is currently pending admin approval.
            You will receive another notification once your account is approved.

            Username: {user.username}
            Role: {UserProfile.objects.get(user=user).role}

            Best regards,
            The WeSolar Team
            """
            from_email = settings.EMAIL_HOST_USER if hasattr(settings, 'EMAIL_HOST_USER') else 'noreply@wesolar.com'
            recipient_list = [user.email]
            
            try:
                send_mail(subject, message, from_email, recipient_list)
            except Exception as e:
                # Log error but don't fail the signup
                print(f"Failed to send email: {e}")
            
            messages.success(request, "your account will be conform by the admin")
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'solar/signup.html', {'form': form})


@staff_member_required
def approve_user(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    profile.is_approved = True
    profile.save()
    
    # Add to group
    if profile.role == 'Field Engineer':
        group, _ = Group.objects.get_or_create(name='Field_Engineers')
        profile.user.groups.add(group)
    elif profile.role == 'Installer':
        group, _ = Group.objects.get_or_create(name='Installers')
        profile.user.groups.add(group)
    elif profile.role == 'Office':
        group, _ = Group.objects.get_or_create(name='Office_Staff')
        profile.user.groups.add(group)
    elif profile.role == 'Loan':
        group, _ = Group.objects.get_or_create(name='Loan_Officers')
        profile.user.groups.add(group)
    elif profile.role == 'Admin':
        # Grant is_staff so @staff_member_required on admin_dashboard allows them in
        profile.user.is_staff = True
        profile.user.save()
        
    messages.success(request, f"User {profile.user.get_full_name()} approved.")
    return redirect('pending_approvals')

@staff_member_required
def reject_user(request, pk):
    """Admin-only: Reject and delete user request."""
    profile = get_object_or_404(UserProfile, pk=pk)
    user = profile.user
    name = user.get_full_name() or user.username
    user.delete() # Cascade deletes profile
    messages.error(request, f"User request for {name} has been rejected and removed.")
    return redirect('pending_approvals')

def logout_view(request):
    logout(request)
    return redirect('login')

# ==========================================
# 0. ROLE CHECK HELPERS (Existing)
# ==========================================
def is_field_engineer(user):
    return user.groups.filter(name='Field_Engineers').exists() or user.is_staff

def is_installer(user):
    return user.groups.filter(name='Installers').exists() or user.is_staff

def is_bank_user(user):
    return user.groups.filter(name='Bank_Users').exists() or user.is_staff

def is_office_staff(user):
    return user.groups.filter(name='Office_Staff').exists() or (hasattr(user, 'userprofile') and user.userprofile.role == 'Admin') or user.is_staff

def is_loan_officer(user):
    return user.groups.filter(name='Loan_Officers').exists() or (hasattr(user, 'userprofile') and user.userprofile.role == 'Loan') or (hasattr(user, 'userprofile') and user.userprofile.role == 'Admin') or user.is_staff

# ==========================================
# 0.5 GLOBAL SEARCH
# ==========================================
@login_required
def global_search(request):
    """
    Redirects search queries to the appropriate dashboard based on user role.
    """
    query = request.GET.get('q', '')
    
    if is_field_engineer(request.user):
        return redirect(f"/dashboard/?q={query}")
    elif is_installer(request.user):
        return redirect(f"/dashboard/?q={query}")
    elif is_office_staff(request.user):
        return redirect(f"/office-dashboard/?q={query}")
    elif is_loan_officer(request.user):
        return redirect(f"/loan-dashboard/?q={query}")
    elif request.user.is_staff:
        return redirect(f"/admin-dashboard/?q={query}")
    
    return redirect('dashboard')

@login_required
def api_global_search(request):
    """
    API Endpoint for Live Search Autocomplete.
    Returns JSON list of matching records.
    """
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
        
    results = []
    
    # 1. Field Engineer (Own Surveys)
    if is_field_engineer(request.user):
        surveys = CustomerSurvey.objects.filter(created_by=request.user).filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query) |
            Q(sc_no__icontains=query)
        )[:5]
        for s in surveys:
            results.append({
                'title': s.customer_name,
                'subtitle': f"Phone: {s.aadhar_linked_phone} | SC: {s.sc_no}",
                'url': f"/site/{s.id}/",
                'type': 'Application'
            })

    # 2. Installer (FE Data + Installer Data)
    elif is_installer(request.user):
        surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query) |
            Q(sc_no__icontains=query)
        ).select_related('installation')[:8]
        
        for s in surveys:
            # Determine if this is "Installer Data" (Active/Completed) or "FE Data" (Pending Claim)
            has_install = hasattr(s, 'installation')
            if has_install:
                 # Installer Data
                status = s.installation.workflow_status
                results.append({
                    'title': s.customer_name,
                    'subtitle': f"SC: {s.sc_no} | Status: {status}",
                    'url': f"/site/{s.id}/",
                    'type': 'Installation' # Distinct Type
                })
            else:
                 # FE Data (Available for Install)
                results.append({
                    'title': s.customer_name,
                    'subtitle': f"SC: {s.sc_no} | Status: Pending Install",
                    'url': f"/site/{s.id}/",
                    'type': 'New Application' # Distinct Type
                })

    # 3. Office Staff (All Surveys) - Default View
    elif is_office_staff(request.user):
        surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query) |
            Q(sc_no__icontains=query)
        )[:5]
        for s in surveys:
            results.append({
                'title': s.customer_name,
                'subtitle': f"Phone: {s.aadhar_linked_phone} | Status: {s.workflow_status}",
                'url': f"/office/update-status/{s.id}/",
                'type': 'Project'
            })

    # 4. Loan Officer (All Surveys)
    elif is_loan_officer(request.user):
        surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query) |
            Q(sc_no__icontains=query)
        )[:5]
        for s in surveys:
            results.append({
                'title': s.customer_name,
                'subtitle': f"Phone: {s.aadhar_linked_phone} | Status: {s.workflow_status}",
                'url': f"/loan-dashboard/?site_id={s.id}",
                'type': 'Loan Application'
            })

    # 5. Admin (All Data Types)
    elif request.user.is_staff:
        # A. Users
        users = UserProfile.objects.filter(
            Q(user__username__icontains=query) |
            Q(mobile_number__icontains=query)
        )[:3]
        for u in users:
            results.append({
                'title': u.user.get_full_name() or u.user.username,
                'subtitle': f"Role: {u.role} | Mobile: {u.mobile_number}",
                'url': f"/admin-dashboard/?q={query}",
                'type': 'User'
            })
            
        # B. FE Data (Surveys without installation or general lookup)
        surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query)
        ).select_related('installation')[:5]
        
        for s in surveys:
            has_install = hasattr(s, 'installation')
            if has_install:
                # C. Installer Data
                results.append({
                    'title': s.customer_name,
                    'subtitle': f"Installer: {s.installation.updated_by.get_full_name()} | Status: {s.installation.workflow_status}",
                    'url': f"/site/{s.id}/",
                    'type': 'Installation Record'
                })
            else:
                # B. FE Data
                results.append({
                    'title': s.customer_name,
                    'subtitle': f"Engineer: {s.created_by.get_full_name()} | Phone: {s.aadhar_linked_phone}",
                    'url': f"/site/{s.id}/",
                    'type': 'FE Application'
                })
            
    return JsonResponse({'results': results})

def get_bank_details_by_phone(request):
    """
    API to fetch bank details based on phone number.
    Looks up CustomerSurvey by phone_number or aadhar_linked_phone.
    Returns parent_bank and parent_bank_ac_no if found.
    """
    phone = request.GET.get('phone')
    if not phone:
        return JsonResponse({'error': 'Phone number required'}, status=400)

    # Search in both phone fields
    survey = CustomerSurvey.objects.filter(
        Q(aadhar_linked_phone__icontains=phone)
    ).order_by('-created_at').first() # Get most recent

    if survey:
        try:
            bank_details = survey.bank_details
            return JsonResponse({
                'found': True,
                'parent_bank': bank_details.parent_bank,
                'parent_bank_ac_no': bank_details.parent_bank_ac_no,
                'customer_name': survey.customer_name # Optional verification for user
            })
        except BankDetails.DoesNotExist:
             return JsonResponse({'found': False, 'message': 'Survey found but no bank details linked.'})
    
    return JsonResponse({'found': False, 'message': 'No survey found with this phone number.'})


# ==========================================
# 1. MASTER DASHBOARD
# ==========================================
@login_required
def master_dashboard(request):
    """
    Redirects to Role-Specific Dashboards.
    - Field Engineer -> FE Dashboard (Own Data)
    - Installer -> Installer Dashboard (All FE Data)
    - Office/Admin -> Separate Office Login/Dashboard
    """
    user = request.user
    
    if is_field_engineer(user):
        return fe_dashboard(request)
    elif is_installer(user):
        return installer_dashboard(request)
    elif is_office_staff(user):
        return redirect('office_dashboard')
    elif is_loan_officer(user):
        return redirect('loan_dashboard')
    elif user.is_staff: 
        # Superusers/Staff go to Admin Dashboard (Pending approvals + Master Lists)
        return redirect('admin_dashboard') # Reuse existing view logic but expand it
    
    return redirect('login')

@login_required
@user_passes_test(is_field_engineer)
def fe_dashboard(request):
    """Field Engineer: Only own records."""
    query = request.GET.get('q', '')
    if query:
        my_surveys = CustomerSurvey.objects.filter(created_by=request.user).filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query) |
            Q(sc_no__icontains=query)
        ).order_by('-created_at')
    else:
        my_surveys = CustomerSurvey.objects.filter(created_by=request.user).order_by('-created_at')
    
    paginator = Paginator(my_surveys, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'solar/fe_dashboard.html', {'surveys': page_obj, 'query': query})


@login_required
@user_passes_test(is_installer)
def installer_dashboard(request):
    """Installer: View basic details of all surveys (uploaded by FE)."""
    # Spec: "installer can see the basic details in the table which was entered from the form(which the field engineer uploaded)"
    query = request.GET.get('q', '')
    if query:
        all_surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query) |
            Q(sc_no__icontains=query)
        ).select_related('installation').order_by('-created_at')
    else:
        all_surveys = CustomerSurvey.objects.all().select_related('installation').order_by('-created_at')

    
    pending_installations = []
    completed_installations = []
    
    for survey in all_surveys:
        if hasattr(survey, 'installation'):
            # It has been claimed/started.
            # Only show in "Completed" if *I* am the one who worked on it.
            if survey.installation.updated_by == request.user:
                completed_installations.append(survey)
            # If claimed by someone else, it disappears from my view entirely (as desired).
        else:
            # No installation yet -> Available for anyone to claim
            pending_installations.append(survey)
            
    pending_paginator = Paginator(pending_installations, 10)
    pending_page = request.GET.get('pending_page')
    pending_page_obj = pending_paginator.get_page(pending_page)

    completed_paginator = Paginator(completed_installations, 10)
    completed_page = request.GET.get('completed_page')
    completed_page_obj = completed_paginator.get_page(completed_page)
            
    return render(request, 'solar/installer_dashboard.html', {
        'pending_installations': pending_page_obj,
        'completed_installations': completed_page_obj,
        'query': query
    })

@staff_member_required
def pending_approvals(request):
    """Admin-only view to see and approve/reject pending users."""
    query = request.GET.get('q', '')
    if query:
        pending_users = UserProfile.objects.filter(is_approved=False).filter(
            Q(user__username__icontains=query) |
            Q(mobile_number__icontains=query)
        )
    else:
        pending_users = UserProfile.objects.filter(is_approved=False)
        
    context = {
        'pending_users': pending_users,
        'query': query,
    }
    return render(request, 'solar/pending_approvals.html', context)


def get_directory_size(directory):
    """Returns the `directory` size in bytes."""
    total_size = 0
    try:
        for dirpath, _, filenames in os.walk(directory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except Exception as e:
        print(f"Error calculating directory size: {e}")
    return total_size


@staff_member_required
def admin_dashboard(request):
    """
    Admin Dashboard: 4 Sections (Approvals moved to separate view)
    1. Field Engineer Data (Master List)
    2. Installer Data (Master List)
    3. Office Data (Recent Office Updates)
    4. Loan Data (Recent Loan Applications)
    """
    query = request.GET.get('q', '')

    if query:
        
        # 2. FE Data (All Surveys)
        fe_data = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query)
        ).select_related('created_by').order_by('-created_at')
        
        # 3. Installer Data (All Installations)
        installer_data = Installation.objects.filter(
            Q(survey__customer_name__icontains=query) |
            Q(survey__aadhar_linked_phone__icontains=query)
        ).select_related('survey', 'updated_by').order_by('-timestamp')
        
        # 4. Office Data (Surveys with Status Tracking)
        office_data = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(aadhar_linked_phone__icontains=query)
        ).exclude(workflow_status='Pending').order_by('-created_at')[:5]
        
        # 5. Loan Data (Bank Details)
        loan_data = BankDetails.objects.filter(
            Q(survey__customer_name__icontains=query) |
            Q(survey__aadhar_linked_phone__icontains=query)
        ).select_related('survey').order_by('-id')[:5]
    else:
        
        # 2. FE Data (All Surveys)
        fe_data = CustomerSurvey.objects.all().select_related('created_by').order_by('-created_at')
        
        # 3. Installer Data (All Installations)
        installer_data = Installation.objects.all().select_related('survey', 'updated_by').order_by('-timestamp')
        
        # 4. Office Data (Recent 5 with status updates)
        office_data = CustomerSurvey.objects.exclude(workflow_status='Pending').order_by('-created_at')[:5]
        
        # 5. Loan Data (Recent 5 loan applications)
        loan_data = BankDetails.objects.all().select_related('survey').order_by('-id')[:5]
    
    # Calculate Storage Limit (5GB)
    total_limit_bytes = 5 * 1024 * 1024 * 1024  # 5 GB in bytes
    used_storage_bytes = get_directory_size(settings.MEDIA_ROOT)
    
    # Calculate percentages and readable formats
    used_storage_gb = used_storage_bytes / (1024 * 1024 * 1024)
    remaining_storage_gb = max(0, 5.0 - used_storage_gb)
    storage_percentage = min(100, (used_storage_bytes / total_limit_bytes) * 100)

    context = {
        'fe_data': fe_data,
        'installer_data': installer_data,
        'office_data': office_data,
        'loan_data': loan_data,
        'query': query,
        'used_storage_gb': round(used_storage_gb, 2),
        'remaining_storage_gb': round(remaining_storage_gb, 2),
        'storage_percentage': round(storage_percentage, 1),
        'maintenance_mode': SiteSettings.get_settings().maintenance_mode,
    }
    return render(request, 'solar/admin_dashboard.html', context)


@login_required
def download_images(request, survey_id):
    """
    Download all images for a given CustomerSurvey as a ZIP file.
    Includes roof_photo, and all installation photos if an installation exists.
    """
    if not (request.user.is_superuser or request.user.is_staff or getattr(request.user.userprofile, 'role', '') in ['Admin', 'Office']):
        messages.error(request, 'You do not have permission to download these files.')
        return redirect('dashboard')

    survey = get_object_or_404(CustomerSurvey, pk=survey_id)

    # Collect all (label, image_field) pairs
    images = []

    if survey.roof_photo:
        images.append((f'roof_photo{os.path.splitext(survey.roof_photo.name)[1]}', survey.roof_photo))

    # Document photos uploaded by Field Engineer
    if survey.pan_card_photo:
        images.append((f'pan_card{os.path.splitext(survey.pan_card_photo.name)[1]}', survey.pan_card_photo))
    if survey.aadhar_photo:
        images.append((f'aadhar_card{os.path.splitext(survey.aadhar_photo.name)[1]}', survey.aadhar_photo))
    if survey.current_bill_photo:
        images.append((f'current_bill{os.path.splitext(survey.current_bill_photo.name)[1]}', survey.current_bill_photo))
    if survey.bank_account_photo:
        images.append((f'bank_account{os.path.splitext(survey.bank_account_photo.name)[1]}', survey.bank_account_photo))

    if hasattr(survey, 'installation'):
        inst = survey.installation
        if inst.inverter_serial_photo:
            images.append((f'inverter_serial{os.path.splitext(inst.inverter_serial_photo.name)[1]}', inst.inverter_serial_photo))
        if inst.inverter_acdb_photo:
            images.append((f'inverter_acdb{os.path.splitext(inst.inverter_acdb_photo.name)[1]}', inst.inverter_acdb_photo))
        if inst.panel_serial_photo:
            images.append((f'panel_serial{os.path.splitext(inst.panel_serial_photo.name)[1]}', inst.panel_serial_photo))
        if inst.site_photos_with_customer:
            images.append((f'site_with_customer{os.path.splitext(inst.site_photos_with_customer.name)[1]}', inst.site_photos_with_customer))

    if not images:
        messages.warning(request, f'No images found for {survey.customer_name}.')
        return redirect('admin_dashboard')

    # Build ZIP in memory
    buffer = io.BytesIO()
    safe_name = survey.customer_name.replace(' ', '_').replace('/', '-')
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, image_field in images:
            try:
                with image_field.open('rb') as img_file:
                    zf.writestr(filename, img_file.read())
            except Exception:
                pass  # Skip any files that can't be read

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{safe_name}_images.zip"'
    return response


@login_required
@user_passes_test(is_office_staff)
def office_dashboard(request):
    """
    Office Staff Dashboard:
    - Lists surveys with Status Tracking.
    - Search by Phone Number.
    """
    query = request.GET.get('q', '')
    if query:
        surveys = CustomerSurvey.objects.filter(
            Q(aadhar_linked_phone__icontains=query) | 
            Q(customer_name__icontains=query) |
            Q(sc_no__icontains=query)
        ).select_related('installation').order_by('-created_at')
    else:
        surveys = CustomerSurvey.objects.all().select_related('installation').order_by('-created_at')
        
    paginator = Paginator(surveys, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
        
    return render(request, 'solar/office_dashboard.html', {'surveys': page_obj, 'query': query})

@login_required
@user_passes_test(is_office_staff)
@login_required
@user_passes_test(is_office_staff)
def office_update_status(request, pk):
    """View for Office Staff to update project status and loan details."""
    survey = get_object_or_404(CustomerSurvey, pk=pk)
    # Ensure bank details exist
    bank_details, created = BankDetails.objects.get_or_create(survey=survey)
    
    if request.method == 'POST':
        form = OfficeStatusForm(request.POST, instance=survey)
        bank_form = OfficeBankDetailsForm(request.POST, instance=bank_details)
        
        if form.is_valid() and bank_form.is_valid():
            form.save()
            bank_form.save()
            messages.success(request, f"Status and Loan details updated for {survey.customer_name}.")
            return redirect('office_dashboard')
        else:
            print("Form Errors:", form.errors)
            print("Bank Form Errors:", bank_form.errors)
    else:
        form = OfficeStatusForm(instance=survey)
        bank_form = OfficeBankDetailsForm(instance=bank_details)
    
    return render(request, 'solar/office_status_form.html', {
        'form': form, 
        'bank_form': bank_form,
        'survey': survey
    })

@login_required
@user_passes_test(is_office_staff)
def office_update_home(request):
    """
    Office Staff Phone Search Landing Page.
    Allows office staff to search for a customer by phone number,
    then redirects to the update status form.
    """
    return render(request, 'solar/office_update_home.html')


@login_required
@user_passes_test(is_office_staff)
def get_survey_by_phone_all(request):
    """
    API Endpoint: Fetch ALL customer surveys by phone number (for Office use).
    Unlike the installer API, this does NOT filter out surveys with installations.
    Returns JSON with matching survey(s) info.
    """
    phone = request.GET.get('phone', '')

    if not phone:
        return JsonResponse({'found': False, 'message': 'Phone number is required.'})

    surveys = CustomerSurvey.objects.filter(
        Q(aadhar_linked_phone=phone)
    ).order_by('-created_at')

    if not surveys.exists():
        return JsonResponse({'found': False, 'message': 'No customer found with this phone number.'})

    if surveys.count() == 1:
        survey = surveys.first()
        return JsonResponse({
            'found': True,
            'count': 1,
            'survey_id': survey.id,
            'customer_name': survey.customer_name,
            'sc_no': survey.sc_no,
            'phase': survey.phase,
            'area': survey.area or '',
            'agreed_amount': str(survey.agreed_amount),
            'workflow_status': survey.workflow_status,
            'phone_number': survey.aadhar_linked_phone or '',
        })

    # Multiple surveys found — return list
    records = []
    for s in surveys:
        records.append({
            'id': s.id,
            'customer_name': s.customer_name,
            'sc_no': s.sc_no,
            'phase': s.phase,
            'area': s.area or '',
            'agreed_amount': str(s.agreed_amount),
            'workflow_status': s.workflow_status,
            'created_at': s.created_at.strftime('%d %b %Y'),
        })

    return JsonResponse({'found': True, 'count': surveys.count(), 'records': records})

@login_required
@user_passes_test(is_loan_officer)
def loan_dashboard(request):
    """
    Loan Dashboard:
    - Search for Customer by Phone Number.
    - View and Update Bank/Loan Details.
    """
    query = request.GET.get('q', '')
    site_id = request.GET.get('site_id')
    customer = None
    bank_details = None
    form = None
    recent_customers = [] # For default view
    
    if query or site_id:
        # Search Logic
        if site_id:
            customer = get_object_or_404(CustomerSurvey, pk=site_id)
        else:
            # Search by Phone Number (including Aadhar linked as backup)
            customer = CustomerSurvey.objects.filter(
                Q(aadhar_linked_phone__icontains=query)
            ).first()
        
        if customer:
            # Fetch or Create Bank Details
            # Use get_or_create to ensure we have a record to edit
            bank_details, created = BankDetails.objects.get_or_create(survey=customer)
            
            # Pre-fill data if new
            if created and customer.bank_account_no:
                 bank_details.parent_bank_ac_no = customer.bank_account_no
                 bank_details.save()
            
            if request.method == 'POST':
                form = BankDetailsForm(request.POST, instance=bank_details)
                if form.is_valid():
                    form.save()
                    messages.success(request, f"Loan details updated for {customer.customer_name}.")
                    return redirect(f"{request.path}?q={query}")
            else:
                form = BankDetailsForm(instance=bank_details)
        else:
            messages.error(request, "Customer not found with this phone number.")
    else:
        # Show recent customers if no query
        recent_customers = list(CustomerSurvey.objects.all().order_by('-created_at')[:20])
        for c in recent_customers:
            try:
                # Accessing reverse one-to-one raises error if missing
                c.cached_loan_status = c.bank_details.loan_pending_status
            except BankDetails.DoesNotExist:
                c.cached_loan_status = None
    
    return render(request, 'solar/loan_dashboard.html', {
        'form': form,
        'customer': customer,
        'query': query,
        'bank_details': bank_details,
        'recent_customers': recent_customers
    })

@login_required
@user_passes_test(is_field_engineer)
def survey_form_view(request):
    if request.method == 'POST':
        form = SurveyForm(request.POST, request.FILES)
        bank_form = BankDetailsForm(request.POST) # Initialize Bank Form
        
        if form.is_valid() and bank_form.is_valid(): # Check both
            survey = form.save(commit=False)
            survey.created_by = request.user
            survey.save()
            
            # Save Bank Details
            bank_params = bank_form.save(commit=False)
            bank_params.survey = survey
            bank_params.loan_pending_status = 'Pending' # Default
            bank_params.save()

            # Handle categorized multi-uploads for survey
            media_map = {
                'roof_photo': 'roof',
                'pan_card_photo': 'pan_card',
                'aadhar_photo': 'aadhar',
                'current_bill_photo': 'current_bill',
                'bank_account_photo': 'bank_account',
                'parent_bank_photo': 'parent_bank',
            }
            
            for field, m_type in media_map.items():
                files = form.cleaned_data.get(field) or []
                for f in files:
                    SurveyMedia.objects.create(survey=survey, file=f, media_type=m_type)

            messages.success(request, 'Survey and Bank Details submitted successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SurveyForm()
        bank_form = BankDetailsForm() # Initialize empty

    return render(request, 'solar/survey_form.html', {
        'form': form, 
        'bank_form': bank_form
    })

@login_required
@user_passes_test(is_field_engineer)
def delete_and_restart(request, pk):
    """Client Policy: Delete record and start fresh for any tech corrections."""
    survey = get_object_or_404(CustomerSurvey, pk=pk)
    if request.method == "POST":
        name = survey.customer_name
        survey.delete()
        messages.warning(request, f"Record for {name} deleted. Please restart fresh.")
        return redirect('create_survey')
    return render(request, 'solar/confirm_delete.html', {'survey': survey})

# ==========================================
# 3. INSTALLATION PORTAL
# ==========================================
@login_required
@login_required
@user_passes_test(is_installer)
def installation_entry(request):
    """Fallback: Installer entry if no ID passed (mostly unused now)."""
    return redirect('dashboard')


@login_required
@user_passes_test(is_installer)
def new_installation(request):
    """
    New Installation Form with Mobile Number Lookup.
    Installer enters phone number, fetches customer details, then fills installation form.
    """
    survey = None
    form = None
    
    if request.method == 'POST':
        survey_id = request.POST.get('survey_id')
        
        if survey_id:
            try:
                survey = CustomerSurvey.objects.get(id=survey_id)
                
                # Check if installation already exists
                if hasattr(survey, 'installation'):
                    messages.error(request, f"Installation already exists for {survey.customer_name}. Cannot create duplicate.")
                    return redirect('dashboard')
                
                # Process installation form
                form = InstallationForm(request.POST, request.FILES)
                if form.is_valid():
                    installation = form.save(commit=False)
                    installation.survey = survey
                    installation.updated_by = request.user
                    installation.save()
                    form.save_m2m() # Standard practice even if no M2M fields

                    # Handle categorized multi-photo uploads
                    media_map = {
                        'inverter_serial_photo': 'inverter_serial',
                        'inverter_acdb_photo': 'inverter_acdb',
                        'panel_serial_photo': 'panel_serial',
                        'site_photos_with_customer': 'site_with_customer',
                        'site_photos_multiple': 'additional',
                    }
                    
                    for field, p_type in media_map.items():
                        files = form.cleaned_data.get(field) or []
                        for f in files:
                            InstallationPhoto.objects.create(installation=installation, photo=f, photo_type=p_type)

                    messages.success(request, f"Installation submitted successfully for {survey.customer_name}!")
                    return redirect('dashboard')
                else:
                    # Form has validation errors
                    for field, errors in form.errors.items():
                        messages.error(request, f"{field.replace('_', ' ').title()}: {', '.join(errors)}")
            except CustomerSurvey.DoesNotExist:
                messages.error(request, "Survey not found.")
                form = InstallationForm()
        else:
            # No survey_id provided
            messages.error(request, "No customer selected. Please fetch customer details first.")
            form = InstallationForm()
    else:
        # GET request: Show empty form
        form = InstallationForm()
    
    return render(request, 'solar/new_installation_form.html', {
        'form': form,
        'survey': survey
    })

def get_survey_by_phone(request):
    """
    API Endpoint: Fetch customer survey details by phone number.
    Returns JSON with customer info for auto-fill.
    Supports multiple surveys per phone number.
    """
    phone = request.GET.get('phone', '')
    
    if not phone:
        return JsonResponse({'found': False, 'message': 'Phone number is required.'})
    
    # Query ALL surveys with this phone number (excluding those with installations)
    surveys = CustomerSurvey.objects.filter(aadhar_linked_phone=phone).order_by('-created_at')
    
    if not surveys.exists():
        return JsonResponse({
            'found': False,
            'message': 'No customer found with this phone number.'
        })
    
    # Filter out surveys that already have installations
    available_surveys = [s for s in surveys if not hasattr(s, 'installation')]
    
    if not available_surveys:
        return JsonResponse({
            'found': False,
            'message': 'All applications for this phone number already have installations completed.'
        })
    
    # If only one available survey, return it directly
    if len(available_surveys) == 1:
        survey = available_surveys[0]
        return JsonResponse({
            'found': True,
            'count': 1,
            'survey_id': survey.id,
            'customer_name': survey.customer_name,
            'connection_type': survey.connection_type,
            'sc_no': survey.sc_no,
            'phase': survey.phase,
            'feasibility_kw': str(survey.feasibility_kw),
            'aadhar_no': survey.aadhar_no,
            'pan_card': survey.pan_card,
            'email': survey.email,
            'phone_number': survey.aadhar_linked_phone or '',
            'area': survey.area,
            'gps_coordinates': survey.gps_coordinates,
            'roof_type': survey.roof_type,
            'structure_type': survey.structure_type,
            'structure_height': str(survey.structure_height),
            'agreed_amount': str(survey.agreed_amount),
            'advance_paid': str(survey.advance_paid) if survey.advance_paid else '0',
            'mefma_status': 'Yes' if survey.mefma_status else 'No',
            'rp_name': survey.rp_name or '',
            'rp_phone_number': survey.rp_phone_number or '',
            'fe_remarks': survey.fe_remarks or '',
            'reference_name': survey.reference_name or '',
            'pms_registration_number': survey.pms_registration_number or '',
            'division': survey.division or '',
            'registration_status': 'Yes' if survey.registration_status else 'No',
        })
    
    # Multiple surveys found - return list for selection
    records = []
    for survey in available_surveys:
        records.append({
            'id': survey.id,
            'customer_name': survey.customer_name,
            'sc_no': survey.sc_no,
            'phase': survey.phase,
            'area': survey.area,
            'feasibility_kw': str(survey.feasibility_kw),
            'agreed_amount': str(survey.agreed_amount),
            'roof_type': survey.roof_type,
            'connection_type': survey.connection_type,
            'created_at': survey.created_at.strftime('%Y-%m-%d'),
        })
    
    return JsonResponse({
        'found': True,
        'count': len(records),
        'records': records
    })

def get_survey_by_id(request):
    """
    API Endpoint: Fetch single survey details by ID.
    Used after user selects from multiple records.
    """
    survey_id = request.GET.get('id', '')
    
    if not survey_id:
        return JsonResponse({'found': False, 'message': 'Survey ID is required.'})
    
    try:
        survey = CustomerSurvey.objects.get(id=survey_id)
        
        # Check if installation already exists
        if hasattr(survey, 'installation'):
            return JsonResponse({
                'found': False,
                'message': f'Installation already exists for this application.'
            })
        
        # Return full customer details
        return JsonResponse({
            'found': True,
            'survey_id': survey.id,
            'customer_name': survey.customer_name,
            'connection_type': survey.connection_type,
            'sc_no': survey.sc_no,
            'phase': survey.phase,
            'feasibility_kw': str(survey.feasibility_kw),
            'aadhar_no': survey.aadhar_no,
            'pan_card': survey.pan_card,
            'email': survey.email,
            'phone_number': survey.aadhar_linked_phone or '',
            'area': survey.area,
            'gps_coordinates': survey.gps_coordinates,
            'roof_type': survey.roof_type,
            'structure_type': survey.structure_type,
            'structure_height': str(survey.structure_height),
            'agreed_amount': str(survey.agreed_amount),
            'advance_paid': str(survey.advance_paid) if survey.advance_paid else '0',
            'mefma_status': 'Yes' if survey.mefma_status else 'No',
            'rp_name': survey.rp_name or '',
            'rp_phone_number': survey.rp_phone_number or '',
            'fe_remarks': survey.fe_remarks or '',
            'reference_name': survey.reference_name or '',
            'pms_registration_number': survey.pms_registration_number or '',
            'division': survey.division or '',
            'registration_status': 'Yes' if survey.registration_status else 'No',
        })
    except CustomerSurvey.DoesNotExist:
        return JsonResponse({
            'found': False,
            'message': 'Survey not found.'
        })


@login_required
@user_passes_test(is_installer)
def update_installation(request, pk):
    """Specific update for a survey ID."""
    survey = get_object_or_404(CustomerSurvey, pk=pk)
    instance = Installation.objects.filter(survey=survey).first()
    
    if request.method == "POST":
        form = InstallationForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            inst = form.save(commit=False)
            if not inst.survey_id:
                inst.survey = survey
            inst.updated_by = request.user
            inst.save()
            form.save_m2m()

            # Handle categorized multi-photo uploads
            media_map = {
                'inverter_serial_photo': 'inverter_serial',
                'inverter_acdb_photo': 'inverter_acdb',
                'panel_serial_photo': 'panel_serial',
                'site_photos_with_customer': 'site_with_customer',
                'site_photos_multiple': 'additional',
            }
            
            for field, p_type in media_map.items():
                files = form.cleaned_data.get(field) or []
                if files:
                    # Replace old images of this type
                    InstallationPhoto.objects.filter(installation=inst, photo_type=p_type).delete()
                    for f in files:
                        InstallationPhoto.objects.create(installation=inst, photo=f, photo_type=p_type)

            messages.success(request, f"Installation data updated for {survey.customer_name}.")
            return redirect('dashboard')
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {', '.join(errors)}")
    else:
        form = InstallationForm(instance=instance, initial={'survey': survey})
        
    return render(request, 'solar/installation_form.html', {'form': form, 'survey': survey})

# ==========================================
# 4. BANK / FINANCE PORTAL
# ==========================================
@login_required
@user_passes_test(is_bank_user)
def bank_entry(request):
    """Bank portal: Handles loan, UTR, and disbursement details."""
    if request.method == "POST":
        survey_id = request.POST.get('survey')
        # Fetch existing instance to allow updates
        instance = BankDetails.objects.filter(survey_id=survey_id).first()
        
        form = BankDetailsForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Finance record updated successfully.")
            return redirect('dashboard')
    else:
        form = BankDetailsForm()
    return render(request, 'solar/bank_form.html', {'form': form})

# ==========================================
# 5. SITE DETAIL / GALLERY
# ==========================================
def _get_site_media_context(customer):
    """Helper to group media files for gallery rendering."""
    survey_media = {}
    for sm in customer.media_files.all():
        if sm.media_type not in survey_media:
            survey_media[sm.media_type] = []
        survey_media[sm.media_type].append(sm)
    
    installation_photos = {}
    if hasattr(customer, 'installation'):
        for ip in customer.installation.additional_photos.all():
            if ip.photo_type not in installation_photos:
                installation_photos[ip.photo_type] = []
            installation_photos[ip.photo_type].append(ip)
    
    return {
        'survey_media': survey_media,
        'installation_photos': installation_photos,
    }

@login_required
def site_detail(request, pk):
    """Technical deep-dive and photo gallery for specific sites."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    context = {'customer': customer}
    context.update(_get_site_media_context(customer))
    return render(request, 'solar/site_detail.html', context)

@login_required
def update_survey(request, pk):
    """Allow Field Engineers to update their own surveys."""
    survey = get_object_or_404(CustomerSurvey, pk=pk)
    
    # Permission Check: Only Admin can edit (FE is read-only)
    if not request.user.is_staff:
        messages.error(request, "Field Engineers have read-only access.")
        return redirect('site_detail', pk=pk)
        
    # Try to fetch existing bank details
    try:
        bank_details = survey.bank_details
    except BankDetails.DoesNotExist:
        bank_details = None

    if request.method == "POST":
        form = SurveyForm(request.POST, request.FILES, instance=survey)
        bank_form = BankDetailsForm(request.POST, instance=bank_details)
        
        if form.is_valid() and bank_form.is_valid():
            form.save()
            
            # Save Bank Details
            bank_obj = bank_form.save(commit=False)
            bank_obj.survey = survey
            bank_obj.save()

            # Handle categorized multi-uploads for survey
            media_map = {
                'roof_photo': 'roof',
                'pan_card_photo': 'pan_card',
                'aadhar_photo': 'aadhar',
                'current_bill_photo': 'current_bill',
                'bank_account_photo': 'bank_account',
                'parent_bank_photo': 'parent_bank',
            }
            
            for field, m_type in media_map.items():
                files = form.cleaned_data.get(field) or []
                if files:
                    # Replace old images of this type
                    SurveyMedia.objects.filter(survey=survey, media_type=m_type).delete()
                    for f in files:
                        SurveyMedia.objects.create(survey=survey, file=f, media_type=m_type)
            
            messages.success(request, "Survey and Bank details updated.")
            return redirect('site_detail', pk=pk)
    else:
        form = SurveyForm(instance=survey)
        bank_form = BankDetailsForm(instance=bank_details)
    
    return render(request, 'solar/survey_form.html', {
        'form': form, 
        'bank_form': bank_form,
        'is_update': True
    })

# ==========================================
# 6. ADMIN & DATA EXPORT
# ==========================================
@staff_member_required
def toggle_registration(request, pk):
    """Admin-only status toggle."""
    survey = get_object_or_404(CustomerSurvey, pk=pk)
    survey.registration_status = not survey.registration_status
    survey.save()
    messages.info(request, f"Status updated for {survey.customer_name}.")
    return redirect('dashboard')

@login_required
def export_solar_data(request):
    """
    Export all details to Excel based on report type.
    Types: master (default), field_engineer, installer, material_dispatch, enquiries, users.
    Office users may download: installer, material_dispatch.
    Staff/Admin may download all types.
    """
    try:
        report_type = request.GET.get('type', 'master')

        # Determine access
        is_staff = request.user.is_staff
        is_office = hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'Office'
        office_allowed_types = {'installer', 'material_dispatch'}

        if not is_staff and not (is_office and report_type in office_allowed_types):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You do not have permission to download this report.")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Create Excel Workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{report_type.title()} Report"

        # Define Styles
        header_font = Font(bold=True)

        # 1. FIELD ENGINEER REPORT
        if report_type == 'field_engineer':
            headers = [
                'Customer Name', 'SC No', 'Phone', 'Connection', 'Phase', 'Contracted Load (KW)', 'Feasibility KW',
                'Aadhar No', 'PAN Card', 'Email', 'Aadhar Linked Phone', 'Bank Account No',
                'Roof Type', 'Structure Type', 'Structure Height', 'Floors', 'Area', 'GPS Coordinates',
                'Agreed Amount', 'Advance Paid', 'MEFMA Status', 'RP Name', 'RP Phone',
                'FE Remarks', 'Reference Name', 'PMS Registration Number', 'Division', 'Registration Status',
                'Discom Status', 'Net Metering Status', 'Subsidy Status', 'Office Remarks',
                'Workflow Status', 'Installation Date', 'Engineer', 'Date Created'
            ]
            ws.append(headers)
            surveys = CustomerSurvey.objects.all().select_related('created_by').order_by('id').distinct()
            for s in surveys:
                ws.append([
                    s.customer_name, s.sc_no, s.aadhar_linked_phone, s.connection_type, s.phase, s.contracted_load, s.feasibility_kw,
                    s.aadhar_no, s.pan_card, s.email, s.aadhar_linked_phone, s.bank_account_no,
                    s.roof_type, s.structure_type, s.structure_height, s.floors if s.floors is not None else '', s.area, s.gps_coordinates,
                    s.agreed_amount, s.advance_paid, 'Yes' if s.mefma_status else 'No', s.rp_name, s.rp_phone_number,
                    s.fe_remarks, s.reference_name, s.pms_registration_number, s.division, 'Yes' if s.registration_status else 'No',
                    s.discom_status, s.net_metering_status, s.subsidy_status, s.office_remarks,
                    s.workflow_status, s.installation_date.strftime("%Y-%m-%d") if s.installation_date else '',
                    s.created_by.get_full_name() if s.created_by else 'Unknown',
                    s.created_at.strftime("%Y-%m-%d %H:%M")
                ])

        # 2. INSTALLER REPORT
        elif report_type == 'installer':
            headers = [
                'Customer Name', 'SC No', 'Phone', 'Connection Type', 'Phase', 'Roof Type', 'Agreed Amount',
                'Installer', 'Install Date', 'Inverter Make', 'Inverter Phase', 
                'AC Cable (m)', 'DC Cable (m)', 'LA Cable (m)', 'Pipes (m)', 'Leftover Materials',
                'DC Volt', 'AC Volt', 'Earth Resistance', 'Warranty Claimed', 'App Installed',
                'Installer Remarks', 'Customer Remarks', 'Customer Rating', 'Status',
                # Materials Dispatched
                'Panels (Count)', 'Structure Kit', 'Inverter (kW)', 'Inverter Phase Type',
                'AC Cable Red (m)', 'AC Cable Black (m)', 'DC Cable R&B (m)', 'LA Cable (m)',
                'Pipes Count', 'Earthing Kit', 'ACDB', 'DCDB', 'MC4 Connectors',
                'Long L Bands', 'Short L Bands', 'T Bands',
                'Tapes Red', 'Tapes Black', 'Tags',
                'Nail Clamps 2 Side', 'Nail Clamps 1 Side', 'Anchor Hardener',
            ]
            ws.append(headers)
            installations = Installation.objects.all().select_related('survey', 'updated_by').order_by('id').distinct()
            for i in installations:
                sur = i.survey
                ws.append([
                    sur.customer_name, sur.sc_no, sur.aadhar_linked_phone, sur.connection_type, sur.phase, sur.roof_type, sur.agreed_amount,
                    i.updated_by.get_full_name() if i.updated_by else 'Unknown',
                    i.timestamp.strftime("%Y-%m-%d %H:%M"),
                    i.inverter_make, i.inverter_phase, i.ac_cable_used, i.dc_cable_used,
                    i.la_cable_used, i.pipes_used, i.leftover_materials, i.dc_voltage, i.ac_voltage, 
                    i.earthing_resistance, 'Yes' if i.warranty_claimed else 'No', 'Yes' if i.app_installation_status else 'No',
                    i.installer_remarks, i.customer_remarks, i.customer_rating,
                    sur.workflow_status,
                    # Materials Dispatched
                    i.panels_count, i.structure_kit_type, i.inverter_kw, i.inverter_phase_type,
                    i.ac_cable_red, i.ac_cable_black, i.dc_cable_red_black, i.la_cable_mtrs,
                    i.pipes_count, i.earthing_kit_count, i.acdb_count, i.dcdb_count, i.mc4_connectors_count,
                    i.long_l_bands_count, i.short_l_bands_count, i.t_bands_count,
                    i.tapes_red_count, i.tapes_black_count, i.tags_count,
                    i.nail_clamps_2side_count, i.nail_clamps_1side_count, i.anchor_hardener_count,
                ])

        # 3. ENQUIRIES REPORT
        elif report_type == 'enquiries':
            headers = ['Name', 'Mobile', 'Email', 'Address', 'Date Received']
            ws.append(headers)
            enquiries = Enquiry.objects.all().order_by('-created_at')
            for e in enquiries:
                ws.append([
                    e.name, e.mobile_number, e.email, e.address, 
                    e.created_at.strftime("%Y-%m-%d %H:%M")
                ])

        # 4. USERS REPORT
        elif report_type == 'users':
            headers = ['Username', 'Full Name', 'Mobile', 'Email', 'Role', 'Status', 'Date Joined']
            ws.append(headers)
            profiles = UserProfile.objects.all().select_related('user').order_by('-user__date_joined')
            for p in profiles:
                ws.append([
                    p.user.username, p.user.get_full_name(), p.mobile_number, p.user.email,
                    p.role, 'Approved' if p.is_approved else 'Pending',
                    p.user.date_joined.strftime("%Y-%m-%d")
                ])

        # 5. MATERIAL DISPATCH REPORT
        elif report_type == 'material_dispatch':
            headers = [
                'Customer Name', 'Mobile Number', 'SC Number',
                # Dispatched Materials
                'Panels (Count)',
                'Structure Kit Type',
                'Inverter (kW)',
                'Inverter Phase Type',
                'AC Cable Red (m)',
                'AC Cable Black (m)',
                'DC Cable Red & Black (m)',
                'LA Cable (m)',
                'Pipes (Count)',
                'Earthing Kit (Count)',
                'ACDB (Count)',
                'DCDB (Count)',
                'MC4 Connectors (Count)',
                'Long L Bands (Count)',
                'Short L Bands (Count)',
                'T Bands (Count)',
                'Tapes Red (Count)',
                'Tapes Black (Count)',
                'Tags (Count)',
                'Nail Clamps 2 Side (Count)',
                'Nail Clamps 1 Side (Count)',
                'Anchor Hardener (Count)',
                'Installation Date',
                'Installer Name',
            ]
            ws.append(headers)
            installations = Installation.objects.all().select_related('survey', 'updated_by').order_by('survey__customer_name')
            for i in installations:
                sur = i.survey
                ws.append([
                    sur.customer_name,
                    sur.aadhar_linked_phone,
                    sur.sc_no,
                    # Materials
                    i.panels_count,
                    i.structure_kit_type,
                    i.inverter_kw,
                    i.inverter_phase_type,
                    i.ac_cable_red,
                    i.ac_cable_black,
                    i.dc_cable_red_black,
                    i.la_cable_mtrs,
                    i.pipes_count,
                    i.earthing_kit_count,
                    i.acdb_count,
                    i.dcdb_count,
                    i.mc4_connectors_count,
                    i.long_l_bands_count,
                    i.short_l_bands_count,
                    i.t_bands_count,
                    i.tapes_red_count,
                    i.tapes_black_count,
                    i.tags_count,
                    i.nail_clamps_2side_count,
                    i.nail_clamps_1side_count,
                    i.anchor_hardener_count,
                    i.timestamp.strftime("%Y-%m-%d %H:%M"),
                    i.updated_by.get_full_name() if i.updated_by else 'Unknown',
                ])

        # 5. MASTER REPORT (Default) - ALL DATA FROM ALL TABLES
        else:
            headers = [
                'Customer Name', 'SC No', 'Phone', 'Connection', 'Phase', 'Contracted Load (KW)', 'Feasibility KW',
                'Aadhar No', 'PAN Card', 'Email', 'Aadhar Linked Phone', 'Bank Account No',
                'Roof Type', 'Structure Type', 'Structure Height', 'Floors', 'Area', 'GPS Coordinates',
                'Agreed Amount', 'Advance Paid', 'MEFMA Status', 'RP Name', 'RP Phone',
                'FE Remarks', 'Reference Name', 'PMS Registration Number', 'Division', 'Registration Status',
                'Discom Status', 'Net Metering Status', 'Subsidy Status', 'Office Remarks',
                'Workflow Status', 'Installation Date', 'Field Engineer Name', 'Survey Date',
                # Bank Details
                'Parent Bank', 'Parent Bank A/C', 'Loan Applied Bank', 'Loan Applied IFSC', 'Loan Applied A/C',
                'Manager Number', 'Loan Status', 'First Loan Amount', 'First Loan UTR', 'First Loan Date',
                'Second Loan Amount', 'Second Loan UTR', 'Second Loan Date'
            ]
            ws.append(headers)
            projects = CustomerSurvey.objects.all().select_related('created_by', 'installation', 'bank_details').order_by('id').distinct()
            
            for p in projects:
                has_i = hasattr(p, 'installation')
                has_b = hasattr(p, 'bank_details')
                
                row = [
                    # FE / Survey Details
                    p.customer_name, p.sc_no, p.aadhar_linked_phone, p.connection_type, p.phase, p.contracted_load, p.feasibility_kw,
                    p.aadhar_no, p.pan_card, p.email, p.aadhar_linked_phone, p.bank_account_no,
                    p.roof_type, p.structure_type, p.structure_height, p.floors if p.floors is not None else '', p.area, p.gps_coordinates,
                    p.agreed_amount, p.advance_paid, 'Yes' if p.mefma_status else 'No', p.rp_name, p.rp_phone_number,
                    p.fe_remarks, p.reference_name, p.pms_registration_number, p.division, 'Yes' if p.registration_status else 'No',
                    p.discom_status, p.net_metering_status, p.subsidy_status, p.office_remarks,
                    p.workflow_status, p.installation_date.strftime("%Y-%m-%d") if p.installation_date else '',
                    p.created_by.get_full_name() if p.created_by else 'Unknown',
                    p.created_at.strftime("%Y-%m-%d %I:%M %p"),
                ]

                # Bank Details
                if has_b:
                    row.extend([
                        p.bank_details.parent_bank, p.bank_details.parent_bank_ac_no, p.bank_details.loan_applied_bank, p.bank_details.loan_applied_ifsc, p.bank_details.loan_applied_ac_no,
                        p.bank_details.manager_number, p.bank_details.loan_pending_status, p.bank_details.first_loan_amount, p.bank_details.first_loan_utr, p.bank_details.first_loan_date.strftime("%Y-%m-%d") if p.bank_details.first_loan_date else '',
                        p.bank_details.second_loan_amount, p.bank_details.second_loan_utr, p.bank_details.second_loan_date.strftime("%Y-%m-%d") if p.bank_details.second_loan_date else ''
                    ])
                else:
                    row.extend([''] * 13) # 13 bank columns

                ws.append(row)

        # Style Header
        for cell in ws[1]:
            cell.font = header_font

        # Create Response
        filename = f"WeSolar_{report_type.title()}_Report_{timestamp}.xlsx"
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response

    except Exception as e:
        import traceback
        error_msg = f"Excel Export failed: {str(e)}\n\n{traceback.format_exc()}"
        return HttpResponse(error_msg, content_type="text/plain", status=500)


# ==========================================
# 7. AJAX API (AUTO-FETCH)
# ==========================================
def get_customer_data(request):
    """API endpoint to auto-fill forms via phone number search."""
    phone = request.GET.get('phone', None)
    if not phone:
        return JsonResponse({'success': False, 'error': 'Phone required'}, status=400)

    # Sanitize phone input (only digits)
    clean_phone = re.sub(r'\D', '', phone)
    
    if customer:
        return JsonResponse({
            'success': True,
            'customer_id': customer.id,
            'customer_name': customer.customer_name,
            'sc_no': customer.sc_no,
            'phase': customer.phase,
            'roof_type': customer.roof_type,
            'structure_type': customer.structure_type,
            'structure_height': customer.structure_height,
        })
    return JsonResponse({'success': False, 'error': 'Record not found'}, status=404)

@login_required
def update_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = None

    from .forms import ProfileUpdateForm
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user, user_profile=profile)
        if form.is_valid():
            form.save()
            
            # Handle multi-uploads for profile
            media_map = {
                'aadhar_photo': 'aadhar',
                'pan_card_photo': 'pan_card',
            }
            for field, m_type in media_map.items():
                files = form.cleaned_data.get(field) or []
                for f in files:
                    ProfileMedia.objects.create(profile=profile, file=f, media_type=m_type)

            messages.success(request, 'Your profile has been updated successfully.')
            # Redirect back to the correct dashboard based on role
            if profile:
                if profile.role == 'Admin':
                    return redirect('admin_dashboard')
                elif profile.role == 'Field Engineer':
                    return redirect('dashboard')
                elif profile.role == 'Installer':
                    return redirect('dashboard')
                elif profile.role == 'Office':
                    return redirect('office_dashboard')
                elif profile.role == 'Loan':
                    return redirect('loan_dashboard')
            return redirect('dashboard')
    else:
        form = ProfileUpdateForm(instance=request.user, user_profile=profile)
    
    return render(request, 'solar/update_profile.html', {'form': form})

# ==========================================
# 8. ENQUIRY SYSTEM
# ==========================================

def create_enquiry(request):
    """Public endpoint for handling enquiry form submissions from landing page."""
    if request.method == "POST":
        form = EnquiryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you! Your enquiry has been submitted successfully.")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors in the enquiry form.")
    else:
        form = EnquiryForm()
    return render(request, 'solar/enquiry_form.html', {'form': form})

@staff_member_required
def enquiry_list(request):
    """View to list all enquiries. Accessible by Admin only."""
    enquiries = Enquiry.objects.all().order_by('-created_at')
    return render(request, 'solar/enquiry_list.html', {'enquiries': enquiries})

# ==========================================
# 9. OFFICE PORTAL RESTRUCTURE
# ==========================================

@staff_member_required
def office_fe_data(request):
    """View to list all Field Engineer data (Customer Surveys). Read-only viewing but with Edit option."""
    surveys = CustomerSurvey.objects.all().order_by('-created_at')
    return render(request, 'solar/office_fe_data.html', {'surveys': surveys})

@staff_member_required
def office_installer_data(request):
    """View to list all Installer data (Installations). Read-only viewing but with Edit option."""
    installations = Installation.objects.all().select_related('survey').order_by('-timestamp')
    return render(request, 'solar/office_installer_data.html', {'installations': installations})

@staff_member_required
def office_workers_profiles(request):
    """View to list all worker types: Admin, Field Engineers, Installers, Office, and Loan."""
    admins = User.objects.filter(userprofile__role='Admin', userprofile__is_approved=True)
    field_engineers = User.objects.filter(userprofile__role='Field Engineer', userprofile__is_approved=True)
    installers = User.objects.filter(userprofile__role='Installer', userprofile__is_approved=True)
    office_users = User.objects.filter(userprofile__role='Office', userprofile__is_approved=True)
    loan_users = User.objects.filter(userprofile__role='Loan', userprofile__is_approved=True)
    
    return render(request, 'solar/office_workers_profiles.html', {
        'admins': admins,
        'field_engineers': field_engineers,
        'installers': installers,
        'office_users': office_users,
        'loan_users': loan_users,
    })

@staff_member_required
def site_detail_fe_view(request, pk):
    """Restricted view: Shows only Field Engineer data (Survey) for Office Admin."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    context = {'customer': customer, 'view_mode': 'fe_only'}
    context.update(_get_site_media_context(customer))
    return render(request, 'solar/site_detail.html', context)

@staff_member_required
def site_detail_installer_view(request, pk):
    """Restricted view: Shows Merged Data (Survey + Installation) for Office Admin."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    try:
        installation = Installation.objects.get(survey=customer)
    except Installation.DoesNotExist:
        installation = None
        
    context = {
        'customer': customer, 
        'installation': installation, 
        'view_mode': 'installer_only'
    }
    context.update(_get_site_media_context(customer))
    return render(request, 'solar/site_detail.html', context)

@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'userprofile') and u.userprofile.role == 'Admin'))
def delete_worker(request, user_id):
    """Delete a worker user. Admin only."""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        worker_name = user.get_full_name() or user.username
        worker_role = user.userprofile.role if hasattr(user, 'userprofile') else 'User'
        
        # Delete the user (profile will cascade delete)
        user.delete()
        
        messages.success(request, f"{worker_role} '{worker_name}' has been deleted successfully.")
        return redirect('office_workers_profiles')
    
    # If not POST, redirect back
    return redirect('office_workers_profiles')

@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'userprofile') and u.userprofile.role == 'Admin'))
def set_worker_password(request, user_id):
    """Set/update a worker's password. Admin only. Updates both Django auth and plain_password."""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        new_password = request.POST.get('new_password', '').strip()
        if new_password:
            user.set_password(new_password)
            user.save()
            if hasattr(user, 'userprofile'):
                user.userprofile.plain_password = new_password
                user.userprofile.save(update_fields=['plain_password'])
            messages.success(request, f"Password updated for {user.get_full_name() or user.username}.")
        else:
            messages.error(request, "Password cannot be empty.")
    return redirect('office_workers_profiles')

@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'userprofile') and u.userprofile.role == 'Admin'))
def delete_application(request, survey_id):
    """Delete a customer application. Admin only. Cascades to Installation and BankDetails."""
    if request.method == 'POST':
        survey = get_object_or_404(CustomerSurvey, id=survey_id)
        customer_name = survey.customer_name
        sc_no = survey.sc_no
        
        # Delete the survey (Installation and BankDetails will cascade delete)
        survey.delete()
        
        messages.success(request, f"Application for '{customer_name}' (SC: {sc_no}) has been deleted successfully.")
        return redirect('admin_dashboard')
    
    # If not POST, redirect back
    return redirect('admin_dashboard')


@login_required
@user_passes_test(is_field_engineer)
def fe_update_survey(request, pk):
    """
    Restricted Edit View for Field Engineers.
    Allows editing specific Loan and Registration details.
    """
    survey = get_object_or_404(CustomerSurvey, pk=pk)
    bank_details, created = BankDetails.objects.get_or_create(survey=survey)

    if request.method == 'POST':
        form = FEUpdateForm(request.POST, instance=survey, bank_details=bank_details)
        if form.is_valid():
            # Save Survey Fields
            survey = form.save(commit=False)
            survey.save()
            
            # Save Bank Details Fields (manually handled)
            bank_details.loan_applied_bank = form.cleaned_data['loan_applied_bank']
            bank_details.loan_applied_ifsc = form.cleaned_data['loan_applied_ifsc']
            bank_details.loan_applied_ac_no = form.cleaned_data['loan_applied_ac_no']
            bank_details.save()
            
            messages.success(request, f"Details updated for {survey.customer_name}")
            return redirect('dashboard')
    else:
        form = FEUpdateForm(instance=survey, bank_details=bank_details)

    return render(request, 'solar/fe_update_form.html', {
        'form': form,
        'survey': survey,
    })

# ==========================================
# STORAGE MANAGEMENT
# ==========================================
@login_required
def manage_storage(request):
    """View for admins to see storage usage and delete old media."""
    # Allow superusers, staff, or users with Admin/Office role
    profile = getattr(request.user, 'userprofile', None)
    user_role = getattr(profile, 'role', '') if profile else ''
    if not (request.user.is_superuser or request.user.is_staff or user_role in ('Admin', 'Office')):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('You do not have permission to access this page.')

    try:
        # Build list of surveys that have at least one media file
        has_media = (
            (~Q(roof_photo='') & ~Q(roof_photo__isnull=True)) |
            (~Q(pan_card_photo='') & ~Q(pan_card_photo__isnull=True)) |
            (~Q(aadhar_photo='') & ~Q(aadhar_photo__isnull=True)) |
            (~Q(current_bill_photo='') & ~Q(current_bill_photo__isnull=True)) |
            (~Q(bank_account_photo='') & ~Q(bank_account_photo__isnull=True)) |
            (~Q(parent_bank_photo='') & ~Q(parent_bank_photo__isnull=True)) | # Keep this line for filtering
            (~Q(installation__inverter_serial_photo='') & ~Q(installation__inverter_serial_photo__isnull=True)) |
            (~Q(installation__inverter_acdb_photo='') & ~Q(installation__inverter_acdb_photo__isnull=True)) |
            (~Q(installation__panel_serial_photo='') & ~Q(installation__panel_serial_photo__isnull=True)) |
            (~Q(installation__site_photos_with_customer='') & ~Q(installation__site_photos_with_customer__isnull=True))
        )
        surveys_with_media = CustomerSurvey.objects.filter(has_media).distinct().order_by('created_at')
    except Exception:
        surveys_with_media = CustomerSurvey.objects.none()

    # Calculate overall stats — guard against missing media directory on server
    total_limit_bytes = 5 * 1024 * 1024 * 1024
    media_root = getattr(settings, 'MEDIA_ROOT', '')
    if media_root and os.path.isdir(media_root):
        used_storage_bytes = get_directory_size(media_root)
    else:
        used_storage_bytes = 0

    used_storage_gb = used_storage_bytes / (1024 * 1024 * 1024)
    remaining_storage_gb = max(0, 5.0 - used_storage_gb)
    storage_percentage = min(100, (used_storage_bytes / total_limit_bytes) * 100)

    paginator = Paginator(surveys_with_media, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'surveys': page_obj,
        'used_storage_gb': round(used_storage_gb, 2),
        'remaining_storage_gb': round(remaining_storage_gb, 2),
        'storage_percentage': round(storage_percentage, 1),
    }
    return render(request, 'solar/storage_management.html', context)

@login_required
def delete_survey_media(request, survey_id):
    """Deletes media files from OS and nulls fields to free space."""
    if request.method == 'POST':
        survey = get_object_or_404(CustomerSurvey, id=survey_id)
        
        # Helper to safely delete file
        def safe_delete_file(file_field):
            if file_field and hasattr(file_field, 'path') and os.path.isfile(file_field.path):
                try:
                    os.remove(file_field.path)
                except Exception as e:
                    print(f"Error deleting file: {e}")

        # Delete from filesystem
        safe_delete_file(survey.roof_photo)
        safe_delete_file(survey.pan_card_photo)
        safe_delete_file(survey.aadhar_photo)
        safe_delete_file(survey.current_bill_photo)
        safe_delete_file(survey.bank_account_photo)
        
        # Nullify DB fields
        survey.roof_photo = None
        survey.pan_card_photo = None
        survey.aadhar_photo = None
        survey.current_bill_photo = None
        survey.bank_account_photo = None
        survey.save()
        
        # Do the same for Installation if exists
        try:
            inst = survey.installation
            safe_delete_file(inst.inverter_serial_photo)
            safe_delete_file(inst.inverter_acdb_photo)
            safe_delete_file(inst.panel_serial_photo)
            safe_delete_file(inst.site_photos_with_customer)
            
            inst.inverter_serial_photo = None
            inst.inverter_acdb_photo = None
            inst.panel_serial_photo = None
            inst.site_photos_with_customer = None
            inst.save()
        except CustomerSurvey.installation.RelatedObjectDoesNotExist:
            pass
            
        messages.success(request, f"Media files successfully deleted for {survey.customer_name}. The project text data is preserved.")
        return redirect('manage_storage')
        
    return redirect('manage_storage')

@login_required
def delete_all_media(request):
    """Deletes media files for ALL projects to free space."""
    if request.method == 'POST':
        # Helper to safely delete file
        def safe_delete_file(file_field):
            if file_field and hasattr(file_field, 'path') and os.path.isfile(file_field.path):
                try:
                    os.remove(file_field.path)
                except Exception as e:
                    print(f"Error deleting file: {e}")

        has_media = (
            (~Q(roof_photo='') & ~Q(roof_photo__isnull=True)) |
            (~Q(pan_card_photo='') & ~Q(pan_card_photo__isnull=True)) |
            (~Q(aadhar_photo='') & ~Q(aadhar_photo__isnull=True)) |
            (~Q(current_bill_photo='') & ~Q(current_bill_photo__isnull=True)) |
            (~Q(bank_account_photo='') & ~Q(bank_account_photo__isnull=True)) |
            (~Q(parent_bank_photo='') & ~Q(parent_bank_photo__isnull=True)) | # Keep this line for filtering
            (~Q(installation__inverter_serial_photo='') & ~Q(installation__inverter_serial_photo__isnull=True)) |
            (~Q(installation__inverter_acdb_photo='') & ~Q(installation__inverter_acdb_photo__isnull=True)) |
            (~Q(installation__panel_serial_photo='') & ~Q(installation__panel_serial_photo__isnull=True)) |
            (~Q(installation__site_photos_with_customer='') & ~Q(installation__site_photos_with_customer__isnull=True))
        )
        surveys_with_media = CustomerSurvey.objects.filter(has_media)
        
        count = 0
        for survey in surveys_with_media:
            # Delete from filesystem
            safe_delete_file(survey.roof_photo)
            safe_delete_file(survey.pan_card_photo)
            safe_delete_file(survey.aadhar_photo)
            safe_delete_file(survey.current_bill_photo)
            safe_delete_file(survey.bank_account_photo)
            
            # Nullify DB fields
            survey.roof_photo = None
            survey.pan_card_photo = None
            survey.aadhar_photo = None
            survey.current_bill_photo = None
            survey.bank_account_photo = None
            survey.save()
            
            # Do the same for Installation if exists
            try:
                inst = survey.installation
                safe_delete_file(inst.inverter_serial_photo)
                safe_delete_file(inst.inverter_acdb_photo)
                safe_delete_file(inst.panel_serial_photo)
                safe_delete_file(inst.site_photos_with_customer)
                
                inst.inverter_serial_photo = None
                inst.inverter_acdb_photo = None
                inst.panel_serial_photo = None
                inst.site_photos_with_customer = None
                inst.save()
            except CustomerSurvey.installation.RelatedObjectDoesNotExist:
                pass
            count += 1
            
        messages.success(request, f"Successfully deleted media files for {count} projects.")
        return redirect('manage_storage')
        
    return redirect('manage_storage')


# ==========================================
# MAINTENANCE MODE TOGGLE
# ==========================================
@staff_member_required
def toggle_maintenance_mode(request):
    if request.method == 'POST':
        settings_obj = SiteSettings.get_settings()
        settings_obj.maintenance_mode = not settings_obj.maintenance_mode
        settings_obj.save()
        status = "enabled" if settings_obj.maintenance_mode else "disabled"
        messages.success(request, f"Maintenance mode {status}.")
    return redirect('admin_dashboard')


# ==========================================
# INSTALLATION MANAGEMENT (ADMIN ONLY)
# ==========================================

@staff_member_required
def reset_installation(request, installation_id):
    """
    Deletes an installation record so the survey becomes 'Pending' again for installers.
    """
    installation = Installation.objects.filter(id=installation_id).first()
    
    if not installation:
        messages.warning(request, "This installation report has already been reset or does not exist.")
        # If we don't have the installation, we can't easily find the survey ID from it.
        # But this view is usually called from site_detail or installation_form which has the survey ID.
        return redirect('admin_dashboard')

    survey_id = installation.survey.id
    if request.method == 'POST':
        # Safely delete files before deleting the record
        def safe_delete_file(file_field):
            if file_field and hasattr(file_field, 'path') and os.path.exists(file_field.path):
                try:
                    os.remove(file_field.path)
                except:
                    pass

        safe_delete_file(installation.inverter_serial_photo)
        safe_delete_file(installation.inverter_acdb_photo)
        safe_delete_file(installation.panel_serial_photo)
        safe_delete_file(installation.site_photos_with_customer)
        
        # Delete related additional photos
        for photo in installation.additional_photos.all():
            safe_delete_file(photo.photo)
            photo.delete()

        installation.delete()
        messages.success(request, "Installation report reset successfully. It is now pending for the installer again.")
        return redirect('site_detail', pk=survey_id)
    
    return redirect('site_detail', pk=survey_id)

@staff_member_required
def delete_additional_photo(request, photo_id):
    """
    Deletes a specific InstallationPhoto instance.
    """
    photo = get_object_or_404(InstallationPhoto, id=photo_id)
    survey_id = photo.installation.survey.id
    if request.method == 'POST':
        if photo.photo and os.path.exists(photo.photo.path):
            try:
                os.remove(photo.photo.path)
            except:
                pass
        photo.delete()
        messages.success(request, "Additional photo deleted.")
    return redirect('site_detail', pk=survey_id)

@staff_member_required
def clear_installation_field(request, installation_id, field_name):
    """
    Clears a specific ImageField in the Installation model.
    """
    installation = get_object_or_404(Installation, id=installation_id)
    if request.method == 'POST':
        if hasattr(installation, field_name):
            file_field = getattr(installation, field_name)
            if file_field and hasattr(file_field, 'path') and os.path.exists(file_field.path):
                try:
                    os.remove(file_field.path)
                except:
                    pass
            setattr(installation, field_name, None)
            installation.save()
            messages.success(request, f"Image field '{field_name}' cleared.")
    return redirect('site_detail', pk=installation.survey.id)

# ==========================================
# STATIC PAGES
# ==========================================

def terms_and_conditions(request):
    return render(request, 'solar/terms_and_conditions.html')

def privacy_policy(request):
    return render(request, 'solar/privacy_policy.html')

from django.contrib.auth import logout as auth_logout

def custom_logout(request):
    """
    Custom logout view that handles GET requests gracefully.
    In Django 5+, the built-in LogoutView requires a POST request to log out,
    and a GET request defaults to showing the admin 'logged out' confirmation page.
    This view instead immediately logs out the user on a GET request and redirects to login,
    fixing the glitch where users are redirected to the admin login screen.
    """
    auth_logout(request)
    return redirect('login')