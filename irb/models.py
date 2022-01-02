from django.db import models
class AllPermissions(models.Model):
    class Meta:
        permissions = [ 
            # accounts permissions
            ('can_list_user', 'Can View Users List'), #list and view detail
            ('can_update_user', 'Can Update Users Account'), # + edit, delete others accout
            ('can_manage_permission', 'Can Manage Permissions'), # give user and position permissions

            # system information (for core.models)
            ('can_list_configuration', 'Can View System Configurations'), # 
            ('can_update_configuration', 'Can Update System Configurations'),

            # collaborations
            ('can_list_collaboration', 'Can View Collaborations List'),
            ('can_update_collaboration', 'Can Update Collaborations'),

            # proposal permissions
            ('can_list_proposal', 'Can View Proposals List'), #list,  special note, 
            ('can_see_proposal_detail', 'Can See Proposal Detail'), #detail, see management page
            ('can_accept_proposal','Can Accept Proposals'), # access accept, send correction comment, to pending
            ('can_assign_proposal_reviewers','Can Assign Proposal Reviewers'), #to assign, view reviewers response and send IRB comment
            ('can_review_proposal', 'Can Review Proposals'), # to view assigned and to review
            ('can_approve_proposal','Can Approve Proposals'), # to approve and reject
            
            # amendment permissions
            ('can_list_amendment', 'Can View Amendments List'), #list,  special note, 
            ('can_see_amendment_detail', 'Can See Amendment Detail'), #detail, view managment page
            ('can_accept_amendment','Can Accept Amendments'), # access accept, send correction comment, to pending
            ('can_assign_amendment_reviewers','Can Assign Amendment Reviewers'), #to assign, view reviewers response, send IRB comment
            ('can_review_amendment', 'Can Review Amendments'), # to view assigned, to review
            ('can_approve_amendment','Can Approve Amendments'), # to approve, reject

            ('can_list_renewal', 'Can View Renewals List'), #list, detail, special note, view managment page
            ('can_see_renewal_detail', 'Can See Renewal Detail'), #detail,
            ('can_accept_renewal','Can Accept Renewals'), # access accept, send correction comment, to pending
            ('can_assign_renewal_reviewers','Can Assign Renewal Reviewers'), #to assign, view reviewers response, send IRB comment
            ('can_review_renewal', 'Can Review Renewals'), # to view assigned, to review
            ('can_approve_renewal','Can Approve Renewals'), # to approve, reject

           
                    
]
