import json
from django.shortcuts import render,redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from core.models import DownloadableIrbFormDocument
from proposal.models import Proposal
from .models import Renewal, RenewalApproval, RenewalReviews, RenewalDeletion, RenewalRejection
from django.contrib import messages
from .forms import RenewalReviewForm, AssignRenewalReviewersForm, RenewalApprovalForm
from accounts.utils import user_required, staff_required
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import  permission_required
from notification.models import notify
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from core.forms import TextSubmitForm
from django.db import transaction
from accounts.models import get_permitted_staffs

# if user is a reviewer 
def can_review(user, is_reviewer, renewal):
    """ checks review permission,  is reviewer, and status """
    if user != renewal.created_by and  user.has_perm('irb.can_review_renewal') and  is_reviewer and renewal.status in ["On Review",  "Reviewed"]: 
        try:
            rv = RenewalReviews.objects.get(renewal = renewal, reviewer = user ) # check if he has reviewed
            return [2, RenewalReviewForm(instance=rv)] # already reviewed
        except RenewalReviews.DoesNotExist:
            return [1, RenewalReviewForm] # can review, first time for this submission number
    return [0,None]


# checks permission and not created and status
def can_accept(user, renewal):
    if not user.has_perm('irb.can_accept_renewal'):
        return (1, "Not permitted!")
    elif user == renewal.created_by:
        return (2, "Warning! You can't accept your own renewal request!")
    elif renewal.status != 'Pending':
        return (3, f"Warning! Renewal request couldnot be accepted at '{renewal.status} status! It has to be on 'Pending' status!")
    return (0, None)

# checks permission, not user and status
def can_pendit(user, renewal):
    if not user.has_perm('irb.can_accept_renewal'):
        return (1, "You don't have pending permission!")  
    elif user == renewal.created_by:
        return (2, "You can't manage your own renewal request")
    elif renewal.status == "Pending":
        return (3, "Already on pending")
    elif renewal.status == "Rejected":
        return (4, "Cannot revert status of a 'Rejected' renewal. The investigator should initiate a new renewal request!")
    return (0, "Can pend it")


# checks renewal approval 
def renewal_can_be_approved(user, renewal):
    if user == renewal.created_by or not user.has_perm('irb.can_approve_renewal'):
        return (0 , "You are not permitted to approve this renewal")

    if not renewal.has_been_approved:
        if renewal.status == "Reviewed":
            return (1, "Approving for the first time") 
        else:
            return (2,  f"Renewal cannot be approved for the first time with '{renewal.status}' status, it has to be on 'Reviewed' status.")
        
    else: #has been approved previously
        if renewal.status != "Rejected":
            return (3, "Since it has been approved previously, you can update the approval letter") #update
        else:
            return (4,  "Cannot be approved, cz eventhough it has been approved, since it is now on 'Rejected' status, it has to be reviewed again")


# requires accepting permission
@staff_required()
def AcceptRenewalRequest(request, pk):
    try:
        renewal = Renewal.objects.get(id = pk)
    except Renewal.DoesNotExist:
        messages.error(request, "Error! Couldn't find the Renewal your requested to accept!")
        return redirect('core:error_page')
    code, msg = can_accept(request.user, renewal)
    if code == 1:
        raise PermissionDenied
    elif code in [2, 3]:
        messages.warning(request, msg)
        return redirect("renewal:renewal_list")
    
    renewal.status = "Submited"
    renewal.submited_date = timezone.now()
    renewal.accepted_by = request.user
    renewal.save()
    notify( renewal.created_by, 'success', f"Your renewal request for {renewal.protocol_number} has been submited!",
    desc=f"The IRB has accepted your renewal request with protocol number '{renewal.protocol_number}' to review it.", )
    messages.success(request, "Accepted Renewal Request Successfully !")
    return redirect('renewal:manage_renewal', pk=renewal.id)


# renewal staff action functionalities
@staff_required()
@permission_required('irb.can_accept_renewal')
def SendCorrectionComment(request):
    """ accepts renewal id and send notification to the investigator """
    if request.method == 'POST':
        try:
            if not request.user.has_perm('irb.can_accept_renewal'):
                return JsonResponse(data = {'error':True, 'msg':str("You have no permission to send correction comments for renewal requests!")})

            data = json.loads(request.body)
            r = Renewal.objects.only('id','protocol_number').get(id = data['r_id'])
            notify  (r.created_by, 'warning', 'You have a correction comment from the IRB for your renewal request!',
                    desc=f"Correct comment from the IRB for your renewal request with protocol number :- '{r.protocol_number}'. The comment is => '{data['comment']}'", )
           
            return JsonResponse(data = {'error':False})
        except Exception as e:
            print("### Exception ", e)
            return JsonResponse(data = {'error':True, 'msg':str(e)})
    else:
        return JsonResponse(data = {'error':True, 'msg':"Unsupported request method"})


@staff_required()
@permission_required('irb.can_see_renewal_detail')
def UpdateSpecialNote(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            r = Renewal.objects.only('id').get(id = data['r_id'])
            note = data['note']
            r.special_note = note 
            r.save()
            return JsonResponse(data = {'error':False})
        except Exception as e:
            print("### Exception ", e)
            return JsonResponse(data = {'error':True, 'msg':str(e)})


#requires accepting permission
@staff_required()  
def ToPending(request, pk):
    try:
        renewal = Renewal.objects.only('id','status','protocol_number').get(id = pk)
        code, msg = can_pendit(request.user, renewal)
        if code == 0:
            renewal.status = 'Pending'
            renewal.save()
            messages.success(request, "Successfully reverted renewal status to pending!")
            notify(renewal.created_by, 'info', "Your renewal status has been updated to 'Pending' status!",
                f"The status of your renewal request with protocol number of '{renewal.protocol_number}' has been updated to Pending status by IRB staffs! ")
            return redirect("renewal:manage_renewal", pk= renewal.id)
        elif code in [2,3,4]:
            messages.warning(request, msg)
            return redirect("renewal:renewal_list")
        else : # for code = 1
            raise PermissionDenied
        
    except:
        messages.error(request, "Error! Couldn't find the renewal you requested while pending!")
        return redirect("core:error_page")



def check_all_reviewed_renewal(renewal,  noti_users=None):
    """
    check whether all the reviewers have reviewed the renewal or not and if all reviewed, send notification
    """
    reviewed_num = RenewalReviews.objects.filter(renewal = renewal).count()
    if renewal.reviewers.count() == reviewed_num:
        renewal.status = 'Reviewed'
        renewal.save()
        if noti_users != None:
            notify  ( noti_users, 'info', f"All reviewers of {renewal.protocol_number} has submited their review!",
                    desc=f"All reviewers of {renewal.protocol_number} has submited their review!", link=f"/renewal/list_assessment_reviews/{renewal.id}/" )
        
       

@staff_required()
@permission_required(['irb.can_review_renewal'])
def ReviewRenewal(request, pk):
     if request.method=="POST" :
        #!!! if you a prefetch_related here for 'renewalreviews_set' then it will fetch it all z reviewers comment
        # until now, then after you saved a new review, if you check the renewalreviews_set.count, it will only know
        # about the previous objects! So DON'T USE PREFETCH_RELATED ON renewalreviews_set
        renewal = Renewal.objects.select_related('created_by').prefetch_related('reviewers').get(id = pk)
        if renewal.created_by == request.user:
            messages.warning(request, "Forbidden, You can't review your own Renewal request!")
            return redirect("renewal:my_renewals")
        if not request.user in renewal.reviewers.all():
            messages.warning(request, "Forbidden, You are not permitted to review this proposal!")
            return redirect("core:error_page")
        if not renewal.status in ['On Review', "Reviewed"]:
            messages.warning(request, f"Forbidden, You cannot perform renewal review on '{renewal.status}' status!")
            return redirect("core:error_page")
        
        noti_users = get_permitted_staffs("can_assign_renewal_reviewers").exclude(id = request.user.id)
        
        try: # check if the reviewer has reviewed this renewal before, if yes, just update it
            previous = RenewalReviews.objects.get(renewal = renewal, reviewer = request.user)
            form = RenewalReviewForm(request.POST, instance=previous )
            if form.is_valid():
                previous = form.save()
                messages.success(request,"You have updated your review!")
                notify( noti_users , 'info', f"{request.user} has updated a renewal review for '{renewal.protocol_number}' !",
                    desc=f"{request.user} has updated a renewal review for the :- '{renewal.protocol_number}'.", 
                    link=f"/renewal/list_assessment_reviews/{renewal.id}/")
                         
            else:
                messages.warning(request, "Invalid data detected, please re-check your inputs!")
                
        # creating new
        except RenewalReviews.DoesNotExist:
            form = RenewalReviewForm(request.POST)
            if form.is_valid():
                new_rvw = form.save(commit=False)
                new_rvw.renewal = renewal
                new_rvw.reviewer = request.user
                new_rvw.save()
                messages.success(request, "You have successfully submitted your renewal reviewer feedback!")
                notify  ( noti_users , 'info', f"{request.user} has submited a renewal review for {renewal.protocol_number} !",
                            desc=f"{request.user} has submitted a review for the renewal with protocol number :- '{renewal.protocol_number}'.", 
                            link=f"/renewal/list_assessment_reviews/{renewal.id}/")
            else:
                messages.warning(request, "Invalid data detected, please re-check your inputs!")
                
            
        check_all_reviewed_renewal(renewal, noti_users)
        return redirect("renewal:renewal_detail", pk=renewal.id)
    

@method_decorator(staff_required(), 'dispatch')
class ApproveRenewal(PermissionRequiredMixin, View):
    permission_required=['irb.can_approve_renewal']
    def dispatch(self, request, *args, **kwargs):
        try:
            self.renewal = Renewal.objects.select_related('created_by').prefetch_related('renewalapproval_set').get(id = self.kwargs['pk'])
        except Renewal.DoesNotExist:
            messages.warning(request, "Warning! Can't find the Renewal you requested.")
            return redirect("renewal:renewal_list")

        code, msg = renewal_can_be_approved(self.request.user, self.renewal)
        if code in [0,2,4]:
            messages.warning(request, f"Warning! {msg}")
            return redirect("renewal:renewal_list")
        self.previous = self.renewal.renewalapproval_set.first()
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs): 
        if self.previous:
            print("got one")
            form = RenewalApprovalForm(instance=self.previous)
        else:
            form = RenewalApprovalForm()
        return render(self.request, "renewal/approve_renewal.html",{'renewal':self.renewal, 'form':form, 'previous_approval_document':self.previous })
        
    def post(self, *args, **kwargs):
        try:
            if self.previous:
                form  = RenewalApprovalForm(self.request.POST, self.request.FILES, instance=self.previous)
            else:
                form  = RenewalApprovalForm(self.request.POST, self.request.FILES)
            print(self.request.POST['end_date'])
            if form.is_valid():
                if self.previous != None:# just updating
                    with transaction.atomic():
                        self.previous = form.save()
                        # self.previous.approval_letter = self.request.FILES.get('approval_letter')
                        self.previous.approval_date = timezone.now()
                        self.previous.approved_by = self.request.user
                        self.previous.save()
                        self.renewal.status = "Approved"
                        self.renewal.has_been_approved = True
                        self.renewal.save()
                        self.renewal.reviewers.clear() #.clear() calls save() method by default
                    messages.success(self.request, "You have updated the approval letter successfully!")
                    try:
                        notify(self.renewal.created_by, 'success', 'Your renewal approval letter has been updated!', link=f"/renewal/renewal_detail/{self.renewal.id}/",
                        desc= f"The approval letter for your renewal with a protocol number of {self.renewal.protocol_number} has been updated!")
                        
                    except Exception:
                        print("Can't send approval notification")

                else: 
                    with transaction.atomic():  
                        approval = RenewalApproval(renewal =self.renewal, approval_letter=self.request.FILES.get('approval_letter'),approved_by= self.request.user)
                        approval.save()
                        self.renewal.status = "Approved"
                        self.renewal.has_been_approved = True
                        self.renewal.save()
                        self.renewal.reviewers.clear() # .clear() calls save() method by default
                    messages.success(self.request, "You have successfully approved a proposal request!")
                    try:
                        notify(self.renewal.created_by, 'success', f"Congradulation! Your renewal request has been approved!", link=f"/renewal/renewal_detail/{self.renewal.id}/",
                        desc =f"Your Renewal request with a protocol number of {self.renewal.protocol_number} is approved! ")
                        notify(self.renewal.reviewers.all(), 'info', f'The renewal with propocol number {self.renewal.protocol_number} is approved! ')
                    except Exception as e:
                        print("Can't send approval notifications!",e)
                return redirect("renewal:renewal_list")
            
            else:
                messages.warning(self.request, "Warning! Please Attach an approval letter.")
                return render(self.request, "renewal/approve_renewal.html",{'renewal':self.renewal, 'form':form, 'last_approval_document':self.previous })
        

        except Exception as e:
            print("######### ",e)
            messages.error(self.request, "Error! An Exception occured when approving a renewal! please try agian later.")
            return redirect("renewal:renewal_list")


@method_decorator(staff_required(), 'dispatch')
class AssignReviewers(PermissionRequiredMixin, View):
    permission_required = ['irb.can_assign_renewal_reviewers']
    def dispatch(self, request, *args, **kwargs) :
        try:
            renewal  = Renewal.objects.select_related('created_by').get(id = self.kwargs['pk'])
            if not renewal.status in [ 'Submited',  "On Review", "Reviewed"]:
                messages.warning(request, f"Forbidden! Can't assign reviewers at '{renewal.status}' Status!")
                return redirect("renewal:manage_renewal", pk=renewal.id)
            elif renewal.created_by == request.user:
                messages.warning(self.request, "Forbidden! Can't assign reviewers for your own renewal request!")
                return redirect("renewal:renewal_list")
            else:
                self.renewal = renewal
                return super().dispatch(request, *args, **kwargs)

        except Exception as e:
            print("@ Exception ",e)
            messages.error(self.request, "Error! Internal Server Error")
            return redirect("core:error_page")

    def get(self, *args, **kwargs):
        form = AssignRenewalReviewersForm(instance=self.renewal, creator= self.renewal.created_by)
        return render(self.request, "proposal/assign_reviewers.html", # use proposal/assign_reviewers template for this too.
             {'form':form,'renewal':True, 'prot_num':self.renewal.protocol_number})

    def post(self, *args, **kwargs):
        try:
            previous_reviewers =list( self.renewal.reviewers.all())
            previous_status = self.renewal.status
            form = AssignRenewalReviewersForm(self.request.POST, instance=self.renewal, creator= self.renewal.created_by)
            if form.is_valid():
                self.renewal = form.save()
                self.renewal.status = 'On Review'
                self.renewal.save()
                current_reviewers = list(self.renewal.reviewers.all().only('id'))
                
                removed_rvs = []
                for r in previous_reviewers:
                    if r not in current_reviewers:
                        removed_rvs.append(r)

                new_reviewers = []
                for r in current_reviewers:
                    if r not in previous_reviewers:
                        new_reviewers.append(r)

                messages.success(self.request, f'You have successfully assigned {len(current_reviewers)} reviewers for the renewal request!')
                if previous_status == 'Submited': # when assigned for z first time, send notification to z investigator
                    notify (self.renewal.created_by, 'info', f"Your Renewal Request '{self.renewal.protocol_number}' has been given to reviewers.",
                        desc=f"Your Renewal Request with a protocol number of '{self.renewal.protocol_number}' has been given to reviewers .", )
                
                # Just send z notification to new reviewers only, send "you r removed notification to the removed reviewers"
                notify(new_reviewers, 'info', 'You have been assigned on a new renewal.', 
                        f"You have been assigned on a new renewal with protocol number '{self.renewal.protocol_number}'.", 
                        link=f"/renewal/renewal_detail/{self.renewal.id}/")

                notify(removed_rvs, 'info', f'You have been removed from being a reviewer for {self.renewal.protocol_number} renewal',
                        f'You have been removed from being a reviewer for {self.renewal.protocol_number} renewal')

                return redirect('renewal:renewal_list')
            else:
                messages.error(self.request, f"Failed {form.errors}")
                return render(self.request, 'proposal/assign_reviewers.html',{'form':form, 'renewal':True,'prot_num':self.renewal.protocol_number})
            

        except Exception as e:
            print("Exception ",e)
            messages.error(self.request,"An unexpected exception has occured. Please try again later!")
            return redirect("core:error_page")


@method_decorator(staff_required(), 'dispatch')
class RejectRenewal(PermissionRequiredMixin, View):
    permission_required= ['irb.can_approve_renewal']
    def post(self, *args, **kwargs):
        try:
            renewal = Renewal.objects.prefetch_related('renewalrejection_set').get(id = self.kwargs['pk'])
        except  Renewal.DoesNotExist:
            messages.error(self.request, "Error! Couldn't find the requested Renewal!")
            return redirect("renewal:manage_renewal", pk=self.kwargs['pk'])
        if self.request.user == renewal.created_by:
            messages.error(self.request, "Forbidden! You can't reject your own renewal request!")
            return redirect("renewal:my_renewals")
        form = TextSubmitForm(self.request.POST, required=True, field_name = "rejection_comment")
        if not form.is_valid():
            print(form.errors)
            messages.warning(self.request, "Error! A rejection needs a comment! please enter you reason for rejection!")
            return redirect("renewal:manage_renewal", pk=self.kwargs['pk'])
        previous = renewal.renewalrejection_set.first()
        if previous:
            with transaction.atomic():
                previous.rejection_comment = self.request.POST['rejection_comment']
                previous.rejected_by = self.request.user
                previous.save() 
                renewal.status = "Rejected"
                renewal.save()
                renewal.reviewers.clear() #.clear() calls save() method by default
            messages.success(self.request, f"You have updated the rejection comment of {renewal.protocol_number}!")

        else:
            with transaction.atomic():
                rej = RenewalRejection(renewal = renewal, rejection_comment = self.request.POST['rejection_comment'], rejected_by= self.request.user)
                rej.save()
                renewal.status = "Rejected"
                renewal.save()
                renewal.reviewers.clear() #.clear() calls save() method by default
            messages.success(self.request, f"You have successfully rejected a renewal request with protocol number {renewal.protocol_number}")
        
        notify(renewal.created_by, 'error', f"  Your renewal request has been rejected!", f"Your renewal request with a protocol number of " 
                                            f"{renewal.protocol_number}, is rejected by the IRB!", link= f"/renewal/list_assessment_reviews/{renewal.id}/")
        
        return redirect("renewal:manage_renewal", pk=renewal.id)
             

@method_decorator(user_required(), 'dispatch')
class DeleteRenewal(View):
    def get(self, *args, **kwargs):
        try:
            renewal = Renewal.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Renewal.DoesNotExist:
            messages.warning(self.request, "Couldn't find the requested Renewal!")
            return redirect("core:error_page")
        if self.request.user == renewal.created_by or self.request.user.has_perm('irb.can_accept_renewal'):
            if not renewal.status in ["Pending", "Rejected"] : 
                messages.warning(self.request, f"You can't delete a renewal with at this stage!")
                return redirect("core:error_page")
            
            crt_date = renewal.created_date.date()
            title = renewal.proposal_title
            creator = renewal.created_by
            with transaction.atomic():
                d = RenewalDeletion(    creator_name = renewal.created_by.full_name, creator_email= renewal.created_by.email, 
                                        proposal_title = title, deleted_by = self.request.user.full_name)
                renewal.delete()
                d.save()
            messages.success(self.request, "You have successfully deleted a renewal!")
            if self.request.user == creator:
                return redirect('renewal:my_renewals')
            else:
                notify(creator, 'error', f'Your renewal has been deleted by IRB staff', 
                    f"One of your renewal with the title '{title}' created at '{crt_date}' has been deleted by IRB staff!")
                return redirect('renewal:renewal_list')
        else:
            raise PermissionDenied
        


