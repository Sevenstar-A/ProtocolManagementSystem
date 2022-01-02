
from django.contrib.auth.models import AnonymousUser
from accounts.utils import staff_is_active
def user_permissions(request):
    if request.user.is_authenticated and staff_is_active ( request.user ):
        return { 'irb_perms':request.user.get_all_permissions()}
    else:
        return { 'irb_perms':[]}