from django import forms
from django.forms import fields, widgets

from proposal.models import Proposal
from .models import Renewal, RenewalApproval, RenewalReviews, RenewalRejection, RenewalDeletion
from core.forms import ACCEPTABLE_DOCUMENT_TYPES_STR
from accounts.models import UserAccount, get_permitted_staffs


# for code 5
class CreateFullRenewalForm(forms.ModelForm):
    proposal_title = forms.CharField( required=True, widget=forms.TextInput(attrs={'class':'form-control round','placeholder':'Proposal Title'}))
    
    proposal_version = forms.IntegerField(required=True, widget=forms.NumberInput(attrs={'class':'form-control','placeholder':'Proposal version', 'min':'1'}))
    renewal_num = forms.IntegerField(required=True, widget=forms.NumberInput(attrs={'class':'form-control','placeholder':'Renewal Number', 'min':'1'}))
    pi_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'PI Full Name'}))
    
    request_letter = forms.FileField(required=True, widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    progress_report = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    last_approval_letter = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    
    class Meta:
        model = Renewal
        fields = [  'proposal_title', 'proposal_version', 'renewal_num', 'pi_name', 
                    'request_letter','progress_report', 'last_approval_letter'
                ]


class CreateRenewalForm2(forms.ModelForm):

    pi_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class':'form-control'}))
    request_letter = forms.FileField(required=True, widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    progress_report = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    last_approval_letter = forms.FileField(required=False,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    
    class Meta:
        model = Renewal
        fields = [  'request_letter','progress_report', 'last_approval_letter',]
        
        
class RenewalReviewForm(forms.ModelForm):
    class Meta:
        model = RenewalReviews
        fields = ['start_date', 'end_date', 'note']
        widgets = {
            'start_date':forms.DateTimeInput(attrs={'class':'form-control round','type':'date'}),
            'end_date':forms.DateTimeInput(attrs={'class':'form-control round','type':'date'}),
            'note':forms.Textarea(attrs={'class':'form-control round'})

            
        }


class AssignRenewalReviewersForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        creator = kwargs.pop('creator', None)
        super(AssignRenewalReviewersForm, self).__init__(*args, **kwargs)
        permitted_users= get_permitted_staffs( 'can_review_amendment', exclude_ids=[creator.id] )
        self.fields['reviewers'] =  forms.ModelMultipleChoiceField(queryset = permitted_users, widget = forms.SelectMultiple( 
                                    attrs={'class':'select2 form-control round col-md-12', 'placeholder':'Select Reviewer'}))
    
    class Meta:
        model = Renewal
        fields = ['reviewers']  


class RenewalApprovalForm(forms.ModelForm):
    class Meta:
        model = RenewalApproval
        fields = ['start_date', 'end_date', 'approval_letter', 'progress_report_duration']
        widgets = {
            'start_date':forms.DateTimeInput(attrs={'class':'form-control round','type':'date', }),
            'end_date':forms.DateTimeInput(attrs={'class':'form-control   round','type':'date',}),
            'progress_report_duration': forms.NumberInput(attrs={'class':'form-control'}),
            'approval_letter': forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR})
        }