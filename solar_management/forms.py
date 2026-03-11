from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
import re
class SurveyForm(forms.ModelForm):
    is_critical_site = forms.BooleanField(required=False, label="Is Critical Site?")

    class Meta:
        model = CustomerSurvey
        fields = [
            'customer_name', 'connection_type', 'sc_no', 'phase', 'contracted_load', 'feasibility_kw',
            'aadhar_no', 'pan_card', 'email', 'aadhar_linked_phone', 
            'area', 'gps_coordinates', 'roof_type', 'roof_photo', 'structure_type',
            'structure_height', 'floors', 'measurements', 'agreed_amount', 'advance_paid', 
            'mefma_status', 'rp_name', 'rp_phone_number', 'co_name', 'co_phone_number',
            'fe_remarks', 'reference_name', 
            'pms_registration_number', 'division', 'registration_status', 'registration_date',
            'pan_card_photo', 'aadhar_photo', 'current_bill_photo', 'bank_account_photo', 'parent_bank_photo'
        ]
        labels = {
            'sc_no': 'Service Connection Number (16 Digits)',
            'contracted_load': 'Contracted Load (KW)',
            'structure_height': 'Structure Height (in Feet)',
            'floors': 'Number of Floors',
            'measurements': 'Measurements (Square Feet)',
            'feasibility_kw': 'Applied Solar Load (KW)',
            'aadhar_no': 'Aadhar Card (12 Digits)',
            'pan_card': 'Pan Card (10 Digits)',
            'email': 'Email-id',
            'aadhar_linked_phone': 'Aadhar Linked Phone Number (10 Digits)',
            'gps_coordinates': 'GPS Coordinates',
            'roof_photo': 'Roof Photo (Optional/Mandatory if Critical)',
            'mefma_status': 'Mefma (Yes/No)',
            'rp_name': 'RP Name',
            'rp_phone_number': 'Phone Number (RP)',
            'co_name': 'CO Name',
            'co_phone_number': 'Phone Number (CO)',
            'reference_name': 'Reference Name',
            'pms_registration_number': 'PM Surya Ghar National Portal Reg. No.',
            'division': 'Division',
            'fe_remarks': 'Remarks',
            'registration_status': 'Registration Status',
            'registration_date': 'Registration Date',
            'pan_card_photo': 'PAN Card Photo',
            'aadhar_photo': 'Aadhar Card Photo',
            'current_bill_photo': 'Current Electricity Bill Photo',
            'bank_account_photo': 'Bank Account Photo',
            'parent_bank_photo': 'Parent Bank Front Page Photo',
        }
        widgets = {
             'gps_coordinates': forms.TextInput(attrs={'placeholder': 'Latitude, Longitude', 'readonly': 'readonly'}),
             'mefma_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
             'registration_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
             'registration_date': forms.DateInput(attrs={'type': 'date'}),
             'customer_name': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Name must contain only letters.'}),
             'aadhar_linked_phone': forms.TextInput(attrs={'pattern': '\d{10}', 'maxlength': '10', 'minlength': '10', 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')", 'title': 'Phone number must be exactly 10 digits.'}),
             'email': forms.EmailInput(attrs={'pattern': '[^, ]+', 'title': 'Enter a single valid email address.'}),
             'rp_name': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'RP Name must contain only letters.'}),
             'co_name': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'CO Name must contain only letters.'}),
             'co_phone_number': forms.TextInput(attrs={'pattern': '\d{10}', 'maxlength': '10', 'minlength': '10', 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')", 'title': 'Phone number must be exactly 10 digits.'}),
             'measurements': forms.TextInput(attrs={'title': 'Alphanumeric values allowed.'}),
             'roof_photo': forms.ClearableFileInput(),
             'pan_card_photo': forms.ClearableFileInput(),
             'aadhar_photo': forms.ClearableFileInput(),
             'current_bill_photo': forms.ClearableFileInput(),
             'bank_account_photo': forms.ClearableFileInput(),
             'parent_bank_photo': forms.ClearableFileInput(),
        }
        help_texts = {
            'structure_height': '',
            'floors': '',
            'measurements': '',
            'contracted_load': '',
            'feasibility_kw': '',
        }


    # Image fields that should be optional when editing
    IMAGE_FIELDS = ['roof_photo', 'pan_card_photo', 'aadhar_photo', 'current_bill_photo', 'bank_account_photo', 'parent_bank_photo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing record, make all image fields optional
        if self.instance and self.instance.pk:
            for field_name in self.IMAGE_FIELDS:
                if field_name in self.fields:
                    self.fields[field_name].required = False

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

    def clean_aadhar_linked_phone(self):
        phone = self.cleaned_data.get('aadhar_linked_phone')
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
        
    def clean_co_name(self):
        name = self.cleaned_data.get('co_name')
        if name and any(char.isdigit() for char in name):
             raise ValidationError("CO Name must contain only text (no numbers).")
        return name

    def clean_co_phone_number(self):
         phone = self.cleaned_data.get('co_phone_number')
         if phone and not re.match(r'^\d{10}$', phone):
             raise ValidationError("CO Phone Number must be exactly 10 digits.")
         return phone

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
        co_name = cleaned_data.get('co_name')
        co_phone = cleaned_data.get('co_phone_number')
        reference_name = cleaned_data.get('reference_name')
        roof_photo = cleaned_data.get('roof_photo')
        pan_card_photo = cleaned_data.get('pan_card_photo')
        aadhar_photo = cleaned_data.get('aadhar_photo')
        current_bill_photo = cleaned_data.get('current_bill_photo')
        parent_bank_photo = cleaned_data.get('parent_bank_photo')
        registration_status = cleaned_data.get('registration_status')
        registration_date = cleaned_data.get('registration_date')

        # Registration Date conditional validation
        if registration_status and not registration_date:
            self.add_error('registration_date', "Registration Date is mandatory if Registration Status is Yes.")

        if not registration_status:
            # Clear it if no it's not applicable
            cleaned_data['registration_date'] = None

        # Roof photo is mandatory
        if not roof_photo:
            if not (self.instance.pk and self.instance.roof_photo):
                 self.add_error('roof_photo', "Roof photo is mandatory.")

        # Document photos are mandatory
        if not pan_card_photo:
            if not (self.instance.pk and self.instance.pan_card_photo):
                self.add_error('pan_card_photo', "PAN Card photo is mandatory.")

        if not aadhar_photo:
            if not (self.instance.pk and self.instance.aadhar_photo):
                self.add_error('aadhar_photo', "Aadhar Card photo is mandatory.")

        if not current_bill_photo:
            if not (self.instance.pk and self.instance.current_bill_photo):
                self.add_error('current_bill_photo', "Current Electricity Bill photo is mandatory.")
                
        if not parent_bank_photo:
            if not (self.instance.pk and self.instance.parent_bank_photo):
                self.add_error('parent_bank_photo', "Parent Bank Front Page photo is mandatory.")

        if mefma_status:
            if not rp_name:
                self.add_error('rp_name', "RP Name is mandatory if MEFMA is Yes.")
            if not rp_phone:
                self.add_error('rp_phone_number', "RP Phone Number is mandatory if MEFMA is Yes.")
            if not co_name:
                self.add_error('co_name', "CO Name is mandatory if MEFMA is Yes.")
            if not co_phone:
                self.add_error('co_phone_number', "CO Phone Number is mandatory if MEFMA is Yes.")
        else:
            if not reference_name:
                self.add_error('reference_name', "Reference Name is mandatory if MEFMA is No.")
        
        return cleaned_data


class InstallationForm(forms.ModelForm):
    class Meta:
        model = Installation
        fields = [
            'inverter_make',
            'inverter_phase',
            'inverter_serial_number',
            'inverter_serial_photo',
            'inverter_acdb_photo',
            'panel_serial_numbers',
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
            # Materials Used
            'panels_count',
            'structure_kit_type',
            'inverter_kw',
            'inverter_phase_type',
            'ac_cable_red',
            'ac_cable_black',
            'dc_cable_red_black',
            'la_cable_mtrs',
            'pipes_count',
            'earthing_kit_count',
            'acdb_count',
            'dcdb_count',
            'mc4_connectors_count',
            'long_l_bands_count',
            'short_l_bands_count',
            't_bands_count',
            'tapes_red_count',
            'tapes_black_count',
            'tags_count',
            'nail_clamps_2side_count',
            'nail_clamps_1side_count',
            'anchor_hardener_count',
        ]
        labels = {
            'inverter_make': 'Inverter Make',
            'inverter_phase': 'Inverter Phase (Single/Three)',
            'inverter_serial_number': 'Inverter Serial Number',
            'inverter_serial_photo': 'Inverter Serial Number (Photo)',
            'inverter_acdb_photo': 'Inverter Photo (with ACDB & DCDB)',
            'panel_serial_numbers': 'Panel Serial Numbers',
            'panel_serial_photo': 'Panel Serial Numbers (Photo)',
            'warranty_claimed': 'Warranty Claimed Status',
            'app_installation_status': 'App Installation Status',
            'site_photos_with_customer': 'Site Photos with Customer',
            'ac_cable_used': 'Used AC Cable length (Mtrs)',
            'dc_cable_used': 'Used DC Cable length (Mtrs)',
            'la_cable_used': 'Used LA Cable length (Mtrs)',
            'pipes_used': 'Used Pipes',
            'leftover_materials': 'Left Over material details',
            'installer_remarks': 'Installer Remarks',
            'customer_remarks': 'Customer Remarks',
            'dc_voltage': 'DC Voltage',
            'ac_voltage': 'AC Voltage',
            'earthing_resistance': 'Earthing Resistance',
            'customer_rating': 'Customer Rating (1-5)',
            # Materials Used
            'panels_count': 'Panels (Count)',
            'structure_kit_type': 'Structure Kit (Normal / Fabrication)',
            'inverter_kw': 'Inverter (kW)',
            'inverter_phase_type': 'Inverter Phase (Single / Three Phase)',
            'ac_cable_red': 'AC Cable Red (Mtrs)',
            'ac_cable_black': 'AC Cable Black (Mtrs)',
            'dc_cable_red_black': 'DC Cable Red & Black (Mtrs)',
            'la_cable_mtrs': 'LA Cable (Mtrs)',
            'pipes_count': 'Pipes (Count)',
            'earthing_kit_count': 'Earthing Kit (Count)',
            'acdb_count': 'ACDB (Count)',
            'dcdb_count': 'DCDB (Count)',
            'mc4_connectors_count': 'MC4 Connectors (Count)',
            'long_l_bands_count': 'Long L Bands (Count)',
            'short_l_bands_count': 'Short L Bands (Count)',
            't_bands_count': 'T Bands (Count)',
            'tapes_red_count': 'Tapes Red (Count)',
            'tapes_black_count': 'Tapes Black (Count)',
            'tags_count': 'Tags (Count)',
            'nail_clamps_2side_count': 'Nail Clamps 2 Side (Count)',
            'nail_clamps_1side_count': 'Nail Clamps 1 Side (Count)',
            'anchor_hardener_count': 'Anchor Hardener (Count)',
        }
        widgets = {
            'inverter_serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SN123456789'}),
            'inverter_serial_photo': forms.ClearableFileInput(),
            'inverter_acdb_photo': forms.ClearableFileInput(),
            'panel_serial_numbers': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PSN001, PSN002, PSN003'}),
            'panel_serial_photo': forms.ClearableFileInput(),
            'site_photos_with_customer': forms.ClearableFileInput(),
            'installer_remarks': forms.Textarea(attrs={'rows': 3}),
            'customer_remarks': forms.Textarea(attrs={'rows': 3}),
            'leftover_materials': forms.Textarea(attrs={'rows': 3}),
            # Material fields - styled for compact mobile layout
            'panels_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'structure_kit_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'inverter_kw': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'inverter_phase_type': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'ac_cable_red': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'ac_cable_black': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'dc_cable_red_black': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'la_cable_mtrs': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'pipes_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'earthing_kit_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'acdb_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'dcdb_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'mc4_connectors_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'long_l_bands_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'short_l_bands_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            't_bands_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'tapes_red_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'tapes_black_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'tags_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'nail_clamps_2side_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'nail_clamps_1side_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'anchor_hardener_count': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make photo fields mandatory if not already handled by model (model has blank=False by default for ImageField unless specified)
        # Model definitions:
        # inverter_serial_photo: Mandatory
        # inverter_acdb_photo: Optional (null=True, blank=True in model) -> User said "Mandatory". We override here.
        self.fields['inverter_acdb_photo'].required = True 
        
        # Customer rating has a default value in the model, so make it optional in the form
        self.fields['customer_rating'].required = False
        self.fields['customer_rating'].initial = 5
        
        # Ensure numeric fields have correct input type for mobile keyboards
        numeric_float_fields = [
            'ac_cable_used', 'dc_cable_used', 'la_cable_used', 'pipes_used',
            'dc_voltage', 'ac_voltage', 'earthing_resistance',
            'inverter_kw', 'ac_cable_red', 'ac_cable_black', 'dc_cable_red_black', 'la_cable_mtrs',
        ]
        for field in numeric_float_fields:
            self.fields[field].widget.attrs['type'] = 'number'
            self.fields[field].widget.attrs['step'] = '0.01'
            self.fields[field].widget.attrs['min'] = '0'

        numeric_int_fields = [
            'panels_count', 'pipes_count', 'earthing_kit_count', 'acdb_count', 'dcdb_count',
            'mc4_connectors_count', 'long_l_bands_count', 'short_l_bands_count', 't_bands_count',
            'tapes_red_count', 'tapes_black_count', 'tags_count',
            'nail_clamps_2side_count', 'nail_clamps_1side_count', 'anchor_hardener_count',
        ]
        for field in numeric_int_fields:
            self.fields[field].widget.attrs['type'] = 'number'
            self.fields[field].widget.attrs['step'] = '1'
            self.fields[field].widget.attrs['min'] = '0'

        # Make all Materials Used fields optional
        materials_fields = [
            'panels_count', 'structure_kit_type', 'inverter_kw', 'inverter_phase_type',
            'ac_cable_red', 'ac_cable_black', 'dc_cable_red_black', 'la_cable_mtrs',
            'pipes_count', 'earthing_kit_count', 'acdb_count', 'dcdb_count',
            'mc4_connectors_count', 'long_l_bands_count', 'short_l_bands_count', 't_bands_count',
            'tapes_red_count', 'tapes_black_count', 'tags_count',
            'nail_clamps_2side_count', 'nail_clamps_1side_count', 'anchor_hardener_count',
        ]
        for field in materials_fields:
            self.fields[field].required = False

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

    
    # Read-only field for display
    agreed_amount = forms.DecimalField(required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate Agreed Amount
        if self.instance and self.instance.pk and self.instance.survey:
            self.fields['agreed_amount'].initial = self.instance.survey.agreed_amount

        # These fields are filled LATER by the Loan Officer — not required at survey creation
        loan_officer_fields = [
            'loan_pending_status',
            'first_loan_amount', 'first_loan_utr', 'first_loan_date',
            'second_loan_amount', 'second_loan_utr', 'second_loan_date',
        ]
        for field in loan_officer_fields:
            self.fields[field].required = False

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
            'loan_applied_bank', 'loan_applied_ifsc', 'loan_applied_ac_no',
            'loan_pending_status',
            'first_loan_amount', 'first_loan_utr', 'first_loan_date',
            'second_loan_amount', 'second_loan_utr', 'second_loan_date',
            'agreed_amount',
        ]
        widgets = {
             'parent_bank': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Bank Name must contain only letters.'}),
             'loan_applied_bank': forms.TextInput(attrs={'pattern': '[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Bank Name must contain only letters.'}),
             'first_loan_date': forms.DateInput(attrs={'type': 'date'}),
             'second_loan_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        
        first_amt = float(cleaned_data.get('first_loan_amount') or 0.0)
        second_amt = float(cleaned_data.get('second_loan_amount') or 0.0)

        first_utr_str = str(cleaned_data.get('first_loan_utr') or '0').strip()
        second_utr_str = str(cleaned_data.get('second_loan_utr') or '0').strip()
        
        if not first_utr_str: first_utr_str = '0'
        if not second_utr_str: second_utr_str = '0'

        first_utr_amt = 0.0
        try:
            first_utr_amt = float(first_utr_str)
        except ValueError:
            self.add_error('first_loan_utr', "Please enter a valid numeric amount.")

        second_utr_amt = 0.0
        try:
            second_utr_amt = float(second_utr_str)
        except ValueError:
            self.add_error('second_loan_utr', "Please enter a valid numeric amount.")

        if first_amt > 0 and first_utr_amt > first_amt:
            self.add_error('first_loan_utr', "UTR amount cannot be greater than the loan amount.")
            
        if second_amt > 0 and second_utr_amt > second_amt:
            self.add_error('second_loan_utr', "UTR amount cannot be greater than the loan amount.")

        if (first_amt > 0 or second_amt > 0) and (first_amt == first_utr_amt) and (second_amt == second_utr_amt):
            cleaned_data['loan_pending_status'] = 'Completed'
        else:
            cleaned_data['loan_pending_status'] = 'Pending'
            
        return cleaned_data


class SignUpForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    mobile_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'type': 'tel',
            'pattern': '[0-9]{10}',
            'maxlength': '10',
            'minlength': '10',
            'oninput': "this.value = this.value.replace(/[^0-9]/g, '')",
            'placeholder': '10-digit mobile number',
            'title': 'Mobile number must be exactly 10 digits'
        })
    )
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True)
    aadhar_photo = forms.FileField(
        required=True, 
        help_text="Upload a clear photo or scan of your Aadhar Card.",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    pan_card_photo = forms.FileField(
        required=True, 
        help_text="Upload a clear photo or scan of your PAN Card.",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'type': 'email',
            'placeholder': 'example@email.com',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_mobile_number(self):
        mobile = self.cleaned_data.get('mobile_number')
        # Remove any non-digit characters
        if mobile:
            mobile = re.sub(r'\D', '', mobile)
            # Check if it's exactly 10 digits
            if len(mobile) != 10:
                raise forms.ValidationError("Mobile number must be exactly 10 digits.")
            # Check if mobile already exists
            if UserProfile.objects.filter(mobile_number=mobile).exists():
                raise forms.ValidationError("This mobile number is already registered.")
        return mobile

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check for valid email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise forms.ValidationError("Please enter a valid email address.")
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("This email is already registered.")
        return email

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
        fields = ['registration_status', 'registration_date', 'pms_registration_number']
        labels = {
            'registration_status': 'Registration Status',
            'registration_date': 'Registration Date',
            'pms_registration_number': 'PM Surya Ghar National Portal Reg. No.',
        }
        widgets = {
            'registration_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
            'registration_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        bank_details = kwargs.pop('bank_details', None)
        super().__init__(*args, **kwargs)
        if bank_details:
            self.fields['loan_applied_bank'].initial = bank_details.loan_applied_bank
            self.fields['loan_applied_ifsc'].initial = bank_details.loan_applied_ifsc
            self.fields['loan_applied_ac_no'].initial = bank_details.loan_applied_ac_no

    def clean(self):
        cleaned_data = super().clean()
        registration_status = cleaned_data.get('registration_status')
        registration_date = cleaned_data.get('registration_date')

        if registration_status and not registration_date:
            self.add_error('registration_date', "Registration Date is mandatory if Registration Status is Yes.")

        if not registration_status:
            cleaned_data['registration_date'] = None

        return cleaned_data

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
        labels = {
            'first_loan_utr': 'First loan utr number',
            'second_loan_utr': 'Second loan utr number',
        }
        widgets = {
             'first_loan_date': forms.DateInput(attrs={'type': 'date'}),
             'second_loan_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields mandatory except status, which we calculate
        mandatory_fields = [
            'first_loan_amount', 'first_loan_utr', 'first_loan_date',
            'second_loan_amount', 'second_loan_utr', 'second_loan_date'
        ]
        for field in mandatory_fields:
            self.fields[field].required = True
        self.fields['loan_pending_status'].required = False
        
    def clean(self):
        cleaned_data = super().clean()
        
        first_amt = float(cleaned_data.get('first_loan_amount') or 0.0)
        second_amt = float(cleaned_data.get('second_loan_amount') or 0.0)

        first_utr_str = str(cleaned_data.get('first_loan_utr') or '0').strip()
        second_utr_str = str(cleaned_data.get('second_loan_utr') or '0').strip()
        
        if not first_utr_str: first_utr_str = '0'
        if not second_utr_str: second_utr_str = '0'

        first_utr_amt = 0.0
        try:
            first_utr_amt = float(first_utr_str)
        except ValueError:
            self.add_error('first_loan_utr', "Please enter a valid numeric amount.")

        second_utr_amt = 0.0
        try:
            second_utr_amt = float(second_utr_str)
        except ValueError:
            self.add_error('second_loan_utr', "Please enter a valid numeric amount.")

        if first_amt > 0 and first_utr_amt > first_amt:
            self.add_error('first_loan_utr', "UTR amount cannot be greater than the loan amount.")
            
        if second_amt > 0 and second_utr_amt > second_amt:
            self.add_error('second_loan_utr', "UTR amount cannot be greater than the loan amount.")

        if (first_amt > 0 or second_amt > 0) and (first_amt == first_utr_amt) and (second_amt == second_utr_amt):
            cleaned_data['loan_pending_status'] = 'Completed'
        else:
            cleaned_data['loan_pending_status'] = 'Pending'
            
        return cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    # User profile fields
    aadhar_photo = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    pan_card_photo = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop('user_profile', None)
        super().__init__(*args, **kwargs)
        if self.user_profile:
            # We don't set initial for FileFields as browsers don't allow it, 
            # but we can handle it in the save method.
            pass

    def save(self, commit=True):
        user = super().save(commit=commit)
        if self.user_profile:
            # Only update if a new file is uploaded or it's being cleared
            if 'aadhar_photo' in self.changed_data:
                self.user_profile.aadhar_photo = self.cleaned_data.get('aadhar_photo')
            if 'pan_card_photo' in self.changed_data:
                self.user_profile.pan_card_photo = self.cleaned_data.get('pan_card_photo')
            if commit:
                self.user_profile.save()
        return user