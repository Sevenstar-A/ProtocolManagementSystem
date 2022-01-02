from django.contrib import messages
from django.shortcuts import render,redirect, get_object_or_404
from django.views import View
from accounts.forms import PositionForm
from notification.forms import *
from notification.models import notify
from accounts.models import Position, UserAccount, get_position_users
from accounts.emails import email_acc_activation
from django.contrib.auth.mixins import LoginRequiredMixin
from proposal.models import Proposal
from amendment.models import Amendment
from renewal.models import Renewal
from accounts.utils import *
from django.utils.decorators import method_decorator


app_name  ='irb'

@method_decorator(user_required(), 'dispatch')
class Dashboard( View):
    def get(self, *args, **kwargs):
        p = Proposal.objects.filter(created_by = self.request.user).values('id','protocol_number', 'title', 'latest_version_num','status')
        a = Amendment.objects.filter(created_by = self.request.user).count()
        r = Renewal.objects.filter(created_by = self.request.user).count()
        return render(self.request, "staff/index.html", {'props':p, 'amends':a, 'renewals':r})


def check(request):
    return render(request, 'staff/s.html',{'form':n})


@staff_required()
def PositionList(request):
    p= Position.objects.all().prefetch_related('permissions', 'useraccount_set')
    return render(request, 'irb/position_list.html', {'positions':p})

@method_decorator(staff_required(), 'dispatch')
class PositionCreate(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        return render(self.request, 'irb/position_create.html', {'form':PositionForm})

    def post(self, *args, **kwargs):
        form = PositionForm(self.request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = self.request.user.full_name
            f.save()
            form.save_m2m()
            messages.success(self.request, "You have successfully created a new IRB Position!")
            return redirect('irb:position_list')
        else:
            messages.error(self.request, "Error! Invalid input detected. Please recheck your inputs and submit again. ")
            return render(self.request, 'irb/position_create.html', {'form':form})


@method_decorator(user_required(), 'dispatch')
class PositionDetail(View):
    def get(self, *args, **kwargs):
        pos = Position.objects.get(id = self.kwargs['pk'])
        return render(self.request, 'irb/position_detail.html', {'pos':pos, 'form':PositionForm(instance=pos)})
    
    def post(self, *args, **kwargs):
        pos = Position.objects.get(id = self.kwargs['pk'])
        form = PositionForm(self.request.POST, instance=pos, )
        if form.is_valid():
            f =form.save(commit=True)
            messages.success(self.request, "You have successfully updated properties of '%s' position " %pos.name)
            return redirect('irb:position_detail', pk=pos.id)
        else:
            messages.error(self.request, "Error! Invalid input detected. Please recheck your inputs and submit again.")
            return render(self.request, 'irb/position_detail.html', {'pos':pos, 'form':form})
    