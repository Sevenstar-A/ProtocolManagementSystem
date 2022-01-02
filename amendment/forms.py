from django import forms
from django.forms import fields

from proposal.models import Proposal
from .models import AMENDMENT_REVIEW_COMMENTS, Amendment, AmendmentReviews 
from django.contrib.auth.models import Permission
from accounts.models import UserAccount, get_permitted_staffs
from core.forms import ACCEPTABLE_DOCUMENT_TYPES_STR


class CreateFullAmendmentForm(forms.ModelForm):
    # def __init__(self, *args, **kwargs):
    #     updating = kwargs.pop('updating', None)
    #     super(CreateFullAmendmentForm, self).__init__(*args, **kwargs)
    #     if updating:
    #         field_names = ['request_letter', 'progress_report', 'track_change', 'amend_form', 'last_approval_letter', 'clean_protocol' ]
    #         for f in field_names:
    #             self.fields[f].required == False 

        
    # protocol_number = forms.CharField(required=True, widget=forms.TextInput(attrs={'type':'hidden'}))
    proposal_title = forms.CharField( required=True, widget=forms.TextInput(attrs={'class':'form-control round','placeholder':'Title'}))
    
    proposal_version = forms.IntegerField(required=True, widget=forms.NumberInput(attrs={'class':'form-control','placeholder':'Protocol version', 'min':'1'}))
    amend_num = forms.IntegerField(required=True, widget=forms.NumberInput(attrs={'class':'form-control','placeholder':'Amendment Number', 'min':'1'}))
    pi_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'PI Name'}))
    
    request_letter = forms.FileField(required=True, widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    progress_report = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    track_change = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    amend_form = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    last_approval_letter = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    clean_protocol = forms.FileField(required=True, widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    
    class Meta:
        model = Amendment
        
        fields = [  'proposal_title', 'proposal_version', 'amend_num', 'pi_name', 'request_letter',
                    'progress_report', 'amend_form', 'track_change','last_approval_letter', 'clean_protocol'
                ]


class CreateAmendmentForm2(forms.ModelForm):
    
    def __init__(self,  *args, **kwargs) :
        prop_title = kwargs.pop('prop_title', None)
        pi_name = kwargs.pop('pi_name',None)
        super(CreateAmendmentForm2, self).__init__(*args, **kwargs)
        if prop_title:
            self.fields['proposal_title'].initial = prop_title
        if pi_name :
            self.fields['pi_name'].initial = pi_name
        
    """
    used for code 1, 2 and 4, only shows updatable fields!
    proposal_version, amend_num and last approval letter will b filled from previous amendments/ parent proposal 
    """
    
    proposal_title = forms.CharField( required=True, widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Title'}))
    pi_name = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control','placeholder':'PI Name'}))
    
    request_letter = forms.FileField(required=True, widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    progress_report = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    track_change = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    amend_form = forms.FileField(required=True,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    last_approval_letter = forms.FileField(required=False,widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    clean_protocol = forms.FileField(required=True, widget=forms.FileInput(attrs={'class':'custom-file-input', 'accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    
    class Meta:
        model = Amendment
        fields = [  'proposal_title', 'pi_name', 'request_letter',
                    'progress_report', 'amend_form', 'track_change','last_approval_letter', 'clean_protocol'
                ]
        

class AssignAmendmentReviewersForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        creator = kwargs.pop('creator', None)
        super(AssignAmendmentReviewersForm, self).__init__(*args, **kwargs)
        permitted_users= get_permitted_staffs('can_review_amendment', exclude_ids=[creator.id])
        self.fields['reviewers'] = forms.ModelMultipleChoiceField(queryset = permitted_users, widget = forms.SelectMultiple( attrs={'class':'select2 form-control round col-md-12',
                                                    'placeholder':'Select Reviewer'}))
    
    class Meta:
        model = Amendment
        fields = ['reviewers']  


class AmendmentReviewForm(forms.ModelForm):
    comment = forms.ChoiceField(choices=AMENDMENT_REVIEW_COMMENTS, widget=forms.RadioSelect(attrs={'class':'form-radio'}))
    note = forms.CharField(widget=forms.Textarea(attrs={'class':'form-control round'}))
    class Meta:
        model = AmendmentReviews
        fields = ['comment','note']


