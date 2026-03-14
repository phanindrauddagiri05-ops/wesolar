from django.contrib import admin
from .models import CustomerSurvey, Installation, SiteSettings, InstallationPhoto

@admin.register(CustomerSurvey)
class CustomerSurveyAdmin(admin.ModelAdmin):
    # Only allow editing of specific fields in the admin panel as per client request
    list_display = ('customer_name', 'sc_no', 'registration_status', 'created_at')
    list_filter = ('registration_status', 'phase')
    search_fields = ('customer_name', 'aadhar_linked_phone', 'sc_no')

class InstallationPhotoInline(admin.TabularInline):
    model = InstallationPhoto
    extra = 1

@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):
    list_display = ('survey', 'timestamp', 'updated_by')
    inlines = [InstallationPhotoInline]

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'maintenance_mode')

    def has_add_permission(self, request):
        # Only allow one SiteSettings record to exist
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deletion of the settings row