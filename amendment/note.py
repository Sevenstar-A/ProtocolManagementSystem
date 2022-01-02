from django import models
from proposal.models import Proposal
from django.conf import settings
from .models import AMENDMENT_TYPE_CODES, AMENDMENT_STATUS
"""
    * if z proposal is initialy submited by z system, proposal field will b, if not parent renewal (previous renewal req) will b
    used inorder to track pi email change, and other renewal history  
    
    * renewal parent - child r/n is like               |                for amendment parent - child r/n is like
                                                       |
       |initial renewal (parent = null)                |                                        |initial amend (parent = null)
       |second renewal (parent = initial renewal)      |      | 2nd amend(parent = initial)     | 3rd amend (parent = initial)          | 4th amend(parent = initial)
       |third renewal (parent = second renewal)        |     

        the difference is caused depending on how we use the parent field in each case.
"""


# for first time amendment request through z system, whether the amendment no is 1 or more (i.e. if there were 3 previous
# amendments without our system the initial amendment will be 4, and for the rest amendment the user will use our system )
class Amendment(models.Model):
    protocol_number = models.CharField(max_length=20 )# a must for all
    proposal = models.ForeignKey(Proposal, on_delete=models.SET_NULL, blank=True, null=True, ) # null for code 3 & 4
    # parent = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True ) 

    # even though the following two seem to be values related with a proposal object, they are directly
    # related with amendments, since they can change independtly from the initial submission. 
    proposal_title = models.TextField() # Could update it, so just show the investigator previous title.
    proposal_ver = models.IntegerField() # If code 1 & 2 := prop.latest_version_with_amendment + 1,     code 3:= user input     code 4:=latest.proposal_version + 1 
    

    # the following are required for every amendment
    amend_num = models.IntegerField()# If code 1:= 1,    code 2= latest.amend_no + 1,   code 3:= user input,   code 4:= latest.amend_no +1
    pi_email = models.EmailField()
    
    request_letter = models.FileField(upload_to=('Amendmet/RequestLetters'), )
    progress_report= models.FileField(upload_to=('Amendmet/ProgressReports'), )
    amend_form = models.FileField(upload_to=('Amendmet/AmendmentForms'), )
    track_change  = models.FileField(upload_to=('Amendmet/TrackChange'), )
    last_approval_letter = models.FileField(upload_to=('Amendmet/ApprovalLetters'), help_text="for code 3 only" )

    status = models.CharField(max_length = 20, choices=AMENDMENT_STATUS, default='Pending')
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    submited_date = models.DateTimeField(blank=True, null=True)# the date on which the S.O accepted the initial amendment req and staus changed from pending to 
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_date = models.DateTimeField(auto_now_add=True)
    
    code = models.IntegerField(choices=AMENDMENT_TYPE_CODES)

    def __str__(self):
        return self.prot_num
    
 


