from django.urls import path, include
from django.views.generic import TemplateView
from customer.views import *

app_name = 'customer'

urlpatterns =[
    
    path('', Dashboard.as_view(), name = 'dashboard'),
    
]
