from django.contrib.auth.decorators import user_passes_test

def installer_only(view_func):
    return user_passes_test(lambda u: u.groups.filter(name='Installers').exists() or u.is_superuser)(view_func)

def admin_only(view_func):
    return user_passes_test(lambda u: u.is_superuser)(view_func)