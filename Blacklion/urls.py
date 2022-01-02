from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

import debug_toolbar
from core.views import Index,check

urlpatterns = [
    # 3rd party urls
    path('__debug__/', include(debug_toolbar.urls)),

    # website urls
    path('check/', check, name = "check"),
    path('', Index, name = "index"),
    path('about/',TemplateView.as_view(template_name= 'blacklion/about.html'),name = 'about'),
    path('services/',TemplateView.as_view(template_name= 'blacklion/services.html'), name = 'services'),
    path('service_detail/<str:service>/',TemplateView.as_view(template_name="blacklion/service_detail/initial_submission.html"), name = 'service_detail'),
    path('gallery/',TemplateView.as_view(template_name='blacklion/gallery.html'), name = 'gallery'),
    path('documents/',TemplateView.as_view(template_name='blacklion/services.html'), name = 'documents'),
    path('latest_reseaches/',TemplateView.as_view(template_name='blacklion/blog.html'),name = 'latest_reseaches'),
    path('contact_us/',TemplateView.as_view(template_name= 'blacklion/contact.html'),name = 'contact_us'),

    # user based urls pi
    path("client/", include('customer.urls')),
    path('home/',include("irb.urls")),
    path('superadmin/', admin.site.urls),

    path('b', TemplateView.as_view(template_name=  'staff/base.html')),
    path('s', TemplateView.as_view(template_name=  'staff/s.html')),
    
    # redirecting urls
    path('core/', include('core.urls')),
    path("accounts/", include("accounts.urls")),
    path('proposal/', include('proposal.urls')),
    path('amendment/', include('amendment.urls')),
    path('renewal/', include('renewal.urls')),
    path('noti/', include('notification.urls')),
    path('connect/', include('connect.urls')),
    path('success/', TemplateView.as_view(template_name ="staff/success_page.html"), name = 'success'),
    
    
]
urlpatterns+= static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
# urlpatterns+= static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS)
