
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages

from proposal.models import *
from proposal.views import get_user_proposal_count_data
from accounts.emails import email_acc_activation

class Dashboard(View):
    def get(self, *args, **kwargs):
        # email_acc_activation(self.request.user, self.request)
        proposals  = Proposal.objects.filter(created_by = self.request.user)
        return render(self.request, 'customer/dashboard.html', {'proposals':proposals, **get_user_proposal_count_data(self.request.user)} )
      