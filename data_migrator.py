from datetime import timezone
import os

from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE','Blacklion.settings')
import django
django.setup()
from core.models import *
from proposal.models import *
from accounts.models import *


"""
setting setup
1. run data_migrator.py
2. add the document formats (downloadable checklists)
    2.1 names of documents
        1. Participating Investigators Signature Form
"""
doc_types = [   'Department support Letter with Original Stamp',
                'Scanned Department minute and Department REC',
                'Department minute and Department REC'

]
titles = ['Professor', 'Mr.', 'Ms.', 'Doctor', 'Ass. Professor', ]
dept = [ ('Pathology ', 'Patho'), ('Orthopedics','Ortho'), ('Dentistry','Dent'), ('Neurology','Neuro'),
            ('Radiology','Radio')
    ]
p_type = ['PHD', 'Faculty']
s_type = ['Survey Based','Social', 'Medical','Community based','Individual', 'Screening','Observational','Epidemiology',
            'Intervention study', 'Clinical Trial', 'Phase I' ]

s_pop = ["Healthy","Patient",'Vulnerable Groups', 'Animals']
impaired = ['Physically','Mentally' ,'None']
ex = ['Male', 'female', 'None', 'other']
res = [ 'Intensive Care', 'Isolation unit', 'Surgery', 'Pediatric Intensive Care', 
        'Transfusion', 'CAT scan', 'Gene therapy']

# cod, name
DownloadableIrbFormDocumentList = [
    [1, 'Initial', 'Participating Investigators Signature Form'],
    (2, 'Initial', 'Amendment Request Form'),
    (3, )
]

def set_initials():
    for d in doc_types:
        InitialProposalDocType.objects.create(name = d)
    print('saved initial doc types')

    
    for t in titles:
        Title.objects.create(name = t)
    print("Saved titles")
    
    for a in dept:
        d = Department(name = a[0], code_name = a[1])
        d.save()
        # Department.objects.create(name = a[0], code_name = a[1])
    print("saved departments")

    for a in p_type:
        b = ProposalType(name = a)
        b.save()

    print("saved Proposal Types")

    for a in s_type:
        if a not in StudyType.objects.all():
            b = StudyType(name = a)
            b.save()
    print("saved Study Types")

    for a in s_pop:
        b = StudyPop(name = a)
        b.save()
    print("Saved pop")

    for a in res:
        b = SpecialRes(name = a)
        b.save()
    print("Saved res")

    for a in impaired:
        b = Impaired(name = a)
        b.save()
    print("Saved Imp")
   
    for a in ex:
        b = Exclusion(name = a)
        b.save()
    print("Saved exc")

    print("initializing protocol prefix ")
    year = str(datetime.now().year)[2:]
    px = SystemConstant(name = "Protocol Prefix", value = f"000/{year}/")
    px.save()
    print("Set Protocol Prefix as ", px.value)

def delete_position_permissions():
    for p in Position.objects.all():
        p.permissions.all().delete()
    print("finished deleting all positions permissions!")

def delete_default_permissions():
    for p in Permission.objects.all():
        if (p.codename.startswith('add') or
                p.codename.startswith('view') or
                p.codename.startswith('can_view') or
                p.codename.startswith('delete') or
                p.codename.startswith('change')):
            p.delete()
    print(Permission.objects.count())

if __name__ == '__main__': 
    # set_initials()
    delete_default_permissions()
    # for u in UserAccount.objects.all():
    #     u.profile_image = 'Accounts/ProfileImages/user.png'
    #     u.save()
    
        
        

    


    

    