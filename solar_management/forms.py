from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import CustomerSurvey, Installation, BankDetails, UserProfile, Enquiry
import re

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class SurveyForm(forms.ModelForm):
    is_critical_site = forms.BooleanField(required=False, label="Is Critical Site?")
    custom_area = forms.CharField(required=False, label="Specify Custom Area", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter custom area name...'}))
    
    # Global Multi-Upload Fields
    roof_photo = MultipleFileField(required=False, label="Roof Photo (Optional/Mandatory if Critical)")
    pan_card_photo = MultipleFileField(required=False, label="PAN Card Photo")
    aadhar_photo = MultipleFileField(required=False, label="Aadhar Card Photo")
    current_bill_photo = MultipleFileField(required=False, label="Current Electricity Bill Photo")
    bank_account_photo = MultipleFileField(required=False, label="Bank Account Photo")
    parent_bank_photo = MultipleFileField(required=False, label="Parent Bank Front Page Photo")
    property_tax_photo = MultipleFileField(required=False, label="Property Tax Photo")

    class Meta:
        model = CustomerSurvey
        fields = [
            'customer_name', 'connection_type', 'sc_no', 'phase', 'contracted_load', 'feasibility_kw',
            'aadhar_no', 'pan_card', 'email', 'aadhar_linked_phone', 
            'area', 'gps_coordinates', 'roof_type', 'structure_type',
            'structure_height', 'floors', 'measurements', 'agreed_amount', 'advance_paid', 
            'mefma_status', 'rp_name', 'rp_phone_number', 'co_name', 'co_phone_number',
            'fe_remarks', 'reference_name', 
            'pms_registration_number', 'division', 'registration_status', 'registration_date',
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
            'property_tax_photo': 'Property Tax Photo',
        }
        widgets = {
             'gps_coordinates': forms.TextInput(attrs={'placeholder': 'Latitude, Longitude'}),
             'mefma_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
             'registration_status': forms.Select(choices=[(True, 'Yes'), (False, 'No')]),
             'registration_date': forms.DateInput(attrs={'type': 'date'}),
             'customer_name': forms.TextInput(attrs={'pattern': r'[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Name must contain only letters.'}),
             'aadhar_linked_phone': forms.TextInput(attrs={'pattern': r'\d{10}', 'maxlength': '10', 'minlength': '10', 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')", 'title': 'Phone number must be exactly 10 digits.'}),
             'email': forms.EmailInput(attrs={'pattern': '[^, ]+', 'title': 'Enter a single valid email address.'}),
             'rp_name': forms.TextInput(attrs={'pattern': r'[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'RP Name must contain only letters.'}),
             'co_name': forms.TextInput(attrs={'pattern': r'[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'CO Name must contain only letters.'}),
             'co_phone_number': forms.TextInput(attrs={'pattern': r'\d{10}', 'maxlength': '10', 'minlength': '10', 'oninput': "this.value = this.value.replace(/[^0-9]/g, '')", 'title': 'Phone number must be exactly 10 digits.'}),
             'measurements': forms.TextInput(attrs={'title': 'Alphanumeric values allowed.'}),
             # Use TextInput for money fields to avoid browser-level decimal validation errors on Android
             'agreed_amount': forms.TextInput(attrs={
                 'inputmode': 'decimal',
                 'pattern': r'[0-9]+(\.[0-9]{1,2})?',
                 'placeholder': 'e.g. 50000',
                 'title': 'Enter a valid amount (up to 2 decimal places).',
                 'oninput': "this.value = this.value.replace(/[^0-9.]/g, '')",
             }),
             'advance_paid': forms.TextInput(attrs={
                 'inputmode': 'decimal',
                 'pattern': r'[0-9]+(\.[0-9]{1,2})?',
                 'placeholder': 'e.g. 5000',
                 'title': 'Enter a valid amount (up to 2 decimal places).',
                 'oninput': "this.value = this.value.replace(/[^0-9.]/g, '')",
             }),
             'area': forms.Select(choices=[
                ('', '--- Select Area ---'),
                ('Rajahmundry', 'Rajahmundry'),
                ('Kovvur', 'Kovvur'),
                ('Mandapeta', 'Mandapeta'),
                ('Nidadavole', 'Nidadavole'),
                ('Others', 'Others'),
             ], attrs={'class': 'form-select'}),
        }
        help_texts = {
            'structure_height': '',
            'floors': '',
            'measurements': '',
            'contracted_load': '',
            'feasibility_kw': '',
        }


    # Image fields that should be optional when editing
    IMAGE_FIELDS = ['roof_photo', 'pan_card_photo', 'aadhar_photo', 'current_bill_photo', 'bank_account_photo', 'parent_bank_photo', 'property_tax_photo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing an existing record, make all image fields optional
        if self.instance and self.instance.pk:
            for field_name in self.IMAGE_FIELDS:
                if field_name in self.fields:
                    self.fields[field_name].required = False
        else:
            # For new records, make mandatory fields required to trigger browser-side validation
            mandatory_photos = ['roof_photo', 'pan_card_photo', 'aadhar_photo', 'current_bill_photo', 'bank_account_photo', 'parent_bank_photo', 'property_tax_photo']
            for field_name in mandatory_photos:
                if field_name in self.fields:
                    self.fields[field_name].required = True
                    
            # Handle custom area logic
            if hasattr(self.instance, 'area') and self.instance.area:
                valid_areas = ['Rajahmundry', 'Kovvur', 'Mandapeta', 'Nidadavole', 'Others']
                if self.instance.area not in valid_areas:
                    self.initial['area'] = 'Others'
                    self.initial['custom_area'] = self.instance.area

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
            raise ValidationError("Invalid PAN Card formate. Enter correct format of PAN card.")
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

    def clean_agreed_amount(self):
        """Normalize agreed_amount: strip spaces, handle leading zeros, validate as decimal."""
        from decimal import Decimal, InvalidOperation
        value = self.cleaned_data.get('agreed_amount')
        if value is None:
            raise ValidationError("Agreed Amount is required.")
        try:
            # value may already be Decimal if Django parsed it; convert to string to normalize
            normalized = Decimal(str(value).strip()).quantize(Decimal('0.01'))
            if normalized < 0:
                raise ValidationError("Agreed Amount cannot be negative.")
            return normalized
        except InvalidOperation:
            raise ValidationError("Enter a valid amount (e.g. 50000 or 50000.00).")

    def clean_advance_paid(self):
        """Normalize advance_paid: strip spaces, handle leading zeros, validate as decimal."""
        from decimal import Decimal, InvalidOperation
        value = self.cleaned_data.get('advance_paid')
        if value is None:
            return Decimal('0.00')
        try:
            normalized = Decimal(str(value).strip()).quantize(Decimal('0.01'))
            if normalized < 0:
                raise ValidationError("Advance Paid cannot be negative.")
            return normalized
        except InvalidOperation:
            raise ValidationError("Enter a valid amount (e.g. 5000 or 5000.00).")



    def clean(self):
        cleaned_data = super().clean()
        area = cleaned_data.get('area')
        custom_area = cleaned_data.get('custom_area')

        if area == 'Others':
            if not custom_area:
                self.add_error('custom_area', "Please specify the custom area.")
            else:
                cleaned_data['area'] = custom_area

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
        bank_account_photo = cleaned_data.get('bank_account_photo')
        parent_bank_photo = cleaned_data.get('parent_bank_photo')
        property_tax_photo = cleaned_data.get('property_tax_photo')

        registration_status = cleaned_data.get('registration_status')
        registration_date = cleaned_data.get('registration_date')

        # Registration Date conditional validation
        if registration_status and not registration_date:
            # Clear it if no it's not applicable
            if not registration_status:
                cleaned_data['registration_date'] = None
            
            # Only enforce mandatory date for NEW surveys
            if not self.instance.pk:
                self.add_error('registration_date', "Registration Date is mandatory if Registration Status is Yes.")

        # ONLY perform mandatory checks for NEW surveys
        if not self.instance.pk:
            # Roof photo is mandatory
            if not roof_photo:
                self.add_error('roof_photo', "Roof photo is mandatory.")

            # Document photos are mandatory
            if not pan_card_photo:
                self.add_error('pan_card_photo', "PAN Card photo is mandatory.")

            if not aadhar_photo:
                self.add_error('aadhar_photo', "Aadhar Card photo is mandatory.")

            if not current_bill_photo:
                self.add_error('current_bill_photo', "Current Electricity Bill photo is mandatory.")
                
            if not property_tax_photo:
                self.add_error('property_tax_photo', "Property Tax photo is mandatory.")
                
            if mefma_status:
                if not rp_name:
                    self.add_error('rp_name', "RP Name is mandatory if MEFMA is Yes.")
                if not rp_phone:
                    self.add_error('rp_phone_number', "RP Phone Number is mandatory if MEFMA is Yes.")
                if not co_name:
                    self.add_error('co_name', "CO Name is mandatory if MEFMA is Yes.")
                if not co_phone:
                    self.add_error('co_phone_number', "CO Phone Number is mandatory if MEFMA is Yes.")
        # Reference Name validation removed per request
        
        return cleaned_data



class InstallationForm(forms.ModelForm):
    site_photos_multiple = MultipleFileField(
        required=False,
        label="Additional Site Photos",
        widget=MultipleFileInput(attrs={'class': 'form-control'})
    )
    inverter_serial_photo = MultipleFileField(required=False, label="Inverter Serial Photo")
    inverter_acdb_photo = MultipleFileField(required=False, label="Inverter ACDB Photo")
    panel_serial_photo = MultipleFileField(required=False, label="Panel Serial Photo")
    site_photos_with_customer = MultipleFileField(required=False, label="Site Photo with Customer")

    class Meta:
        model = Installation
        fields = [
            'inverter_make',
            'inverter_phase',
            'inverter_serial_number',
            'panel_serial_numbers',
            'warranty_claimed',
            'app_installation_status',
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
            # Specific Used Materials
            'panels_used',
            'structure_kit_used',
            'inverter_kw_used',
            'inverter_phase_type_used',
            'ac_cable_red_used',
            'ac_cable_black_used',
            'dc_cable_red_black_used',
            'la_cable_mtrs_used',
            'pipes_count_used',
            'earthing_kit_count_used',
            'acdb_count_used',
            'dcdb_count_used',
            'mc4_connectors_count_used',
            'long_l_bands_count_used',
            'short_l_bands_count_used',
            't_bands_count_used',
            'tapes_red_count_used',
            'tapes_black_count_used',
            'tags_count_used',
            'nail_clamps_2side_count_used',
            'nail_clamps_1side_count_used',
            'anchor_hardener_count_used',
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
            'inverter_phase': forms.Select(choices=[('', '--- Select Phase ---'), ('Single Phase', 'Single Phase'), ('Three Phase', 'Three Phase')], attrs={'class': 'form-select'}),
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
            
            # Specific Used Material fields - styled for compact mobile layout
            'panels_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'structure_kit_used': forms.Select(attrs={'class': 'form-select form-select-sm used-field'}),
            'inverter_kw_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0', 'step': '0.01'}),
            'inverter_phase_type_used': forms.Select(attrs={'class': 'form-select form-select-sm used-field'}),
            'ac_cable_red_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0', 'step': '0.01'}),
            'ac_cable_black_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0', 'step': '0.01'}),
            'dc_cable_red_black_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0', 'step': '0.01'}),
            'la_cable_mtrs_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0', 'step': '0.01'}),
            'pipes_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'earthing_kit_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'acdb_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'dcdb_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'mc4_connectors_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'long_l_bands_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'short_l_bands_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            't_bands_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'tapes_red_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'tapes_black_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'tags_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'nail_clamps_2side_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'nail_clamps_1side_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),
            'anchor_hardener_count_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm used-field', 'min': '0'}),

            # Used material fields - styled for consistency
            'ac_cable_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'dc_cable_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'la_cable_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            'pipes_used': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'step': '0.01'}),
            # Electrical readings with decimal support
            'dc_voltage': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'ac_voltage': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'earthing_resistance': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make photo fields mandatory if not already handled by model
        # Make used material fields optional since they were removed from UI but are required in model
        optional_fields = ['ac_cable_used', 'dc_cable_used', 'la_cable_used', 'pipes_used']
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False
                
        # Make all new dispatched and used fields mandatory
        mandatory_fields = [
            'panels_count', 'structure_kit_type', 'inverter_kw', 'inverter_phase_type',
            'ac_cable_red', 'ac_cable_black', 'dc_cable_red_black', 'la_cable_mtrs',
            'pipes_count', 'earthing_kit_count', 'acdb_count', 'dcdb_count', 'mc4_connectors_count',
            'long_l_bands_count', 'short_l_bands_count', 't_bands_count', 'tapes_red_count',
            'tapes_black_count', 'tags_count', 'nail_clamps_2side_count', 'nail_clamps_1side_count',
            'anchor_hardener_count',
            'panels_used', 'structure_kit_used', 'inverter_kw_used', 'inverter_phase_type_used',
            'ac_cable_red_used', 'ac_cable_black_used', 'dc_cable_red_black_used', 'la_cable_mtrs_used',
            'pipes_count_used', 'earthing_kit_count_used', 'acdb_count_used', 'dcdb_count_used',
            'mc4_connectors_count_used', 'long_l_bands_count_used', 'short_l_bands_count_used',
            't_bands_count_used', 'tapes_red_count_used', 'tapes_black_count_used', 'tags_count_used',
            'nail_clamps_2side_count_used', 'nail_clamps_1side_count_used', 'anchor_hardener_count_used'
        ]
        for field in mandatory_fields:
            if field in self.fields:
                self.fields[field].required = True
        # Make photo fields optional to allow clearing
        self.fields['inverter_serial_photo'].required = False
        self.fields['inverter_acdb_photo'].required = False
        self.fields['panel_serial_photo'].required = False
        self.fields['site_photos_with_customer'].required = False
        
        # Customer rating has a default value in the model, so make it optional in the form
        self.fields['customer_rating'].required = False
        self.fields['customer_rating'].initial = 5
        
        # Ensure numeric fields have correct input type for mobile keyboards
        numeric_float_fields = [
            'ac_cable_used', 'dc_cable_used', 'la_cable_used', 'pipes_used',
            'dc_voltage', 'ac_voltage', 'earthing_resistance',
            'inverter_kw', 'ac_cable_red', 'ac_cable_black', 'dc_cable_red_black', 'la_cable_mtrs',
            'inverter_kw_used', 'ac_cable_red_used', 'ac_cable_black_used', 'dc_cable_red_black_used', 'la_cable_mtrs_used',
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
            'panels_used', 'pipes_count_used', 'earthing_kit_count_used', 'acdb_count_used', 'dcdb_count_used',
            'mc4_connectors_count_used', 'long_l_bands_count_used', 'short_l_bands_count_used', 't_bands_count_used',
            'tapes_red_count_used', 'tapes_black_count_used', 'tags_count_used',
            'nail_clamps_2side_count_used', 'nail_clamps_1side_count_used', 'anchor_hardener_count_used',
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
            'panels_used', 'structure_kit_used', 'inverter_kw_used', 'inverter_phase_type_used',
            'ac_cable_red_used', 'ac_cable_black_used', 'dc_cable_red_black_used', 'la_cable_mtrs_used',
            'pipes_count_used', 'earthing_kit_count_used', 'acdb_count_used', 'dcdb_count_used',
            'mc4_connectors_count_used', 'long_l_bands_count_used', 'short_l_bands_count_used', 't_bands_count_used',
            'tapes_red_count_used', 'tapes_black_count_used', 'tags_count_used',
            'nail_clamps_2side_count_used', 'nail_clamps_1side_count_used', 'anchor_hardener_count_used',
        ]
        for field in materials_fields:
            self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()
        
        # Check that used quantity is not greater than dispatched
        material_pairs = [
            ('panels_count', 'panels_used', 'Panels'),
            ('inverter_kw', 'inverter_kw_used', 'Inverter (kW)'),
            ('ac_cable_red', 'ac_cable_red_used', 'AC Cable Red'),
            ('ac_cable_black', 'ac_cable_black_used', 'AC Cable Black'),
            ('dc_cable_red_black', 'dc_cable_red_black_used', 'DC Cable Red/Black'),
            ('la_cable_mtrs', 'la_cable_mtrs_used', 'LA Cable'),
            ('pipes_count', 'pipes_count_used', 'Pipes'),
            ('earthing_kit_count', 'earthing_kit_count_used', 'Earthing Kit'),
            ('acdb_count', 'acdb_count_used', 'ACDB'),
            ('dcdb_count', 'dcdb_count_used', 'DCDB'),
            ('mc4_connectors_count', 'mc4_connectors_count_used', 'MC4 Connectors'),
            ('long_l_bands_count', 'long_l_bands_count_used', 'Long L Bands'),
            ('short_l_bands_count', 'short_l_bands_count_used', 'Short L Bands'),
            ('t_bands_count', 't_bands_count_used', 'T Bands'),
            ('tapes_red_count', 'tapes_red_count_used', 'Tapes Red'),
            ('tapes_black_count', 'tapes_black_count_used', 'Tapes Black'),
            ('tags_count', 'tags_count_used', 'Tags'),
            ('nail_clamps_2side_count', 'nail_clamps_2side_count_used', 'Nail Clamps 2-Side'),
            ('nail_clamps_1side_count', 'nail_clamps_1side_count_used', 'Nail Clamps 1-Side'),
            ('anchor_hardener_count', 'anchor_hardener_count_used', 'Anchor/Hardener'),
        ]
        
        for disp_field, used_field, name in material_pairs:
            disp_val = cleaned_data.get(disp_field)
            used_val = cleaned_data.get(used_field)
            
            if disp_val is not None and used_val is not None:
                if used_val > disp_val:
                    # add user facing error 
                    self.add_error(used_field, f"Used {name} cannot exceed Dispatched ({disp_val}).")
                    
        return cleaned_data
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
            'workflow_status': 'Approval / Installation Status',
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
        # The user requested to remove mandatory for installation status, discom status, 
        # net metering status, and subsidy status.
        optional_fields = ['workflow_status', 'discom_status', 'net_metering_status', 'subsidy_status']
        for field in optional_fields:
            self.fields[field].required = False

        self.fields['installation_date'].required = False


    def clean_installation_date(self):
        date = self.cleaned_data.get('installation_date')
        # if not date:
        #     raise ValidationError("Installation Completed Date is mandatory.")
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
             'parent_bank': forms.TextInput(attrs={'pattern': r'[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Bank Name must contain only letters.'}),
             'loan_applied_bank': forms.TextInput(attrs={'pattern': r'[a-zA-Z\s]+', 'oninput': "this.value = this.value.replace(/[^a-zA-Z\s]/g, '')", 'title': 'Bank Name must contain only letters.'}),
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
            'title': 'Mobile number must be exactly 10 digits'
        })
    )
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True)
    aadhar_photo = MultipleFileField(
        required=True, 
        help_text="Upload a clear photo or scan of your Aadhar Card.",
        widget=MultipleFileInput(attrs={'class': 'form-control'})
    )
    pan_card = forms.CharField(
        max_length=10, 
        required=True,
        help_text="Enter your 10-digit PAN Card Number.",
        widget=forms.TextInput(attrs={
            'pattern': '^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
            'title': 'Invalid PAN Card formate. Enter correct format of PAN card.',
            'oninput': "this.value = this.value.toUpperCase()",
            'maxlength': '10',
            'minlength': '10',
            'class': 'form-control',
            'autocomplete': 'off'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'type': 'email',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), required=True)

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

    def clean_pan_card(self):
        pan = self.cleaned_data.get('pan_card', '').upper().strip()
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
            raise forms.ValidationError("Invalid PAN Card formate. Enter correct format of PAN card.")
        return pan

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
        fields = ['name', 'mobile_number', 'email', 'address', 'remarks']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
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
        # Make loan fields optional for the Office page
        optional_fields = [
            'first_loan_amount', 'first_loan_utr', 'first_loan_date',
            'second_loan_amount', 'second_loan_utr', 'second_loan_date'
        ]
        for field in optional_fields:
            self.fields[field].required = False
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
    aadhar_photo = MultipleFileField(required=False, widget=MultipleFileInput(attrs={'class': 'form-control'}))
    pan_card_photo = MultipleFileField(required=False, widget=MultipleFileInput(attrs={'class': 'form-control'}))
    
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
            # Legacy single-file fields are now handled via ProfileMedia in views.
            # We don't save the list of files to the single FileField.
            if commit:
                self.user_profile.save()
        return user