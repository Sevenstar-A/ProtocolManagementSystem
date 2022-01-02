from django import forms
from django.contrib.auth.models import Permission
from django.db.models import fields
from django.forms import widgets
from django.utils.functional import empty


from accounts.models import UserAccount, get_permitted_staffs
from .models import (ProposalType, InitialProposalDocType, Proposal,
                    InitialProposalDocument, Investigators, VersionedProposal, VersionedRelatedDocs, ProposalReviewerFeedback,
                    ProposalIrbComment, IONIZING_RADIATION_USE)

from core.models import  StudyPop, StudyType, Impaired, Exclusion, SpecialRes, Department
from core.forms import FileSubmitForm, ACCEPTABLE_DOCUMENT_TYPES_STR
from django.forms import modelformset_factory
from .models import *



class Initial_Create_Form(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        title = kwargs.pop('title', None)
        super(Initial_Create_Form, self).__init__(*args,**kwargs)
        if title:
            self.fields['title'].initial = title

    # just for displaying, the title data is saved to the proposal table    
    title = forms.CharField(widget=forms.Textarea(attrs={'class':'form-control round','title':'Title #1' })) 
    
    study_types_chk =  StudyType.objects.all().values('id', 'name')
    study_pops_chk = StudyPop.objects.all().values('id', 'name')
    impaired_chk = [i[0] for i in IMPAIRED]
    exclusion_chk = [e[0] for e in EXCLUSION]
    special_res_chk = SpecialRes.objects.all().values('id', 'name')
    
    study_type = forms.CharField(required=True, widget=forms.TextInput(attrs={'type':'text'  ,'title':'study_type #2', }))
    other_study = forms.CharField(required =False,widget = forms.Textarea(attrs={'class':'form-control round', }))
    
    study_pop = forms.CharField(required=True, widget=forms.TextInput(attrs={'type':'text','title':'Study Population #6', }))
    
    department = forms.ModelChoiceField(empty_label='Select Department', queryset=Department.objects.all(), widget = forms.Select(attrs={"class":"custom-select form-control",'title':'Department #3',}))
    proposal_type = forms.ModelChoiceField(empty_label='Select Proposal Type', queryset=ProposalType.objects.all(), widget = forms.Select(attrs={"class":"custom-select form-control",'title':'#4',}))
    
    min_age = forms.IntegerField(required=False, widget =forms.NumberInput(attrs={'class':'form-control'}),)
    max_age = forms.IntegerField(required=False, widget =forms.NumberInput(attrs={'class':'form-control'}),)
    min_pediatric =forms.IntegerField(required=False, widget =forms.NumberInput(attrs={'class':'form-control'}),)
    max_pediatric =forms.IntegerField(required=False, widget =forms.NumberInput(attrs={'class':'form-control'}),)
    min_pediatric_age_type = forms.ChoiceField(required=False, choices=AGE_TYPES, widget=forms.Select(attrs={'class':'form-control', 'type':'drop-down'}))
    max_pediatric_age_type = forms.ChoiceField(required=False, choices=AGE_TYPES, widget=forms.Select(attrs={'class':'form-control'}))
    
    impaired = forms.CharField(required=True, widget=forms.TextInput(attrs={'type':'text', 'title':'Impaired #7', }))
    
    exclusion = forms.CharField(required = True,widget=forms.TextInput(attrs={'type':'text','title':'Requested Exclusion #10', }))
    other_exclusion = forms.CharField(required =False,widget = forms.Textarea(attrs={'class':'form-control round'}))
    
    
    special_res = forms.CharField(required=True, widget=forms.TextInput(attrs={'type':'text','title':'Special Resource #11', }))
    other_special_res = forms.CharField(required =False,widget = forms.Textarea(attrs={'class':'form-control col-lg-6 round'}))
    
    ionizing_rad = forms.ChoiceField(initial="None",choices=IONIZING_RADIATION_USE, widget=forms.RadioSelect(attrs={'class':'form-radio', }))
    inves_new_drug_type = forms.ChoiceField(initial="None",choices=INVESTICATIONAL_NEW_DRUG_TYPE, widget=forms.RadioSelect(attrs={'class':'form-radio',  'onclick':'display_fda_info()'}))
    fda_no = forms.CharField(required =False,widget = forms.TextInput(attrs={'class':'form-control'}))
    fda_name = forms.CharField(required =False,widget = forms.TextInput(attrs={'class':'form-control'}))
    fda_sponsor = forms.CharField(required =False,widget = forms.TextInput(attrs={'class':'form-control'}))
    fda_holder = forms.CharField(required =False,widget = forms.TextInput(attrs={'class':'form-control'}))

    procedure_use = forms.ChoiceField( initial='Invasive', choices=PROCEDURE_USE,  widget=forms.RadioSelect(attrs={'class':'form-radio'}))
    multisite_collab =forms.ChoiceField( initial='No', choices=BOOLEAN_CHOICES, widget=forms.RadioSelect(attrs={'class':'form-radio'}))
    financial_dis = forms.ChoiceField( initial='No', choices=BOOLEAN_CHOICES, widget=forms.RadioSelect(attrs={'class':'form-radio'}))
    conflict_int = forms.CharField(required=False, widget = forms.Textarea(attrs={'class':'form-control ml-2 col-12 round', 'placeholder':'Specify Conflict of interest...', 'onclick':'display_conflict()'}))
    collaborator_inis = forms.CharField(required=False, widget = forms.TextInput(attrs={'class':'form-control', 'style':'margin-left:10px;margin-right:10px;'}))
    
    class Meta:
        model = InitialSubmission
        fields = [  'study_type', 'other_study','department','proposal_type','total_par',
                    'study_pop','min_age','max_age', 'min_pediatric', 'max_pediatric','min_pediatric_age_type', 'max_pediatric_age_type', 'impaired','exclusion',
                    'other_exclusion','special_res', 'other_special_res', 'ionizing_rad', 'inves_new_drug_type', 
                    'fda_no','fda_name','fda_sponsor', 'fda_holder', 'procedure_use', 'multisite_collab', 'financial_dis', 
                    'conflict_int', 'collaborator_inis', 'fund',  
                  ]
        widgets = {
        
            'total_par':forms.NumberInput(attrs={'class':'form-control', 'title':'Total Participants #5'}),
            'fund':forms.TextInput(attrs={'class':'form-control', 'title':'Funding Inistitute #19'}),
        }
 

class Proposal_Doc_Create_Form(forms.ModelForm): 
    
    def __init__(self, *args, **kwargs):
        super(Proposal_Doc_Create_Form, self).__init__(*args, **kwargs)
        self.empty_permitted = False
        
    doc = forms.FileField(required=True, widget = forms.FileInput(attrs={'class':'custom-file-input','accept':ACCEPTABLE_DOCUMENT_TYPES_STR}))
    doc_type = forms.ModelChoiceField(  required=True, queryset = InitialProposalDocType.objects.exclude(name="Other Related Document").only('name'),  
                                        empty_label="Select Document Type", widget=forms.Select(attrs={"class":" form-control"})) 
    class Meta:
        model = InitialProposalDocument
        fields = ['doc','doc_type']

    
class Investigator_Create_Form(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(Investigator_Create_Form, self).__init__(*args, **kwargs)
        self.empty_permitted = False
        
    class Meta:
        model = Investigators
        fields  =  ['name', 'email', 'insititution', 'cv', 'is_pi']
        widgets = {
            'name':forms.TextInput(attrs={'class':'form form-control', 'placeholder':'Full Name','required':"", 'style': 'display:inline'}),
            'email': forms.EmailInput(attrs={'class':'form form-control','placeholder':'email', 'style': 'display:inline'}),
            'insititution':forms.TextInput(attrs={'class':'form form-control','placeholder':'Inistitution', 'style': 'display:inline'}),
            'cv':forms.FileInput(attrs = { 'style': 'display:inline; width:180px','accept':ACCEPTABLE_DOCUMENT_TYPES_STR }),
            'is_pi':forms.CheckboxInput(attrs={'class':'switchery','type':'checkbox', }),
        }
    

class AssignProposalReviewersForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        creator = kwargs.pop('creator', None)
        super(AssignProposalReviewersForm, self).__init__(*args, **kwargs)
        permitted_users= get_permitted_staffs("can_review_proposal", exclude_ids=[creator.id])
        self.fields['reviewers'] = forms.ModelMultipleChoiceField(queryset = permitted_users, widget = forms.SelectMultiple( attrs={'class':'select2 form-control round col-md-12',
                                                    'placeholder':'Select Reviewers'}))
    
    class Meta:
        model = Proposal
        fields = ['reviewers']
    

class ProposalAcceptanceForm(forms.ModelForm):
    review_type = forms.ChoiceField(choices=REVIEW_TYPES, widget=forms.RadioSelect(attrs={'class':'form-radio'}))
    special_note = forms.CharField(required=False, widget=forms.Textarea(attrs={ 'rows': '10', 'class':'col-md-12 form-control '}))
    
    class Meta:
        model = Proposal
        fields = ['special_note', 'review_type']


class ProposalReviewerFeedbackForm(forms.ModelForm):
    class Meta:
        model = ProposalReviewerFeedback
        fields = ['study_ass_doc']
        widgets = {
            'study_ass_doc':forms.FileInput(attrs={'class':'custom-file-input','accept':ACCEPTABLE_DOCUMENT_TYPES_STR})
            } 


class VersionedProposalForm(forms.ModelForm):
    class Meta:
        model = VersionedProposal
        fields = ['response_doc','clean_doc','track_change']
        widgets = {
                'response_doc':forms.FileInput(attrs={'class':'custom-file-input','accept':ACCEPTABLE_DOCUMENT_TYPES_STR}),
                'clean_doc':forms.FileInput(attrs={'class':'custom-file-input','accept':ACCEPTABLE_DOCUMENT_TYPES_STR}),
                'track_change':forms.FileInput(attrs={'class':'custom-file-input','accept':ACCEPTABLE_DOCUMENT_TYPES_STR})
            } 


class ProposalIrbCommentForm(forms.ModelForm):
    decision_type = forms.ChoiceField(choices=IRB_COMMENT_DECISTION_TYPES, widget=forms.RadioSelect(attrs={'class':'form-radio'}))
    
    class Meta:
        model = ProposalIrbComment
        fields= ['irb_comment_doc', 'decision_type']
        widgets = {
            'irb_comment_doc': forms.FileInput(attrs={'class':'custom-file-input','accept':ACCEPTABLE_DOCUMENT_TYPES_STR}), 
        }