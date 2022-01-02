from django.urls import path, include
from django.views.generic import TemplateView
from .views import *


app_name = "irb"

urlpatterns = [
    path("", Dashboard.as_view(), name = "home"),
    path("email/",TemplateView.as_view(template_name = "staff/email.html"), name = "email"),
    
    path('position_create/', PositionCreate.as_view(), name = 'position_create'),
    path('position_list/', PositionList, name = "position_list"),
    path('position_detail/<int:pk>/', PositionDetail.as_view(), name="position_detail" )
]