from django.db import models, transaction
from django.conf import settings
from proposal.models import Proposal

AMENDMENT_STATUS = [
    # ('Email Confirmation', 'Email Confirmation'),
    ('Pending', 'Pending'), # When the Inv requests the amendment, staffs can send him correction comments and he can update it
    ("Submited", "Submited"), # When S.O accepts the request
    ('On Review', 'On Review'), # staffs accepted the request to be reviewed. so staffs with can_review_amendment permission can submit their reviews
    ('Reviewed','Reviewed'), # when all staffs who have to review the amendment submit there review, on of them updates it to reviewed
    ('On Comment', 'On Comment'), # Same as proposal on comment status
    ('Approved', 'Approved'), # a staff with the permission to can_approve_amendment can approve
    ('Rejected', 'Rejected') 
    
]

AMENDMENT_TYPE_CODES =  [
    ('1',"Initial Found: New Amendment"), #if there is an initial submission with the same protocol number, but no amendment and no renewal was requested before
    ('2',"Initial Found: Version Amendment "), # if there is an initial submission and amendment with the same protocol number, but no renewal is found
    ('3',"Initial Found: New Amendment After Renewal"),  #If there is an initial submission and a renewal with the same protocol nummber, but no amendment reques
                                    #so, for this case, the latest app_letter will be from the latest renewal request, then 
    ('4',"Initial Found: Version Amendment & Renewal Found"),   # if there is an initial submission, amendment and renewal with the same protocol number,
                                    # but the version of the latest amendments are greater than the renewal, (means 2 amendments 
                                    # in a row without a renewal. So the latest approval letter will be the app_letter of z amendment
    
    ('5', "No Initial: New Amendment"),
    ('6', "No Initial: Version Amendment"),
    ('7', "No Initial: New Amendment After Renewal"),
    ('8', "No Initial: Version Amendment & Renewal Found"),
    
]

AMENDMENT_REVIEW_COMMENTS = [
        ('Expedited (Miner changes)','Expedited (Miner changes)'),
        ('Full Reviewed', 'Full Reviewed')
    ]


# FOR MORE INFO REFER amendment/note.py file
class Amendment(models.Model):
    protocol_number = models.CharField(max_length=20 )# a must for all
    proposal = models.ForeignKey(Proposal, on_delete=models.SET_NULL, blank=True, null=True, ) # null for code > 4
    
    proposal_title = models.TextField() # Could update it, so just show the investigator previous title.
    proposal_version = models.IntegerField() # If code 1 & 2 := prop.latest_version_with_amendment + 1,     code 3:= user input     code 4:=latest.proposal_version + 1 

    amend_num = models.IntegerField()# If code 1,3, or 7:= 1,    code 2,4,6,8= latest.amend_no + 1,   code 5:= user input,   
    pi_name = models.CharField(max_length=100)
    
    request_letter = models.FileField(upload_to=('Amendment/RequestLetters'), )
    progress_report= models.FileField(upload_to=('Amendment/ProgressReports'), )
    amend_form = models.FileField(upload_to=('Amendment/AmendmentForms'), )
    track_change  = models.FileField(upload_to=('Amendment/TrackChange'), )
    last_approval_letter = models.FileField(upload_to=('Amendment/ApprovalLetters'), help_text="for code 3 only" )
    clean_protocol = models.FileField(upload_to="Amendment/CleanProtocol", )

    reviewers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="amend_reviewers", blank=True)
    status = models.CharField(max_length = 20, choices=AMENDMENT_STATUS, default='Pending')
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL,related_name="approver_staff", on_delete=models.SET_NULL, blank=True, null=True)
    submited_date = models.DateTimeField(blank=True, null=True)# the date on which the S.O accepted the amendment req and staus changed from pending to sumited
    
    special_note= models.TextField(blank=True)
    has_been_approved = models.BooleanField(default=False) # this one is used to check whether or not the amendment was approved before or not, regardless of the current status
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    code = models.IntegerField(choices=AMENDMENT_TYPE_CODES,editable=False)
    
    submission_count = models.IntegerField(default=1)# count num of re-submissions, (how many times did the irb commented and the investigator updated the amendment)
    class Meta:
        ordering = ['-id'] #works for version number ordering too
       
    def __str__(self):
        return f"{self.protocol_number}'s amend {self.amend_num}: code {self.code}"
    
 
class AmendmentReviews(models.Model):
    amendment = models.ForeignKey(Amendment, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    comment = models.CharField(max_length=50, choices=AMENDMENT_REVIEW_COMMENTS)
    note = models.TextField()
    submission_num = models.IntegerField(default=1) # for which submission was this reviewer comment, (same as version number of proposal, but since there is no version here...)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date= models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-submission_num']
    

class AmendmentIrbComment(models.Model):
    compiled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, )
    amendment = models.ForeignKey(Amendment, on_delete=models.CASCADE)
    submission_num = models.IntegerField(default=1)
    compiled_doc = models.FileField(upload_to='Amendment/AmendmentCompiledReviewDocs', default="" )
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


class AmendmentApproval(models.Model):
    amendment = models.ForeignKey(Amendment, on_delete=models.CASCADE,)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,related_name='approver', null=True)
    approval_date = models.DateTimeField(auto_now_add=True)
    approval_letter = models.FileField(upload_to='Amendment/ApprovalLetters') 
    
       
class AmendmentRejection(models.Model):
    amendment = models.ForeignKey(Amendment, on_delete=models.CASCADE)
    submission_count = models.IntegerField()
    rejection_comment = models.TextField()
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL,  on_delete=models.SET_NULL, blank=True, null=True)
    rejection_date = models.DateTimeField(auto_now_add=True)
    

class AmendmentDeletion(models.Model):
    creator_name = models.CharField(max_length=300)
    creator_email = models.CharField(max_length=300)
    proposal_title = models.TextField()
    deleted_by = models.CharField(max_length=300)
    deleted_date = models.DateTimeField(auto_now_add=True)
