from django.urls import path
from django.views.generic import TemplateView
from .views import CoreDashboard

app_name = 'core'
urlpatterns = [
    path('', CoreDashboard, name = "dashboard"),
    path('error_page/', TemplateView.as_view(template_name = 'staff/error_page.html'), name = 'error_page')

]