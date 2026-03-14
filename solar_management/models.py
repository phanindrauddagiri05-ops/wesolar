from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('Field Engineer', 'Field Engineer'),
        ('Installer', 'Installer'),
        ('Office', 'Office'),
        ('Admin', 'Admin'),
        ('Loan', 'Loan'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    worker_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_approved = models.BooleanField(default=False)
    plain_password = models.CharField(max_length=128, blank=True, help_text="Stored for admin reference only")
    aadhar_photo = models.FileField(upload_to='users/documents/', null=True, blank=True, help_text="Photo/Scan of Aadhar Card")
    pan_card_photo = models.FileField(upload_to='users/documents/', null=True, blank=True, help_text="Photo/Scan of PAN Card")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new or not self.worker_id:
            self.worker_id = f"WS-USR-{self.id:04d}"
            super().save(update_fields=['worker_id'])

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class CustomerSurvey(models.Model):
    # --- Field Engineer Section ---
    CONNECTION_CHOICES = [('Domestic', 'Domestic'), ('Commercial', 'Commercial'), ('GHS', 'GHS')]
    PHASE_CHOICES = [('Single Phase', 'Single Phase'), ('Three Phase', 'Three Phase')]
    ROOF_CHOICES = [('Normal', 'Normal'), ('Plastic shed', 'Plastic shed'), ('Cement shed', 'Cement shed')]
    STRUCTURE_CHOICES = [('Normal', 'Normal'), ('Vertical', 'Vertical'), ('Horizontal', 'Horizontal'), ('Fabrication', 'Fabrication')]

    customer_name = models.CharField(max_length=255)
    application_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    connection_type = models.CharField(max_length=50, choices=CONNECTION_CHOICES)
    sc_no = models.CharField(max_length=16, help_text="16 Digits")
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)
    contracted_load = models.FloatField(default=0.0, help_text="Contracted Load (KW)") # New Field
    feasibility_kw = models.FloatField(help_text="Maximum KW (Applied Solar Load)")
    aadhar_no = models.CharField(max_length=12, help_text="12 Digits") 
    pan_card = models.CharField(max_length=10, help_text="10 Digits")
    email = models.EmailField()
    aadhar_linked_phone = models.CharField(max_length=10, default="0000000000", help_text="10 Digits")
    bank_account_no = models.CharField(max_length=30, blank=True) 
    phone_number = models.CharField(max_length=15, null=True, blank=True) # Restored for Office Search
    
    # Roof & Structure
    roof_type = models.CharField(max_length=100, choices=ROOF_CHOICES)
    roof_photo = models.ImageField(upload_to='surveys/roofs/', null=True, blank=True, help_text="Mandatory if critical site")
    
    # Document Photos (FileField to accept all formats: PDF, HEIC, JPG, PNG, etc.)
    pan_card_photo = models.FileField(upload_to='surveys/documents/', null=True, blank=True, help_text="Photo/Scan of PAN Card")
    aadhar_photo = models.FileField(upload_to='surveys/documents/', null=True, blank=True, help_text="Photo/Scan of Aadhar Card")
    current_bill_photo = models.FileField(upload_to='surveys/documents/', null=True, blank=True, help_text="Photo/Scan of Current Electricity Bill")
    bank_account_photo = models.FileField(upload_to='surveys/documents/', null=True, blank=True, help_text="Photo/Scan of Bank Account")
    structure_type = models.CharField(max_length=100, choices=STRUCTURE_CHOICES)
    structure_height = models.FloatField(help_text="in Feet")
    floors = models.PositiveIntegerField(null=True, blank=True, help_text="Number of Floors")
    gps_coordinates = models.CharField(max_length=100)
    AREA_CHOICES = [
        ('Rajahmundry', 'Rajahmundry'),
        ('Kovvur', 'Kovvur'),
        ('Mandapeta', 'Mandapeta'),
        ('Nidadavole', 'Nidadavole'),
        ('Others', 'Others'),
    ]
    area = models.CharField(max_length=255)
    measurements = models.CharField(max_length=255, help_text="Measurements (Square Feet)", null=True, blank=True)
    
    # Pricing & Status
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    advance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    mefma_status = models.BooleanField(default=False, help_text="Yes if MEFMA, No if Not")
    rp_name = models.CharField(max_length=255, null=True, blank=True)
    rp_phone_number = models.CharField(max_length=15, null=True, blank=True)
    co_name = models.CharField(max_length=255, null=True, blank=True)
    co_phone_number = models.CharField(max_length=15, null=True, blank=True)
    reference_name = models.CharField(max_length=255, null=True, blank=True, help_text="Reference Name if not MEFMA")
    fe_remarks = models.TextField(blank=True)
    pms_registration_number = models.CharField(max_length=50, blank=True) 
    division = models.CharField(max_length=100, blank=True) 
    registration_status = models.BooleanField(default=False) 
    registration_date = models.DateField(null=True, blank=True)
    
    parent_bank_photo = models.FileField(upload_to='surveys/documents/', null=True, blank=True, help_text="Photo/Scan of Parent Bank Front Page")

    # Office Tracking Fields
    STATUS_CHOICES = [('Pending', 'Pending'), ('Completed', 'Completed')]
    
    installation_date = models.DateField(null=True, blank=True) # New Field
    
    discom_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    net_metering_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    subsidy_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    office_remarks = models.TextField(blank=True)

    WORKFLOW_STATUS_CHOICES = [('Pending', 'Pending'), ('Completed', 'Completed')]
    workflow_status = models.CharField(max_length=20, choices=WORKFLOW_STATUS_CHOICES, default='Pending')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new or not self.application_id:
            self.application_id = f"WS-APP-{self.id:05d}"
            super().save(update_fields=['application_id'])

    def __str__(self):
        return f"{self.customer_name} ({self.sc_no})"
    
    @property
    def masked_aadhar(self):
        if self.aadhar_no and len(self.aadhar_no) == 12:
            return f"********{self.aadhar_no[-4:]}"
        return "Invalid Aadhar"

    @property
    def masked_pan(self):
        if self.pan_card and len(self.pan_card) == 10:
            return f"******{self.pan_card[-4:]}"
        return "Invalid PAN"

    @property
    def has_installation(self):
        return hasattr(self, 'installation')

class Installation(models.Model):
    STRUCTURE_KIT_CHOICES = [('Normal', 'Normal'), ('Fabrication', 'Fabrication')]
    INVERTER_PHASE_TYPE_CHOICES = [('Single Phase', 'Single Phase'), ('Three Phase', 'Three Phase')]
    # --- Installer Section ---
    survey = models.OneToOneField(CustomerSurvey, on_delete=models.CASCADE, related_name='installation')
    
    # Tech Details
    inverter_make = models.CharField(max_length=100)
    inverter_phase = models.CharField(max_length=50, blank=True)
    inverter_serial_number = models.CharField(max_length=200, blank=True, help_text="Inverter Serial Number(s)")
    inverter_serial_photo = models.ImageField(upload_to='installations/inverters/', null=True, blank=True)
    inverter_acdb_photo = models.ImageField(upload_to='installations/acdb/', null=True, blank=True)
    panel_serial_numbers = models.TextField(blank=True, help_text="Panel Serial Numbers (one per line or comma separated)")
    panel_serial_photo = models.ImageField(upload_to='installations/panels/', null=True, blank=True)
    
    # Measurements
    ac_cable_used = models.FloatField(help_text="in Meters", null=True, blank=True)
    dc_cable_used = models.FloatField(help_text="in Meters", null=True, blank=True)
    la_cable_used = models.FloatField(help_text="in Meters", default=0.0, null=True, blank=True)
    pipes_used = models.FloatField(help_text="in Meters", default=0.0, null=True, blank=True)
    leftover_materials = models.TextField(blank=True)
    
    # Status & Remarks
    warranty_claimed = models.BooleanField(default=False)
    app_installation_status = models.BooleanField(default=False)
    site_photos_with_customer = models.ImageField(upload_to='installations/site/', null=True, blank=True)
    
    installer_remarks = models.TextField(blank=True)
    customer_remarks = models.TextField(blank=True)
    customer_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5, help_text="Rate the experience (1-5)")
    
    # Electrical Readings
    dc_voltage = models.FloatField(default=0.0, help_text="in Volts") # New Field
    ac_voltage = models.FloatField(default=0.0, help_text="in Volts") # New Field
    earthing_resistance = models.FloatField(default=0.0, help_text="in Ohms") # New Field

    # --- Materials Used Section ---
    panels_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Panels")
    structure_kit_type = models.CharField(max_length=20, choices=STRUCTURE_KIT_CHOICES, blank=True, default='Normal', help_text="Normal / Fabrication")
    inverter_kw = models.FloatField(default=0.0, blank=True, help_text="Inverter capacity in kW")
    inverter_phase_type = models.CharField(max_length=20, choices=INVERTER_PHASE_TYPE_CHOICES, blank=True, default='Single Phase', help_text="Single / Three Phase")
    ac_cable_red = models.FloatField(default=0.0, blank=True, help_text="AC Cable Red in Meters")
    ac_cable_black = models.FloatField(default=0.0, blank=True, help_text="AC Cable Black in Meters")
    dc_cable_red_black = models.FloatField(default=0.0, blank=True, help_text="DC Cable Red & Black in Meters")
    la_cable_mtrs = models.FloatField(default=0.0, blank=True, help_text="LA Cable in Meters")
    pipes_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Pipes")
    earthing_kit_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Earthing Kits")
    acdb_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of ACDBs")
    dcdb_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of DCDBs")
    mc4_connectors_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of MC4 Connectors")
    long_l_bands_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Long L Bands")
    short_l_bands_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Short L Bands")
    t_bands_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of T Bands")
    tapes_red_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Red Tapes")
    tapes_black_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Black Tapes")
    tags_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Tags")
    nail_clamps_2side_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of 2-Side Nail Clamps")
    nail_clamps_1side_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of 1-Side Nail Clamps")
    anchor_hardener_count = models.PositiveIntegerField(default=0, blank=True, help_text="Number of Anchor Hardeners")

    timestamp = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Installation for {self.survey.customer_name}"
class InstallationPhoto(models.Model):
    PHOTO_TYPE_CHOICES = [
        ('inverter_serial', 'Inverter Serial'),
        ('inverter_acdb', 'Inverter ACDB'),
        ('panel_serial', 'Panel Serial'),
        ('site_with_customer', 'Site with Customer'),
        ('additional', 'Additional Site Photos'),
    ]
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name='additional_photos')
    photo = models.ImageField(upload_to='installations/site_additional/')
    photo_type = models.CharField(max_length=50, choices=PHOTO_TYPE_CHOICES, default='additional')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_photo_type_display()} for {self.installation.survey.customer_name}"

class SurveyMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('roof', 'Roof Photos'),
        ('pan_card', 'PAN Card'),
        ('aadhar', 'Aadhar Card'),
        ('current_bill', 'Current Bill'),
        ('bank_account', 'Bank Account'),
        ('parent_bank', 'Parent Bank'),
    ]
    survey = models.ForeignKey(CustomerSurvey, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='surveys/media/')
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_media_type_display()} for {self.survey.customer_name}"

class ProfileMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('aadhar', 'Aadhar Card'),
        ('pan_card', 'PAN Card'),
    ]
    profile = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='profiles/media/')
    media_type = models.CharField(max_length=50, choices=MEDIA_TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_media_type_display()} for {self.profile.user.username}"

class BankDetails(models.Model):
    survey = models.OneToOneField('CustomerSurvey', on_delete=models.CASCADE, related_name='bank_details')
    
    # Bank Info
    parent_bank = models.CharField(max_length=100)
    parent_bank_ac_no = models.CharField(max_length=20)
    loan_applied_bank = models.CharField(max_length=100)
    loan_applied_ifsc = models.CharField(max_length=11)
    loan_applied_ac_no = models.CharField(max_length=20)
    manager_number = models.CharField(max_length=15, blank=True, null=True) # New field for Loan Dashboard
    
    # Loan Tracking
    LOAN_STATUS_CHOICES = [('Pending', 'Pending'), ('Completed', 'Completed')]
    loan_pending_status = models.CharField(max_length=20, choices=LOAN_STATUS_CHOICES, default='Pending')
    
    # First Loan
    first_loan_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    first_loan_utr = models.CharField(max_length=50, blank=True)
    first_loan_date = models.DateField(null=True, blank=True)
    
    # Second Loan
    second_loan_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    second_loan_utr = models.CharField(max_length=50, blank=True)
    second_loan_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Finances for {self.survey.customer_name}"

class Enquiry(models.Model):
    name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=15)
    address = models.TextField()
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Enquiry from {self.name} ({self.mobile_number})"

class SiteSettings(models.Model):
    """Singleton model to store global site settings like maintenance mode."""
    maintenance_mode = models.BooleanField(default=False, help_text="When enabled, all pages show a maintenance screen.")

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj