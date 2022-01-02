from django.urls import path
from .views import *
from .action_views import *
from django.views.generic import TemplateView

app_name = 'proposal'

urlpatterns = [
    path('my_proposals/',MyProposals.as_view(), name = 'my_proposals'), #done
    path('proposal_create/',CreateProposal.as_view(), name = "proposal_create"), # #donedone
    path('create_docs/<pk>/', CreateDocs.as_view(), name ='create_docs'),#done
    path('versioned_create/<int:pk>/', CreateVersioned.as_view(), name ="versioned_create" ), #done
    
    path('proposal_initial_form_update/<pk>/', UpdateInitialSumbissionForm.as_view(), name = "proposal_initial_form_update"), #done
    path('proposal_initial_docs_update/<pk>/', UpdateInitialSubmissionDocs.as_view(), name = "proposal_initial_docs_update"), #done
    path('proposal_versioned_update/<pk>/', UpdateVersioned.as_view(), name = "proposal_versioned_update"),
    
    path('proposal_detail/<int:pk>/', ProposalDetail.as_view(), name = 'proposal_detail'), #done
    path('proposal_detail/<int:pk>/<int:ver>/', ProposalDetail.as_view(), name = 'specific_ver_detail'), #detail for specific version, but the template is z same

    path("proposal_list/", ListProposals.as_view(), name = "proposal_list"), #done
    path('assigned_proposal/', AssignedProposals.as_view(), name = 'assigned_proposal'), #done
    path('list_assessment_reviews/<int:pk>/', ListAssassmentReviews.as_view(), name = "list_assessment_reviews"), #done
    
    #----- Actions
    # for staffs
    path('to_pending/<int:pk>/', ToPending.as_view(), name="to_pending"), #done
    # path('to_reviewed/<int:pk>/', ToReviewed, name="to_reviewed"),
    path('accept_prop/<int:pk>/', AcceptPropReq.as_view(), name="accept_prop"), #done
    path('prop_review/<int:pk>/', ProposalReview.as_view(), name="prop_review"), #done
    path('reject_proposal/<int:pk>/', RejectProposal.as_view(), name="reject_proposal"),
    path('approve_proposal/<int:pk>/',ApproveProposal.as_view(), name='approve_proposal'),
    path('assign_reviewers/<int:pk>/', AssignReviewers.as_view(), name='assign_reviewers'), #done
    path("manage_proposal/<int:pk>/", ManageProposal.as_view(), name="manage_proposal"), #done
    
    # ajax requests
    path('update_special_note/', UpdateSpecialNote, name='update_special_note'),
    path('correction_comment/', SendCorrectionComment, name= 'correction_comment'), #done
    path('delete_proposal/<int:pk>/', DeleteProposal.as_view(), name='delete_proposal'),
 
    # path('compose_app_let/<int:pk>/',ComposeApprovalLetter.as_view(), name="compose_app_let"),
]