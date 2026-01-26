from django.core.exceptions import PermissionDenied

def admin_only(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper
