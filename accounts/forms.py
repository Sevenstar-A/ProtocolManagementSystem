from django import forms
from django.forms import fields, widgets
from django.forms.widgets import Select
from django.contrib.auth.models import Permission
from accounts.models import GENDERS, Position, Title, UserAccount
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm
from core.forms import ACCEPTABLE_DOCUMENT_TYPES_STR

GENDERS_CHOICES = [
    ('','Select Gender'),
    ('-','-'),
    ('Male','Male'),
    ('Female', 'Female')
]

class CustomerCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', 
        widget=forms.PasswordInput(attrs={
            'class':"form-control",
            'autocomplete':"new-password",
            'placeholder':'Password',
            'minlength':8,
        }))
    password2 = forms.CharField(label='Password confirmation', 
        widget=forms.PasswordInput(attrs={
            'class':"form-control",
            'autocomplete':"new-password",
            'placeholder':'Re-enter password',
            'minlength':8,
        }))
    title = forms.ModelChoiceField(required=False, queryset=Title.objects.all().only('id','name'), empty_label="Your Title", widget=forms.Select(attrs={'class':'form-control'}))
    sex = forms.ChoiceField(choices=GENDERS, initial="Select Sex", widget=forms.Select(attrs={'type':'dropdown', 'class':'form-control'}))
    class Meta:
        model = UserAccount
        fields  =('title', 'first_name', 'last_name', 'phone_number','profile_image', 'sex', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'First Name'}),
            'last_name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Last Name'}),
            'phone_number':forms.TextInput(attrs={'class':'form-control','autocomplete':'off', 'placeholder':'Phone Number', 'value':''}),
            'email': forms.EmailInput(attrs={'class':'form-control', 'placeholder':'Email', }),
            'profile_image':forms.FileInput(attrs ={'class':'custom-file-input', 'placeholder':'Profile Image','accept':ACCEPTABLE_DOCUMENT_TYPES_STR}), 
            
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(CustomerCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_customer = True
            
        if commit:
            user.save()
        return user


class IrbStaffCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password',
            widget = forms.PasswordInput(attrs={
                    'class': "form-control",
                    'autocomplete': "new-password",
                    'placeholder': 'Password',
                    'minlength': 8,
                }))
    password2 = forms.CharField(label='Password confirmation',
            widget = forms.PasswordInput(attrs={
                'class':"form-control",
                'autocomplete':"new-password", 
                'placeholder':'Re-enter password', 
                'minlength': 8,
            }))
    position = forms.ModelChoiceField(required=True, empty_label='Select Your IRB Position', queryset=Position.objects.all().only('id','name'), widget=forms.Select(attrs={'class':'form-control'}) )
    title = forms.ModelChoiceField(required=False, queryset=Title.objects.all().only('id','name'), empty_label="Your Title", widget=forms.Select(attrs={'class':'form-control'}))
    
    class Meta:
        model = UserAccount
        fields  =('title','first_name', 'last_name','phone_number','profile_image','position', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'First Name', 'autocapitalize':'word'}),
            'last_name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Last Name','autocapitalize':'word'}),
            'phone_number':forms.TextInput(attrs={'class':'form-control', 'placeholder':'Phone Number','autocorrect':"off", 'value':''}),
            'email': forms.EmailInput(attrs={'class':'form-control', 'placeholder':'Email', }),
            'profile_image':forms.FileInput(attrs ={'class':'custom-file-input', 'placeholder':'Profile Image','accept':ACCEPTABLE_DOCUMENT_TYPES_STR})
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(IrbStaffCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_staff = True
        if commit:
            
            user.save()
        return user


class PositionForm(forms.ModelForm):
    name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class':'form-control col-6'}))
    permissions = forms.ModelMultipleChoiceField(  queryset=Permission.objects.prefetch_related('content_type') , 
                                widget = forms.SelectMultiple(attrs=
                                    {   'class':'duallistbox-multi-selection',
                                        'size':'20',
                                        'onclick': 'get_id()',
                                        'multiple':"multiple"}))
    class Meta:
        model = Position
        fields = ['name','permissions']


class UserAccountForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        edit = kwargs.pop('edit', False) 
        super(UserAccountForm, self).__init__(*args, **kwargs)
        if edit and self.instance:
          
            self.fields['user_permissions'] = forms.ModelMultipleChoiceField( required=False, queryset= Permission.objects.prefetch_related('content_type'), 
                                            widget = forms.SelectMultiple(attrs=
                                                {   'class':'duallistbox-multi-selection',
                                                    'size':'20',
                                                    'onclick': 'get_id()',
                                                    'multiple':"multiple"}))
           
            
    sex = forms.ChoiceField (required=False, choices=GENDERS_CHOICES, widget=forms.Select(attrs={'class': 'form-control','type':'dropdown'}),)
    title = forms.ModelChoiceField (required=False, queryset=Title.objects.all(), empty_label="No Title", widget=forms.Select(attrs={'class': 'form-control',}),)
    position = forms.ModelChoiceField (required=False, queryset=Position.objects.all(), empty_label="No Position", widget=forms.Select(attrs={'class': 'form-control',}),)
    phone_number = forms.CharField (required = False, widget= forms.TextInput(attrs={'class': 'form-control'}), )
    profile_image = forms.ImageField(required=False, widget=forms.FileInput())
    class Meta:
        model = UserAccount
        fields = ['first_name', 'last_name', 'sex','title', 'email', 'phone_number', 'profile_image', 'position', 'user_permissions', ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control',}),
            'last_name': forms.TextInput(attrs={'class': 'form-control',}),
            'email':forms.EmailInput(attrs={'class': 'form-control', 'disabled':'true'}),
        }


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Current password',
        'minlength': "8",
    }))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'New password',
        'minlength': "8",
    }))
    retype_new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Repeat new password',
        'minlength': "8",
    }))

    class Meta:
        fields = ['current_password', 'new_password', 'retype_new_password']


class AdminUpdatePasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'New password'
    }))
    retype_new_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Repeat new password'
    }))

    class Meta:
        fields = ['current_password', 'new_password', 'retype_new_password']
