from django.urls import path
from django.views.generic import TemplateView
from .views import *
from .views_amend_actions import *

app_name  ='amendment'

urlpatterns =[
    path('my_amendments/', MyAmmendments.as_view(), name= 'my_amendments'), #done
    path('check_prot_num/', CheckProtocolNum.as_view(), name="check_prot_num"), #done
    
    #all except code 5
    path("request_proposal_amendment/<str:prot_num>/", CreateProposalAmendment.as_view(), name="request_proposal_amendment"), #1 done
    #code 5
    path("request_new_amendment/<str:prot_num>/", CreateNewAmendment.as_view(), name = "request_new_amendment"), #done
    
    path("amend_detail/<int:pk>/", AmendmentDetail.as_view(), name="amend_detail"), # done
    path("update_amend/<int:pk>/", UpdateAmendment.as_view(), name="update_amend"), # done
    # get method lists assessment reviews and post method saves AmendmentIrbComment
    path("list_assessment_reviews/<int:pk>/",ListAssassmentReviews.as_view(), name = "list_assessment_reviews"), #done
    
   
    # staff actions
    path("manage_amendment/<int:pk>/", ManageAmendment.as_view(), name= "manage_amendment"), #done
    path("amendment_list/",ListAmendments.as_view(), name="amendment_list"), #done
    path('update_special_note/', UpdateSpecialNote, name='update_special_note'), #done
    path("assigned_amendment/",AssignedAmendments.as_view(), name="assigned_amendment"), #done
    path("review_amend/<int:pk>/",ReviewAmendment, name ="review_amend"), #done
    path("correction_comment/",SendCorrectionComment, name="correction_comment"), #done
    path('accept_amend/<int:pk>/', AcceptAmendmentRequest, name ="accept_amend"), #done
    path('to_pending/<int:pk>/',ToPending, name="to_pending"), #done
    path('assign_reviewers/<int:pk>/', AssignReviewers.as_view(), name="assign_reviewers"), #done
    path('approve_amend/<int:pk>/', ApproveAmendment.as_view(), name="approve_amend" ),
    path('reject_amendment/<int:pk>/', RejectAmendment.as_view(), name = "reject_amendment"),
    path('delete_amendment/<int:pk>/', DeleteAmendment.as_view(), name = "delete_amendment"), #done
    
]