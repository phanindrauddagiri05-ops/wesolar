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
    mobile_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class CustomerSurvey(models.Model):
    # --- Field Engineer Section ---
    CONNECTION_CHOICES = [('Domestic', 'Domestic'), ('Commercial', 'Commercial'), ('GHS', 'GHS')]
    PHASE_CHOICES = [('Single Phase', 'Single Phase'), ('Three Phase', 'Three Phase')]
    ROOF_CHOICES = [('Normal', 'Normal'), ('Plastic shed', 'Plastic shed'), ('Cement shed', 'Cement shed')]
    STRUCTURE_CHOICES = [('Normal', 'Normal'), ('Vertical', 'Vertical'), ('Horizontal', 'Horizontal')]

    customer_name = models.CharField(max_length=255)
    connection_type = models.CharField(max_length=50, choices=CONNECTION_CHOICES)
    sc_no = models.CharField(max_length=16, help_text="16 Digits")
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)
    feasibility_kw = models.FloatField(help_text="Maximum KW (Applied Solar Load)")
    aadhar_no = models.CharField(max_length=12, help_text="12 Digits") 
    pan_card = models.CharField(max_length=10, help_text="10 Digits")
    email = models.EmailField()
    aadhar_linked_phone = models.CharField(max_length=10, default="0000000000", help_text="10 Digits")
    bank_account_no = models.CharField(max_length=30, blank=True) 
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True) # Restored for Office Search
    
    # Roof & Structure
    roof_type = models.CharField(max_length=100, choices=ROOF_CHOICES)
    roof_photo = models.ImageField(upload_to='surveys/roofs/', null=True, blank=True, help_text="Mandatory if critical site")
    structure_type = models.CharField(max_length=100, choices=STRUCTURE_CHOICES)
    structure_height = models.FloatField(help_text="in Feet")
    gps_coordinates = models.CharField(max_length=100)
    area = models.CharField(max_length=255)
    
    # Pricing & Status
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    advance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    mefma_status = models.BooleanField(default=False, help_text="Is MEFMA approved?")
    rp_name = models.CharField(max_length=255, blank=True, null=True)
    rp_phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    fe_remarks = models.TextField(blank=True)
    reference_name = models.CharField(max_length=255, blank=True) 
    pms_registration_number = models.CharField(max_length=50, blank=True) 
    division = models.CharField(max_length=100, blank=True) 
    registration_status = models.BooleanField(default=False) 
    
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
    # --- Installer Section ---
    survey = models.OneToOneField(CustomerSurvey, on_delete=models.CASCADE, related_name='installation')
    
    # Tech Details
    inverter_make = models.CharField(max_length=100)
    inverter_phase = models.CharField(max_length=50, blank=True)
    inverter_serial_photo = models.ImageField(upload_to='installations/inverters/')
    inverter_acdb_photo = models.ImageField(upload_to='installations/acdb/', null=True, blank=True)
    panel_serial_photo = models.ImageField(upload_to='installations/panels/')
    
    # Measurements
    ac_cable_used = models.FloatField(help_text="in Meters")
    dc_cable_used = models.FloatField(help_text="in Meters")
    la_cable_used = models.FloatField(help_text="in Meters", default=0.0)
    pipes_used = models.FloatField(help_text="in Meters", default=0.0)
    leftover_materials = models.TextField(blank=True)
    
    # Status & Remarks
    warranty_claimed = models.BooleanField(default=False)
    app_installation_status = models.BooleanField(default=False)
    site_photos_with_customer = models.ImageField(upload_to='installations/site/')
    
    installer_remarks = models.TextField(blank=True)
    customer_remarks = models.TextField(blank=True)
    
    # Electrical Readings
    dc_voltage = models.FloatField(default=0.0, help_text="in Volts") # New Field
    ac_voltage = models.FloatField(default=0.0, help_text="in Volts") # New Field
    earthing_resistance = models.FloatField(default=0.0, help_text="in Ohms") # New Field
    
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Installation for {self.survey.customer_name}"
    


# ... Ensure your CustomerSurvey and Installation models are above this ...

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
    LOAN_STATUS_CHOICES = [('First', 'First'), ('Second', 'Second'), ('Both', 'Both'), ('Pending', 'Pending')]
    loan_pending_status = models.CharField(max_length=20, choices=LOAN_STATUS_CHOICES)
    
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