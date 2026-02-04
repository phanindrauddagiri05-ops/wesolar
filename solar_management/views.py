import csv
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User

from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
from .forms import SurveyForm, InstallationForm, BankDetailsForm, SignUpForm, LoginForm, EnquiryForm

# ==========================================
# 0. AUTHENTICATION & LANDING
# ==========================================

def landing_page(request):
    """Landing page with 3 options: Field Engineer, Installer, Office."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'solar/landing.html')

def custom_login_view(request):
    # Get role from query params to customize UI (Hoisted for scope availability)
    role = request.GET.get('role', 'User')
    role_name = role.replace('_', ' ').title()

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data['mobile_number']
            password = form.cleaned_data['password']
            
            profile = None # Initialize to avoid UnboundLocalError
            
            # 1. Try to look up profile first (Standard Flow)
            try:
                profile = UserProfile.objects.get(mobile_number=mobile)
            except UserProfile.DoesNotExist:
                profile = None

            user = None
            if profile:
                # If profile exists, authenticate using linked user
                user = authenticate(username=profile.user.username, password=password)

            # 2. If no user found via Profile, try direct auth (Superusers/Staff bypass)
            if not user:
                 user = authenticate(username=mobile, password=password)

            if user:
                 # 1. Admin/Staff Bypass (Always Allowed if on Office/Generic login)
                if user.is_staff:
                    if role == 'office' or role == 'User':
                        login(request, user)
                        return redirect('office_dashboard')
                    else:
                         messages.error(request, "Admins should use the Office Login.")
                         return render(request, 'solar/login.html', {'form': form, 'role_name': role_name, 'role_slug': role})

                # 2. Standard User Check (Requires Profile)
                if not profile:
                     messages.error(request, "User Profile not found.")
                else:
                    # Strict Role Check
                    user_role = profile.role
                    role_map = {
                        'field_engineer': 'Field Engineer',
                        'installer': 'Installer',
                        'office': 'Office'
                    }

                    if role in role_map:
                        expected_role = role_map[role]
                        if user_role != expected_role:
                            messages.error(request, f"Access Denied: This form is strictly for {expected_role}s.")
                            return render(request, 'solar/login.html', {'form': form, 'role_name': role_name, 'role_slug': role})

                    if profile.is_approved:
                        login(request, user)
                        return redirect('dashboard')
                    else:
                        messages.error(request, "Your account is pending admin verification.")
            else:
                messages.error(request, "Invalid credentials.")
    else:
        form = LoginForm()
    
    return render(request, 'solar/login.html', {'form': form, 'role_name': role_name, 'role_slug': role})

def office_login_view(request):
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
                return redirect('office_dashboard')

            # 3. If not, try looking up via UserProfile (for regular Office staff)
            try:
                profile = UserProfile.objects.select_related('user').get(mobile_number=mobile)
                user = authenticate(username=profile.user.username, password=password)
            except UserProfile.DoesNotExist:
                pass
                
            if user:
                # STRICT Office Check
                if user.is_staff or (profile and profile.role == 'Office'):
                        login(request, user)
                        return redirect('office_dashboard')
                else:
                        messages.error(request, "Access Denied: This portal is for Office Staff only.")
            else:
                messages.error(request, "Invalid credentials.")
    else:
        form = LoginForm()
        
    return render(request, 'solar/office_login.html', {'form': form})
    
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
        
    messages.success(request, f"User {profile.user.get_full_name()} approved.")
    return redirect('office_dashboard')

def logout_view(request):
    logout(request)
    return redirect('landing')

# ==========================================
# 0. ROLE CHECK HELPERS (Existing)
# ==========================================
def is_field_engineer(user):
    return user.groups.filter(name='Field_Engineers').exists() or user.is_staff

def is_installer(user):
    return user.groups.filter(name='Installers').exists() or user.is_staff

def is_bank_user(user):
    return user.groups.filter(name='Bank_Users').exists() or user.is_staff

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
    elif user.is_staff: 
        # Superusers/Staff go to Office Dashboard (Pending approvals + Master Lists)
        return redirect('office_dashboard') # Reuse existing view logic but expand it
    
    return render(request, 'solar/landing.html')

@login_required
@user_passes_test(is_field_engineer)
def fe_dashboard(request):
    """Field Engineer: Only own records."""
    my_surveys = CustomerSurvey.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'solar/fe_dashboard.html', {'surveys': my_surveys})

@login_required
@user_passes_test(is_installer)
def installer_dashboard(request):
    """Installer: View basic details of all surveys (uploaded by FE)."""
    # Spec: "installer can see the basic details in the table which was entered from the form(which the field engineer uploaded)"
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
        'completed_installations': completed_installations
    })

@staff_member_required
def office_dashboard(request):
    """
    Office/Admin Dashboard: 3 Sections
    1. Account Confirmation (Pending Users)
    2. Field Engineer Data (Master List)
    3. Installer Data (Master List)
    """
    # 1. Pending Approvals
    pending_users = UserProfile.objects.filter(is_approved=False)
    
    # 2. FE Data (All Surveys)
    fe_data = CustomerSurvey.objects.all().select_related('created_by').order_by('-created_at')
    
    # 3. Installer Data (All Installations)
    installer_data = Installation.objects.all().select_related('survey', 'updated_by').order_by('-timestamp')
    
    context = {
        'pending_users': pending_users,
        'fe_data': fe_data,
        'installer_data': installer_data,
    }
    return render(request, 'solar/office_dashboard.html', context)

@login_required
@user_passes_test(is_field_engineer)
def create_survey(request):
    """Initial data entry for Field Engineers with role restriction."""
    if request.method == "POST":
        form = SurveyForm(request.POST, request.FILES)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.created_by = request.user
            survey.save()
            messages.success(request, f"Project for {survey.customer_name} created.")
            return redirect('dashboard')
    else:
        form = SurveyForm()
    return render(request, 'solar/survey_form.html', {'form': form})

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
        
    if request.method == "POST":
        form = SurveyForm(request.POST, request.FILES, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, "Survey details updated.")
            return redirect('site_detail', pk=pk)
    else:
        form = SurveyForm(instance=survey)
    
    return render(request, 'solar/survey_form.html', {'form': form, 'is_update': True})

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
def export_solar_data(request):
    """Export master tracker to CSV - restricted to staff."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="WeSolar_Master_Report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Customer Name', 'SC No', 'Phone', 'Phase', 'Roof Type', 
        'Status', 'Inverter', 'AC Cable', 'Bank', 'UTR'
    ])

    projects = CustomerSurvey.objects.all().select_related('installation', 'bank_details')
    for p in projects:
        has_i = hasattr(p, 'installation')
        has_b = hasattr(p, 'bank_details')
        writer.writerow([
            p.customer_name, p.sc_no, p.phone_number, p.phase, p.roof_type,
            'Registered' if p.registration_status else 'Pending',
            p.installation.inverter_make if has_i else 'N/A',
            p.installation.ac_cable_used if has_i else '0',
            p.bank_details.loan_applied_bank if has_b else 'N/A',
            p.bank_details.first_loan_utr if has_b else 'N/A',
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
            return redirect('landing')
        else:
            messages.error(request, "Please correct the errors in the enquiry form.")
    return redirect('landing')

@login_required
def enquiry_list(request):
    """View to list all enquiries. Read-only for most, manageable by Admin."""
    enquiries = Enquiry.objects.all().order_by('-created_at')
    return render(request, 'solar/enquiry_list.html', {'enquiries': enquiries})