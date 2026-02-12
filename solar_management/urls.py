from django.urls import path
from . import views

urlpatterns = [
    # Auth & Landing
    path('', views.landing_page, name='landing'),
    path('login/', views.custom_login_view, name='login'),
    path('admin-portal/login/', views.admin_login_view, name='admin_login'),
    path('signup/', views.signup_view, name='signup'),
    path('admin-portal/approve/<int:pk>/', views.approve_user, name='approve_user'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin Portal (Formerly Office)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/fe-view/<int:pk>/', views.site_detail_fe_view, name='site_detail_fe_view'),
    path('admin-portal/installer-view/<int:pk>/', views.site_detail_installer_view, name='site_detail_installer_view'),

    # New Office Portal
    path('office-dashboard/', views.office_dashboard, name='office_dashboard'),

    # Master Dashboard
    path('dashboard/', views.master_dashboard, name='dashboard'),
    
    # Survey (Field Engineer)

    path('survey/new/', views.create_survey, name='create_survey'),
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
    
    # Enquiry System
    path('enquiry/new/', views.create_enquiry, name='create_enquiry'),
    path('enquiry/list/', views.enquiry_list, name='enquiry_list'),

    # Admin Data Views
    path('admin-portal/fe-data/', views.office_fe_data, name='office_fe_data'),
    path('admin-portal/installer-data/', views.office_installer_data, name='office_installer_data'),
    path('admin-portal/workers-profiles/', views.office_workers_profiles, name='office_workers_profiles'),
]