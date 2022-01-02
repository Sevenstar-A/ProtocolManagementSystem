from django import forms
from django.forms.models import ModelForm
from core.forms import ACCEPTABLE_IMAGE_TYPES_STR
from connect.models import News


class NewsForm(ModelForm):

    class Meta:
        model = News 
        fields = ['title', 'image', 'content', 'tags', 'published']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control','accept':ACCEPTABLE_IMAGE_TYPES_STR
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Content of the NEWS...',
                'rows': 15
            }),
            'tags': forms.CheckboxSelectMultiple(attrs={
                'class': 'from-control'
            }),
            
        }
