from django.urls import path
from .views import (MyRenewals, CheckProtocolNum, CreateNewRenewal, CreateProposalRenewal, UpdateRenewal,
                    RenewalDetail, ListRenewals, AssignedRenewals, ManageRenewal, ListAssassmentReviews)
                    
from .views_renewal_actions import (AssignReviewers, ApproveRenewal, RejectRenewal, DeleteRenewal,
                                    SendCorrectionComment, UpdateSpecialNote, AcceptRenewalRequest, ToPending, ReviewRenewal,
                                    )

app_name  ='renewal'

urlpatterns =[
    path('my_renewals/', MyRenewals.as_view(), name= 'my_renewals'), #done
    path('check_prot_num/', CheckProtocolNum.as_view(), name="check_prot_num"), #done
    #all except code 5
    path("request_proposal_renewal/<str:prot_num>/", CreateProposalRenewal.as_view(), name="request_proposal_renewal"), #done 
    # for code 5 only
    path("request_new_renewal/<str:prot_num>/", CreateNewRenewal.as_view(), name = "request_new_renewal"), #done
    
    path("renewal_detail/<int:pk>/", RenewalDetail.as_view(), name="renewal_detail"), #done 
    path("update_renewal/<int:pk>/", UpdateRenewal.as_view(), name="update_renewal"), #done
    # get method lists assessment reviews and post method saves AmendmentIrbComment
    path("list_assessment_reviews/<int:pk>/",ListAssassmentReviews.as_view(), name = "list_assessment_reviews"), 
    
    # staff actions
    path("manage_renewal/<int:pk>/", ManageRenewal.as_view(), name= "manage_renewal"), #done
    path("renewal_list/",ListRenewals.as_view(), name="renewal_list"), #done
    path('update_special_note/', UpdateSpecialNote, name='update_special_note'), #done
    path("assigned_renewal/",AssignedRenewals.as_view(), name="assigned_renewal"), #done
    path("review_renewal/<int:pk>/",ReviewRenewal, name ="review_renewal"), #done
    path("correction_comment/",SendCorrectionComment, name="correction_comment"), #done
    path('accept_renewal/<int:pk>/', AcceptRenewalRequest, name ="accept_renewal"), #done
    path('to_pending/<int:pk>/',ToPending, name="to_pending"), #done
    path('assign_reviewers/<int:pk>/', AssignReviewers.as_view(), name="assign_reviewers"), #done
    path('approve_renewal/<int:pk>/', ApproveRenewal.as_view(), name="approve_renewal" ),
    path('reject_renewal/<int:pk>/', RejectRenewal.as_view(), name = "reject_renewal"),
    path('delete_renewal/<int:pk>/', DeleteRenewal.as_view(), name = "delete_renewal"), 
]

