from .models import ProposalReviewerFeedback

# except for can_review, the error code of the rest is like
# 0 is clean
# 1 means is creator of the object
# 2 means the status of the proposal doesnot permit the opration
# 3 means has no permission

def can_pendit(user, prop):
    if user == prop.created_by:
        return 1
    elif prop.status == "Pending":
        return 2
    
    return 0

# if user is a reviewer of the latest version and has not reviewed it yet and still the 
def  can_review(user, prop):
    """ checks review perm, not creator, is reviewer and status """
    if  user.has_perm('irb.can_review_proposal') and user != prop.created_by and prop.status in ['On Review', "Reviewed"]:
        if prop.reviewers.only('id').filter(id = user.id): # check if user is 1 of z reviewers 
            # check if he has reviewed
            rv = ProposalReviewerFeedback.objects.filter(reviewer = user, proposal = prop, version =prop.latest_version_num ).first() 
            if not rv:
                return 1 # Can Review
            else:
                return 2 # already reviewed
        
    return 0

# 0 for clean 1 for is creator, 2 for status invalid
def can_send_correction_comment(user, prop):
    if user.has_perm('irb.can_accept_proposal') and user!=prop.created_by and prop.status not in [ "Rejected"]:
        return 0
    return 1


def can_approve(user, prop):
    # check permission
    if user == prop.created_by:
        return 1
    elif not prop.status in ['Submited', 'On Review', 'Reviewed']:
        return 2 
    return 0
    

def can_accept(user, prop):
    if user == prop.created_by:
        return 1
    elif not prop.status == "Pending":
        return 2 
    return 0

def can_assign_reviewers(user, prop):
    if user == prop.created_by:
        return 1
    elif not prop.status in ['Submited', 'On Review', 'Reviewed']:
        return 2 
    return 0

def can_view_reviewers_response(user, prop):
    if user == prop.created_by:
        return 1
    elif not user.has_perm('irb.can_assign_proposal_reviewers'):
        return 3
    return 0
