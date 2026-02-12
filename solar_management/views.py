import csv
import re
import sys
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, User

from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
from .forms import SurveyForm, InstallationForm, BankDetailsForm, SignUpForm, LoginForm, EnquiryForm, OfficeStatusForm
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
        
    messages.success(request, f"User {profile.user.get_full_name()} approved.")
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
    return user.groups.filter(name='Office_Staff').exists()

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
    elif user.is_staff: 
        # Superusers/Staff go to Admin Dashboard (Pending approvals + Master Lists)
        return redirect('admin_dashboard') # Reuse existing view logic but expand it
    
    return redirect('login')

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
def admin_dashboard(request):
    """
    Admin Dashboard: 3 Sections
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
            models.Q(phone_number__icontains=query) | 
            models.Q(customer_name__icontains=query) |
            models.Q(sc_no__icontains=query)
        ).select_related('installation').order_by('-created_at')
    else:
        surveys = CustomerSurvey.objects.all().select_related('installation').order_by('-created_at')
        
    return render(request, 'solar/office_dashboard.html', {'surveys': surveys, 'query': query})

@login_required
@user_passes_test(is_office_staff)
def office_update_status(request, pk):
    """View for Office Staff to update project status."""
    survey = get_object_or_404(CustomerSurvey, pk=pk)
    
    if request.method == 'POST':
        form = OfficeStatusForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.success(request, f"Status updated for {survey.customer_name}.")
            return redirect('office_dashboard')
    else:
        form = OfficeStatusForm(instance=survey)
    
    return render(request, 'solar/office_status_form.html', {'form': form, 'survey': survey})

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
    """View to list Field Engineers and Installers separately."""
    field_engineers = User.objects.filter(groups__name='Field_Engineers')
    installers = User.objects.filter(groups__name='Installers')
    return render(request, 'solar/office_workers_profiles.html', {
        'field_engineers': field_engineers,
        'installers': installers
    })

@staff_member_required
def site_detail_fe_view(request, pk):
    """Restricted view: Shows only Field Engineer data (Survey) for Office Admin."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    return render(request, 'solar/site_detail.html', {'customer': customer, 'view_mode': 'fe_only'})

@staff_member_required
def site_detail_installer_view(request, pk):
    """Restricted view: Shows only Installer data (Installation) for Office Admin."""
    customer = get_object_or_404(CustomerSurvey, pk=pk)
    return render(request, 'solar/site_detail.html', {'customer': customer, 'view_mode': 'installer_only'})