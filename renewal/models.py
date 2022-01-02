from django.db import models
from django.conf import settings
from proposal.models import Proposal

# File documents upload to Renewal/ Folder

RENEWAL_STATUS = [
    ('Pending', 'Pending'), # When the Inv requests the renewal, staffs can send him correction comments and he can update it
    ("Submited", "Submited"), # When S.O accepts the request
    ('On Review', 'On Review'), # staffs accepted the request to be reviewed. so staffs with can_review_renewal permission can submit their reviews
    ('Reviewed','Reviewed'), # when all staffs who have to review the renewal submit there review, on of them updates it to reviewed
    ('Approved', 'Approved'), # a staff with the permission to can_approve_renewal can approve
    ('Rejected', 'Rejected') # a staff with the permission to can_approve_renewal can reject
   
]


RENEWAL_TYPE_CODES =  [
    ('1',"Initial Found: New Renewal"), #if there is an initial submission with the same protocol number, but no amendment and no renewal was requested before
    ('2',"Initial Found: New Renewal After Amendment"), # if there is an initial submission and amendment with the same protocol number, but no renewal is found
    
    ('3',"Initial Found: Version Renewal") , #If there is an initial submission and a renewal with the same protocol nummber, but no amendment reques
                                    #so, for this case, the latest app_letter will be from the latest renewal request, then 
    ('4',"Initial Found: Version Renewal & Amendment Found"),   # if there is an initial submission, amendment and renewal with the same protocol number,
                                    # but the version of the latest renewal is greater than the amendment, (means no amendment was requested for this version 
                                    # So the latest approval letter will be the app_letter of z renewal request
    
    ('5', "No Initial: New Renewal"),
    ('6', "No Initial: New Renewal After Amendment"),
    ('7', "No Initial: Version Renewal"),
    ('8', "No Initial: Version Renewal & Amendment Found"),
    
]

# for renewal there is no On Comment status, the workflow only has 1 cycle
class Renewal(models.Model):
    protocol_number = models.CharField(max_length=20 )# a must for all
    proposal = models.ForeignKey(Proposal, on_delete=models.SET_NULL, blank=True, null=True, ) # null for code > 4
    
    proposal_title = models.TextField() # No updating, unless it's code is 5. just show the investigator previous title.
    proposal_version = models.IntegerField() # No updating, unless it's code is 5. just show the investigator the latest version  

    request_letter = models.FileField(upload_to='Renewal/RequestLetters')
    progress_report = models.FileField(upload_to='Renewal/ProgressReports')
    last_approval_letter = models.FileField(upload_to='Renewal/IrbApprovalLetters', )

    renewal_num = models.IntegerField()# If code 1,2,6 = 1,    code 3,4,7,8 = latest.renewal_num + 1,   code 5:= user input  
    pi_name = models.CharField(max_length=100)

    reviewers = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="renewal_reviewers", blank=True)
    status = models.CharField(max_length = 20, choices=RENEWAL_STATUS, default='Pending')
    has_been_approved = models.BooleanField(default=False) # this one is used to check whether or not the renewal was approved before or not, regardless of the current status
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL,related_name="renewal_approver_staff", on_delete=models.SET_NULL, blank=True, null=True)
    submited_date = models.DateTimeField(blank=True, null=True)# the date on which the S.O accepted the renewal req and staus changed from pending to sumited 
    
    special_note= models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    code = models.IntegerField(choices=RENEWAL_TYPE_CODES,editable=False)
    
    class Meta:
        ordering = ('-created_date',)
        

class RenewalReviews(models.Model):
    renewal = models.ForeignKey(Renewal, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    note = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date= models.DateTimeField(auto_now=True)

    # class Meta:
    #     ordering = ['-id']
    

# we will fetch 'last approval letter' from this table
class RenewalApproval(models.Model):
    renewal = models.ForeignKey(Renewal, on_delete=models.CASCADE)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    progress_report_duration = models.IntegerField(blank=True, null=True, help_text="In Months") #
    approval_letter = models.FileField(upload_to='Renewal/ApprovalLetters')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,related_name='renewal_approver', null=True)
    approved_date = models.DateTimeField(blank=True, null=True)
    dummy = models.IntegerField()
    
    
    def __str__(self):
        return f"{self.renewal}'s approval letter for {self.start_date.date} - {self.end_date.date}"
    
     
class RenewalRejection(models.Model):
    renewal = models.ForeignKey(Renewal, on_delete=models.CASCADE)
    rejection_comment = models.TextField()
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL,  on_delete=models.SET_NULL, blank=True, null=True)
    rejection_date = models.DateTimeField(auto_now_add=True)
    

class RenewalDeletion(models.Model):
    creator_name = models.CharField(max_length=300)
    creator_email = models.CharField(max_length=300)
    proposal_title = models.TextField()
    deleted_by = models.CharField(max_length=300)
    deleted_date = models.DateTimeField(auto_now_add=True)






