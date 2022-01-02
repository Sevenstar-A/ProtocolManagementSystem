from datetime import date
import json
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http.response import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from accounts.forms import *
from notification.models import notify
from proposal.models import *
from proposal.forms import *
from core.forms import FileSubmitForm, TextSubmitForm
from django.forms import  modelformset_factory
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required, permission_required
from .user_status_validators import *
from accounts.utils import  staff_required, user_required
from django.utils.decorators import method_decorator
# views highly related with irb staff activities 
# mostly action nek neger

# requires accepting permission
@method_decorator(staff_required(), 'dispatch')
class AcceptPropReq( PermissionRequiredMixin, View):
    # try: #never use a try inside a transaction.atomic, but since this is outside z transaction, it's fine
        # with transaction.atomic:
        permission_required= ['irb.can_accept_proposal']
        def get(self, *args, **kwargs):
            return redirect("proposal:manage_proposal", pk=self.kwargs['pk'])

        def post(self, *args, **kwargs):
            try:
                prop = Proposal.objects.get(id = self.kwargs['pk'])
            except Exception as e:
                messages.error(self.request, "Error! Couldn't find the proposal your requested to accept!")
                return redirect('core:error_page')

            if not can_accept(self.request.user, prop) == 0:
                messages.error(self.request, "Forbidden! You cannot accept this protocol!")
                return redirect('core:error_page')


            form = ProposalAcceptanceForm(self.request.POST, instance=prop)
            if form.is_valid():
                prop = form.save(commit=False)
                if prop.latest_version_num == 1:
                    if prop.protocol_number == '-':
                        deprt_code_name = InitialSubmission.objects.values_list('department__code_name').get(proposal = prop)
                        prop = generate_prot_num(prop, deprt_code_name[0])
                        if not prop:
                            messages.error(self.request, "Error! Could not generate protocol number!")
                            return redirect("core:error_page")
                    prop.accepted_by = self.request.user # first time accepted by
                    prop.accepted_date = timezone.now() # first time accepted date

                else:
                    latest = prop.get_latest_ver_obj()
                    latest.accepted_date = timezone.now()
                    latest.accepted_by = self.request.user
                    latest.save()

                prop.status = 'Submited'
                prop.save()
                
                notify( prop.created_by, 'success', f"Your initial submission request has been accepted!",
                        desc=f"The IRB has accepted your initial submission request for the proposal with protocol number {prop.protocol_number} on {prop.accepted_date.date()}.", )
                
                messages.success(self.request, "Accepted Proposal Submission Request Successfully !")
                return redirect("proposal:manage_proposal", pk=prop.id)
            else:
                print(form.errors)
                messages.error(self.request, f"Error, Invalid data to accept {form.errors}")
                return redirect("proposal:manage_proposal", pk=prop.id)


@method_decorator(staff_required(), 'dispatch')
class ToPending( PermissionRequiredMixin, View):
    permission_required = ['irb.can_accept_proposal']
    def get(self, *args, **kwargs):
        try:
            p = Proposal.objects.only('id','status','protocol_number').get(id = self.kwargs['pk'])
            if can_pendit(self.request.user, p) == 0:
                p.status = 'Pending'
                p.save()
                messages.success(self.request, "Successfully reverted proposal status to pending!")
                notify(p.created_by, 'warning', 'Your protocol has been reverted to Pending status!',
                        f"Your protocol with protocol number of '{p.protocol_number}' has been reverted to Pending status by IRB staffs! ")
                return redirect("proposal:proposal_list")
            else:
                messages.warning(self.request, "Forbidden, You can't pend this protocol!")
                return redirect('core:error_page')
        except:
            messages.error(self.request, "Error! Couldn't find the propsal you requested while pending!")
            return redirect("core:error_page")


def check_all_reviewed( prop, noti_users=None):
    """
    check whether all the users have reviewed the proposal or not and if all reviewed, send notification
    """
    reviewed_num = ProposalReviewerFeedback.objects.filter(proposal = prop, version = prop.latest_version_num).count()
    num_of_reviewers = prop.reviewers.count() 
    if num_of_reviewers > 0 and num_of_reviewers  == reviewed_num:
        prop.status = 'Reviewed'
        prop.save()
        if noti_users != None:
            notify  ( noti_users, 'info', f"All reviewers of {prop.protocol_number} has submited their review!",
                    desc=f"All reviewers of {prop.protocol_number} has submited their review!", link= f"/proposal/proposal_detail/{prop.id}/" )
            

@method_decorator(staff_required(), 'dispatch')
class ProposalReview( PermissionRequiredMixin, View):
    permission_required = ['irb.can_review_proposal']
    def post(self, *args, **kwargs):
        prop = Proposal.objects.get(id = self.kwargs['pk'])
        if  can_review(self.request.user, prop) == 0: # for review the error codes change, reffer the source code of can_review()
            messages.warning(self.request, "Forbidden. You can't access this page! ")
            return redirect("proposal:assigned_proposal")

        form = FileSubmitForm(self.request.POST, self.request.FILES, required=True, field_name = 'study_ass_doc')
        if not self.request.method=="POST" or  not form.is_valid():
            messages.error(self.request, "Error. Please Upload the File Document ")
            return redirect("proposal:assigned_proposal")

            #!!! if you a prefetch_related here for 'proposalreviewerfeedback_set' then it will fetch it all z reviewers comment
            # until now, then after you saved a new review, if you check the proposalreviewerfeedback_set.count, it will only know
            # about the previous objects! So DON'T USE PREFETCH_RELATED ON proposalreviewerfeedback_set
        doc_file = self.request.FILES['study_ass_doc'] 
        if not prop.status in ['On Review', "Reviewed"]:
            messages.warning(self.request, f"Forbidden, You can't submit a review comment with {prop.status} status")
            return redirect("core:error_page") 
        
        if not self.request.user in prop.reviewers.all():
            messages.warning(self.request, "Forbidden, You are not permitted to review this proposal!")
            return redirect("core:error_page")



        # check if the reviewer has submitted other reviews before for this current version, if yes just update it.
        previous = ProposalReviewerFeedback.objects.filter(proposal = prop, version = prop.latest_version_num, reviewer = self.request.user).first() 
        # get users to notify
        noti_users = get_permitted_staffs( "can_assign_proposal_reviewers", [self.request.user.id]) #exclude current user if he is one of the reviewer assigners
            
        if previous:
            previous.study_ass_doc = doc_file
            previous.save()
            messages.success(self.request,"You have updated your review successfully!")
            
            notify( noti_users , 'info', f"{self.request.user} has updated a review for {prop.protocol_number} !",
                    desc=f"{self.request.user} has updated a review for the proposal :- '{prop.protocol_number}' on {timezone.now().date()}.",
                    link=f"/proposal/proposal_detail/{prop.id}/" )
                
            
        else:
            rv = ProposalReviewerFeedback.objects.create(reviewer = self.request.user, proposal = prop, study_ass_doc =doc_file, version = prop.latest_version_num ) 
            rv.save()
            messages.success(self.request, "You have successfully submitted your reviewer feedback!")
            notify  ( noti_users , 'info', f"{self.request.user} has submited a review for {prop.protocol_number} !",
                            desc=f"{self.request.user} has submitted a review for the proposal :- '{prop.protocol_number}' on {timezone.now().date()}.",
                            link=f"/proposal/proposal_detail/{prop.id}/" )
                
            
        check_all_reviewed( prop, noti_users)
        return redirect("proposal:assigned_proposal")


@staff_required()
@permission_required('irb.can_accept_proposal')
def SendCorrectionComment(request):
    """ accepts proposal id and send notification to the investigator """

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            p = Proposal.objects.only('id','protocol_number').get(id = data['p_id'])

            notify  (p.created_by, 'warning', 'You have a correction comment from the IRB! click View Detail.',
                    desc=f"Correction comment from the IRB for latest submission request with protocol number :- '{p.protocol_number}'. \n Comment is => '{data['comment']}'", )
           
            return JsonResponse(data = {'error':False})
        except Exception as e:
            print("### Exception ", e)
            return JsonResponse(data = {'error':True, 'msg':str(e)})
    else:
        return JsonResponse(data = {'error':False, 'msg':"unsupported request method!"} )


@staff_required()
@permission_required('irb.can_list_proposal')
def UpdateSpecialNote(request):
    """ accepts proposal id and send notification to the investigator """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            p = Proposal.objects.only('id','protocol_number').get(id = data['p_id'])
            note = data['note']
            p.special_note = note 
            p.save()
            return JsonResponse(data = {'error':False})
        except Exception as e:
            print("### Exception ", e)
            return JsonResponse(data = {'error':True, 'msg':str(e)})


@method_decorator(staff_required(), 'dispatch')
class AssignReviewers( PermissionRequiredMixin, View):
    permission_required = ['irb.can_assign_proposal_reviewers']
    def dispatch(self, request, *args, **kwargs) :
        try:
            self.prop  = Proposal.objects.get(id = self.kwargs['pk'])
            can_assign = can_assign_reviewers(self.request.user, self.prop)
            if can_assign == 0:
                return super().dispatch(request, *args, **kwargs)
            elif can_assign == 1:
                messages.warning(self.request, "Forbidden! Can't assign reviewers for your own protocol!")
            elif can_assign == 2:
                messages.warning(request, f"Forbidden! Can't assign reviewers at '{self.prop.status}' Status!")
            return redirect("core:error_page")
                

        except Exception as e:
            print("@ Exception ",e)
            messages.error(self.request, "Error! Internal Server Error")
            return redirect("core:error_page")

    def get(self, *args, **kwargs):
        form = AssignProposalReviewersForm(instance=self.prop, creator =self.prop.created_by)
        return render(self.request, "proposal/assign_reviewers.html", {'form':form,'prot_num':self.prop.protocol_number})

    def post(self, *args, **kwargs):
        try:
            previous_reviewers =list( self.prop.reviewers.all().only('id'))
            previous_status = self.prop.status
            form = AssignProposalReviewersForm(self.request.POST, instance=self.prop, creator =self.prop.created_by)
            
            if form.is_valid():
                self.prop = form.save()
                self.prop.status = 'On Review'
                self.prop.save()
                current_reviewers = list(self.prop.reviewers.all().only('id'))
                removed_rvs = []
                for r in previous_reviewers:
                    if r not in current_reviewers:
                        removed_rvs.append(r)

                new_reviewers = []
                for r in current_reviewers:
                    if r not in previous_reviewers:
                        new_reviewers.append(r)

                check_all_reviewed( self.prop)
                messages.success(self.request, 'You have successfully assigned reviewers for the proposal!')
                
                if previous_status == 'Submited': # when assigned for z first time, send notification to z investigator
                    notify (self.prop.created_by, 'info', f"Your Proposal '{self.prop.protocol_number}' has been given to reviewers.",
                        desc=f"Your Proposal with a protocol number of '{self.prop.protocol_number}' has been given to reviewers .", 
                        link=f"/proposal/proposal_detail/{self.prop.id}/")
                
                # Just send z notification to new reviewers only, send "you r removed notification to the "
                notify(new_reviewers, 'info', 'You have been assigned on a new proposal.', 
                        f"You have been assigned on a new proposal with protocol number '{self.prop.protocol_number}'.", 
                        link= f"/proposal/proposal_detail/{self.prop.id}/")

                notify(removed_rvs, 'info', f'You have been removed from being a reviewer for {self.prop.protocol_number}',
                        f'You have been removed from being a reviewer for {self.prop.protocol_number}')
                return redirect('proposal:proposal_list')
                
            else:
                messages.error(self.request, f"Error! Invalid input data detected. Please re-check your inputs. ")
                return render(self.request, 'proposal/assign_reviewers.html',{'form':form, 'prot_num':self.prop.protocol_number})
            

        except Exception as e:
            print("Exception ",e)
            messages.error(self.request,"An unexpected exception has occured. Please try again later!")
            return redirect("core:error_page")


# for permitted, investigators &/or reviewers, z inv can submit next version protocol   
# status = any
@method_decorator(user_required(), 'dispatch')
class ListAssassmentReviews(View):
    
    def dispatch(self, request, *args, **kwargs):
        try:
            prop = Proposal.objects.prefetch_related('proposalirbcomment_set', 'proposalapprovals_set').get(id = kwargs['pk'])
        except Proposal.DoesNotExist:
            messages.warning(request, "Warning! Can't find the proposal you requested.")
            return redirect("proposal:proposal_list")
        self.prop = prop
        self.previous = prop.proposalirbcomment_set.filter(version = prop.latest_version_num).first()
        return super().dispatch(request, *args, **kwargs)
        
    def get(self, *args, **kwargs):
        # try:
            if self.prop.status in ["On Review", "Reviewed", "On Comment"] and self.request.user.has_perm('irb.can_assign_proposal_reviewers') and self.request.user != self.prop.created_by:
                if self.previous:
                    form = ProposalIrbCommentForm(instance= self.previous)
                else:
                    form = ProposalIrbCommentForm
            else:
                form = None
            return render(self.request, 'proposal/list_assassment_reviews.html',{ 'prop':self.prop,'form':form, 'can_approve':can_approve(self.request.user, self.prop) })
        
        # except Exception as e:
        #     print("Exception ",e)
        #     messages.error(self.request, "Error! Internal Server Error!")
        # return redirect("core:error_page")

    def post(self, *args, **kwargs):
            if not self.prop.status in ["On Review", "Reviewed", "On Comment"]:
                messages.warning(self.request, f"Forbidden! You can't send Irb comment at '{self.prop.status}' status!")
                return redirect('proposal:list_assessment_reviews', pk=self.prop.id)
            
            if self.previous:
                form = ProposalIrbCommentForm(self.request.POST, self.request.FILES, instance= self.previous)
                if form.is_valid():
                    with transaction.atomic():
                        previous = form.save(commit=False) 
                        previous.created_by = self.request.user
                        previous.save()
                        self.prop.status = "On Comment"
                        self.prop.save()
                    messages.success(self.request, f"You have updated the irb assessment document for '{self.prop.protocol_number}'.")
                    
                    notify( self.prop.created_by, 'info', "There was an update for an assessment review comment.", 
                            f"The Irb has updated the assessment review comment on {self.prop.protocol_number}! for version {self.prop.latest_versin_num}.",
                            link=f"/proposal/list_assessment_reviews/{self.prop.id}/")
                
                else:
                    messages.error(self.request, "Warning! Invalid input data detected! Be sure that you have submited a valid decistion type and comment document!")
                    return redirect('proposal:list_assessment_reviews', pk=self.prop.id)
            
            else:
                form = ProposalIrbCommentForm(self.request.POST, self.request.FILES)
                if form.is_valid():
                    with transaction.atomic():
                        new = ProposalIrbComment(created_by = self.request.user, proposal = self.prop, decision_type =self.request.POST['decision_type'],  version=self.prop.latest_version_num, irb_comment_doc = self.request.FILES.get('irb_comment_doc'))
                        new.save()
                        self.prop.status = "On Comment"
                        self.prop.save()
                    messages.success(self.request, "You have successfully sent your comment!")

                    notify(self.prop.created_by, 'success',f"You have comment from the IRB {self.prop.protocol_number}!", 
                        f"The Irb has sent you a comment document for your protocol '{self.prop.protocol_number}'. ",
                        link=f"/proposal/list_assessment_reviews/{self.prop.id}/")
                
                else:
                    messages.error(self.request, "Warning! Invalid input data detected! Be sure that you have submited a valid decistion type and comment document!")
                    return redirect('proposal:list_assessment_reviews', pk=self.prop.id)
            
        
        
            return redirect('proposal:list_assessment_reviews', pk=self.prop.id)

            
        # except Exception as e:
        #     print("#####",e)
        #     messages.error(self.request, "Error! Internal Server Error, please try agai later.")
        #     return redirect('proposal:proposal_list')


@method_decorator(staff_required(), 'dispatch')  
class ApproveProposal( PermissionRequiredMixin, View):
    permission_required = ['irb.can_approve_proposal']
    def dispatch(self, request, *args, **kwargs):
        try:
            self.prop = Proposal.objects.select_related('created_by').prefetch_related('proposalapprovals_set').get(id = self.kwargs['pk'])
        except Proposal.DoesNotExist:
            messages.warning(request, "Warning! Can't find the proposal you requested.")
            return redirect("proposal:proposal_list")

        if self.prop.latest_version_num == 1 and  self.prop.status != "Reviewed" and self.prop.status != 'Approved' :
            messages.warning(request, f"Warning! You can't approve a proposal for the first time  with '{self.prop.status}' Status! It needs to be on 'Reviewed' Status!")
            return redirect("proposal:proposal_list")
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        last_document = self.prop.proposalapprovals_set.first()
        return render(self.request, "proposal/approve_proposal.html",{'prop':self.prop, 'last_approval_document':last_document })
        
    def post(self, *args, **kwargs):
        try:
            if not 'approval_letter' in self.request.FILES:
                messages.warning(self.request, "Warning! Please Attach an approval letter.")
                return redirect("proposal:proposal_list")
            
            previous = self.prop.proposalapprovals_set.first() 
            if previous != None:
                with transaction.atomic():
                    previous.approval_letter = self.request.FILES.get('approval_letter')
                    previous.approval_date = timezone.now()
                    previous.approved_by = self.request.user
                    previous.save()
                    self.prop.status = "Approved"
                    self.prop.has_been_approved = True
                    self.prop.save()
                    self.prop.reviewers.clear() #.clear() calls save() method by default
                messages.success(self.request, "You have updated the approval letter!")
                notify(self.prop.created_by, 'success', 'Your proposal approval letter has been updated!', f"The approval letter for your proposal with a protocol number of {self.prop.protocol_number} has been updated!",
                    link=f"/proposal/list_assessment_reviews/{self.prop.id}/")
                    
                
            else: 
                with transaction.atomic():  
                    approval = ProposalApprovals(proposal =self.prop, approval_letter=self.request.FILES.get('approval_letter'),approved_by= self.request.user)
                    approval.save()
                    self.prop.status = "Approved"
                    self.prop.has_been_approved = True
                    self.prop.save()
                    self.prop.reviewers.clear() #.clear() calls save() method by default
                messages.success(self.request, "You have successfully approved a proposal request!")
                
                notify(self.prop.created_by, 'success', 'Congradulation! Your proposal has been approved!', f"Your proposal with a protocol number of {self.prop.protocol_number} is approved! ",
                    link=f"/proposal/list_assessment_reviews/{self.prop.id}/")
                
                notify(self.prop.reviewers.all(), 'info', f'The proposal with propocol number {self.prop.protocol_number} is approved! ')
                
            return redirect("proposal:proposal_list")

        except Exception as e:
            print("######### ",e)
            messages.error(self.request, "Error! An Exception occured when approving! please try agian later.")
            return redirect("proposal:proposal_list")


@method_decorator(staff_required(), 'dispatch')
class RejectProposal(PermissionRequiredMixin, View):
    permission_required= ['irb.can_approve_proposal']
    def post(self, *args, **kwargs):
        try:
            prop = Proposal.objects.prefetch_related('proposalrejection_set').get(id = self.kwargs['pk'])
        except  Proposal.DoesNotExist:
            messages.error(self.request, "Error! Couldn't find the requested proposal!")
            return redirect("proposal:manage_proposal", pk=self.kwargs['pk'])
        form = TextSubmitForm(self.request.POST, required=True, field_name = "rejection_comment")
        if not form.is_valid():
            messages.warning(self.request, "Error! A rejection needs a comment! please enter you reason for rejection!")
            return redirect("proposal:manage_proposal", pk=self.kwargs['pk'])
        previous = prop.proposalrejection_set.first()
        if previous:
            with transaction.atomic():
                previous.rejection_comment = self.request.POST['rejection_comment']
                previous.rejected_by = self.request.user
                previous.version = prop.latest_version_num
                previous.save() 
                prop.status = "Rejected"
                prop.save()
                prop.reviewers.clear() #.clear() calls save() method by default
            messages.success(self.request, f"You have updated the rejection comment of {prop.protocol_number}!")

        else:
            with transaction.atomic():
                rej = ProposalRejection(proposal = prop, rejection_comment = self.request.POST['rejection_comment'], version = prop.latest_version_num, rejected_by= self.request.user)
                rej.save()
                prop.status = "Rejected"
                prop.save()
                prop.reviewers.clear() #.clear() calls save() method by default
            messages.success(self.request, f"You have successfully rejected a proposal request with protocol number {prop.protocol_number}")
        
        notify(prop.created_by, 'error', f" Your proposal request has been rejected!", f"Your proposal request with a protocol number of {prop.protocol_number}," 
                                            "is rejected by the IRB!", link= f"/proposal/list_assessment_reviews/{prop.id}/")
    
        return redirect("proposal:manage_proposal", pk=prop.id)
            

@method_decorator(user_required(), 'dispatch')
class DeleteProposal(View):
    def get(self, *args, **kwargs):
        try:
            prop = Proposal.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Proposal.DoesNotExist:
            messages.warning(self.request, "Couldn't find the requested proposal!")
            return redirect("core:error_page")
        if self.request.user == prop.created_by or self.request.user.has_perm('irb.can_accept_proposal'):
            if prop.protocol_number != '-':
                messages.warning(self.request, "You can't delete this proposal since it has been already registered and a protocol number is given to it!")
                return redirect("core:error_page")

            if not prop.status in ["Pending", "Rejected"]: 
                messages.warning(self.request, f"You can't delete a proposal with {prop.status}!")
                return redirect("core:error_page")
            
            crt_date = prop.created_date.date()
            title = prop.title
            creator = prop.created_by
            with transaction.atomic():
                d = ProposalDeletion(creator_name = prop.created_by.full_name, creator_email=prop.created_by.email,
                                    proposal_title = title, deleted_by = self.request.user.full_name)
                prop.delete()
                d.save()
            messages.success(self.request, "You have successfully deleted a proposal!")
            if self.request.user == creator:
                return redirect('proposal:my_proposals')
            else:
                notify(creator, 'error', f'Your proposal has been deleted by IRB staff', 
                    f"One of your proposals with the title '{title}' create at '{crt_date}' has been deleted by IRB staff!")
                return redirect('proposal:proposal_list')
        else:
            raise PermissionDenied
        
        
