from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. Admin Interface
    path('admin/', admin.site.urls),

    # 2. Authentication (Login/Logout)
    # This points to templates/registration/login.html
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # 3. Solar Management App URLs
    # This pulls in all routes from solar_management/urls.py
    path('', include('solar_management.urls')),
]

# 4. Media & Static Files Support
# Necessary for viewing uploaded Panel/Inverter photos during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)