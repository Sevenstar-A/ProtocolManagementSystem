from datetime import time
from django.utils import timezone
from proposal.models import Proposal, ProposalApprovals
from amendment.models import Amendment, AmendmentApproval
from renewal.models import Renewal, RenewalApproval

from .models import Department
from core.models import SystemConstant

# validates whether a protocol number has a valid format or not 
def validate_prot_num(prot_num:str):
    dep_names = list(Department.objects.values_list('code_name'))
    dns = [ i[0] for i in dep_names ]
    parts = prot_num.split('/')
    if len(parts) != 3:
        return (False, "Wrong protocol Format")
    i =  parts[0]
    y = parts[1]
    dn = parts[2]
    e = ""
    current_year = (timezone.datetime.today().year - 2000)
    if len(i) != 3 or not i.isnumeric() or not int(i) > 0:
        e+="Wrong index format, "
    
    if len(y) != 2 or not y.isnumeric() or int(y) > current_year:
        e += "Wrong year format, "
    if not dn in dns:
        e += "Wrong department name"
    
    if e == "":
        # check if the protocol number is not from the future. w/h means everything c'd b okey, but
        # gena le wedefit yemiset protocol number almehonun check enarg, using 
        px = SystemConstant.objects.get(name ='Protocol Prefix')
        px = int(px.value.split('/')[0])
        if int(i) > px and int(y) >= current_year:
            return (False, "You are using a protocol number from the future! Correct your input.")
        return (True, None) 

    return (False, e) 


# code, msg, prop?, title, amend_num, renewal_num, status, version, last_approval_letter
def get_protocol_code(prot_num):
    """
    -   this function searchs for an initial submission, amendmets and renewals for a given protocol number, then figure out which one is the latest and 
        returns basic information from the latest object,  it also validates if the protocol number has valid format or not.

    -   it can be used to get the latest approval letter for a particular protocol number
    """
    # inputs protocol number, 
    # return code, msg, prop?, title, status, pi name, amend_num, renewal_num, created_by, version, latest_approval letter
    valid, error = validate_prot_num(prot_num)
    if not valid:
        return { 'code':0, 'msg':error }
        
    try: 
        prop = Proposal.objects.prefetch_related('proposalapprovals_set').get(protocol_number = prot_num)
        # if there is a proposal then search related amendments and renewals
        amendment = Amendment.objects.prefetch_related('amendmentapproval_set').filter(proposal = prop).first()
        renewal = Renewal.objects.prefetch_related('renewalapproval_set').filter(proposal = prop).first()
        result = { 'proposal':prop,'created_by':prop.created_by, 'version':prop.latest_version_num_with_amend , }
        
        if not amendment and not renewal:
            print("code 1")
            approval = prop.proposalapprovals_set.first() # if not approved, it will return None, 
            result.update( {'code':1, 'msg':"Initial submission of the protocol is found, but no amendment or renewal request was found!", 
                            'title':prop.title, 'status':prop.status, 'amend_num':0, 'renewal_num':0, 'pi_name':prop.pi_name, })
            
        elif amendment and not renewal:
            print("code 2")
            approval = amendment.amendmentapproval_set.first() 
            result.update( {'code':2, 'msg':"Initial submission and previous Amendment of the protocol are found but no renewal request is found!", 'title':amendment.proposal_title,
                                    'status':amendment.status, 'amend_num':amendment.amend_num , 'renewal_num':0, 'pi_name':amendment.pi_name, })
        
        elif not amendment and renewal:
            print("code 3")
            approval = renewal.renewalapproval_set.first() 
            result.update({ 'code':3, 'msg':"Initial submission and previous renewal request of the protocol are found, but no previous amendment is found!", 'title':prop.title, 
                            'status':renewal.status, 'amend_num':0, 'renewal_num':renewal.renewal_num,'pi_name':renewal.pi_name, })
        
        else: # if both are found
            print("code 4")
            latest_obj = renewal if renewal.proposal_version >= amendment.proposal_version else amendment  #the reverse will not work, cz for a given version, always the renewal is the latest 
            approval = renewal.renewalapproval_set.first() if renewal.proposal_version >= amendment.proposal_version else  amendment.amendmentapproval_set.first() 
            result.update( { 'code':4, 'msg':"Initial submission, previous amendment and renewal found!", 'title':latest_obj.proposal_title, 'status':latest_obj.status, 
                                    'amend_num':amendment.amend_num , 'renewal_num':renewal.renewal_num, 'pi_name':latest_obj.pi_name})
        
        result['approval_letter'] = approval.approval_letter if approval else None
        return result
    
    except Proposal.DoesNotExist:
        amendment = Amendment.objects.prefetch_related('amendmentapproval_set').filter(protocol_number = prot_num).first()
        renewal = Renewal.objects.prefetch_related('renewalapproval_set').filter(protocol_number = prot_num).first()
        
        if not amendment and not renewal:
            print("code 5")
            approval = None
            result= {    'code':5, 'msg':"The initial submission of this protocol was NOT submited with this system. There was no related amendment or renewal request was found either!", 
                        'amend_num':0, 'renewal_num':0, 'created_by':None, 'pi_name':None, 'title':None, 'status':None, 'version':None}
        
        elif amendment and not renewal:
            print("code 6")
            approval = amendment.amendmentapproval_set.first() 
            result= {   'code':6, 'msg':"The initial submission of this protocol was NOT submited with this system. But an amendment request with this protocol number is found!", 'amend_num':amendment.amend_num, 
                        'renewal_num':0,'created_by':amendment.created_by, 'pi_name':amendment.pi_name, 'title':amendment.proposal_title, 'status':amendment.status, 'version':amendment.proposal_version, }
        
        elif not amendment and renewal:
            print("code 7")
            approval = renewal.renewalapproval_set.first() 
            result={    'code':7, 'msg':"The initial submission of this protocol was not submited with this system. But a renewal request with this protocol number is found!", 'amend_num':0, 
                        'renewal_num':renewal.renewal_num, 'created_by':renewal.created_by, 'pi_name':renewal.pi_name, 'title':renewal.proposal_title, 'status':renewal.status, 'version':renewal.proposal_version, }
        
        else: # if both are found
            print("code 8")
            latest_obj = renewal if renewal.proposal_version >= amendment.proposal_version else amendment  #the reverse will not work, cz for a given version, always the renewal is the latest 
            approval = renewal.renewalapproval_set.first() if renewal.proposal_version >= amendment.proposal_version else  amendment.amendmentapproval_set.first() 
            result= {   'code':8, 'msg':"The initial submission of this protocol was not submited with this system. But related amendment request and renewal request are found!",  'title':latest_obj.title, 'amend_num':  amendment.amend_num, 
                        'renewal_num':renewal.renewal_num, 'created_by':latest_obj.created_by, 'pi_name':latest_obj.pi_name, 'status':latest_obj.status,  'version':renewal.proposal_version, }
        
        result['approval_letter'] = approval.approval_letter if approval else None
        return result
    except Exception as e:
        print(e)
        return {'code':0, 'msg':'An Expected error occured! please try again later!'}

