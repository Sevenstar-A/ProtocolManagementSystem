from django import forms
from django.forms import fields
from .models import Notification, UserNotification
class n(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['tag', 'noti', 'desc', 'link','receivers']
