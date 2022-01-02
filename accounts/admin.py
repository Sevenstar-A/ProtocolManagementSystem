from django.contrib import admin
from django.apps import apps 
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Permission

from .models import UserAccount
from accounts.forms import CustomerCreationForm

class UserAdmin(BaseUserAdmin):

    #form = UserChangeForm
    # add_form = CustomerCreationForm

    list_display = ('email','first_name','last_name', 'is_staff','is_customer', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('title','first_name','last_name','profile_image', 'sex')}),
        ('User Type', {'fields': ('is_active','is_customer', 'is_staff','status','position','is_superuser')}),
        ('Permissions', {'fields':('groups','user_permissions')}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email','title', 'first_name','last_name','sex', 'password1', 'password2', 'is_staff','is_customer', 'is_superuser','position', 'profile_image',)}
        ),
    )
    
    search_fields = ('email',)
    ordering = ('email','date_joined')
    filter_horizontal = ('groups', 'user_permissions')

admin.site.register(UserAccount, UserAdmin)

models = apps.get_app_config('accounts').get_models()

for m in models:
    try:
        admin.site.register(m)
    except:
        pass


