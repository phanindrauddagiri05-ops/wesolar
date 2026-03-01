from django.shortcuts import render
from django.conf import settings


class MaintenanceModeMiddleware:
    """
    Middleware that intercepts all requests when maintenance mode is ON
    and shows a maintenance page instead.
    Admin users and the admin portal URLs are exempt.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Import here to avoid AppRegistryNotReady errors at startup
        from .models import SiteSettings

        # Paths that are always accessible regardless of maintenance mode
        exempt_paths = [
            '/admin/',          # Django built-in admin
            '/maintenance/',    # The maintenance page itself
        ]

        # Check if current path is exempt
        is_exempt = any(request.path.startswith(p) for p in exempt_paths)

        # Check if user is a staff/admin — they bypass maintenance
        is_admin = request.user.is_authenticated and request.user.is_staff

        if not is_exempt and not is_admin:
            try:
                site_settings = SiteSettings.get_settings()
                if site_settings.maintenance_mode:
                    return render(request, 'solar/maintenance.html', status=503)
            except Exception:
                pass  # If DB not ready, don't block

        return self.get_response(request)
