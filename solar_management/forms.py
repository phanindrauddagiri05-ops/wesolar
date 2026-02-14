from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
import re
class SurveyForm(forms.ModelForm):
    is_critical_site = forms.BooleanField(required=False, label="Is Critical Site?")
    phone_number = forms.CharField(required=True, label="Aadhar Linked Phone Number (10 Digits)", widget=forms.TextInput(attrs={'pattern': '\d{10}', 'maxlength': '10', 'minlength': '10', 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')", 'title': 'Phone number must be exactly 10 digits.'}))

    class Meta:
        model = CustomerSurvey
        fields = [
            'customer_name', 'connection_type', 'sc_no', 'phase', 'feasibility_kw',
            'aadhar_no', 'pan_card', 'email', 'phone_number', 
            'area', 'gps_coordinates', 'roof_type', 'roof_photo', 'structure_type',
            'structure_height', 'agreed_amount', 'advance_paid', 
            'mefma_status', 'rp_name', 'rp_phone_number', 
            'fe_remarks', 'reference_name', 
            'pms_registration_number', 'division', 'registration_status',
        ]
        labels = {
            'sc_no': 'Service Connection Number (16 Digits)',
            'feasibility_kw': 'Applied Solar Load (KW)',
            'aadhar_no': 'Aadhar Card (12 Digits)',
            'pan_card': 'Pan Card (10 Digits)',
            'email': 'Email-id',
            'phone_number': 'Aadhar Linked Phone Number (10 Digits)',
            'gps_coordinates': 'GPS Coordinates',
            'roof_photo': 'Roof Photo (Optional/Mandatory if Critical)',
            'mefma_status': 'Mefma (Yes/No)',
            'rp_name': 'RP Name',
            'rp_phone_number': 'Phone Number (RP)',
            'reference_name': 'Reference Name',
            'pms_registration_number': 'PM Surya Ghar National Portal Reg. No.',
            'division': 'Division',
            'fe_remarks': 'Remarks',
            'registration_status': 'Registration Status',
        }
        widgets = {
             'gps_coordinates': forms.TextInput(attrs={'placeholder': 'Latitude, Longitude', 'readonly': 'readonly'}),
             'mefma_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
             'registration_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
             'customer_name': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Name must contain only letters.'}),
             'phone_number': forms.TextInput(attrs={'pattern': '\d{10}', 'maxlength': '10', 'minlength': '10', 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')", 'title': 'Phone number must be exactly 10 digits.'}),
             'email': forms.EmailInput(attrs={'pattern': '[^, ]+', 'title': 'Enter a single valid email address.'}),
             'rp_name': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'RP Name must contain only letters.'}),
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

    def clean_rp_name(self):
        name = self.cleaned_data.get('rp_name')
        if name and any(char.isdigit() for char in name):
             raise ValidationError("RP Name must contain only text (no numbers).")
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Check length is exactly 10 digits
            if not re.match(r'^\d{10}$', phone):
                 raise ValidationError("Aadhar Linked Phone Number must be exactly 10 digits.")
        return phone

    def clean_customer_name(self):
        name = self.cleaned_data.get('customer_name')
        if name and any(char.isdigit() for char in name):
             raise ValidationError("Customer Name must contain only text (no numbers).")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Ensure single email and basic validity (Django handles format, we ensure no multiple emails/junk)
        if email:
            if ',' in email or ' ' in email:
                 raise ValidationError("Please enter a single valid email address.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        mefma_status = cleaned_data.get('mefma_status')
        rp_name = cleaned_data.get('rp_name')
        rp_phone = cleaned_data.get('rp_phone_number')
        reference_name = cleaned_data.get('reference_name')
        roof_photo = cleaned_data.get('roof_photo')

        # Roof photo is mandatory (removed critical site checkbox logic)
        if not roof_photo:
            if not (self.instance.pk and self.instance.roof_photo):
                 self.add_error('roof_photo', "Roof photo is mandatory.")
        
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
    
    # Read-only field for display
    agreed_amount = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate Agreed Amount
        if self.instance and self.instance.pk and self.instance.survey:
            self.fields['agreed_amount'].initial = self.instance.survey.agreed_amount

    def clean_parent_bank(self):
        bank = self.cleaned_data.get('parent_bank')
        if bank and any(char.isdigit() for char in bank):
            raise ValidationError("Parent Bank Name must contain only text (no numbers).")
        return bank

    def clean_loan_applied_bank(self):
        bank = self.cleaned_data.get('loan_applied_bank')
        if bank and any(char.isdigit() for char in bank):
            raise ValidationError("Loan Applied Bank Name must contain only text (no numbers).")
        return bank



    class Meta:
        model = BankDetails
        fields = [
            'parent_bank', 'parent_bank_ac_no', 
            'loan_applied_bank', 'loan_applied_ifsc', 'loan_applied_ac_no', 'manager_number',
        ]
        widgets = {
             'parent_bank': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Bank Name must contain only letters.'}),
             'loan_applied_bank': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Bank Name must contain only letters.'}),
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
            'registration_status': 'Registration Status',
            'pms_registration_number': 'PM Surya Ghar National Portal Reg. No.',
        }
        widgets = {
            'registration_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
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