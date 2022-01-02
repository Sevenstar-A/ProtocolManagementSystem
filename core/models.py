from django.contrib.auth.models import User
from django.db import models
from django.conf import settings
from django.db.models.aggregates import Max


IRB_FORM_DOCUMENT_TYPES = (
    ('General', 'General'),
    ('Initial Submission', 'Initial Submission'),
    ('Amendment', 'Amendment'),
    ('Renewal', 'Renewal'),
    ('SAE', 'SAE')
)

MODEL_NAMES = [ ('Initial Submission', 'Initial Submission'),
                ('Amendment', 'Amendment'),
                ('Renewal', 'Renewal'),
                ('Sae', 'Sae')
            ]

# These are system generated constants, do not alter their name or value unless you are very sure of it.
class SystemConstant(models.Model):
    name = models.CharField(max_length=100, )
    value = models.CharField(max_length=50, blank=True)
    last_updated_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name


# ex. Anatomy, Pediatric...
class Department(models.Model):
    name = models.CharField(max_length=200)
    code_name = models.CharField(max_length= 100, blank=True, )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, help_text=('The user who created the proposal type object'))
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self):
        if not self.code_name :
            self.code_name = self.name[:4]
        super(Department, self).save()

    
    class Meta:
        ordering =['name']
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    
# Reference sample documents for clients  
# crud it alone
class DownloadableIrbFormDocument(models.Model):
    code = models.IntegerField(unique=True, help_text="used for searching and fetching") 
    name = models.CharField(max_length=200, help_text="used for client view")
    to = models.CharField(max_length=20, choices=IRB_FORM_DOCUMENT_TYPES)
    doc = models.FileField(upload_to='IRBFormatDocuments')
    description = models.CharField(max_length=200, blank=True, )
    created_by = models.CharField(max_length=200, default = "System", blank=True, )
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"

# --------  Related with Initial submission form 
# survey based
class StudyType(models.Model):
    name = models.CharField(unique=True, max_length=200)# unique, bcz we use names to save which study types a proposal uses, so 
    code_name = models.CharField(max_length= 100, blank=True,)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, help_text=('The user who created the proposal type object'))
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self):
        if not self.code_name :
            self.code_name = self.name[:4]
        super(StudyType, self).save()

    class Meta:
        ordering =['id']
        verbose_name = "Study Type"
        verbose_name_plural = "Study Types"


class StudyPop(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name


class SpecialRes(models.Model):
    name = models.CharField(unique=True, max_length=200) # unique bcz, we use names to identify which special resource each proposal uses
    def __str__(self):
        return self.name
    # class Meta:
    #     ordering=["id"]


# the following 2 are not used inside the logic, we used hard coded names (found in proposal.models), 
# any updates will b done through source code (bcz 99% they will not b changed)

# the following are just, incase if we need to make they dynamic
class Impaired(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name


class Exclusion(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name


# -------- End of related with initial submission form