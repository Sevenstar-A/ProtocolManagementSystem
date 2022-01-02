import json
from django.shortcuts import render,redirect, get_object_or_404
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.views import View
from django.contrib.auth.decorators import  permission_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from core.models import DownloadableIrbFormDocument
from proposal.models import Proposal
from .models import *
from django.contrib import messages
from .forms import *
from core.forms import TextSubmitForm, FileSubmitForm
from core.utils import get_protocol_code
from core.models import Department
from accounts.utils import user_required, staff_required
from accounts.models import UserAccount, get_permitted_staffs
from notification.models import notify
from .views_renewal_actions import can_review, renewal_can_be_approved
from django.contrib.auth.mixins import  PermissionRequiredMixin


def set_renewal_values(renewal_obj, prot_num,  status, created_by,  code, title=None, renewal_num=None, pi_name=None, proposal=None, proposal_version=None):
    renewal_obj.protocol_number = prot_num
    renewal_obj.status = status 
    renewal_obj.created_by = created_by
    renewal_obj.code = code
    print("seting title")
    if title:
        renewal_obj.proposal_title = title
    print("seting renewal num")
    if renewal_num:
        renewal_obj.renewal_num = renewal_num
    print("seting pi_name", pi_name,"---")
    if pi_name:
        renewal_obj.pi_name = pi_name
    if proposal :
        renewal_obj.proposal = proposal
    if proposal_version:
        renewal_obj.proposal_version = proposal_version 

    return renewal_obj


@method_decorator(user_required(), 'dispatch') 
class MyRenewals(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        renewals = Renewal.objects.select_related('created_by').prefetch_related('renewalapproval_set').filter(created_by = self.request.user)
        return render(self.request, 'renewal/my_renewals.html', {'renewals':renewals})


@method_decorator(user_required(), 'dispatch')
class CheckProtocolNum( View):
    def get(self,*args, **kwargs):
        dn = list(Department.objects.values_list('code_name'))
        d = [ i[0] for i in dn ]
        return render(self.request, "renewal/check_prot_num.html",{'dept_names':json.dumps(d)})
    
    def post(self, *args, **kwargs):
        prot_num = self.request.POST['prot_num'] #is like 001/01/Anat
        prot_num = prot_num.replace('/','-')
        return redirect ("renewal:request_proposal_renewal", prot_num=prot_num)
     

# all except code 5
@method_decorator(user_required(), 'dispatch')
class CreateProposalRenewal( View):
    def dispatch(self, request, *args, **kwargs):
        self.prot_num = str(self.kwargs['prot_num']).replace('-','/')
        result = get_protocol_code(self.prot_num)
        self.code = result['code']
        if self.code == 0:
            messages.error(self.request, f"Error! {result['msg']}")
            return redirect('core:error_page')
        elif self.code == 5: 
            return redirect("renewal:request_new_renewal", prot_num=self.kwargs['prot_num'])
       
        self.prop =  result['proposal'] if 'proposal' in result else None  
        if self.request.user != result['created_by']:
            messages.error(request, "Forbidden, You can't request a Renewal for this protocol number!")
            return redirect("renewal:check_prot_num")

        status = result['status'] 
        if status != "Approved" and status != "Rejected" :
            if self.code == 1:
                messages.warning(request, f"Forbidden, The proposal it self is in '{status}' status, you cannot request a renewal at this stage!  CODE: {self.code}")
            elif self.code == 2:
                messages.warning(request, f"Forbidden! There is another amendment request on process with '{status}' status for this protocol number '{self.prot_num}'.  CODE: {self.code}")
            elif self.code == 3:
                messages.warning(request, f"Forbidden! There is another renewal request on process with '{status}' status for this protocol number '{self.prot_num}'.  CODE: {self.code}")
            else: # if code is 4,6,7,8 it 
                messages.warning(request, f"Forbidden! There is another request on process with '{status}' status for this protocol number '{self.prot_num}'. CODE: {self.code}")
            return redirect("renewal:check_prot_num")
       
        self.last_approval_letter = result['approval_letter']
        self.proposal_version = result['version'] # since a renewal request doesnot change version number
        self.renewal_num = result['renewal_num'] + 1 # request next renewal number
        self.title = result['title'] 
        self.pi_name = result['pi_name']
        self.msg = result['msg']
                
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        form = CreateRenewalForm2()
        return render(self.request, "renewal/create_renewal.html", {    'form':form, 'title':self.title, 'pi_name':self.pi_name, 'prot_num':self.prot_num,'code':self.code, 'msg':self.msg,
                                                                        'app_letter':self.last_approval_letter,'prop_ver':self.proposal_version, 'renewal_num':self.renewal_num })
        

    def post(self, *args, **kwargs):
        form = CreateRenewalForm2(self.request.POST, self.request.FILES)  
        if form.is_valid():
            renewal = form.save(commit=False)
            with transaction.atomic():

                if not self.pi_name and 'pi_name' in self.request.POST: # incase pi_name was none, (c'd b), then z front end will let z user set pi_name, use it
                    print("this is it")
                    self.pi_name = self.request.POST['pi_name'] 
                
                if self.last_approval_letter: # id document is found, use it else use what the user has submitted (cz if doc was not found, the ui let's the user to submit)
                    renewal.last_approval_letter = self.last_approval_letter
                
                elif 'last_approval_letter' in self.request.FILES:
                    renewal.last_approval_letter = self.request.FILES.get('last_approval_letter')
                else:
                    messages.warning(self.request, "Forbidden! Last approval letter missing. We could not find it on our system, So Please upload last approval letter.")
                    return render(self.request, "renewal/create_renewal.html", {    'form':form, 'title':self.title, 'pi_name':self.pi_name, 'prot_num':self.prot_num,'code':self.code, 'msg':self.msg,
                                                                                    'app_letter':None, 'prop_ver':self.proposal_version, 'renewal_num':self.renewal_num, })
                
                renewal = set_renewal_values(   renewal, self.prot_num, "Pending", self.request.user,  self.code, title=self.title,
                                                renewal_num=self.renewal_num, pi_name=self.pi_name, proposal=self.prop, proposal_version= self.proposal_version)
                
                renewal.save()
            staffs = get_permitted_staffs('can_accept_renewal')
            notify(staffs, 'info', f'New Renewal Request by {renewal.created_by}', f'{renewal.created_by} has requested a new renewal request for {self.prot_num}.',
            link=f"/renewal/renewal_detail/{renewal.id}/")
            
            messages.success(self.request, " You have successfully requested a renewal!")
            return redirect("renewal:my_renewals")

        else:
            print("errors",form.errors)
            messages.warning(self.request, "Forbidden! Invalid data detected!")
            return render(self.request, "renewal/create_renewal.html", {    'form':form, 'title':self.title, 'pi_name':self.pi_name, 'prot_num':self.prot_num,'code':self.code,'msg':self.msg, 
                                                                            'app_letter':self.last_approval_letter, 'prop_ver':self.proposal_version, 'renewal_num':self.renewal_num })


# code 5 request_new_renewal/002-21-anat/ 
@method_decorator(user_required(), 'dispatch')
class CreateNewRenewal( View): #for code 5 only
    def dispatch(self, request, *args, **kwargs):
        self.prot_num = str(self.kwargs['prot_num']).replace('-','/')
        result = get_protocol_code(self.prot_num,)
        code = result['code']
        if code == 0:
            messages.error(self.request, f"Error! {result['msg']}")
            return redirect('core:error_page')
        
        elif code != 5: 
            return redirect ("renewal:request_proposal_renewal", self.kwargs['prot_num'])
            
        return super().dispatch(request, *args, **kwargs)
    
    def get(self,*args, **kwargs):
        form = CreateFullRenewalForm
        return render(self.request, "renewal/create_new_renewal.html",{'form':form, 'prot_num':self.prot_num})
    
    def post(self, *args, **kwargs):
        form = CreateFullRenewalForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            renewal = form.save(commit = False)
            renewal = set_renewal_values(renewal, self.prot_num, "Pending", self.request.user,  5)
            renewal.save()
            messages.success(self.request, " You have successfully requested a renewal!")
            staffs = get_permitted_staffs('can_accept_renewal')
            notify(staffs, 'info', f'New Renewal Request by {renewal.created_by}', f'{renewal.created_by} has requested a new renewal request. But the Initial submission was not throught this system and also this is the first time for an renewal request using this system!',
            link=f"/renewal/renewal_detail/{renewal.id}/")
            return redirect("renewal:my_renewals")
        else:
            messages.warning(self.request, "Invalid Data! Please re-check your inputs.")
            return render(self.request, "renewal/create_new_renewal.html",{'form':form, 'prot_num':self.prot_num})


@method_decorator(user_required(), 'dispatch')
class UpdateRenewal( View):
    def dispatch(self, request, *args, **kwargs):
        try:
            renewal = Renewal.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Renewal.DoesNotExist:
            messages.error(self.request, "Error, Couldn't find the renewal you requested!")
            return redirect("renewal:my_renewals")
        if self.request.user != renewal.created_by:
            messages.warning(self.request, "Forbidden, You can't access this renewal, since you arenot the creator!")
            return redirect("renewal:my_renewals")
        if renewal.status != "Pending":
            messages.warning(self.request, f"You can't update a renewal request at '{renewal.status}' status! It should be on 'Pending' status.")
            return redirect("renewal:my_renewals")
        self.renewal = renewal
        return super().dispatch(request, *args, **kwargs)
    

    def get(self, *args, **kwargs):
        if self.renewal.code == 5:
            form = CreateFullRenewalForm ( instance=self.renewal)
            return render(self.request, "renewal/update_new_renewal.html",{'form':form, 'prot_num':self.renewal.protocol_number,'renewal':self.renewal})
        else:
            form = CreateRenewalForm2 (instance =self.renewal)
            return render(self.request, "renewal/update_renewal.html", {'form':form, 'prot_num':self.renewal.protocol_number,'code':self.renewal.code, 'app_letter':self.renewal.last_approval_letter,'pi_name':self.renewal.pi_name,
                                                                        'title':self.renewal.proposal_title, 'prop_ver':self.renewal.proposal_version, 'renewal_num':self.renewal.renewal_num, 'renewal':self.renewal })
        
    def post(self, *args, **kwargs):
        
        if self.renewal.code == 5:
            form = CreateFullRenewalForm (self.request.POST, self.request.FILES,  instance=self.renewal, )
        else:
            form = CreateRenewalForm2 (self.request.POST, self.request.FILES, instance = self.renewal)
        
        if not form.is_valid():
            print(form.errors)
            messages.error(self.request, "Error, Invalid data detected. Please re-check your inputs and try again!")
            if self.renewal.code == 5:
                return render(self.request, "renewal/update_new_renewal.html",{'form':form, 'prot_num':self.renewal.protocol_number, 'renewal':self.renewal})               
            else:
                return render(self.request, "renewal/update_renewal.html", {'form':form, 'prot_num':self.renewal.protocol_number,'code':self.renewal.code, 'app_letter':self.renewal.last_approval_letter,
                                                                            'prop_ver':self.renewal.proposal_version, 'renewal_num':self.renewal.renewal_num, 'renewal':self.renewal })

        # if form is valid
        self.renewal = form.save()
        
        messages.success(self.request, "You have successfully updated your renewal request!")
        if 'send_notification' in self.request.POST:
            staffs = get_permitted_staffs('can_accept_renewal')
            notify( staffs, 'info', f"{self.request.user} has updated a renewal request.", 
                    desc=f"{self.request.user} has updated his\her renewal request for the protocol number {self.renewal.protocol_number}.", 
                    link=f"/renewal/renewal_detail/{self.renewal.id}/")

        return redirect("renewal:my_renewals")
  
      


@method_decorator(staff_required(), 'dispatch')
class ListRenewals(PermissionRequiredMixin, View):
    permission_required = ['irb.can_list_renewal']
    def get(self, *args, **kwargs):
        return render(self.request, 'renewal/renewal_list.html', {'renewals':Renewal.objects.select_related('created_by').all()})


@method_decorator(user_required(), 'dispatch')
class RenewalDetail( View):
    def get(self, *args, **kwargs):
        try:
            renewal = Renewal.objects.select_related('proposal', 'created_by').prefetch_related('renewalreviews_set','reviewers',).get(id = self.kwargs['pk'])
        except Renewal.DoesNotExist:
            messages.error(self.request, "Couldn't find the Renewal you requested!")
            return redirect("core:error_page")

        is_creator = True if self.request.user == renewal.created_by else False
        is_reviewer = self.request.user in renewal.reviewers.all()
        if not is_creator and not is_reviewer and not self.request.user.has_perm('irb.can_see_renewal_detail'):
            raise PermissionDenied 
        
        code, review_form = can_review(self.request.user, is_reviewer, renewal)
        data = {'is_creator':is_creator, 'renewal':renewal,  'rv_feedback_count':renewal.renewalreviews_set.count(), 
                'can_review':code, 'review_form':review_form} 
          
        return render(self.request, 'renewal/renewal_detail.html', data)


@method_decorator(staff_required(), 'dispatch')
class AssignedRenewals(PermissionRequiredMixin, View):
    permission_required = ['irb.can_review_renewal']
    def get(self, *args, **kwargs):
        try:
            renewals = Renewal.objects.select_related('created_by').filter(reviewers__id = self.request.user.id)
            return render(self.request, 'renewal/assigned_renewals.html', {'renewals': renewals})
        except Exception as e:
            print("@@@@ Exception ", e)
            return redirect('irb:home')


@method_decorator(staff_required(), 'dispatch')
class ManageRenewal(PermissionRequiredMixin, View):
    permission_required = ['irb.can_see_renewal_detail']

    def get(self, *args, **kwargs):
        try:
            renewal = Renewal.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Renewal.DoesNotExist:
            messages.error(self.request, "Error! Couldn't find the requested renewal!")
            return redirect("core:error_page")
        app_code, app_msg = renewal_can_be_approved(self.request.user, renewal)
        data ={ 'renewal':renewal, 'note_form':TextSubmitForm(field_name = "special_note", value = renewal.special_note),
                'rejection_form':TextSubmitForm(required=True, field_name = 'rejection_comment', value ="" ),
                'correction_form':TextSubmitForm(field_name = "correction_comment") ,
                'app_code': app_code, 'app_msg' : app_msg, 'err_codes':[2,4]
            }
        
        return render(self.request, "renewal/manage_renewal.html",data )

        
# for renewal, only permitted staff see the assasment page, since their will be no IRB comment
# the S.O will either approve or reject the request, but don't send IRB comment
@method_decorator(staff_required(), 'dispatch')
class ListAssassmentReviews(PermissionRequiredMixin, View):
    permission_required = ['irb.can_assign_renewal_reviewers']
    def get(self, *args, **kwargs):
        try:
            renewal = Renewal.objects.select_related('created_by').get(id = self.kwargs['pk'])
        except Renewal.DoesNotExist:
            messages.error(self.request, "Error, Couldn't find the renewal you requested!")
            return redirect("core:error_page")
        is_creator = True if self.request.user == renewal.created_by else False
        if is_creator: #creators should not see renewal assasment page, cz it only shows reviewers assassment review, which they can't see
            raise PermissionDenied

        if not is_creator and not self.request.user.has_perm('irb.can_assign_renewal_reviewers'):
           raise PermissionDenied
        reviews = RenewalReviews.objects.select_related('reviewer').filter(renewal = renewal) 
        return render(self.request, 'renewal/renewal_assessment_reviews.html',{'is_creator':is_creator,'renewal':renewal, 'reviews':reviews})
    
    


        