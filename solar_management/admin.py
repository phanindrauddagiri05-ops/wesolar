from django.contrib import admin
from .models import CustomerSurvey, Installation

@admin.register(CustomerSurvey)
class CustomerSurveyAdmin(admin.ModelAdmin):
    # Only allow editing of specific fields in the admin panel as per client request
    list_display = ('customer_name', 'sc_no', 'registration_status', 'created_at')
    list_filter = ('registration_status', 'phase')
    search_fields = ('customer_name', 'aadhar_linked_phone', 'sc_no')

admin.site.register(Installation)