import json
from django import forms
from django.contrib.auth.decorators import  permission_required
from django.utils.decorators import method_decorator
from django.core.checks import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth.mixins import  PermissionRequiredMixin
from amendment.models import Amendment, AmendmentReviews, AmendmentIrbComment
from core.models import Department
from notification.models import notify
from django.contrib import messages
from .forms import CreateAmendmentForm2, CreateFullAmendmentForm, AssignAmendmentReviewersForm, AmendmentReviewForm
from core.forms import FileSubmitForm

from django.db import transaction
from core.forms import TextSubmitForm
from core.utils import get_protocol_code

from accounts.utils import user_required, staff_required
from accounts.models import UserAccount, get_permitted_staffs

    

def set_amend_values(amend_obj, prot_num,status, created_by,  code, amend_num=None, proposal=None, proposal_version=None):
    amend_obj.protocol_number = prot_num
    amend_obj.status = status 
    amend_obj.created_by = created_by
    amend_obj.code = code
    if amend_num:
        amend_obj.amend_num = amend_num
    if proposal :
        amend_obj.proposal = proposal
    if proposal_version:
        amend_obj.proposal_version = proposal_version  
    return amend_obj


# if user is a reviewer of the latest submission number 
def can_review(user,is_reviewer, amend):
    """ checks review permission,  is reviewer, and status """
    if user.has_perm('irb.can_review_amendment') and  is_reviewer: 
        if amend.status == "On Comment":
            return [3, None] # Can't review, but can see detail
        elif amend.status in ["On Review",  "Reviewed"]: 
            try:
                rv = AmendmentReviews.objects.get(reviewer = user, amendment = amend,  submission_num=amend.submission_count) # check if he has reviewed
                return [2, AmendmentReviewForm(instance=rv)] # already reviewed
            except AmendmentReviews.DoesNotExist:
                return [1, AmendmentReviewForm] # can review, first time for this submission number
    return [0,None]


# checks amendment approval 
def amendment_can_be_approved(user, amend):
    if user == amend.created_by or not user.has_perm('irb.can_approve_amendment'):
        return (0 , "You are not permitted to approve this amendment")

    if not amend.has_been_approved:
        if amend.submission_count == 1:
            if amend.status == "Reviewed":
                return (1, "Approving for the first time")
            else:
                return (2,  f"Amendment cannot be approved for the first time with '{amend.status}' status, it has to be on 'Reviewed' status.")
        
        elif amend.submission_count > 1 and amend.status in ['Submited', 'On Review', 'Reviewed']: #2nd or above submission 
            return (3, "You can approve since it has been previously reviewed.")
        else:
            return (4, "Cannot be approved, change the status or submission number")

    else: #has been approved previously
        if amend.status != "Rejected":
            return (5, "Since it has been approved previously, you can update the approval letter")
        else:
            return (6,  "Cannot be approved, cz eventhough it has been approved, since it is now on 'Rejected' status, it has to be reviewed again")


@method_decorator(user_required(), 'dispatch')
class CheckProtocolNum( View):
    def get(self,*args, **kwargs):
        dn = list(Department.objects.values_list('code_name'))
        d = [ i[0] for i in dn ]
        return render(self.request, "amendment/check_prot_num.html",{'dept_names':json.dumps(d)})
    
    def post(self, *args, **kwargs):
        prot_num = self.request.POST['prot_num'] #is like 001/01/Anat
        prot_num = prot_num.replace('/','-')
        return redirect ("amendment:request_proposal_amendment", prot_num=prot_num)


# code 5 request_new_amend/002-21-anat/ 
@method_decorator(user_required(), 'dispatch')
class CreateNewAmendment( View): #for code 5 only
    def dispatch(self, request, *args, **kwargs):
        self.prot_num = str(self.kwargs['prot_num']).replace('-','/')
        result = get_protocol_code(self.prot_num,)
        code = result['code']
        if code == 0:
            messages.error(self.request, f"Error! {result['msg']}")
            return redirect('core:error_page')
        
        elif code != 5: 
            return redirect ("amendment:request_proposal_amendment", self.kwargs['prot_num'])

        return super().dispatch(request, *args, **kwargs)
    
    def get(self,*args, **kwargs):
        form = CreateFullAmendmentForm
        return render(self.request, "amendment/create_new_amendment.html",{'form':form, 'prot_num':self.prot_num})
    
    def post(self, *args, **kwargs):
        form = CreateFullAmendmentForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            amend = form.save(commit = False)
            amend = set_amend_values(amend, self.prot_num, "Pending", self.request.user,  5)
            amend.save()
            messages.success(self.request, " You have successfully requested an amendment!")
            staffs = get_permitted_staffs('can_accept_amendment')
            notify(staffs, 'info', f'New Amendment Request by {amend.created_by}', f'{amend.created_by} has requested a new amendment request. But the Initial submission was not throught this system and also this is the first time for an amendment request using this system!',
            link=f"/amendment/amend_detail/{amend.id}/")
            return redirect("amendment:my_amendments")
        else:
            messages.warning(self.request, "Invalid Data! Please re-check your inputs.")
            return render(self.request, "amendment/create_new_amendment.html",{'form':form, 'prot_num':self.prot_num})


# all except code 5
@method_decorator(user_required(), 'dispatch')
class CreateProposalAmendment( View):
    def dispatch(self, request, *args, **kwargs):
        self.prot_num = str(self.kwargs['prot_num']).replace('-','/')
        result = get_protocol_code(self.prot_num)
        self.code = result['code']
        if self.code == 0:
            messages.error(self.request, f"Error! {result['msg']}")
            return redirect('core:error_page')
        elif self.code == 5: 
            return redirect("amendment:request_new_amendment", prot_num=self.kwargs['prot_num'])
       
        self.prop =  result['proposal'] if 'proposal' in result else None  
        if self.request.user != result['created_by']:
            print("#########", result['created_by'])
            messages.error(request, "Forbidden, You can't request amendment for this protocol number!")
            return redirect("amendment:check_prot_num")

        status = result['status'] 
        # check for rejected proposal
        # rejected amendment
        # rejected renewal
        if status != "Approved" and status != "Rejected" :
            if self.code == 1:
                messages.warning(request, f"Forbidden, The proposal it self is in {status} status, you cannot request an amendment at this stage!  CODE: {self.code}")
            elif self.code == 2:
                messages.warning(request, f"Forbidden! There is another amendment on process with {status} status for this protocol number '{self.prot_num}'.  CODE: {self.code}")
            elif self.code == 3:
                messages.warning(request, f"Forbidden! There is another renewal request on process with {status} status for this protocol number '{self.prot_num}'.  CODE: {self.code}")
            else: # if code is 4,6,7,8 it means there is either 
                messages.warning(request, f"Forbidden! There is another request on process with {status} status for this protocol number '{self.prot_num}'. CODE: {self.code}")
            return redirect("amendment:check_prot_num")
       

        self.last_approval_letter = result['approval_letter']
        self.proposal_version = result['version'] + 1 # since an amendment request changes version number
        self.amend_num = result['amend_num'] + 1 # request next amendment number
        self.title = result['title'] 
        self.pi_name = result['pi_name']
        self.msg = result['msg']
                
        return super().dispatch(request, *args, **kwargs)


    def get(self, *args, **kwargs):

        form = CreateAmendmentForm2(prop_title=self.title, pi_name=self.pi_name, )
        return render(self.request, "amendment/create_amendment.html", {'form':form, 'prot_num':self.prot_num,'msg':self.msg, 'app_letter':self.last_approval_letter,
                                                                        'prop_ver':self.proposal_version, 'amend_num':self.amend_num })
        

    def post(self, *args, **kwargs):
        form = CreateAmendmentForm2(self.request.POST, self.request.FILES) # didn't use prop_title & pi_name, cz they were used just to initialize
        if form.is_valid():
            amend = form.save(commit=False)
            with transaction.atomic():
                amend = set_amend_values(amend, self.prot_num, "Pending", self.request.user,  self.code, amend_num=self.amend_num, proposal=self.prop, proposal_version= self.proposal_version)
                if self.last_approval_letter: # id document is found, use it else use what the user has submitted (cz if doc was not found, the ui let's the user to submit)
                    amend.last_approval_letter = self.last_approval_letter
                
                elif 'last_approval_letter' in self.request.FILES:
                    amend.last_approval_letter = self.request.FILES.get('last_approval_letter')
                else:
                    messages.warning(self.request, "Forbidden! Last approval letter missing! Please upload last approval letter.")
                    return render(self.request, "amendment/create_amendment.html", {'form':form, 'prot_num':self.prot_num,'msg':self.msg,'app_letter':None,
                                                                                    'prop_ver':self.proposal_version, 'amend_num':self.amend_num})
                amend.save()
            staffs = get_permitted_staffs('can_accept_amendment')
            notify(staffs, 'info', f'New Amendment Request by {amend.created_by}', f'{amend.created_by} has requested a new amendment request for {self.prot_num}. ',
            link=f"/amendment/amend_detail/{amend.id}/")
            
            messages.success(self.request, " You have successfully requested an amendment!")
            return redirect("amendment:my_amendments")

        else:
            print("errors",form.errors)
            messages.warning(self.request, "Forbidden! Invalid data detected!")
            return render(self.request, "amendment/create_amendment.html", {'form':form, 'prot_num':self.prot_num,'msg':self.msg, 'app_letter':self.last_approval_letter,
                                                                            'prop_ver':self.proposal_version, 'amend_num':self.amend_num})


@method_decorator(user_required(), 'dispatch')
class UpdateAmendment( View):
    def dispatch(self, request, *args, **kwargs):
        try:
            amend = Amendment.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Amendment.DoesNotExist:
            messages.error(self.request, "Error, Couldn't find the amendment you requested!")
            return redirect("amendment:my_amendments")
        if self.request.user != amend.created_by:
            messages.warning(self.request, "Forbidden, You can't access this amendment, since you are not the creator!")
            return redirect("amendment:my_amendments")
        if not amend.status in [ "Pending", "On Comment"]:
            messages.warning(self.request, f"You can't update an amendment request with '{amend.status}' status! It should be either at 'Pending' or 'On Comment' status.")
            return redirect("amendment:my_amendments")
        self.amend = amend
        return super().dispatch(request, *args, **kwargs)
    

    def get(self, *args, **kwargs):
        if self.amend.code == 5:
            form = CreateFullAmendmentForm ( instance=self.amend)
            return render(self.request, "amendment/update_new_amendment.html",{'form':form, 'prot_num':self.amend.protocol_number,'amend':self.amend})
        else:
            form = CreateAmendmentForm2 (instance =self.amend)
            return render(self.request, "amendment/update_amendment.html", {'form':form, 'prot_num':self.amend.protocol_number,'code':self.amend.code, 'app_letter':self.amend.last_approval_letter,
                                                                            'prop_ver':self.amend.proposal_version, 'amend_num':self.amend.amend_num, 'amend':self.amend })
        
    def post(self, *args, **kwargs):
        prev_status = self.amend.status

        if self.amend.code == 5:
            form = CreateFullAmendmentForm (self.request.POST, self.request.FILES,  instance=self.amend, )
        else:
            form = CreateAmendmentForm2 (self.request.POST, self.request.FILES, instance = self.amend)
        
        if not form.is_valid():
            print(form.errors)
            messages.error(self.request, "Error, Invalid data detected. Please re-check your inputs and try again!")
            if self.amend.code == 5:
                return render(self.request, "amendment/update_new_amendment.html",{'form':form, 'prot_num':self.amend.protocol_number,'amend':self.amend})               
            else:
                return render(self.request, "amendment/update_amendment.html", {'form':form, 'prot_num':self.amend.protocol_number,'code':self.amend.code, 'app_letter':self.amend.last_approval_letter,
                                                                            'prop_ver':self.amend.proposal_version, 'amend_num':self.amend.amend_num,'amend':self.amend })

        # if form is valid
        self.amend = form.save(commit=False)
        #! if the updating is for irb comment, add the submission count by 1, just to track the number of times
        #! the user has updated z request due to IRB comment
        if prev_status=="On Comment":
            self.amend.submission_count += 1
        self.amend.status = "Pending"
        self.amend.save() 
        
        messages.success(self.request, "You have successfully updated your amendment request!")
        if 'send_notification' in self.request.POST:
            staffs = get_permitted_staffs('can_accept_amendment')
            notify( staffs, 'info', f"{self.request.user} has updated an amendment request.", 
                    desc=f"{self.request.user} has updated his\her amendment request for the protocol number {self.amend.protocol_number}.", 
                    link=f"/amendment/amend_detail/{self.amend.id}/")

        return redirect("amendment:my_amendments")
  
      
@method_decorator(user_required(), 'dispatch') 
class MyAmmendments(View):
    def get(self, *args, **kwargs):
        amends = Amendment.objects.filter(created_by = self.request.user).prefetch_related()
        return render(self.request, "amendment/my_amendments.html", {'amends':amends})


@method_decorator(staff_required(), 'dispatch')
class ListAmendments(PermissionRequiredMixin, View):
    permission_required = ['irb.can_list_amendment']
    def get(self, *args, **kwargs):
        return render(self.request, 'amendment/amendment_list.html', {'amends':Amendment.objects.select_related('created_by').all()})


@method_decorator(user_required(), 'dispatch')
class AmendmentDetail( View):

    def get(self, *args, **kwargs):
        try:
            amend = Amendment.objects.select_related('created_by').prefetch_related('amendmentreviews_set','reviewers',).get(id = self.kwargs['pk'])
        except Amendment.DoesNotExist:
            messages.error(self.request, "Couldn't find the Amendment you requested!")
            return redirect("core:error_page")

        is_creator = True if self.request.user == amend.created_by else False
        is_reviewer = self.request.user in amend.reviewers.all()
        if not is_creator and not is_reviewer and not self.request.user.has_perm('irb.can_see_amendment_detail'):
            raise PermissionDenied 

        code, review_form = can_review(self.request.user,is_reviewer, amend)
        data = {'is_creator':is_creator, 'amend':amend,  'rv_feedback_count':amend.amendmentreviews_set.count(), 
                'can_review':code, 'review_form':review_form} 
          
        return render(self.request, 'amendment/amendment_detail.html', data)


@method_decorator(staff_required(), 'dispatch')
class AssignedAmendments(PermissionRequiredMixin, View):
    permission_required = ['irb.can_review_amendment']
    def get(self, *args, **kwargs):
        try:
            amends = Amendment.objects.select_related('created_by').filter(reviewers__id = self.request.user.id)
            return render(self.request, 'amendment/assigned_amendments.html', {'amends': amends})
        except Exception as e:
            print("@@@@ Exception ", e)
            return redirect('irb:home')

   
# for client to view irb comments and update the amendment, for permitted staffs to upload irb comment doc 

@method_decorator(user_required(), 'dispatch')
@method_decorator(permission_required(['irb.can_assign_amendment_reviewers']),'post')
class ListAssassmentReviews( View):
    def dispatch(self, request, *args, **kwargs):
        try:
            amend = Amendment.objects.select_related('created_by').prefetch_related('amendmentirbcomment_set').get(id = self.kwargs['pk'])
        except Amendment.DoesNotExist:
            messages.error(request, "Error, Couldn't find the amendment you requested!")
            return redirect("core:error_page")

        if request.user != amend.created_by and not request.user.has_perm('irb.can_assign_amendment_reviewers'):
           raise PermissionDenied
        self.amend = amend
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        # try:
            if self.request.user == self.amend.created_by:
                data = {'is_creator':True, }

            else:  # if not creator and user has permission
                reviews = AmendmentReviews.objects.select_related('reviewer').filter(amendment = self.amend) 
                data = {'is_creator':False, 'reviews':reviews,'form':FileSubmitForm}
            amend_submissions = [i for i in range(self.amend.submission_count, 0,-1)]
            data.update({'amend':self.amend, 'submissions':amend_submissions})
            return render(self.request, 'amendment/amendment_assessment_reviews.html',data)
    
    def post(self, *args, **kwargs):
        print("entering")
        if self.request.user == self.amend.created_by:
            messages.warning(self.request, "Forbidden, You can't upload a comment for your own amendment request!")
            return redirect("core:error_page")
        
        form = FileSubmitForm(self.request.POST,self.request.FILES)

        if form.is_valid():
            prev = self.amend.amendmentirbcomment_set.filter(submission_num = self.amend.submission_count).first()
            if prev:
                with transaction.atomic():
                    prev.compiled_doc = self.request.FILES['file_doc']
                    prev.compiled_by = self.request.user
                    prev.save()
                    self.amend.status = "On Comment"
                    self.amend.save()
                messages.success(self.request, "You have successfully updated the IRB comment.")
                notify(self.amend.created_by, 'info', f"The IRB has updated the IRB comment document of your amendment!", f"The IRB comment document of your amendment with protocol number {self.amend.protocol_number} has been updated!",
                    link=f'/amendment/list_assessment_reviews/{self.amend.id}/')
            else:
                with transaction.atomic():
                    new = AmendmentIrbComment(compiled_by=self.request.user,amendment=self.amend,submission_num=self.amend.submission_count,compiled_doc=self.request.FILES['file_doc'] )
                    new.save()
                    self.amend.status = "On Comment"
                    self.amend.save()
                messages.success(self.request, "You have successfully sent IRB comment for the creator of this amendment.")
                notify( self.amend.created_by, 'info', f"You have a new IRB comment document for your amendment.", f"The IRB has a sent you comment document for your amendment request with protocol number {self.amend.protocol_number} for your submission #{self.amend.submission_count}!",
                        link=f'/amendment/list_assessment_reviews/{self.amend.id}/')
            return redirect('amendment:amendment_list')
        else:
            print(form.errors)
            messages.warning(self.request, "Invalid data detected, please re-check your inputs and submit again!")
            reviews = AmendmentReviews.objects.select_related('reviewer').filter(amendment = self.amend) 
            amend_submissions = [i for i in range(self.amend.submission_count, 0, -1)]
            data = {'is_creator':False, 'reviews':reviews, 'amend':self.amend,'form':form, 'submissions':amend_submissions}
            return render(self.request, 'amendment/amendment_assessment_reviews.html',data)


        

@method_decorator(staff_required(), 'dispatch')
class ManageAmendment(PermissionRequiredMixin, View):
    permission_required = ['irb.can_see_amendment_detail']

    def get(self, *args, **kwargs):
        try:
            amend = Amendment.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Amendment.DoesNotExist:
            messages.error(self.request, "Error! Couldn't find the requested amendment!")
            return redirect("core:error_page")
        app_code, app_msg = amendment_can_be_approved(self.request.user, amend)
        data ={ 'amend':amend, 'note_form':TextSubmitForm(field_name = "special_note", value = amend.special_note),
                'rejection_form':TextSubmitForm(required=True, field_name = 'rejection_comment', value ="" ),
                'correction_form':TextSubmitForm(field_name = "correction_comment") ,
                'app_code': app_code, 'app_msg' : app_msg, 'err_codes':[2,4,6]
            }
        
        return render(self.request, "amendment/manage_amendment.html",data )

        