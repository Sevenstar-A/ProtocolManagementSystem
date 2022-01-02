import threading
from django.contrib import messages
from django.contrib.auth import authenticate, get_user, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.messages.api import info
from django.core.mail import message
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from accounts.models import get_permitted_staffs
from notification.models import notify

from accounts.utils import *

from accounts.forms import *

from .emails import account_activation_token, email_acc_activation


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = UserAccount.objects.get(id=uid)
    except Exception as e:
        # (TypeError, ValueError, OverflowError, UserAccount.DoesNotExist):
        print("@@@ Exception:- ", e)
        user = None
    if user is not None:
        if account_activation_token.check_token(user, token):
            if user.status == 0:
                user.is_active = True
                if user.is_customer:
                    user.status = 2
                else:
                    user.status = 1 # email confirmed but unverified stuff account, 
                user.save()
                if user.is_staff: #if user is staff send notification for irb staffs to activate the account
                    activators = get_permitted_staffs('can_update_user') 
                    print("############ activators", activators)
                    notify(activators,'info', f"New staff user registration needs account activation.",link = f"/accounts/edit_user_account/{user.id}/",
                    desc= f"A user named {user.full_name} has confirmed his/her email account and is requesting account activation.")
                
                if user.is_customer:
                    messages.success(request, "Congradulations, You have successfully activated your email! ", extra_tags=('index'))
                    login(request, user)
                    return redirect('/')
                else:
                    messages.success(request, "Congradulations, You have successfully activated your EMAIL! ", extra_tags='login')
                    messages.info(request, "Your account need to be verified by system admins! You will recieve an email notification, please wait. Thank you.", extra_tags='login')
            
        else:
            messages.error(request, "Error, Activation link is invalid!", extra_tags='login')
    else:
        messages.error(request, "Error, User not found")
        
    return redirect("accounts:login")
        

def loginview(request):
    if request.user.is_authenticated:
        if request.user.is_staff :
            return redirect ('irb:home')
        else:
            return redirect('index')

    else:
        if request.method == 'POST':
            email = request.POST.get('email')
            password = request.POST.get('password')
            form = AuthenticationForm(request)
            user = authenticate(request, username = email, password = password)
            if user is not None:
                # for status == 0, the user = None in z 1st place, bcz:- status = 1 after email confirmation
                if user.status == 0:
                    return redirect('accounts:confirm_email', email=user.email)
                
                elif user.status == 1: # need account activation (for staff accounts only)
                    return render(request, "registration/unverified.html")

                elif user.status == 2: # can login and use system
                    login(request, user)
                    if user.is_customer:
                        return redirect ('irb:home')
                    else:
                        return redirect('irb:home')
                
                else:  # suspeded but not deleted account 
                    return render(request, "registration/suspended.html")

            else: # pseudo delete (the system admins delete z account, but the system has it as is_active = False)
                messages.warning(request, 'Email or password is wrong!', extra_tags="login")
                return render(request, 'registration/login.html', {'form':form})

        return render(request, 'registration/login.html', {'form':AuthenticationForm})


def logoutview(request):
    logout(request)
    return redirect('/')        


class EmailAcctivationThread(threading.Thread):
    def __init__(self, user, request):
        self.user = user 
        self.request= request
        threading.Thread.__init__(self) 

    def run(self):
        try:
            email_acc_activation(self.user, self.request)
        except Exception as e:
            print("Exception ", e)


class CustomerSignup(View):
    def get(self, *args, **kwargs):
        return render(self.request, "registration/client_signup.html", {'form':CustomerCreationForm})
    def post(self, *args, **kwargs):
        form = CustomerCreationForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            # check if terms of agreement is checked
            agree_checkbox = self.request.POST.get('agree_chkbox', None)
            if not agree_checkbox:
                messages.error(self.request, "Please read the terms of service and select the checkbox.")
                return render(self.request, "registration/client_signup.html", {'form':form})
            # password validation
            password = form.data['password1']
            try:
                validate_password(password)
            except ValidationError as e:
                form.add_error('password2', e.error_list)
                messages.error(self.request, "Please re-check your inputs!", extra_tags="staff_signup")
                return render(self.request, "registration/client_signup.html", {'form':form})
            user =form.save()
            messages.success(self.request, "You have created a new account. Please confirm your email address! ", extra_tags="confirm_email")
            
            EmailAcctivationThread(user, self.request).start()
            return redirect("accounts:confirm_email", user.email)
            # email = email_acc_activation(user, self.request)
            # if email:
                # return redirect("accounts:confirm_email", user.email)
            # else:
            #     return render(self.request, "registration/acc_verif_email_notsent.html", {'user', user})

        else:
            messages.error(self.request, "Please re-check your inputs!")
            return render(self.request, "registration/client_signup.html", {'form':form})
            
 
class AdminSignup(View):
    def get(self, *args, **kwargs):
        return render(self.request, "registration/staff_signup.html", {'form':IrbStaffCreationForm})
    
    def post(self, *args, **kwargs):
        form = IrbStaffCreationForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            agree_checkbox = self.request.POST.get('agree_chkbox', None)
            if not agree_checkbox:
                messages.error(self.request, "Please read the terms of service and select the checkbox.")
                return render(self.request, "registration/staff_signup.html", {'form':form})
            # password validation
            password = form.data['password1']
            try:
                validate_password(password)
            except ValidationError as e:
                form.add_error('password2', e.error_list)
                messages.error(self.request, "Please re-check your inputs!", extra_tags="staff_signup")
                return render(self.request, "registration/staff_signup.html", {'form':form})
            user= form.save(commit=True)
            # notification 
            # notify(UserAccount.objects.filter(position__name = 'Secreteriat Officer'),'info', f"A staff named '{c.full_name}' need registration confirmation."
            # ,desc=f"A new user has been registred by the name '{c.full_name}' at {c.date_joined.date}" ,link='/irb/list_users/all/')
            EmailAcctivationThread(user, self.request).start()
            return redirect("accounts:confirm_email", user.email)         
        else:
            print(form.errors)
            messages.error(self.request, "Please re-check your inputs!", extra_tags="staff_signup")
            return render(self.request, "registration/staff_signup.html", {'form':form})


class ConfirmEmail(View):
    def get(self, *args, **kwargs):
        try:
            user = UserAccount.objects.get(email = self.kwargs['email'])
            if user.status == 0:
                return render(self.request, "registration/confirm_email.html", {'user':user})
            else:
                messages.info(self.request, "This email has been activated previsouly", extra_tags='-')
                return redirect('accounts:login')
                
        except Exception as e:
            messages.error(self.request, "Account could not be found!", extra_tags='login')
            print("Exception...",e)
            return redirect("accounts:login")

    # for re-send confirmation
    def post(self, *args, **kwargs):
        try:
            user = UserAccount.objects.get(id = self.request.POST.get('uid'))
            EmailAcctivationThread(user, self.request).start()
            return redirect("accounts:confirm_email", user.email)
            
        except Exception as e:
            messages.error(self.request, "Error! An Unexpected exception occured. Try again later.")
            print("Exception ", e)
            return redirect("account:login")

@method_decorator(user_required(), 'dispatch')
class MyProfile(View):
    def get(self, *args, **kwargs):
        user_form = UserAccountForm(instance=self.request.user)
        user_form.fields['position'].disabled = True # a user can't change his own position
        user_form.fields.pop('user_permissions')
        password_form = ChangePasswordForm()
        return render(self.request, 'accounts/account_settings.html', {
            'my_profile':True,
            'profile_image':self.request.user.profile_image,
            'user_account': self.request.user,
            'user_account_form': user_form,
            'password_form': password_form,
        })

    def post(self, *args, **kwargs):
        form = UserAccountForm(instance=self.request.user, data=self.request.POST, files=self.request.FILES)
        # remove email and position
        form.fields.pop('email')
        form.fields.pop('position')
        if form.is_valid():
            form.save()
            messages.success(self.request, "You have updated your account successfully!")
            return redirect('accounts:my_profile')
        else:
            print(form.errors)
            messages.error(self.request, "Error! Invalid form input, please re-check your inputs again!")
            password_form = ChangePasswordForm()
            return render(self.request, 'accounts/account_settings.html', {
            'user_account': self.request.user,
            'profile_image':self.request.user.profile_image,
            'user_account_form': form,
            'password_form': password_form,
        })
            
@method_decorator(user_required(), 'dispatch')
class AccountSetting( View):

    # logged in users account setting
    def get(self, *args, **kwargs):
        logged_in_user = get_user(self.request)
        user_account_form = UserAccountForm(instance=logged_in_user)
        # title and email can only be edited through admin
        # disable them in GET requests and remove them in the POST
        user_account_form.fields['title'].disabled = True
        user_account_form.fields['email'].disabled = True
        user_account_form.fields['position'].disabled = True
        password_form = ChangePasswordForm()
        return render(self.request, 'accounts/account_settings.html', {
                        'user_account': logged_in_user,
                        'user_account_form': user_account_form,
                        'password_form': password_form,
        })

    def post(self, *args, **kwargs):
        logged_in_user = get_user(self.request)
        form = UserAccountForm(instance=logged_in_user, data=self.request.POST, files=self.request.FILES)
        # remove email and title
        form.fields.pop('email')
        form.fields.pop('title')
        form.fields.pop('position')
        if form.is_valid():
            form.save()
            messages.success(self.request, "User account updated successfully!!!")
            return redirect('accounts:account_setting')
        else:
            print("Errors occured in account settings form: ", form.errors)

@method_decorator(user_required(), 'dispatch')
class ChangePassword( View):
    def post(self, *args, **kwargs):
        
        logged_in_user = get_user(self.request)
        form = ChangePasswordForm(data=self.request.POST)
        if form.is_valid():
            # check if current password is correct
            if logged_in_user.check_password(form.data['current_password']):
                # check if new_password and retyped_password are same
                if form.data['new_password'] == form.data['retype_new_password']:
                    new_password = form.data['new_password']
                    try:
                        validate_password(new_password)
                    except ValidationError as e:
                        for error in e.error_list:
                            messages.error(self.request, error.messages[0])
                        return redirect('accounts:account_setting')
                    logged_in_user.set_password(new_password)
                    logged_in_user.save()
                    # login the current user b/c changing password
                    # invalidates the session
                    login(self.request, logged_in_user)
                    messages.success(self.request, 'Password Changed successfully!!!')
                    return redirect('accounts:account_setting')
                else:
                    messages.error(self.request, 'Entered new passwords do no match')
                    return redirect('accounts:account_setting')
            else:
                messages.error(self.request, 'Wrong password entered.')
                return redirect('accounts:account_setting')
        else:
            for error in form.errors:
                messages.error(self.request, f"{error}: {form.errors[error]}")
            return redirect('accounts:account_setting')

@method_decorator(staff_required(), 'dispatch')
class ResetPassword( PermissionRequiredMixin, View):
    permission_required = ['irb.can_update_user']
    def post(self, *args, **kwargs):
        
        user_id = None
        reset_password_form = ChangePasswordForm(data=self.request.POST)
        reset_password_form.fields.pop('current_password')
        reset_password_form.fields.update({'user_id': forms.IntegerField()})
        user_id = reset_password_form.data['user_id']
        user = UserAccount.objects.get(id=user_id)
        if reset_password_form.is_valid():
            # check if new_password and retyped_password are same
            if reset_password_form.data['new_password'] == reset_password_form.data['retype_new_password']:
                new_password = reset_password_form.data['new_password']
                try:
                    validate_password(new_password)
                except ValidationError as e:
                    for error in e.error_list:
                        messages.error(self.request, error.messages[0])
                    return redirect('accounts:edit_user_account', user_id)
                user.set_password(new_password)
                user.save()
                messages.success(self.request, 'Password Changed successfully!!!')
                return redirect('accounts:edit_user_account', user_id)
            else:
                messages.error(self.request, 'Entered new passwords do no match')
                return redirect('accounts:edit_user_account', user_id)
        else:
            messages.error(self.request, 'Error while reseting password')
            return redirect('accounts:edit_user_account', user_id)


@method_decorator(staff_required(), 'dispatch')
class UsersList( PermissionRequiredMixin, View):
    permission_required = ['irb.can_list_user']
    def get(self, *args, **kwargs):
        if 'type' in self.kwargs:
            is_staff = True if self.kwargs['type']=='staff' else False
            list_type = self.kwargs['type']
            users = UserAccount.objects.select_related('title').filter(is_staff = is_staff) 
        else:
            list_type = None
            users = UserAccount.objects.select_related('title').all()
        return render(self.request, 'accounts/users_list.html', {'users_list':users, 'type': list_type}) 


@method_decorator(staff_required(), 'dispatch')
class EditUserAccount( PermissionRequiredMixin, View):
    permission_required = ['irb.can_update_user']
    # auth and admin
    def get(self, *args, **kwargs):
        user_id = kwargs['user_id']
        user = UserAccount.objects.get(id=user_id)
        if user == self.request.user:
            # messages.warning(self.request, "You cannot have admin level update for your own account! But can update your profile.")
            return redirect("accounts:my_profile")

        user_account_form = UserAccountForm(instance=user, edit=True)
        reset_password_form = ChangePasswordForm()
        # remove current_password field from form
        reset_password_form.fields.pop('current_password')
        user_id_field = forms.IntegerField(widget=forms.NumberInput(attrs={
            'type': 'hidden',
            'value': user_id,
        }))
        reset_password_form.fields.update({'user_id': user_id_field})
        return render(self.request, 'accounts/edit_account.html', {
            'user_account_form': user_account_form,
            'profile_image':user.profile_image,
            'password_form': reset_password_form,
            'user_account': user,
        })


    def post(self, *args, **kwargs):
        user_id = kwargs['user_id']
        user = UserAccount.objects.get(id=user_id)
        user_account_form = UserAccountForm(instance=user, data=self.request.POST, files=self.request.FILES)
        reset_password_form = ChangePasswordForm( data=self.request.POST, files=self.request.FILES)
        user_account_form.fields.pop('email')
        reset_password_form.fields.pop('current_password')
        user_id_field = forms.IntegerField(widget=forms.NumberInput(attrs={
            'type': 'hidden',
            'value': user_id,
        }))
        reset_password_form.fields.update({'user_id': user_id_field})
        if user_account_form.is_valid():
            user_account_form.save()
            messages.success(self.request, "Account information updated successfully.")
            return redirect('accounts:edit_user_account', user_id=user_id)
        else:
            messages.error(self.request, "Error! Invalid inut data detected! Please re-check your inputs.")
            return render(self.request, 'accounts/edit_account.html', {
                'user_account_form': user_account_form,
                'profile_image':user.profile_image,
                'password_form': reset_password_form,
                'user_account': user,
            })

@method_decorator(staff_required(), 'dispatch')
class ToggleUserStatus( PermissionRequiredMixin, View):
    """
    Suspend or activate an account (from status 2 => 3 or from status 3 => 2)
    """
    permission_required = ['irb.can_update_user']
    
    def get(self, *args, **kwargs):
        user_id = kwargs['user_id']
        if self.request.user.id == user_id:
            messages.warning(self.request, "Forbiden, You can't Suspend or Activate your own account")
            return redirect('core:error_page')
        user:UserAccount = UserAccount.objects.get(id=user_id)
        if user.status == 2: # if user is ACTIVE
            messages.success(self.request, "You have successfully suspended an account!")
            user.status = 3 # change to SUSPENDED
        else:
            messages.success(self.request, "You have successfully activated an account!")
            user.status = 2 # change to ACTIVE
        user.save()
        
        return redirect('accounts:users_list')

@method_decorator(staff_required(), 'dispatch')
class ToggleUserIsActive( PermissionRequiredMixin, View):
    permission_required = ['irb.can_update_user']
    def get(self, *args, **kwargs):
        
        user_id = kwargs['user_id']
        if self.request.user.id == user_id:
            messages.error(self.request, "Forbidden, You can't Delete or Restore your own account!")
            return redirect('core:error_page')

        user: UserAccount = UserAccount.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        messages.success(self.request, "Successfully updated user account!")
        return redirect('accounts:users_list')

@method_decorator(staff_required(), 'dispatch')
class SearchUsers( PermissionRequiredMixin, View):
    permission_required = ['irb.can_list_user']
    def get(self, *args, **kwargs):
        keyword = self.request.GET.get('keyword')
        users_list = UserAccount.objects.filter(Q(full_name__icontains=keyword) | Q(email__icontains=keyword)).distinct()
        return render(self.request, 'accounts:users_list.html', {
            'users_list': users_list,
        })

@method_decorator(staff_required(), 'dispatch')
class FilterUserByStatus( PermissionRequiredMixin, View):
    permission_required = ['irb.can_list_user']
    def get(self, *args, **kwargs):
        status_id = kwargs['status_id']
        return render(self.request, 'accounts/users_list.html', {
            'users_list': UserAccount.objects.select_related('position').filter(status=status_id).distinct()
        })