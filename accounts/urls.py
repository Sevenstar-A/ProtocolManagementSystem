from django.urls import path
from django.contrib import admin
from .views import *

app_name = "accounts"

urlpatterns = [
    path("signup/",CustomerSignup.as_view(), name = "signup"),
    path('member_signup/', AdminSignup.as_view(), name = "member_signup"),
    
    path('my_profile/', MyProfile.as_view(), name = 'my_profile'),
    path('account_setting/', AccountSetting.as_view(), name="account_setting"),
    path('change_password/', ChangePassword.as_view(), name="change_password"),
    path('users_list/', UsersList.as_view(), name='users_list'),
    path('users_list/<str:type>/', UsersList.as_view(), name='users_type_list'),
    path('edit_user_account/<int:user_id>/', EditUserAccount.as_view(), name="edit_user_account"),
    path('reset_password/', ResetPassword.as_view(), name="reset_password"),
    path('toggle-user-active-status/<int:user_id>/', ToggleUserStatus.as_view(), name="toggle_user_active_status"),
    path('delete_user/<int:user_id>/', ToggleUserIsActive.as_view(), name="delete_user"),
    path('filter_user_status/<int:status_id>/', FilterUserByStatus.as_view(), name="filter_user"),

    path('confirm_email/<str:email>/', ConfirmEmail.as_view(), name = "confirm_email" ),
    path('activate/<str:uidb64>/<str:token>/', activate, name="activate"),
    path('login/', loginview, name="login"),
    path("logout/", logoutview, name = "logout"),
   
    
]