from django.urls import path
from . import views

urlpatterns = [
    # Auth & Landing
    path('', views.custom_login_view, name='login'), # Login is now Home
    # path('login/', views.custom_login_view, name='login'), # Removed redundant path
    path('admin-portal/login/', views.admin_login_view, name='admin_login'),
    path('signup/', views.signup_view, name='signup'),
    path('admin-portal/approve/<int:pk>/', views.approve_user, name='approve_user'),
    path('admin-portal/reject/<int:pk>/', views.reject_user, name='reject_user'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin Portal (Formerly Office)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/fe-view/<int:pk>/', views.site_detail_fe_view, name='site_detail_fe_view'),
    path('admin-portal/installer-view/<int:pk>/', views.site_detail_installer_view, name='site_detail_installer_view'),

    # New Office Portal
    path('office-dashboard/', views.office_dashboard, name='office_dashboard'),
    path('office/update-status/<int:pk>/', views.office_update_status, name='office_update_status'),

    # Master Dashboard
    path('dashboard/', views.master_dashboard, name='dashboard'),
    path('loan-dashboard/', views.loan_dashboard, name='loan_dashboard'),
    path('search/', views.global_search, name='global_search'),
    path('api/search/', views.api_global_search, name='api_global_search'),
    
    # Survey (Field Engineer)

    path('survey/new/', views.survey_form_view, name='create_survey'),
    path('survey/update/<int:pk>/', views.update_survey, name='update_survey'),
    path('survey/restart/<int:pk>/', views.delete_and_restart, name='delete_and_restart'),
    
    # Installation (Installer)
    path('installation/update/<int:pk>/', views.update_installation, name='update_installation'),
    
    # Bank (Finance)
    path('bank/new/', views.bank_entry, name='bank_entry'),
    
    # Details & Admin Actions
    path('site/<int:pk>/', views.site_detail, name='site_detail'),
    path('toggle-registration/<int:pk>/', views.toggle_registration, name='toggle_registration'),
    
    # Export & API
    path('export/csv/', views.export_solar_data, name='export_solar_data'),
    path('api/get-customer-data/', views.get_customer_data, name='get_customer_data'),
    path('api/get-bank-details/', views.get_bank_details_by_phone, name='get_bank_details_by_phone'),
    
    # Enquiry System
    path('enquiry/new/', views.create_enquiry, name='create_enquiry'),
    path('enquiry/list/', views.enquiry_list, name='enquiry_list'),

    # Admin Data Views
    path('office-portal/fe-data/', views.office_fe_data, name='office_fe_data'),
    path('office-portal/installer-data/', views.office_installer_data, name='office_installer_data'),
    path('office-portal/workers-profiles/', views.office_workers_profiles, name='office_workers_profiles'),
]