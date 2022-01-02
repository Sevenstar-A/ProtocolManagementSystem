from datetime import timezone
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','Blacklion.settings')
from Blacklion.settings import BASE_DIR, MEDIA_ROOT
import django
django.setup()

from core.models import *
from proposal.models import *
from notification.models import *
from django.utils.timesince import timesince as timesince_
from django.utils import timezone
from django.contrib import auth
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.backends import ModelBackend
from accounts.models import Position
from django.db import transaction
from django.templatetags.static import static
from notification.serializers import NotiSerializer, UserNotificationSerializer


from amendment.models import *
from accounts.models import *
from renewal.models import Renewal, RenewalApproval



def _user_get_permissions(user, obj=None, from_name='group'):
    permissions = set()

    name = 'get_%s_permissions' % from_name
    b = auth.get_backends()[0]
    
    print(type(b))
    for backend in auth.get_backends():
        
        if hasattr(backend, name):
            print("backend = ",backend, " \n", )
            print("name = ",name)
            print("att = ",getattr(backend, name)(user, obj))

            permissions.update(getattr(backend, name)(user, obj))
    return permissions

def validate_prot_num(prot_num:str):
    parts = prot_num.split('/')
    if len(parts) != 3:
        return False
    i =  parts[0]
    y = parts[1]
    dn = parts[2]
    e = ""
    if len(i) != 3 or not i.isnumeric() or not int(i) >0:
        e+="Wrong index format, "
        datetime.datetime.today
    if len(y) != 2 or not y.isnumeric() or int(y) > (datetime.today().year - 2000):
        e += "Wrong year format, "
    if not dn in ['anat']:
        e+= "Wrong department name"
    if e == "":
        return True 
    return [False, e] 


# <td><a href = "{{f.doc.url}} " target="_blank" >{{f.doc|get_filename|truncatechars_html:30}}</a></td>
#                                                 <td><a href = "{{f.doc.url}}" download >download</a></td>
#                                                 <td><a onclick="delete_item('{{f.id}}')"><i id="other_icon_{{f.id}}" class="fa fa-trash red"></i></a></td>
def v(x):
    px = SystemConstant.objects.get(name ='Protocol Prefix')
    px= int(px.value.split('/')[0])
    if x > px:
        print ("You are using a protocol number from the future! Correct your input.")
    else:
        print("good!") 
     
if __name__ == '__main__':
    
    for r in RenewalApproval.objects.all():
        r.start_date = timezone.now() 
        r.end_date = timezone.now() 
        r.progress_report_duration = 6
        r.save()
