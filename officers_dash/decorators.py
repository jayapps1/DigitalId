# decorators.py
from django.shortcuts import redirect
from functools import wraps

def profile_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.profile_completed:
            return redirect("officers_dash:complete_profile")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
