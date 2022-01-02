import json
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import request
from django.http.response import HttpResponseRedirect, JsonResponse
from django.forms import  modelformset_factory, inlineformset_factory
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.db.models import Q
from accounts.utils import *
from core.forms import TextSubmitForm, MultipleFileSubmit
from accounts.forms import *
from notification.models import notify
from proposal.models import *
from proposal.forms import *
from .user_status_validators import *
from django.contrib.auth.context_processors import auth
from django.core.exceptions import PermissionDenied


STATUS_SEARCH = {'approved':'Approved', 'pending':'Pending', 'on_review': 'On Review','on_comment':'On Comment', 'rejected':'Rejected'}

def get_user_proposal_full_data(user):
    pass

def get_user_proposal_count_data(user):
    all = Proposal.objects.filter(created_by = user)
    return {
        'all':all.count(),
        'approved':  all.filter(status ='Approved').count(),
        'pending' : all.filter(status = 'Pending').count(),
        'rejected' : all.filter(status = 'Rejected').count(),
        'on_comment' : all.filter(status = 'On Comment').count(),
        'on_review' : all.filter(status = 'Under Review').count()
    }

@method_decorator(user_required(), 'dispatch')
class MyProposals(  View):
    def get(self, *args, **kwargs):
        p = Proposal.objects.filter(created_by = self.request.user).select_related('initialsubmission').prefetch_related('initialproposaldocument_set','proposalirbcomment_set')
        return render(self.request, "proposal/my_proposals.html",{'props':p})

@method_decorator(user_required(), 'dispatch')
class CreateProposal( View):
    def get(self, *args, **kwargs):
        return render(self.request, 'proposal/proposal_create.html',
                        {'proposal_form':Initial_Create_Form()})
    
    def post(self, args, **kwargs):
        form = Initial_Create_Form(self.request.POST, self.request.FILES,)
        if form.is_valid() :
            with transaction.atomic():
                prop = Proposal(title = self.request.POST['title'], created_by = self.request.user)
                prop.save()
                initial = form.save(commit=False)
                initial.proposal = prop
                initial.study_type = self.get_names(initial.study_type) 
                initial.study_pop = self.get_names(initial.study_pop)
                initial.special_res = self.get_names(initial.special_res)
                initial.impaired = self.get_names(initial.impaired)
                initial.exclusion = self.get_names(initial.exclusion)
                initial.save()
            
            messages.success(self.request, "Successfully created Proposal! Now please upload proposal documents.")
            return redirect(f"/proposal/create_docs/{prop.id}/")
        else:
            print(form.errors)
            messages.error(self.request, "Couldn't Create Proposal! Please fill the following inputs properly!")
            return render(self.request, 'proposal/proposal_create.html',{'proposal_form':form, })

    def get_names(self,s):
        if s[-1] == ",":
            s = s[:len(s) -1]
        s = s.replace(",",", ")
        return s


@method_decorator(user_required(), 'dispatch')
class UpdateInitialSumbissionForm( View):
    def dispatch(self, request, *args, **kwargs):
        try:
            p = Proposal.objects.select_related('initialsubmission').get(id = kwargs["pk"])
        except Proposal.DoesNotExist:
            messages.error(request, "Error. Couldn't find the requested proposal!")
            return redirect('core:erro_page')
        if p.status !='Pending' or p.created_by != request.user :
            messages.error(request, "Forbidden! You can't Update this proposal!")
            return redirect('core:error_page')
        if p.latest_version_num != 1:
            messages.error(request, "Forbidden! You can't Update this version, because it is not the latest version for this protocol!")
            return redirect('core:error_page')
        self.p = p
        self.initialsubmission = p.initialsubmission
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        return render(self.request, 'proposal/proposal_update.html',{'proposal_form':Initial_Create_Form( instance=self.initialsubmission, title= self.p.title) })
    
    def post(self, args, **kwargs):
        form = Initial_Create_Form(self.request.POST, self.request.FILES, instance=self.initialsubmission, )
        if form.is_valid():
            with transaction.atomic():
                self.p.title = self.request.POST['title']
                self.p.save()
                self.initial = form.save(commit=False)
                
                self.initial.study_type = self.get_names(self.initial.study_type) 
                self.initial.study_pop = self.get_names(self.initial.study_pop)
                self.initial.special_res = self.get_names(self.initial.special_res)
                self.initial.impaired = self.get_names(self.initial.impaired)
                self.initial.exclusion = self.get_names(self.initial.exclusion)
                self.initial.save()
            if 'send_notification' in self.request.POST:
                staffs = get_permitted_staffs('can_accept_proposal')
                notify(staffs, 'info', f"{self.request.user} has updated an initial submission form.", 
                desc=f"{self.request.user} has updated an initial submission form.", link=f"/proposal/proposal_detail/{self.p.id}/")

                
            messages.success(self.request, "Successfully updated initial proposal form! ")
            return redirect("proposal:my_proposals")
           
        else:
            print(form.errors)
            messages.error(self.request, "Couldn't update proposal! Please fill the following inputs properly!")
            return render(self.request, 'proposal/proposal_update.html',{'proposal_form':form, })

    def get_names(self,s):
        if s[-1] == ",":
            s = s[:len(s) -1]
        s = s.replace(",",", ")
        return s

@method_decorator(user_required(), 'dispatch')
class CreateDocs( View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.prop = Proposal.objects.only('id','status').prefetch_related('initialproposaldocument_set').get(id=self.kwargs["pk"])
        except Proposal.DoesNotExist:
            messages.error(self.request, "Error! Couldn't find the requested proposal!")
            return redirect("core:error_page")
        if request.user != self.prop.created_by or self.prop.latest_version_num != 1 :
            messages.error(request, "Forbidden! You can't upload documents for this protocol!")
            return redirect('core:error_page')

        if self.prop.status != "Pending":
            messages.error(request, f"Forbidden! You can't upload docuemnts at '{self.prop.status}' status, it needs to be on Pending status. Please contact the irb to change the status to Pending for you!")
            return redirect('core:my_proposals')

        if len( self.prop.initialproposaldocument_set.all()) > 0 :
            messages.error(request, "Forbidden! You have already submitted your documents!")
            return redirect('proposal:my_proposals')
                
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        
        doc_types = InitialProposalDocType.objects.exclude(name = "Other Related Document").only('name')

        Doc_FormSet = modelformset_factory(InitialProposalDocument , form=Proposal_Doc_Create_Form,  extra=len(doc_types) )
        doc_formset = Doc_FormSet(prefix = "doc_form", queryset=InitialProposalDocument.objects.none())
        
        Cors_FormSet = modelformset_factory ( Investigators,form=Investigator_Create_Form, extra=1)
        cors_formset = Cors_FormSet(prefix='cors_form', queryset=Investigators.objects.none())

        invs_sign_form = DownloadableIrbFormDocument.objects.filter(name ="Participating Investigators Signature Form")

        return render(self.request, 'proposal/create_docs.html',{  'doc_formset':doc_formset, 'doc_types':doc_types ,  'invs_form':FileSubmitForm(required =True, field_name = 'inv_doc'),
                                                                    'cors_formset':cors_formset, 'proposal':self.prop,'invs_sign_form':invs_sign_form,})
    
    def post(self, *args, **kwargs):
        Doc_FormSet = modelformset_factory(model= InitialProposalDocument , form=Proposal_Doc_Create_Form, )
        doc_form = Doc_FormSet(self.request.POST, self.request.FILES, prefix='doc_form')

        Cors_FormSet = modelformset_factory (model=Investigators,form=Investigator_Create_Form )
        cors_form =Cors_FormSet(self.request.POST, self.request.FILES, prefix='cors_form')

        inv_form = FileSubmitForm(self.request.POST, self.request.FILES, required =True, field_name = 'inv_doc')
        
        if doc_form.is_valid() and cors_form.is_valid() and inv_form.is_valid():
            docs = doc_form.save(commit=False)
            for d in docs:
                d.proposal = self.prop
            InitialProposalDocument.objects.bulk_create(docs)
                
            cos = cors_form.save(commit=False)
            for c in cos:
                c.proposal = self.prop
            
            Investigators.objects.bulk_create(cos)
            if 'other_docs' in self.request.FILES:
                doc_type, created = InitialProposalDocType.objects.get_or_create(name = "Other Related Document") 
                other_docs = []
                for f in self.request.FILES.getlist('other_docs'):
                    d = InitialProposalDocument(doc = f, doc_type = doc_type, proposal=self.prop,)
                    other_docs.append(d)
                InitialProposalDocument.objects.bulk_create(other_docs)

            pi = Investigators.objects.filter(proposal = self.prop, is_pi = True).first()
            if pi:
                self.prop.pi_name = pi.name
                self.prop.save()
            ini= self.prop.initialsubmission
            ini.co_inv_doc = self.request.FILES['inv_doc']
            ini.save()

            staffs = get_permitted_staffs('can_accept_proposal', [self.request.user.id])
            notify(staffs, 'info',  f'{self.request.user} has submited a new proposal!', f"A proposal was submitted by a user named {self.request.user}",
                                        link=f'/proposal/proposal_detail/{self.prop.id}/')
            
            messages.success(self.request, "Successfully Uploaded Proposal Documents!")
            return redirect('irb:home')

        else:
            part_inv_form = DownloadableIrbFormDocument.objects.filter(name ="Participating Investigators Signature Form")
            data = {"editing":True,  'doc_formset':doc_form, 'doc_types':InitialProposalDocType.objects.all() , 'invs_form':FileSubmitForm(required =True, field_name = 'inv_doc'),
                                    'cors_formset':cors_form,   'proposal':self.prop,'invs_sign_form':part_inv_form}

            if not doc_form.is_valid():
                data.update({'doc_errors':True})
                messages.error(self.request, "Error! Invalid documents for initial submition detected, Please re-check your inputs!")
            
            if not cors_form.is_valid():
                data.update({'cors_errors':True})
                messages.error(self.request, "Error! Invalid data detected about investigators, Please re-check your inputs!")
            
            if not inv_form.is_valid():
                data.update({'part_inv_doc_error':True})
                messages.error(self.request, "Error! Please Upload a file listing the signiture of investigators!")

            # return render(self.request, 'proposal/create_docs.html',{  'doc_formset':doc_formset, 'doc_types':doc_types ,  'invs_form':FileSubmitForm(required =True, field_name = 'inv_doc'),
            #                                                         'cors_formset':cors_formset, 'proposal':self.prop,'invs_sign_form':invs_sign_form,})
    
            return render(self.request, 'proposal/create_docs.html', data)


@method_decorator(user_required(), 'dispatch')
class UpdateInitialSubmissionDocs( View):
    def dispatch(self, request, *args, **kwargs) :
        self.prop = Proposal.objects.only('id','status').prefetch_related('investigators_set').get(id=self.kwargs["pk"])
        if request.user != self.prop.created_by or self.prop.latest_version_num != 1 :
            messages.error(request, "Forbidden! You can't upload docuemnts for this protocol!")
            return redirect('core:error_page')

        if self.prop.status != "Pending":
            messages.error(request, f"Forbidden! You can't upload docuemnts at '{self.prop.status}' status, it needs to be on Pending status. Please contact the irb to change the status to Pending for you!")
            return redirect('proposal:my_proposals')

        self.initial_docs  = InitialProposalDocument.objects.select_related('doc_type').filter(proposal = self.prop)
        if len( self.initial_docs) == 0 :
            messages.error(request, "Warning! You have not uploaded any documents yet, please create the documents first!")
            return redirect('proposal:create_docs', pk=self.kwargs['pk'])
                
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        
        doc_types = InitialProposalDocType.objects.exclude(name = "Other Related Document").only('name')
       
        Doc_FormSet = inlineformset_factory (Proposal, InitialProposalDocument , form=Proposal_Doc_Create_Form,  extra=0 )
        prop_documents = InitialProposalDocument.objects.filter(proposal = self.prop).exclude(doc_type__name = "Other Related Document")
        doc_formset = Doc_FormSet(prefix = "doc_form", instance=self.prop, queryset=prop_documents)
        
        Cors_FormSet = inlineformset_factory (parent_model=Proposal,model= Investigators,form=Investigator_Create_Form, extra=0)
        cors_formset = Cors_FormSet(prefix='cors_form', instance=self.prop)
        
        part_inv_form = DownloadableIrbFormDocument.objects.filter(name ="Participating Investigators Signature Form")
        inv_form = FileSubmitForm(required =False, field_name = 'inv_doc')
        co_inv_doc = self.prop.initialsubmission.co_inv_doc if self.prop.initialsubmission.co_inv_doc else None
        return render(self.request, 'proposal/update_initial_docs.html',{"editing":True, 'prop':self.prop, 'initial_docs':self.initial_docs, 'doc_formset':doc_formset, 'doc_types':doc_types, 'inv_form':inv_form,  
                                                                    'cors_formset':cors_formset, 'co_inv_doc':co_inv_doc, 'proposal':self.prop,'part_inv_form':part_inv_form,})
    
    def post(self, *args, **kwargs):
        Doc_FormSet = inlineformset_factory(Proposal, model= InitialProposalDocument , form=Proposal_Doc_Create_Form, extra=0 )
        doc_form = Doc_FormSet(self.request.POST, self.request.FILES, prefix='doc_form', instance=self.prop)

        Cors_FormSet = inlineformset_factory (parent_model=Proposal, model=Investigators,form=Investigator_Create_Form )
        cors_form =Cors_FormSet(self.request.POST, self.request.FILES, prefix='cors_form', instance=self.prop)
        inv_form = FileSubmitForm(self.request.POST, self.request.FILES, required =False, field_name = 'inv_doc')
        # check validity
        if doc_form.is_valid() and cors_form.is_valid() and inv_form.is_valid():
            docs = doc_form.save()
            cos = cors_form.save()
                
            # save if new "other docs" are sent 
            if 'other_docs' in self.request.FILES:
                doc_type, created = InitialProposalDocType.objects.get_or_create(name = "Other Related Document") 
                other_docs = []
                for f in self.request.FILES.getlist('other_docs'):
                    d = InitialProposalDocument(doc = f, doc_type = doc_type, proposal=self.prop,)
                    other_docs.append(d)
                InitialProposalDocument.objects.bulk_create(other_docs)
            
            # update inv signiture form
            if 'inv_doc' in self.request.FILES:
                initial = self.prop.initialsubmission 
                initial.co_inv_doc = self.request.FILES['inv_doc']
                initial.save()
            

            # delete other related docs
            if 'deleted_other_docs' in self.request.POST and self.request.POST['deleted_other_docs'] != "":
                choosen_ones = self.request.POST['deleted_other_docs'].split(',')
                for d in InitialProposalDocument.objects.filter(id__in = choosen_ones): 
                    d.delete()

            # delete correspondent investigators
            if 'deleted_cors_ids' in self.request.POST and self.request.POST['deleted_cors_ids'] != "":
                choosen_ones = self.request.POST['deleted_cors_ids'].split(',')
                current_num_invs = self.prop.investigators_set.count()
                if len(choosen_ones) >= current_num_invs:
                    messages.warning(self.request, f"Forbidden, There should be at least one investigator, so you cannot delete {len(choosen_ones)} investigators since the proposal currently has {current_num_invs} investigators.")
                else:
                    for i in Investigators.objects.filter(id__in = choosen_ones):
                        i.delete()
            
            if 'send_notification' in self.request.POST:
                staffs = get_permitted_staffs('can_accept_proposal')
                notify(staffs, 'info', f"{self.request.user} has updated an initial submission form.", 
                desc=f"{self.request.user} has updated an initial submission form.", link=f"/proposal/proposal_detail/{self.prop.id}/")
            
            pi = Investigators.objects.filter(proposal = self.prop, is_pi = True).first()
            if pi:
                self.prop.pi_name = pi.name
                self.prop.save()
            messages.success(self.request, "You have successfully updated your documents!")
            return redirect('proposal:my_proposals')
            
        else:
            if not doc_form.is_valid():
                print("doc errors",doc_form.errors)
                messages.error(self.request, "Error! Invalid documents for initial submition detected, Please re-check your inputs!")
            if not cors_form.is_valid():
                print("cors errors ", cors_form.errors)
                messages.error(self.request, "Error! Invalid data detected about investigators, Please re-check your inputs!")
            
            part_inv_form = DownloadableIrbFormDocument.objects.filter(name ="Participating Investigators Signature Form")
            inv_form = FileSubmitForm(required =False, field_name = 'inv_doc')
            doc_types = InitialProposalDocType.objects.exclude(name = "Other Related Document").only('name')
            co_inv_doc = self.prop.initialsubmission.co_inv_doc if self.prop.initialsubmission.co_inv_doc else None
       
            
            return render(self.request, 'proposal/update_initial_docs.html',{   "editing":True, 'prop':self.prop, 'initial_docs':self.initial_docs,  'doc_formset':doc_form, 'inv_form':inv_form, 
                                                                                'doc_types':doc_types,'cors_formset':cors_form, 'co_inv_doc':co_inv_doc,  'part_inv_form':part_inv_form})


@method_decorator(staff_required(), 'dispatch')
class ListProposals( PermissionRequiredMixin, View):
    permission_required = ['irb.can_list_proposal']
    def get(self, *args, **kwargs):
        try:
            p = Proposal.objects.all().select_related()
            return render(self.request, 'proposal/proposal_list.html', {'props':p})
        except Exception as e:
            messages.error(self.request, "An Exception has occured. Please try again latter" )
            print("@@@ Exception ",e )
            return redirect('irb:home')

@method_decorator(staff_required(), 'dispatch')
class AssignedProposals( PermissionRequiredMixin, View):
    permission_required = ['irb.can_review_proposal']
    def get(self, *args, **kwargs):
        try:
            props = Proposal.objects.filter(Q(reviewers__id = self.request.user.id),   ~Q(status='Approved') )
            return render(self.request, 'proposal/assigned_proposals.html', {'props': props})
        except Exception as e:
            print("@@@@ Exception ", e)
            return redirect('irb:home')


"""
for the following 
"""

@method_decorator(user_required(), 'dispatch')
class ProposalDetail(  View):
    """
        - by default shows, z detail of z latest version of z proposal, 
            if version is specified, return z detail of z requested version,
        - users = creator or current reviewers or can_see_proposal_detail permitted users
    """
    def get(self, *args, **kwargs):
        try:
            prop = Proposal.objects.select_related('created_by').prefetch_related('reviewers').get(id = self.kwargs['pk'])
        except:
            messages.error(self.request, "Couldn't find the proposal you requested!")
            return redirect("core:error_page")

        can_rvw = can_review( self.request.user, prop)
        # z creator or a reviewer or can_see proposal detail
        if self.request.user != prop.created_by and not self.request.user.has_perm('irb.can_see_proposal_detail') and can_rvw == 0:
            raise PermissionDenied

        ver = self.kwargs['ver'] if 'ver' in self.kwargs else None
        
        if ver !=None: # if version is specified
            obj = prop.get_specific_version(ver) 
        else:
            obj = prop.get_specific_version(prop.latest_version_num)
        if obj == None:
            messages.error( self.request, "Couldn't find the requested version of this proposal!")
            return redirect("core:error_page")   

        is_creator = True if self.request.user == prop.created_by else False 
        versions =  [v for v in range(prop.latest_version_num, 0, -1)]
        
        if self.request.user.has_perm('irb.can_assign_proposal_reviewers'):
            rv_feedback = ProposalReviewerFeedback.objects.select_related('reviewer').filter(proposal = prop, version = obj.version)
        else:
            rv_feedback = []
        data = {'is_creator':is_creator, 'prop_obj':prop, 'prop':obj, 'cur_ver':obj.version, 'versions':versions, 'rv_feedback':rv_feedback} 
        
        if obj.version == 1:
            docs = InitialProposalDocument.objects.select_related('doc_type').filter(proposal = prop)
            data.update({ 'docs': docs, 'invs': prop.investigators_set.all()})
        else:
            # use this newly fetched documents, don't use the prefetch_selected documents
            docs  =VersionedRelatedDocs.objects.filter(versioned_proposal =obj)
            data.update( {'rel_docs' :obj.versionedrelateddocs_set.all() })
        
        data.update ({ 
                        'can_review': can_review( self.request.user, prop),
                        'can_send_correction_comment': can_send_correction_comment( self.request.user, prop),
                        'can_view_reviewers_response': can_view_reviewers_response( self.request.user, prop),
                    })
        if data['can_review'] > 0:
            data['review_form'] = FileSubmitForm(required=True, field_name = 'study_ass_doc')

        return render ( self.request, 'proposal/proposal_detail.html', data)


@method_decorator(user_required(), 'dispatch')
class CreateVersioned( View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.prop = Proposal.objects.select_related('created_by').get(id = self.kwargs['pk'])
            creator = self.prop.created_by
            if  request.user == creator and self.prop.status == 'On Comment':
                return super().dispatch(request, *args, **kwargs)
            elif self.prop.status != 'On Comment':
                messages.warning(request, f"Forbidden! You cannot submit another version at '{self.prop.status}' status!")
            else:
                 messages.warning(request, "Forbidden! You are unathorized to manage this proposal! ")
            return redirect("core:error_page")

        except Exception as e:
            print("Exception ", e)
            messages.warning(request, "Error! Couldn't find the proposal you requested")
            return redirect("core:error_page")


    def get(self, *args, **kwargs):
        return render(self.request, "proposal/versioned_create.html", {'prop':self.prop, 'form':VersionedProposalForm, 
                            'other_docs_form':MultipleFileSubmit(required=False, prefix = 'other')})


    def post(self, *args, **kwargs):
        try:
            form = VersionedProposalForm(self.request.POST, self.request.FILES)
            other_docs_form = MultipleFileSubmit(self.request.FILES, required=False, prefix = 'other')

            if form.is_valid() and other_docs_form.is_valid():
                v = form.save(commit=False)
                with transaction.atomic():
                    # update the proposal object
                    self.prop.latest_version_num += 1 
                    self.prop.latest_version_num_with_amend += 1 
                    self.prop.status = "Pending"
                    self.prop.save()

                    v.proposal = self.prop                     
                    v.version = self.prop.latest_version_num
                    v.save()
                    
                    if 'other-file_docs' in self.request.FILES:
                        others = []
                        for f in self.request.FILES.getlist('other-file_docs'):
                            others.append( VersionedRelatedDocs(versioned_proposal = v, doc = f))
                        
                        VersionedRelatedDocs.objects.bulk_create(others)

                    messages.success(self.request, f"Successfully submited Version-{v.version} of 'self.prop.protocol_number'. ")
                    staffs = get_permitted_staffs('can_accept_proposal', )
                    notify( staffs, 'info',  f'{self.request.user} has submited version {self.prop.latest_version_num}!', 
                            f"{self.request.user} has submited version {self.prop.latest_version_num} for the protocol {self.prop.protocol_number}",
                            link=f'/proposal/proposal_detail/{self.prop.id}/')
            
                    return redirect('proposal:my_proposals')
            else:
                print(form.errors, " ", other_docs_form.errors)
                messages.error(self.request, "Error. Invalid data detected! Please re-check your ")
                return render(self.request, "proposal/versioned_create.html", {'prop':self.prop, 'form':form, 'other_docs_form':other_docs_form})

        except Exception as e:
            print("Exception ",e)
            messages.error(self.request, "Error! Internal Server Error!")
            return redirect("core:error_page")


@method_decorator(user_required(), 'dispatch')
class UpdateVersioned( View):
    def dispatch(self, request, *args, **kwargs):
        try:
            prop = Proposal.objects.get(pk = kwargs['pk'])     
        except Proposal.DoesNotExist:
            messages.error(request, "Error, Couldn't find the requested version proposal!")
            return redirect("core:error_page")
        
        if not request.user == prop.created_by :
            messages.warning(request, "Forbidden, You can't access this protocol since you did not manage it!")
            return redirect("core:error_page")
       
        if prop.status != "Pending":
            messages.warning(request, f"Forbidden, You can't update this version since it is on '{prop.status}' Status, you can only update it when it is on 'Pending' status!")
            return redirect("core:error_page")
        ver = prop.get_latest_ver_obj()
        self.versioned = ver
        self.prop = prop
        return super().dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        related_docs  =VersionedRelatedDocs.objects.filter(versioned_proposal =self.versioned)
        return render(self.request, "proposal/versioned_update.html", 
                                    {'prop':self.prop,'versioned':self.versioned, 
                                    'form':VersionedProposalForm(instance=self.versioned),
                                    'other_docs_form':MultipleFileSubmit(required=False, prefix = 'other'),
                                    'rel_docs':related_docs})
    
    def post(self, *args, **kwargs):
        try:
            form = VersionedProposalForm(self.request.POST, self.request.FILES, instance=self.versioned)
            other_docs_form = MultipleFileSubmit(self.request.FILES, required=False, prefix = 'other')
            
            if form.is_valid() and other_docs_form.is_valid:
                with transaction.atomic():
                    self.versioned = form.save()
                    self.prop.status = "Pending"
                    self.prop.save()
                    
                    if 'other-file_docs' in self.request.FILES:
                        others = []
                        for f in self.request.FILES.getlist('other-file_docs'):
                            others.append( VersionedRelatedDocs(versioned_proposal = self.versioned, doc = f))
                        
                        VersionedRelatedDocs.objects.bulk_create(others)

                if 'deleted_docs' in self.request.POST and self.request.POST['deleted_docs'] != '':
                    del_doc_ids = self.request.POST['deleted_docs'].split(',')
                    choosen_ones =  VersionedRelatedDocs.objects.filter(id__in = del_doc_ids)
                    for d in choosen_ones:
                        d.delete()
                   
                messages.success(self.request, f"Successfully Updated Version-{self.versioned.version} of '{self.prop.protocol_number}'. ")
                if 'send_notification' in self.request.POST:
                    staffs = get_permitted_staffs('can_accept_proposal')
                    notify( staffs, 'info', f"{self.request.user} has updated version {self.prop.latest_version_num} of {self.prop.protocol_number}.", 
                            desc=f"{self.request.user} has sumited updated proposal for{self.prop.protocol_number}.", 
                            link=f"/proposal/proposal_detail/{self.prop.id}/")

                return redirect('proposal:proposal_versioned_update', pk = self.prop.id)
            else:
                print(form.errors)
                messages.error(self.request, "Error. Invalid data detected! Please re-check your ")
                return render(self.request, "proposal/versioned_update.html", {'prop':self.prop,'versioned':self.versioned, 'form':form})

        except Exception as e:
            print("Exception ",e)
            messages.error(self.request, "Error! Internal Server Error!")
            return redirect("core:error_page")


@method_decorator(staff_required(), 'dispatch')
class ManageProposal( PermissionRequiredMixin, View):
    permission_required = ['irb.can_see_proposal_detail']
    def get(self, *args, **kwargs):
        try:
            prop = Proposal.objects.select_related('initialsubmission').get(id = self.kwargs['pk'])
        except Proposal.DoesNotExist:
            messages.error(self.request, "Error! Couldn't find the requested proposal!")
            return redirect("core:error_page")
        data = {'can_accept':can_accept(self.request.user, prop), 'can_pendit':can_pendit(self.request.user, prop),
                'can_assign':can_assign_reviewers(self.request.user, prop), 'can_send_correction_comment': can_send_correction_comment(self.request.user, prop),
                'can_approve':can_approve(self.request.user, prop), 
        
                }
        data.update(
            {   'prop':prop, 'initial':prop.initialsubmission,
                'accept_form':ProposalAcceptanceForm(instance=prop), 
                'note_form':TextSubmitForm(field_name = "special_note", value = prop.special_note),
                'rejection_form':TextSubmitForm(required=True, field_name = 'rejection_comment', value ="" ),
                'correction_form':TextSubmitForm(field_name = "correction_comment") ,
                'ps':self.request.user.get_all_permissions()
            }
        )
        return render(self.request, "proposal/manage_proposal.html",data )

       