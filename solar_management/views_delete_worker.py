# Temporary file to hold delete_worker view
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404

@user_passes_test(lambda u: u.userprofile.role == 'Admin')
def delete_worker(request, user_id):
    """Delete a worker user. Admin only."""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        worker_name = user.get_full_name() or user.username
        worker_role = user.userprofile.role if hasattr(user, 'userprofile') else 'User'
        
        # Delete the user (profile will cascade delete)
        user.delete()
        
        messages.success(request, f"{worker_role} '{worker_name}' has been deleted successfully.")
        return redirect('office_workers_profiles')
    
    # If not POST, redirect back
    return redirect('office_workers_profiles')
