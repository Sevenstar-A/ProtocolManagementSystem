
from django.contrib.auth import decorators
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def user_is_active(user):
    if  user.is_active and user.status == 2:
        return True 
    return False


def staff_is_active(user):
    """
    check if user is active and is staff
    """
    if user_is_active(user) and user.is_staff:
        return True 
    return False


def user_required():
    def decorator(view_func):
        def wrap(request,*args,**kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            elif not user_is_active(request.user):
                raise PermissionDenied
            else:
                return view_func(request,*args,**kwargs) 
        return wrap
    return decorator


def staff_required():
    def decorator(view_func):
        def wrap(request,*args,**kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            elif not staff_is_active(request.user):
                raise PermissionDenied
            else:
                return view_func(request,*args,**kwargs) 

        return wrap
    return decorator
