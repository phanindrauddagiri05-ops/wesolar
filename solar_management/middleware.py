from django.shortcuts import render
from django.conf import settings


class MaintenanceModeMiddleware:
    """
    Middleware that intercepts all requests when maintenance mode is ON
    and shows a maintenance page instead.
    Only /admin/ (Django built-in admin) and /maintenance/ are exempt.
    Even staff/admin users are blocked from the custom dashboards.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Import here to avoid AppRegistryNotReady errors at startup
        from .models import SiteSettings

        # Paths that are always accessible regardless of maintenance mode
        exempt_paths = [
            '/admin/',          # Django built-in admin only
            '/maintenance/',    # The maintenance page itself
        ]

        # Check if current path is exempt
        is_exempt = any(request.path.startswith(p) for p in exempt_paths)

        if not is_exempt:
            try:
                site_settings = SiteSettings.get_settings()
                if site_settings.maintenance_mode:
                    return render(request, 'solar/maintenance.html', status=503)
            except Exception:
                pass  # If DB not ready, don't block

        return self.get_response(request)

