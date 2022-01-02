from django.urls import path, include
from .views import *


app_name = 'noti'

urlpatterns =[
    # page
    path('notifications/', ListNotifications, name = 'notifications'),
    path('notifications/<str:status>/', ListNotifications, name = 'notifications'),
    path('notification_detail/<int:pk>/',NotificationDetail, name = "notification_detail"),
    
    # api
    path('api_get_unread/', GetUnread, name = 'api_get_unread'),
    path('get_last_noti_id', GetLastNotiId, name = 'get_last_noti_id'),
    path('api_mark_all_as_read/', MarkAllAsRead, name = 'api_mark_all_as_read'),
    path('mark_user_notification_as_read/<int:pk>/', MarkUserNotificationAsRead, name = 'mark_user_notification_as_read'),
    path('delete/<int:pk>/', GetUnread, name = 'delete'),
    
]

#  pattern(r'^$', views.AllNotificationsList.as_view(), name='all'),
#     pattern(r'^unread/$', views.UnreadNotificationsList.as_view(), name='unread'),
#     pattern(r'^mark-all-as-read/$', views.mark_all_as_read, name='mark_all_as_read'),
#     pattern(r'^mark-as-read/(?P<slug>\d+)/$', views.mark_as_read, name='mark_as_read'),
#     pattern(r'^mark-as-unread/(?P<slug>\d+)/$', views.mark_as_unread, name='mark_as_unread'),
#     pattern(r'^delete/(?P<slug>\d+)/$', views.delete, name='delete'),
#     pattern(r'^api/unread_count/$', views.live_unread_notification_count, name='live_unread_notification_count'),
#     pattern(r'^api/all_count/$', views.live_all_notification_count, name='live_all_notification_count'),
#     pattern(r'^api/unread_list/$', views.live_unread_notification_list, name='live_unread_notification_list'),
#     pattern(r'^api/all_list/', views.live_all_notification_list, name='live_all_notification_list'),
