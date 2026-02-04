from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
import re
class SurveyForm(forms.ModelForm):
    is_critical_site = forms.BooleanField(required=False, label="Is Critical Site?", help_text="Check if roof photo is mandatory")

    class Meta:
        model = CustomerSurvey
        exclude = ['created_by', 'created_at']

    def clean_sc_no(self):
        sc_no = self.cleaned_data.get('sc_no')
        if not re.match(r'^\d{16}$', str(sc_no)):
            raise ValidationError("SC Number must be exactly 16 digits.")
        return sc_no

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if not re.match(r'^\d{10}$', str(phone)):
            raise ValidationError("Phone number must be exactly 10 digits.")
        return phone
        
    def clean_aadhar_linked_phone(self):
        phone = self.cleaned_data.get('aadhar_linked_phone')
        if not re.match(r'^\d{10}$', str(phone)):
            raise ValidationError("Aadhar Linked Phone number must be exactly 10 digits.")
        return phone

    def clean_aadhar_no(self):
        aadhar = self.cleaned_data.get('aadhar_no')
        if not re.match(r'^\d{12}$', str(aadhar)):
            raise ValidationError("Aadhar Number must be exactly 12 digits.")
        return aadhar

    def clean_pan_card(self):
        pan = self.cleaned_data.get('pan_card')
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', str(pan)):
            raise ValidationError("Invalid PAN Card format (e.g., ABCDE1234F).")
        return pan
    
    def clean(self):
        cleaned_data = super().clean()
        mefma = cleaned_data.get('mefma_status')
        rp_name = cleaned_data.get('rp_name')
        rp_phone = cleaned_data.get('rp_phone_number')
        
        is_critical = cleaned_data.get('is_critical_site')
        roof_photo = cleaned_data.get('roof_photo')

        if mefma:
            if not rp_name:
                self.add_error('rp_name', "RP Name is required if MEFMA is Yes.")
            if not rp_phone:
                self.add_error('rp_phone_number', "RP Phone is required if MEFMA is Yes.")
                
        if is_critical and not roof_photo:
            # Only add specific error if there isn't one already (e.g. invalid image)
            if not self.has_error('roof_photo'):
                self.add_error('roof_photo', "Roof Photo is required for critical sites.")
            
        return cleaned_data

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
        fields = '__all__'
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
    mobile_number = forms.CharField(max_length=15, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ['name', 'mobile_number', 'email', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }