from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
import re
class SurveyForm(forms.ModelForm):
    is_critical_site = forms.BooleanField(required=False, label="Is Critical Site?", help_text="Check if roof photo is mandatory")

    class Meta:
        model = CustomerSurvey
        fields = [
            'customer_name', 'connection_type', 'sc_no', 'phase', 'contracted_load', 'feasibility_kw',
            'aadhar_no', 'pan_card', 'email', 'phone_number', 'aadhar_linked_phone', 
            # 'phone_number' re-enabled for FE as Primary Contact
            'area', 'gps_coordinates', 'roof_type', 'roof_photo', 'structure_type',
            'structure_height', 'agreed_amount', 'advance_paid', 
            'mefma_status', 'rp_name', 'rp_phone_number', 
            'fe_remarks', 'reference_name', 
            'pms_registration_number', 'division',
            # Post-Installation Fields (Mandatory/Optional per user request)
            'installation_date', 'workflow_status', 
            'discom_status', 'net_metering_status', 'subsidy_status',
             # 'registration_status' excluded as it is "Editable after submission" (Admin/Office)
        ]
        labels = {
            'sc_no': 'Service Connection Number (16 Digits)',
            'contracted_load': 'Contracted Load (KW)',
            'feasibility_kw': 'Applied Solar Load (KW)',
            'aadhar_no': 'Aadhar Card (12 Digits)',
            'pan_card': 'Pan Card (10 Digits)',
            'email': 'Email-id',
            'phone_number': 'Primary Phone Number (10 Digits)',
            'aadhar_linked_phone': 'Aadhar Linked Phone Number (10 Digits)',
            'gps_coordinates': 'GPS Coordinates',
            'roof_photo': 'Roof Photo (Optional/Mandatory if Critical)',
            'mefma_status': 'Mefma (Yes/No)',
            'rp_name': 'RP Name',
            'rp_phone_number': 'Phone Number (RP)',
            'reference_name': 'Reference Name',
            'pms_registration_number': 'PM Surya Ghar National Portal Reg. No.',
            'division': 'Division',
            'fe_remarks': 'Remarks',
            'installation_date': 'Installation Completed Date',
            'workflow_status': 'Installation Status',
            'discom_status': 'Discom Status',
            'net_metering_status': 'Net Metering',
            'subsidy_status': 'Subsidy',
        }
        widgets = {
             'gps_coordinates': forms.TextInput(attrs={'placeholder': 'Latitude, Longitude', 'readonly': 'readonly'}),
             'mefma_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
             'installation_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_sc_no(self):
        sc_no = self.cleaned_data.get('sc_no')
        if not re.match(r'^\d{16}$', sc_no):
            raise ValidationError("Service Connection Number must be exactly 16 digits.")
        return sc_no

    def clean_aadhar_no(self):
        aadhar = self.cleaned_data.get('aadhar_no')
        if not re.match(r'^\d{12}$', aadhar):
            raise ValidationError("Aadhar Number must be exactly 12 digits.")
        return aadhar

    def clean_pan_card(self):
        pan = self.cleaned_data.get('pan_card')
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
            raise ValidationError("Invalid PAN Card format (e.g., ABCDE1234F).")
        return pan

    def clean_rp_phone_number(self):
         phone = self.cleaned_data.get('rp_phone_number')
         if phone and not re.match(r'^\d{10}$', phone):
             raise ValidationError("RP Phone Number must be exactly 10 digits.")
         return phone

    def clean(self):
        cleaned_data = super().clean()
        is_critical = cleaned_data.get('is_critical_site')
        roof_photo = cleaned_data.get('roof_photo')
        mefma_status = cleaned_data.get('mefma_status')
        rp_name = cleaned_data.get('rp_name')
        rp_phone = cleaned_data.get('rp_phone_number')
        reference_name = cleaned_data.get('reference_name')

        if is_critical and not roof_photo:
            if not (self.instance.pk and self.instance.roof_photo):
                 self.add_error('roof_photo', "Roof photo is mandatory for critical sites.")
        
        if mefma_status:
            if not rp_name:
                self.add_error('rp_name', "RP Name is mandatory if MEFMA is Yes.")
            if not rp_phone:
                self.add_error('rp_phone_number', "RP Phone Number is mandatory if MEFMA is Yes.")
        else:
            if not reference_name:
                self.add_error('reference_name', "Reference Name is mandatory if MEFMA is No.")
        
        return cleaned_data


class InstallationForm(forms.ModelForm):
    class Meta:
        model = Installation
        fields = [
            'inverter_make',
            'inverter_serial_photo',
            'inverter_phase',
            'inverter_acdb_photo',
            'panel_serial_photo',
            'warranty_claimed',
            'app_installation_status',
            'site_photos_with_customer',
            'ac_cable_used',
            'dc_cable_used',
            'la_cable_used',
            'pipes_used',
            'leftover_materials',
            'installer_remarks',
            'customer_remarks',
            'dc_voltage',
            'ac_voltage',
            'earthing_resistance',
            'customer_rating',
        ]
        labels = {
            'inverter_make': 'Inverter Make',
            'inverter_serial_photo': 'Inverter Serial Number (Photo)',
            'inverter_phase': 'Inverter Phase (Single/Three)',
            'inverter_acdb_photo': 'Inverter Photo (with ACDB & DCDB)',
            'panel_serial_photo': 'Panel Serial Numbers Photo',
            'warranty_claimed': 'Warranty Claimed Status',
            'app_installation_status': 'App Installation Status',
            'site_photos_with_customer': 'Site Photos with Customer',
            'ac_cable_used': 'Used AC Cable length (Mtrs)',
            'dc_cable_used': 'Used DC Cable length (Mtrs)',
            'la_cable_used': 'Used LA Cable length (Mtrs)',
            'pipes_used': 'Used Pipes',
            'leftover_materials': 'Left Over material details',
            'installer_remarks': 'Remarks',
            'customer_remarks': 'Customer Remarks',
            'dc_voltage': 'DC Voltage',
            'ac_voltage': 'AC Voltage',
            'earthing_resistance': 'Earthing Resistance',
            'customer_rating': 'Customer Rating (1-5)',
        }
        widgets = {
            'installer_remarks': forms.Textarea(attrs={'rows': 3}),
            'customer_remarks': forms.Textarea(attrs={'rows': 3}),
            'leftover_materials': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make photo fields mandatory if not already handled by model (model has blank=False by default for ImageField unless specified)
        # Model definitions:
        # inverter_serial_photo: Mandatory
        # inverter_acdb_photo: Optional (null=True, blank=True in model) -> User said "Mandatory". We override here.
        self.fields['inverter_acdb_photo'].required = True 
        
        # Ensure numeric fields have correct input type for mobile keyboards
        numeric_fields = ['ac_cable_used', 'dc_cable_used', 'la_cable_used', 'pipes_used', 'dc_voltage', 'ac_voltage', 'earthing_resistance']
        for field in numeric_fields:
            self.fields[field].widget.attrs['type'] = 'number'
            self.fields[field].widget.attrs['step'] = '0.01'

class OfficeStatusForm(forms.ModelForm):
    class Meta:
        model = CustomerSurvey
        fields = [
            'customer_name', 
            'installation_date',
            'workflow_status', # Installation Status
            'discom_status', 
            'net_metering_status', 
            'subsidy_status', 
            'agreed_amount',
            'office_remarks'
        ]
        labels = {
            'workflow_status': 'Installation Status',
            'discom_status': 'Discom Status',
            'net_metering_status': 'Net Metering Status',
            'subsidy_status': 'Subsidy Status',
            'installation_date': 'Installation Completed Date',
            'office_remarks': 'Remarks (Optional)',
        }
        widgets = {
            'installation_date': forms.DateInput(attrs={'type': 'date'}),
            'office_remarks': forms.Textarea(attrs={'rows': 3}),
            'customer_name': forms.TextInput(attrs={'readonly': 'readonly'}),
            'agreed_amount': forms.NumberInput(attrs={'readonly': 'readonly'}), # Read-only as per "Fetched from existing data" requirement
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Enforce Status Choices from Model (Pending/Completed)
        # Ensure mandatory fields have 'required' attribute
        mandatory_fields = ['installation_date', 'workflow_status', 'discom_status', 'net_metering_status', 'subsidy_status']
        for field in mandatory_fields:
            self.fields[field].required = True

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Clean string and validate length
            clean_phone = re.sub(r'\D', '', str(phone))
            if len(clean_phone) != 10:
                raise ValidationError("Phone Number must be exactly 10 digits.")
            return clean_phone
        return phone

    def clean_installation_date(self):
        date = self.cleaned_data.get('installation_date')
        if not date:
            raise ValidationError("Installation Completed Date is mandatory.")
        return date

class BankDetailsForm(forms.ModelForm):
    # User Spec: "Mandatory (Editable after submission)" -> We make them required here for initial survey
    parent_bank = forms.CharField(required=True, label="Parent Bank")
    parent_bank_ac_no = forms.CharField(required=True, label="Parent Bank Ac Number (Fetch logic pending)")
    loan_applied_bank = forms.CharField(required=False, label="Loan Applied Bank (Optional - Fill later)")
    loan_applied_ifsc = forms.CharField(required=False, label="Loan Applied Bank IFSC (Optional - Fill later)")
    loan_applied_ac_no = forms.CharField(required=False, label="Loan Applied Bank Ac Number (Optional - Fill later)")
    manager_number = forms.CharField(required=False, label="Manager Number")

    first_loan_amount = forms.DecimalField(required=False, initial=0.0)
    second_loan_amount = forms.DecimalField(required=False, initial=0.0)
    
    # Read-only field for display
    agreed_amount = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate Agreed Amount
        if self.instance and self.instance.pk and self.instance.survey:
            self.fields['agreed_amount'].initial = self.instance.survey.agreed_amount
        
        # Ensure Status is mandatory
        self.fields['loan_pending_status'].required = True

        # Add date widgets
        self.fields['first_loan_date'].widget = forms.DateInput(attrs={'type': 'date'})
        self.fields['second_loan_date'].widget = forms.DateInput(attrs={'type': 'date'})

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('loan_pending_status')

        # Helper to check mandatory fields
        def check_mandatory(fields, prefix):
            for field in fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f"{prefix} details are mandatory when status is '{status}'.")

        if status == 'First' or status == 'Both':
            check_mandatory(['first_loan_amount', 'first_loan_utr', 'first_loan_date'], "First Loan")

        if status == 'Second' or status == 'Both':
            check_mandatory(['second_loan_amount', 'second_loan_utr', 'second_loan_date'], "Second Loan")
        
        return cleaned_data

    class Meta:
        model = BankDetails
        fields = [
            'parent_bank', 'parent_bank_ac_no', 
            'loan_applied_bank', 'loan_applied_ifsc', 'loan_applied_ac_no', 'manager_number',
            'loan_pending_status', 
            'first_loan_amount', 'first_loan_utr', 'first_loan_date',
            'second_loan_amount', 'second_loan_utr', 'second_loan_date',
        ]


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
        ('loan', 'Loan'),
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

class FEUpdateForm(forms.ModelForm):
    # Bank Details Fields (Mapped manually in View)
    loan_applied_bank = forms.CharField(required=True, label="Loan Applied Bank")
    loan_applied_ifsc = forms.CharField(required=True, label="Loan Applied Bank IFSC")
    loan_applied_ac_no = forms.CharField(required=True, label="Loan Applied Bank Ac Number")

    class Meta:
        model = CustomerSurvey
        fields = ['registration_status', 'pms_registration_number']
        labels = {
            'registration_status': 'Registration Status (Registered/Pending)',
            'pms_registration_number': 'PM Surya Ghar National Portal Reg. No.',
        }
        widgets = {
            'registration_status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        bank_details = kwargs.pop('bank_details', None)
        super().__init__(*args, **kwargs)
        if bank_details:
            self.fields['loan_applied_bank'].initial = bank_details.loan_applied_bank
            self.fields['loan_applied_ifsc'].initial = bank_details.loan_applied_ifsc
            self.fields['loan_applied_ac_no'].initial = bank_details.loan_applied_ac_no

class OfficeBankDetailsForm(forms.ModelForm):
    """
    Strict validation form for Office Portal.
    Requirements: First/Second Loan Amounts, UTRs, Dates are Mandatory.
    """
    class Meta:
        model = BankDetails
        fields = [
            'loan_pending_status',
            'first_loan_amount', 'first_loan_utr', 'first_loan_date',
            'second_loan_amount', 'second_loan_utr', 'second_loan_date',
        ]
        widgets = {
             'first_loan_date': forms.DateInput(attrs={'type': 'date'}),
             'second_loan_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields mandatory as per requirement
        mandatory_fields = [
            'loan_pending_status',
            'first_loan_amount', 'first_loan_utr', 'first_loan_date',
            'second_loan_amount', 'second_loan_utr', 'second_loan_date'
        ]
        for field in mandatory_fields:
            self.fields[field].required = True