# python import 
import os
from datetime import datetime
# django import
from django.db import models
from django.conf import settings
from django.db import transaction
# project imports
from core.models import *

BOOLEAN_CHOICES = [ ('Yes', 'Yes'), ('No', 'No')]


PROPOSAL_STATUS = [
    # ('Email Confirmation', 'Email Confirmation'),
    ('Pending', 'Pending'),
    ('Submited','Submited'),
    ('On Review', 'On Review'),
    ('Reviewed','Reviewed'),
    ('On Comment', 'On Comment'),
    ('Approved', 'Approved'),
    ('Rejected', 'Rejected')
]

# --- Radio Choices
IONIZING_RADIATION_USE = [("Mediacally Indicated Only", "Mediacally Indicated Only"), ("None", "None"),    ]

INVESTICATIONAL_NEW_DRUG_TYPE = [ ("IND","IND"), ("IDE","IDE"),("None","None"),]

PROCEDURE_USE = [("Invasive","Invasive"), ("Non-invasive","Non-invasive"),("Not Applicable","Not Applicable"), ]
# ---- End of Radio Choices

# --- Check box choices

EXCLUSION = [("None","None"), ("Male","Male"), ("Female","Female")]

IMPAIRED = [("None","None"), ("Physically","Physically"), ("Cognitively","Cognitively"), ("Mentally","Mentally")]

# When S.O Accepts a request
REVIEW_TYPES = [
    ("Full Board", "Full Board"),
    ("Expediated", "Expediated"),
    ("Emergency", "Emergency")
]

# when S.O sends irb comment
IRB_COMMENT_DECISTION_TYPES = [
    ('Approved', 'Approved'),
    ('Resubmission', "Resubmission"),
    ('Approved With Recommendation', 'Approved With Recommendation'),
]
# --- End of Checkbox choice

AGE_TYPES = [
    ('Day', 'Day'),
    ('Month', 'Month'),
    ('Year', "Year")
]


# ex. PHD, Faculty
class ProposalType(models.Model):
    name = models.CharField(max_length=200)
    code_name = models.CharField(max_length= 100, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, help_text=('The user who created the proposal type object'))
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


#ex.  acceptance certificate, 
# Document Types used on initial submission for the drop down listing different doc types 
class InitialProposalDocType(models.Model):
    name = models.CharField(max_length=100, help_text="Doc Type name,")# like CV, Personal Detail, Acceptance Certificate, Rejection Letter
    proposal_types = models.ManyToManyField(ProposalType, blank=True,  help_text="For which proposal types should this Doc type be related to by default")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class ProposalManger(models.Manager):
    pass

# the proposals of clients
class Proposal(models.Model):
    title = models.TextField( help_text="Protocol Title")
    protocol_number = models.CharField(max_length=15, help_text="Protocol Number", default="-")
    
    status = models.CharField(max_length=25, choices= PROPOSAL_STATUS, default='Pending')
    reviewers = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    pi_name = models.CharField(max_length=300, blank=True, default="")
    
    has_been_approved = models.BooleanField(default=False) # this one is used to check whether or not the amendment was approved before or not, regardless of the current status
    latest_version_num= models.IntegerField(default=1,  help_text="Latest version from initial and versioned submissions.")
    latest_version_num_with_amend = models.IntegerField(default=1,  help_text="Latest version including amendment versions.")

    special_note = models.TextField(blank=True )
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPES, blank=True) #filled by S.O when accepting initial submission
    decision_type = models.CharField(max_length=30, choices=IRB_COMMENT_DECISTION_TYPES, blank=True) # filled by S.O when when sending an IRB Comment 

    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name = 'acceptor_staff', on_delete=models.SET_NULL, blank=True, null=True)
    accepted_date = models.DateTimeField(blank=True, null=True) # date of submission
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,related_name='user_proposal', on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    year_index = models.DecimalField(max_digits=3,decimal_places=0,default=0)
    
    class Meta:
        ordering = ["-created_date"]
        

    
    def __str__(self):
        if self.protocol_number:
            return self.protocol_number
        return f"{self.title}"

    def get_all_versioned_props(self):
        return  self.versionedproposal_set.all()
    
    def get_specific_version(self, version):
        """ returns object of the specified version for a proposal object, if it exitsts"""
        if version == 1:
            try:
                return InitialSubmission.objects.select_related('department').get(proposal = self)
            except Exception as e:
                return None
        else:
            try:
                return VersionedProposal.objects.prefetch_related('versionedrelateddocs_set').get(proposal =self, version = version)
            except Exception as e:
                return None

    def old_get_latest_ver_obj(self):
        l = self.versionedproposal_set.first()
        if l:
            return l
        return self.initialsubmission

    def get_latest_ver_obj(self, prefetch_related=None):
        """ returns latest version object of a proposal, so if it only has initial submission
        it will return initial submission, if it has versioned proposals it will return z latest of them.
        """
        if prefetch_related !=None:
            try:
                l = VersionedProposal.objects.prefetch_related(*prefetch_related).get(proposal = self, version =self.latest_version_num)
                return l
            except:
                # self.initialsubmission.prefetch_related(*prefetch_related)
                return InitialSubmission.objects.prefetch_related(*prefetch_related).filter(id = self.id).first()

        else:
            try:
                l = VersionedProposal.objects.get(proposal = self, version =self.latest_version_num)
                return l
            except:
                return InitialSubmission.objects.filter(id = self.id).first()

         
    def get_prop_ver_nums(self):
        """ returns a list of version numbers for a proposal object, starting from latest upto 1, """
        ver_nums =[1] # by default we have version 1 i.e. the initial submission
        ver_props =  self.versionedproposal_set.values_list('version').all()
        if ver_props:
            for v in ver_props:
                ver_nums.append(v.version) 

        return ver_nums


def generate_year_index( index):
        y = ""
        for i in range(3 - len(str(index))):
            y += "0"
        return y+str(index)     


def generate_prefix (s): # s has a format of "001/21/"
    s = s.split("/")
    index = int(s[0])
    year = s[1]
    current_year= str(datetime.now().year)[2:]
    if year == current_year:
        index = index+1
    else:
        index = 1
        year = str(int(current_year) +1)
    year_index = generate_year_index(index)
    return year_index+"/"+year+"/"

   
def generate_prot_num(prop, department_code_name):
    try:
        obj, created = SystemConstant.objects.get_or_create(name = "Protocol Prefix")
        if created:
            year = str(datetime.now().year)[2:]
            obj.value = f"000/{year}/"
            obj.save()
        prefix = generate_prefix(obj.value)
        with transaction.atomic():
            prop.protocol_number = prefix+department_code_name
            prop.status = "Submited"
            prop.save()
            print("for the proposal ", prop.protocol_number)
            obj.value = prefix
            obj.save()
        return prop
    except Exception as e:
        print("@ an exception ",e)
        return False
        


class InitialSubmission(models.Model):
    proposal = models.OneToOneField(Proposal, on_delete=models.CASCADE)
    version = models.IntegerField(default=1)
    
    # form data
    study_type = models.CharField(max_length=400, help_text="Comma separated names of study types")
    other_study = models.TextField(blank=True, null=True,help_text="You can specify Others.")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    proposal_type = models.ForeignKey(ProposalType, on_delete=models.SET_NULL, null=True)
    
    # participants info
    total_par = models.IntegerField()
    study_pop = models.CharField(max_length=300, help_text="Comma separated names of study pop")
    min_age  = models.IntegerField(blank = True, null=True)
    max_age = models.IntegerField(blank = True, null=True)
    min_pediatric = models.IntegerField(blank = True, null=True)
    max_pediatric = models.IntegerField(blank = True, null=True)
    min_pediatric_age_type = models.CharField(max_length=30, blank=True, choices=AGE_TYPES, default='Year' )
    max_pediatric_age_type = models.CharField(max_length=30, blank=True, choices=AGE_TYPES, default='Day' )

    impaired =  models.CharField(max_length=100,  help_text="Comma separated names of impaired names")
    exclusion =  models.CharField(max_length=100,  help_text="Comma separated names of excluded names")
    other_exclusion = models.TextField(blank=True, null=True,help_text="You can specify Others.")
    
    # resource
    special_res =  models.CharField(max_length = 500, help_text="Comma separated names of resource names")
    other_special_res = models.TextField(blank=True, null=True,help_text="You can specify Others.")

    ionizing_rad = models.CharField(max_length=500, choices=IONIZING_RADIATION_USE)
    
    # investigational new drug
    inves_new_drug_type = models.CharField(max_length=8, choices=INVESTICATIONAL_NEW_DRUG_TYPE)
    fda_no = models.CharField(max_length=50, blank=True, null=True)
    fda_name = models.CharField(max_length=50, blank=True, null=True)
    fda_sponsor = models.CharField(max_length=50, blank=True, null=True)
    fda_holder = models.CharField(max_length=50, blank=True, null=True)

    procedure_use = models.CharField(max_length=50, choices=PROCEDURE_USE)
    multisite_collab = models.CharField(max_length=50, )
    financial_dis = models.CharField(max_length=50)

    conflict_int = models.TextField(blank=True, null=True,help_text="You can specify Others.")

    collaborator_inis = models.CharField(max_length=200, blank=True, null=True)
    fund = models.CharField(max_length=200, help_text="Name of Funding Organization")
    co_inv_doc = models.FileField(upload_to="ProposalDocuments/Co-InvestigatorsSigniture", help_text="A scanned file of list of co-investigators with their signiture.", blank=True, null = True )    
    
    def __str__(self):
        return f"{self.proposal}'s initial submission"
    

# this is the actual proposal documents 
class InitialProposalDocument(models.Model):
    doc = models.FileField(upload_to="ProposalDocuments/InitialProposalDocuments")
    doc_type = models.ForeignKey(InitialProposalDocType, on_delete=models.PROTECT,  )
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    # created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proposal}'s doc"

class Investigators(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, help_text="Full name with title")
    email = models.EmailField()
    insititution = models.CharField(max_length=150, blank=True)
    cv = models.FileField(upload_to="ProposalDocuments/InvestigatorsCV", )
    is_pi = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.proposal}'s inv"
        
    def delete(self,*args, **kwargs):
        self.cv.delete() 
        super().delete(*args,**kwargs)
    
   

# Versioned Proposal Related things
class VersionedProposal(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    version = models.IntegerField()
   
    response_doc = models.FileField(upload_to='ProposalDocuments/VersionedProposals/ResponseDocuments')
    clean_doc = models.FileField(upload_to='ProposalDocuments/VersionedProposals/CleanDocuments')
    track_change = models.FileField(upload_to='ProposalDocuments/VersionedProposals/TrackChange')

    #dates
    accepted_date = models.DateTimeField(blank=True, null=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL,related_name="accepted_by", on_delete=models.SET_NULL, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proposal.protocol_number}'s Version {self.version}"
    
    class Meta:
        ordering = ['-created_date']


class VersionedRelatedDocs(models.Model):
    versioned_proposal = models.ForeignKey(VersionedProposal, on_delete=models.CASCADE)
    doc =  models.FileField(upload_to='ProposalDocuments/VersionedProposals/RelatedDocuments')

    def delete(self, *args, **kwargs):
        self.doc.delete()
        super().delete(*args, **kwargs)

    # def delete(self, *args, **kwargs):
    #     os.remove(os.path.join(settings.MEDIA_ROOT, self.doc.name))
    #     super(VersionedRelatedDocs,self).delete(*args,**kwargs)

# Feedback comment of each reviewer on a proposal (initial or versioned)
# the permissions are controlled by proposal.can_review
class ProposalReviewerFeedback(models.Model):
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, )
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    version = models.IntegerField(default=1)
    study_ass_doc = models.FileField(upload_to='ProposalDocuments/ReviewDocs')
    created_date =  models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    def __str__(self):
        c = f"{self.reviewer}'s Review for version {self.version} "
        c+= f" of - {self.proposal.protocol_number}"
        return c
    

# permissions controlled by proposal.can_compile_feedback
class ProposalIrbComment(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    version = models.IntegerField(default=1)
    irb_comment_doc = models.FileField(upload_to='ProposalDocuments/ProposalCompiledReviewDocs', default="" )
    decision_type = models.CharField(max_length=100, choices=IRB_COMMENT_DECISTION_TYPES)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, )
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


class ProposalApprovals(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    approval_letter = models.FileField(upload_to="ProposalDocuments/ProposalApprovalLetters")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL,  on_delete=models.SET_NULL, blank=True, null=True)
    approval_date = models.DateTimeField(auto_now_add=True)

# this is where the latest approval letter of a protocol can be found
# it's latest approval letter c'd b from initial submission approval, or from amendment or from renewal
class ProtocolApprovals(models.Model):
    protocol_number = models.CharField(max_length=25)
    start_date = models.DateField()
    end_date = models.DateField()
    progress_report_duration = models.IntegerField(null=True) 
    approval_letter = models.FileField(upload_to="ProposalDocuments/ProtocolApprovalLetters")
    approved_from = models.CharField(max_length=50, blank=True, choices=MODEL_NAMES)
    object_id = models.IntegerField()
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL,  on_delete=models.SET_NULL, blank=True, null=True)
    approved_date = models.DateTimeField(auto_now_add=True)
    

class ProposalRejection(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    version = models.IntegerField()
    rejection_comment = models.TextField()
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL,  on_delete=models.SET_NULL, blank=True, null=True)
    rejection_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


class ProposalDeletion(models.Model):
    creator_name = models.CharField(max_length=300)
    creator_email = models.CharField(max_length=300)
    proposal_title = models.TextField()
    deleted_by = models.CharField(max_length=300)
    deleted_date = models.DateTimeField(auto_now_add=True)
