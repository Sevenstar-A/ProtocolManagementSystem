from django.contrib.auth.models import Permission
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required


def Index(request):
    return render(request, "blacklion/index.html")

@login_required
def CoreDashboard(request):
    if request.user.is_staff:
        return redirect('irb:home')
        
def check(request):
    return render(request, "check.html", {})

