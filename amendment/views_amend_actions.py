from datetime import date, time
import json
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http.response import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from accounts.forms import *
from notification.models import notify
from .models import *
from .forms import *
from django.forms import  modelformset_factory
from django.utils import timezone
from django.db import transaction
from accounts.utils import user_required, staff_required
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import  permission_required
from core.forms import TextSubmitForm

def can_accept(user, amend):
    if not user.has_perm('irb.can_accept_amendment'):
        return (1, "Not permitted!")
    elif user == amend.created_by:
        return (2, "Warning! You can't accept your own amendment request!")
    elif amend.status != 'Pending':
        return (3, f"Warning! Amendment request couldnot be accepted at '{amend.status} status! It has to be on 'Pending' status!")
    return (0, None)


def can_pendit(user, amend):
    if not user.has_perm('irb.can_accept_amendment'):
        return (1, "You don't have pending permission!")  
    elif user == amend.created_by:
        return (2, "You can't manage your own amendment request")
    elif amend.status == "Pending":
        return (3, "Already on pending")
    elif amend.status == "Rejected":
        return (4, "Cannot revert status of a 'Rejected' amendment. The investigator should initiate a new amendment request!")
    
    return (0, "Can pend it")


# amendment staff action functionalities
@staff_required()
@permission_required('irb.can_accept_amendment')
def SendCorrectionComment(request):
    """ accepts amendment id and send notification to the investigator """
    if request.method == 'POST':
        try:
            if not request.user.has_perm('irb.can_accept_amendment'):
                return JsonResponse(data = {'error':True, 'msg':str("You have no permission to send correction comments for amendment requests!")})

            data = json.loads(request.body)
            a = Amendment.objects.only('id','protocol_number').get(id = data['a_id'])
            notify  (a.created_by, 'warning', 'You have a correction comment from the IRB!',
                    desc=f"Correct comment from the IRB for latest amendment request with protocol number :- '{a.protocol_number}'. The comment is => '{data['comment']}'", )
           
            return JsonResponse(data = {'error':False})
        except Exception as e:
            print("### Exception ", e)
            return JsonResponse(data = {'error':True, 'msg':str(e)})
    else:
        return JsonResponse(data = {'error':True, 'msg':"Unsupported request method"})



# requires accepting permission
@staff_required()
def AcceptAmendmentRequest(request, pk):
    try:
        amend = Amendment.objects.get(id = pk)
    except Amendment.DoesNotExist:
        messages.error(request, "Error! Couldn't find the Amendment your requested to accept!")
        return redirect('core:error_page')
    code, msg = can_accept(request.user, amend)
    if code == 1:
        raise PermissionDenied
    elif code in [2, 3]:
        messages.warning(request, msg)
        return redirect("amendment:amendment_list")
    
    amend.status = "Submited"
    amend.submited_date = timezone.now()
    amend.accepted_by = request.user
    amend.save()
    notify( amend.created_by, 'success', f"Your amendment request for {amend.protocol_number} has been submited!",
    desc=f"The IRB has accepted your amendment request with protocol number '{amend.protocol_number}' to review it.", )
    messages.success(request, "Accepted Amendment Request Successfully !")
    return redirect('amendment:manage_amendment', pk=amend.id)


#requires accepting permission
@staff_required()  
def ToPending(request, pk):
    try:
        amend = Amendment.objects.only('id','status','protocol_number').get(id = pk)
        code, msg = can_pendit(request.user, amend)
        if code == 0:
            amend.status = 'Pending'
            amend.save()
            messages.success(request, "Successfully reverted amendment status to pending!")
            notify(amend.created_by, 'info', "Your amendment status has been updated to 'Pending' status!",
                f"The status of your amendment request with protocol number of '{amend.protocol_number}' has been updated to Pending status by IRB staffs! ")
            return redirect("amendment:manage_amendment", pk= amend.id)
        elif code in [2,3,4]:
            messages.warning(request, msg)
            return redirect("amendment:amendment_list")
        else :
            raise PermissionDenied
        
    except:
        messages.error(request, "Error! Couldn't find the amendment you requested while pending!")
        return redirect("core:error_page")


def check_all_reviewed_amendment(amend,  noti_users=None):
    """
    check whether all the reviewers have reviewed the amendment or not and if all reviewed, send notification
    """
    reviewed_num = AmendmentReviews.objects.filter(amendment = amend, submission_num =amend.submission_count).count()
    if amend.reviewers.count() == reviewed_num:
        amend.status = 'Reviewed'
        amend.save()
        if noti_users != None:
            notify  ( noti_users, 'info', f"All reviewers of {amend.protocol_number} has submited their review!",
                    desc=f"All reviewers of {amend.protocol_number} has submited their review!", link=f"/amendment/list_assessment_reviews/{amend.id}/" )
        

@staff_required()
@permission_required(['irb.can_review_amendment'])
def ReviewAmendment(request, pk):
     if request.method=="POST" :
        #!!! if you a prefetch_related here for 'amendmentreviews_set' then it will fetch it all z reviewers comment
        # until now, then after you saved a new review, if you check the amendmentreviews_set.count, it will only know
        # about the previous objects! So DON'T USE PREFETCH_RELATED ON amendmentreviews_set
        amend = Amendment.objects.select_related('created_by').prefetch_related('reviewers').get(id = pk)
        if amend.created_by == request.user:
            messages.warning(request, "Forbidden, You can't review your own Amendment request!")
            return redirect("amendment:my_amendments")
        if not request.user in amend.reviewers.only('id'):
            messages.warning(request, "Forbidden, You are not permitted to review this proposal!")
            return redirect("core:error_page")
        if not amend.status in ['On Review', "Reviewed"]:
            messages.warning(request, f"Forbidden, You cannot perform amendment review on '{amend.status}' status!")
            return redirect("core:error_page")
        
        noti_users = get_permitted_staffs("can_assign_amendment_reviewers").exclude(id = request.user.id)
        
        try: # check if the reviewer has reviewed this amendment before, if yes, just update it
            previous = AmendmentReviews.objects.get(amendment = amend, reviewer = request.user, submission_num = amend.submission_count)
            form = AmendmentReviewForm(request.POST, instance=previous )
            if form.is_valid():
                previous = form.save()
                messages.success(request,"You have updated your review!")
                notify( noti_users , 'info', f"{request.user} has updated an amendment review for '{amend.protocol_number}' !",
                    desc=f"{request.user} has updated an amendment review for the :- '{amend.protocol_number}'.", 
                    link=f"/amendment/list_assessment_reviews/{amend.id}/")
                         
            else:
                messages.warning(request, "Invalid data detected, please re-check your inputs!")
                
        # creating new
        except AmendmentReviews.DoesNotExist:
            form = AmendmentReviewForm(request.POST)
            if form.is_valid():
                new_rvw = form.save(commit=False)
                new_rvw.amendment = amend
                new_rvw.reviewer = request.user
                new_rvw.submission_num = amend.submission_count 
                new_rvw.save()
                messages.success(request, "You have successfully submitted your amendment reviewer feedback!")
                notify  ( noti_users , 'info', f"{request.user} has submited an amendment review for {amend.protocol_number} !",
                            desc=f"{request.user} has submitted a review for the amendment with protocol number :- '{amend.protocol_number}'.", 
                            link=f"/amendment/list_assessment_reviews/{amend.id}/")
            else:
                messages.warning(request, "Invalid data detected, please re-check your inputs!")
                
            
        check_all_reviewed_amendment(amend, noti_users)
        return redirect("amendment:amend_detail", pk=amend.id)
    

@staff_required()
@permission_required('irb.can_see_amendment_detail')
def UpdateSpecialNote(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            a = Amendment.objects.only('id','protocol_number').get(id = data['a_id'])
            note = data['note']
            a.special_note = note 
            a.save()
            return JsonResponse(data = {'error':False})
        except Exception as e:
            print("### Exception ", e)
            return JsonResponse(data = {'error':True, 'msg':str(e)})


@method_decorator(staff_required(), 'dispatch')
class ApproveAmendment(PermissionRequiredMixin, View):
    permission_required=['irb.can_approve_amendment']
    def dispatch(self, request, *args, **kwargs):
        try:
            self.amend = Amendment.objects.select_related('created_by').prefetch_related('amendmentapproval_set').get(id = self.kwargs['pk'])
        except Amendment.DoesNotExist:
            messages.warning(request, "Warning! Can't find the Amendment you requested.")
            return redirect("amendment:amendment_list")

        if not self.amend.has_been_approved and not self.amend.status in ["On Review", "Reviewed"] :
            messages.warning(request, f"Warning! You can't approve an amendment for the first time  with '{self.amend.status}' Status! It needs to be on either 'On Review' or 'Reviewed' Status!")
            return redirect("amendment:amendment_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        previous = self.amend.amendmentapproval_set.first() 
        return render(self.request, "amendment/approve_amendment.html",{'amend':self.amend, 'last_approval_document':previous })
        
    def post(self, *args, **kwargs):
        try:
            if not 'approval_letter' in self.request.FILES:
                messages.warning(self.request, "Warning! Please Attach an approval letter.")
                return redirect("amendment:amendment_list")

            previous = self.amend.amendmentapproval_set.first() 
            # if self.amend.has_been_approved else None
            # just updating
            if previous != None:
                with transaction.atomic():
                    previous.approval_letter = self.request.FILES.get('approval_letter')
                    previous.approval_date = timezone.now()
                    previous.approved_by = self.request.user
                    previous.save()
                    self.amend.status = "Approved"
                    self.amend.has_been_approved = True
                    self.amend.save()
                    self.amend.reviewers.clear() #.clear() calls save() method by default
                messages.success(self.request, "You have updated the approval letter!")
                try:
                    notify(self.amend.created_by, 'success', 'Your amendment approval letter has been updated!', link=f"/amendment/amend_detail/{self.amend.id}/",
                    desc= f"The approval letter for your amendment with a protocol number of {self.amend.protocol_number} has been updated!")
                    
                except Exception:
                    print("Can't send approval notification")

            else: 
                with transaction.atomic():  
                    approval = AmendmentApproval(amendment =self.amend, approval_letter=self.request.FILES.get('approval_letter'),approved_by= self.request.user)
                    approval.save()
                    self.amend.status = "Approved"
                    self.amend.has_been_approved = True
                    self.amend.save()
                    self.amend.reviewers.clear() # .clear() calls save() method by default
                    
                    if self.amend.code <=2: #1 or 2
                        prop = self.amend.proposal
                        if prop:
                            prop.latest_version_num_with_amend = self.amend.proposal_version
                            prop.save()
                            print ("setting proposal version", self.amend.proposal_version)
                        else:
                            messages.error(self.request, "Error! Couldn't find the proposal related with this amendment!")
                    
                messages.success(self.request, "You have successfully approved a proposal request!")
                try:
                    notify(self.amend.created_by, 'success', f"Congradulation! Your amendment request has been approved!", link=f"/amendment/amend_detail/{self.amend.id}/",
                    desc =f"Your Amendment request with a protocol number of {self.amend.protocol_number} is approved! ")
                    notify(self.amend.reviewers.all(), 'info', f'The amendment with propocol number {self.amend.protocol_number} is approved! ')
                except Exception as e:
                    print("Can't send approval notifications!",e)
            return redirect("amendment:amendment_list")

        except Exception as e:
            print("######### ",e)
            messages.error(self.request, "Error! An Exception occured when approving an amendment! please try agian later.")
            return redirect("amendment:amendment_list")


@method_decorator(staff_required(), 'dispatch')
class AssignReviewers(PermissionRequiredMixin, View):
    permission_required = ['irb.can_assign_amendment_reviewers']
    def dispatch(self, request, *args, **kwargs) :
        try:
            amend  = Amendment.objects.get(id = self.kwargs['pk'])
            if not amend.status in [ 'Submited',  "On Review", "Reviewed"]:
                messages.warning(request, f"Forbidden! Can't assign reviewers at '{amend.status}' Status!")
                return redirect("amendment:manage_amendment", pk=amend.id)
            elif amend.created_by == request.user:
                messages.warning(self.request, "Forbidden! Can't assign reviewers for your own amendment request!")
                return redirect("amendment:amendment_list")
            else:
                self.amend = amend
                return super().dispatch(request, *args, **kwargs)

        except Exception as e:
            print("@ Exception ",e)
            messages.error(self.request, "Error! Internal Server Error")
            return redirect("core:error_page")

    def get(self, *args, **kwargs):
        form = AssignAmendmentReviewersForm(instance=self.amend, creator= self.amend.created_by)
        # 
        return render(self.request, "proposal/assign_reviewers.html", # use proposal/assign_reviewers template for this too.
             {'form':form,'amendment':True, 'prot_num':self.amend.protocol_number})

    def post(self, *args, **kwargs):
        try:
            previous_reviewers =list( self.amend.reviewers.all().only('id'))
            previous_status = self.amend.status
            form = AssignAmendmentReviewersForm(self.request.POST, instance=self.amend, creator= self.amend.created_by)
            if form.is_valid():
                self.amend = form.save()
                self.amend.status = 'On Review'
                self.amend.save()
                current_reviewers = list(self.amend.reviewers.all().only('id'))
                
                removed_rvs = []
                for r in previous_reviewers:
                    if r not in current_reviewers:
                        removed_rvs.append(r)

                new_reviewers = []
                for r in current_reviewers:
                    if r not in previous_reviewers:
                        new_reviewers.append(r)

                messages.success(self.request, f'You have successfully assigned {len(current_reviewers)} reviewers for the amendment request!')
                if previous_status == 'Submited': # when assigned for z first time, send notification to z investigator
                    notify (self.amend.created_by, 'info', f"Your Amendment Request '{self.amend.protocol_number}' has been given to reviewers.",
                        desc=f"Your Amendment Request with a protocol number of '{self.amend.protocol_number}' has been given to reviewers .", )
                
                # Just send z notification to new reviewers only, send "you r removed notification to the removed reviewers"
                notify(new_reviewers, 'info', 'You have been assigned on a new amendment.', 
                        f"You have been assigned on a new amendment with protocol number '{self.amend.protocol_number}'.", 
                        link=f"/amendment/amend_detail/{self.amend.id}/")

                notify(removed_rvs, 'info', f'You have been removed from being a reviewer for {self.amend.protocol_number} amendment',
                        f'You have been removed from being a reviewer for {self.amend.protocol_number} amendment')

                return redirect('amendment:amendment_list')
            else:
                messages.error(self.request, f"Failed {form.errors}")
                return render(self.request, 'proposal/assign_reviewers.html',{'form':form, 'amendment':True,'prot_num':self.amend.protocol_number})
            

        except Exception as e:
            print("Exception ",e)
            messages.error(self.request,"An unexpected exception has occured. Please try again later!")
            return redirect("core:error_page")



@method_decorator(staff_required(), 'dispatch')
class RejectAmendment(PermissionRequiredMixin, View):
    permission_required= ['irb.can_approve_amendment']
    def post(self, *args, **kwargs):
        try:
            amend = Amendment.objects.prefetch_related('amendmentrejection_set').get(id = self.kwargs['pk'])
        except  Amendment.DoesNotExist:
            messages.error(self.request, "Error! Couldn't find the requested Amendment!")
            return redirect("amendment:manage_amendment", pk=self.kwargs['pk'])
        if self.request.user == amend.created_by:
            messages.error(self.request, "Forbidden! You can't reject your own amendment request!")
            return redirect("amendment:my_amendments")
        form = TextSubmitForm(self.request.POST, required=True, field_name = "rejection_comment")
        if not form.is_valid():
            print(form.errors)
            messages.warning(self.request, "Error! A rejection needs a comment! please enter you reason for rejection!")
            return redirect("amendment:manage_amendment", pk=self.kwargs['pk'])
        previous = amend.amendmentrejection_set.first()
        if previous:
            with transaction.atomic():
                previous.rejection_comment = self.request.POST['rejection_comment']
                previous.rejected_by = self.request.user
                previous.submission_count = amend.submission_count
                previous.save() 
                amend.status = "Rejected"
                amend.save()
                amend.reviewers.clear() #.clear() calls save() method by default
            messages.success(self.request, f"You have updated the rejection comment of {amend.protocol_number}!")

        else:
            with transaction.atomic():
                rej = AmendmentRejection(amendment = amend, rejection_comment = self.request.POST['rejection_comment'],submission_count=amend.submission_count, rejected_by= self.request.user)
                rej.save()
                amend.status = "Rejected"
                amend.save()
                amend.reviewers.clear() #.clear() calls save() method by default
            messages.success(self.request, f"You have successfully rejected an amendment request with protocol number {amend.protocol_number}")
        
        notify(amend.created_by, 'error', f"Your amendment request has been rejected!", f"Your amendment request with a protocol number of {amend.protocol_number}," 
                                                "is rejected by the IRB!", link= f"/amendment/list_assessment_reviews/{amend.id}/")
        
        return redirect("amendment:manage_amendment", pk=amend.id)
             

@method_decorator(user_required(), 'dispatch')
class DeleteAmendment(View):
    def get(self, *args, **kwargs):
        try:
            amend = Amendment.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Amendment.DoesNotExist:
            messages.warning(self.request, "Couldn't find the requested Amendment!")
            return redirect("core:error_page")
        if self.request.user == amend.created_by or self.request.user.has_perm('irb.can_accept_amendment'):
            if not amend.status in ["Pending", "Rejected"] or amend.submission_count != 1: 
                messages.warning(self.request, f"You can't delete an amendment with at this stage!")
                return redirect("core:error_page")
            
            crt_date = amend.created_date.date()
            title = amend.proposal_title
            creator = amend.created_by
            with transaction.atomic():
                d = AmendmentDeletion(  creator_name = amend.created_by.full_name,creator_email= amend.created_by.email, 
                                        proposal_title = title, deleted_by = self.request.user.full_name)
                amend.delete()
                d.save()
            messages.success(self.request, "You have successfully deleted an amendment!")
            if self.request.user == creator:
                return redirect('amendment:my_amendments')
            else:
                notify(creator, 'error', f'Your amendment has been deleted by IRB staff', 
                    f"One of your amendment with the title '{title}' created at '{crt_date}' has been deleted by IRB staff!")
                return redirect('amendment:amendment_list')
        else:
            raise PermissionDenied
        
