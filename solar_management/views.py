import csv
import re
import sys
from datetime import datetime
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User

from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
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
         if request.user.is_staff:
             return redirect('office_dashboard')
         try:
             # Try to find profile role
            profile = request.user.userprofile
            if 'Field Engineer' in profile.role:
                return redirect('dashboard')
            elif 'Installer' in profile.role:
                return redirect('dashboard')
            elif 'Office' in profile.role:
                return redirect('office_dashboard')
         except:
             pass 
         
         if request.user.is_staff: # Admin/Superuser
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
        form = SignUpForm(request.POST)
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
            UserProfile.objects.create(
                user=user,
                mobile_number=form.cleaned_data['mobile_number'],
                role=form.cleaned_data['role'],
                is_approved=False
            )

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
        
    messages.success(request, f"User {profile.user.get_full_name()} approved.")
    return redirect('admin_dashboard')

@staff_member_required
def reject_user(request, pk):
    """Admin-only: Reject and delete user request."""
    profile = get_object_or_404(UserProfile, pk=pk)
    user = profile.user
    name = user.get_full_name() or user.username
    user.delete() # Cascade deletes profile
    messages.error(request, f"User request for {name} has been rejected and removed.")
    return redirect('admin_dashboard')

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
            Q(phone_number__icontains=query) |
            Q(sc_no__icontains=query)
        )[:5]
        for s in surveys:
            results.append({
                'title': s.customer_name,
                'subtitle': f"Phone: {s.phone_number} | SC: {s.sc_no}",
                'url': f"/site/{s.id}/",
                'type': 'Application'
            })

    # 2. Installer (FE Data + Installer Data)
    elif is_installer(request.user):
        surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(phone_number__icontains=query) |
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
            Q(phone_number__icontains=query) |
            Q(sc_no__icontains=query)
        )[:5]
        for s in surveys:
            results.append({
                'title': s.customer_name,
                'subtitle': f"Phone: {s.phone_number} | Status: {s.workflow_status}",
                'url': f"/office/update-status/{s.id}/",
                'type': 'Project'
            })

    # 4. Loan Officer (All Surveys)
    elif is_loan_officer(request.user):
        surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(aadhar_linked_phone__icontains=query) |
            Q(sc_no__icontains=query)
        )[:5]
        for s in surveys:
            phone = s.phone_number if s.phone_number else s.aadhar_linked_phone
            results.append({
                'title': s.customer_name,
                'subtitle': f"Phone: {phone} | Status: {s.workflow_status}",
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
            Q(phone_number__icontains=query)
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
                    'subtitle': f"Engineer: {s.created_by.get_full_name()} | Phone: {s.phone_number}",
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
        Q(phone_number__icontains=phone) | 
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
            Q(phone_number__icontains=query) |
            Q(sc_no__icontains=query)
        ).order_by('-created_at')
    else:
        my_surveys = CustomerSurvey.objects.filter(created_by=request.user).order_by('-created_at')
    
    return render(request, 'solar/fe_dashboard.html', {'surveys': my_surveys, 'query': query})


@login_required
@user_passes_test(is_installer)
def installer_dashboard(request):
    """Installer: View basic details of all surveys (uploaded by FE)."""
    # Spec: "installer can see the basic details in the table which was entered from the form(which the field engineer uploaded)"
    query = request.GET.get('q', '')
    if query:
        all_surveys = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(phone_number__icontains=query) |
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
            
    return render(request, 'solar/installer_dashboard.html', {
        'pending_installations': pending_installations,
        'completed_installations': completed_installations,
        'query': query
    })

@staff_member_required
def admin_dashboard(request):
    """
    Admin Dashboard: 5 Sections
    1. Account Confirmation (Pending Users)
    2. Field Engineer Data (Master List)
    3. Installer Data (Master List)
    4. Office Data (Recent Office Updates)
    5. Loan Data (Recent Loan Applications)
    """
    query = request.GET.get('q', '')

    if query:
        # 1. Pending Approvals
        pending_users = UserProfile.objects.filter(is_approved=False).filter(
            Q(user__username__icontains=query) |
            Q(mobile_number__icontains=query)
        )
        
        # 2. FE Data (All Surveys)
        fe_data = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(phone_number__icontains=query)
        ).select_related('created_by').order_by('-created_at')
        
        # 3. Installer Data (All Installations)
        installer_data = Installation.objects.filter(
            Q(survey__customer_name__icontains=query) |
            Q(survey__phone_number__icontains=query)
        ).select_related('survey', 'updated_by').order_by('-timestamp')
        
        # 4. Office Data (Surveys with Status Tracking)
        office_data = CustomerSurvey.objects.filter(
            Q(customer_name__icontains=query) |
            Q(phone_number__icontains=query)
        ).exclude(workflow_status='Pending').order_by('-created_at')[:5]
        
        # 5. Loan Data (Bank Details)
        loan_data = BankDetails.objects.filter(
            Q(survey__customer_name__icontains=query) |
            Q(survey__phone_number__icontains=query)
        ).select_related('survey').order_by('-id')[:5]
    else:
        # 1. Pending Approvals
        pending_users = UserProfile.objects.filter(is_approved=False)
        
        # 2. FE Data (All Surveys)
        fe_data = CustomerSurvey.objects.all().select_related('created_by').order_by('-created_at')
        
        # 3. Installer Data (All Installations)
        installer_data = Installation.objects.all().select_related('survey', 'updated_by').order_by('-timestamp')
        
        # 4. Office Data (Recent 5 with status updates)
        office_data = CustomerSurvey.objects.exclude(workflow_status='Pending').order_by('-created_at')[:5]
        
        # 5. Loan Data (Recent 5 loan applications)
        loan_data = BankDetails.objects.all().select_related('survey').order_by('-id')[:5]
    
    context = {
        'pending_users': pending_users,
        'fe_data': fe_data,
        'installer_data': installer_data,
        'office_data': office_data,
        'loan_data': loan_data,
        'query': query,
    }
    return render(request, 'solar/admin_dashboard.html', context)


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
            Q(phone_number__icontains=query) | 
            Q(customer_name__icontains=query) |
            Q(sc_no__icontains=query)
        ).select_related('installation').order_by('-created_at')
    else:
        surveys = CustomerSurvey.objects.all().select_related('installation').order_by('-created_at')
        
    return render(request, 'solar/office_dashboard.html', {'surveys': surveys, 'query': query})

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
                Q(phone_number__icontains=query) | 
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
            bank_details = bank_form.save(commit=False)
            bank_details.survey = survey
            bank_details.loan_pending_status = 'Pending' # Default
            bank_details.save()

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
                    messages.success(request, f"Installation submitted successfully for {survey.customer_name}!")
                    return redirect('dashboard')
                else:
                    # Form has validation errors - add message
                    messages.error(request, "Please correct the errors below and try again.")
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
    surveys = CustomerSurvey.objects.filter(phone_number=phone).order_by('-created_at')
    
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
            'phone_number': survey.phone_number or '',
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
            'phone_number': survey.phone_number or '',
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
            inst.survey = survey
            inst.updated_by = request.user
            inst.save()
            messages.success(request, f"Installation data updated for {survey.customer_name}.")
            return redirect('dashboard')
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
@login_required
def site_detail(request, pk):
    """Technical deep-dive and photo gallery for specific sites."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    return render(request, 'solar/site_detail.html', {'customer': customer})

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
@staff_member_required
@login_required
@staff_member_required
def export_solar_data(request):
    """
    Export data to CSV based on report type.
    Types: master (default), field_engineer, installer, enquiries, users.
    """
    report_type = request.GET.get('type', 'master')
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="WeSolar_{report_type.title()}_Report_{timestamp}.csv"'
    writer = csv.writer(response)

    # 1. FIELD ENGINEER REPORT
    if report_type == 'field_engineer':
        writer.writerow([
            'Customer Name', 'SC No', 'Phone', 'Connection', 'Phase', 
            'Roof Type', 'Structure', 'Height', 'Area', 'Lat/Long',
            'Agreed Amount', 'Advance', 'Feasibility KW', 'Engineer', 'Date'
        ])
        surveys = CustomerSurvey.objects.all().select_related('created_by').order_by('-created_at')
        for s in surveys:
            writer.writerow([
                s.customer_name, s.sc_no, s.phone_number, s.connection_type, s.phase,
                s.roof_type, s.structure_type, s.structure_height, s.area, s.gps_coordinates,
                s.agreed_amount, s.advance_paid, s.feasibility_kw, 
                s.created_by.get_full_name() if s.created_by else 'Unknown',
                s.created_at.strftime("%Y-%m-%d")
            ])

    # 2. INSTALLER REPORT
    elif report_type == 'installer':
        writer.writerow([
            'Customer Name', 'SC No', 'Phone', 'Installer', 'Install Date',
            'Inverter Make', 'Inverter Phase', 'AC Cable (m)', 'DC Cable (m)', 
            'LA Cable (m)', 'Pipes (m)', 'DC Volt', 'AC Volt', 'Earth Res', 'Status'
        ])
        installations = Installation.objects.all().select_related('survey', 'updated_by').order_by('-timestamp')
        for i in installations:
            writer.writerow([
                i.survey.customer_name, i.survey.sc_no, i.survey.phone_number,
                i.updated_by.get_full_name() if i.updated_by else 'Unknown',
                i.timestamp.strftime("%Y-%m-%d"),
                i.inverter_make, i.inverter_phase, i.ac_cable_used, i.dc_cable_used,
                i.la_cable_used, i.pipes_used, i.dc_voltage, i.ac_voltage, 
                i.earthing_resistance, 
                'Completed' if i.survey.workflow_status == 'Completed' else 'In Progress'
            ])

    # 3. ENQUIRIES REPORT
    elif report_type == 'enquiries':
        writer.writerow(['Name', 'Mobile', 'Email', 'Address', 'Date Received'])
        enquiries = Enquiry.objects.all().order_by('-created_at')
        for e in enquiries:
            writer.writerow([
                e.name, e.mobile_number, e.email, e.address, 
                e.created_at.strftime("%Y-%m-%d %H:%M")
            ])

    # 4. USERS REPORT
    elif report_type == 'users':
        writer.writerow(['Username', 'Full Name', 'Mobile', 'Email', 'Role', 'Status', 'Date Joined'])
        profiles = UserProfile.objects.all().select_related('user').order_by('-user__date_joined')
        for p in profiles:
            writer.writerow([
                p.user.username, p.user.get_full_name(), p.mobile_number, p.user.email,
                p.role, 'Approved' if p.is_approved else 'Pending',
                p.user.date_joined.strftime("%Y-%m-%d")
            ])

    # 5. MASTER REPORT (Default)
    else:
        writer.writerow([
            'Customer Name', 'SC No', 'Phone', 'Phase', 'Roof Type', 
            'Status', 'Inverter', 'AC Cable', 'Bank', 'UTR', 'Loan Status'
        ])
        projects = CustomerSurvey.objects.all().select_related('installation', 'bank_details')
        for p in projects:
            has_i = hasattr(p, 'installation')
            has_b = hasattr(p, 'bank_details')
            writer.writerow([
                p.customer_name, p.sc_no, p.phone_number, p.phase, p.roof_type,
                p.workflow_status,
                p.installation.inverter_make if has_i else 'N/A',
                p.installation.ac_cable_used if has_i else '0',
                p.bank_details.loan_applied_bank if has_b else 'N/A',
                p.bank_details.first_loan_utr if has_b else 'N/A',
                p.bank_details.loan_pending_status if has_b else 'N/A'
            ])

    return response

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
    
    customer = CustomerSurvey.objects.filter(phone_number=clean_phone).first()
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
    return redirect('login')

@login_required
def enquiry_list(request):
    """View to list all enquiries. Read-only for most, manageable by Admin."""
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
    """View to list all worker types: Field Engineers, Installers, Office, and Loan."""
    field_engineers = User.objects.filter(userprofile__role='Field Engineer', userprofile__is_approved=True)
    installers = User.objects.filter(userprofile__role='Installer', userprofile__is_approved=True)
    office_users = User.objects.filter(userprofile__role='Office', userprofile__is_approved=True)
    loan_users = User.objects.filter(userprofile__role='Loan', userprofile__is_approved=True)
    
    return render(request, 'solar/office_workers_profiles.html', {
        'field_engineers': field_engineers,
        'installers': installers,
        'office_users': office_users,
        'loan_users': loan_users,
    })

@staff_member_required
def site_detail_fe_view(request, pk):
    """Restricted view: Shows only Field Engineer data (Survey) for Office Admin."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    return render(request, 'solar/site_detail.html', {'customer': customer, 'view_mode': 'fe_only'})

@staff_member_required
def site_detail_installer_view(request, pk):
    """Restricted view: Shows Merged Data (Survey + Installation) for Office Admin."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    try:
        installation = Installation.objects.get(survey=customer)
    except Installation.DoesNotExist:
        installation = None
    return render(request, 'solar/site_detail.html', {'customer': customer, 'installation': installation, 'view_mode': 'merged'})

@user_passes_test(lambda u: hasattr(u, 'userprofile') and u.userprofile.role == 'Admin')
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

@user_passes_test(lambda u: hasattr(u, 'userprofile') and u.userprofile.role == 'Admin')
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

    return render(request, 'solar/fe_update_form.html', {'form': form, 'survey': survey})