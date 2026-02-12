from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
import re
class SurveyForm(forms.ModelForm):
    is_critical_site = forms.BooleanField(required=False, label="Is Critical Site?", help_text="Check if roof photo is mandatory")

    class Meta:
        model = CustomerSurvey
        model = CustomerSurvey
        fields = [
            'customer_name', 'connection_type', 'sc_no', 'phase', 'feasibility_kw',
            'aadhar_no', 'pan_card', 'email', 'phone_number', 'aadhar_linked_phone', 
            # 'bank_account_no',  <-- Removed as per BankDetails integration
            'area', 'gps_coordinates', 'roof_type', 'roof_photo', 'structure_type',
            'structure_height', 'agreed_amount', 'advance_paid', 
            'mefma_status', 'rp_name', 'rp_phone_number', 
            'fe_remarks', 'reference_name', 
            'pms_registration_number', 'division',
             # 'registration_status' excluded as per previous fix
        ]
        widgets = {
             'gps_coordinates': forms.TextInput(attrs={'placeholder': 'Latitude, Longitude'}),
        }
# ... (Validation methods remain same) ...

class InstallationForm(forms.ModelForm):
    class Meta:
        model = Installation
        exclude = ['survey', 'updated_by', 'created_at']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # survey field is excluded, so we don't need to configure it here

class BankDetailsForm(forms.ModelForm):
    class Meta:
        model = BankDetails
        exclude = ['survey'] 
        widgets = {
            'first_loan_date': forms.DateInput(attrs={'type': 'date'}),
            'second_loan_date': forms.DateInput(attrs={'type': 'date'}),
        }

class SignUpForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    mobile_number = forms.CharField(max_length=15, required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_mobile_number(self):
        mobile = self.cleaned_data.get('mobile_number')
        if UserProfile.objects.filter(mobile_number=mobile).exists():
            raise forms.ValidationError("This mobile number is already registered.")
        return mobile

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

class LoginForm(forms.Form):
    LOGIN_TYPE_CHOICES = [
        ('', 'Select Login Type'),
        ('field_engineer', 'Field Engineer'),
        ('installer', 'Installer'),
        ('office', 'Office'),
        ('admin', 'Admin'),
    ]
    login_type = forms.ChoiceField(
        choices=LOGIN_TYPE_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'style': 'cursor: pointer;'})
    )
    mobile_number = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=True)

class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ['name', 'mobile_number', 'email', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }