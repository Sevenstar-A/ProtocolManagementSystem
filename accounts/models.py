from django.core import validators
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MinValueValidator, MinLengthValidator
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Permission, GroupManager, Group, PermissionsMixin
from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import GroupManager
from django.db.models import Q 
from django.templatetags.static import static

USER_STATUS = (
    (0, 'EMAIL CONFIRMATION'),
    (1, 'NOT VERIFIED'), # for staffs only:-  is_active is always True, but the account is not activated yet
    (2, 'ACTIVE'), #active user who can login and user the system
    (3, 'SUSPENDED')
)

GENDERS = (('Male','Male'), ('Female','Female'))
allowed_image_extensions = ['png','jpg','jpeg','webp','jiff','jfif']


"""
    returns list of distinict users who have the specified permission ethier through their irb position permission
    or direct user permission 
"""


class Title(models.Model):
    name = models.CharField(verbose_name='Title name', max_length=200, unique=True)
    created_by = models.CharField(max_length=100, default="System", help_text="The Name of user who created the Title, default is system")
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class Position(models.Model):
    name = models.CharField(verbose_name='IRB Position', max_length=200, unique=True) # same as the group name
    permissions = models.ManyToManyField(Permission,verbose_name='permissions',blank=True)
    created_by = models.CharField(max_length=100, default="System", help_text="The Name of user who created the position, default is system")
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    

    class Meta:
        verbose_name_plural = 'IRB Positions'

    def __str__(self):
        return self.name


class UserAccountManager(BaseUserManager):
    use_in_migrations = True
    
    def create_user(self, email,password, first_name, last_name, **extra_fields):
        user = self.model(email =   self.normalize_email(email),
                                    first_name = first_name, last_name =last_name,
                                    **extra_fields
                        )
        user.set_password(password)
        user.save(using = self.db)
        return user

    def create_superuser(self, email, password, first_name, last_name, **extra_fields):
        user = self.create_user(email, password, first_name, last_name, **extra_fields)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.status= 2
        user.save(using= self.db)
        return user       


# A few helper functions for common logic between User and AnonymousUser.
def _user_get_permissions(user, obj, from_name):
    permissions = set()
    name = 'get_%s_permissions' % from_name
    for backend in auth.get_backends():
        if hasattr(backend, name):
            permissions.update(getattr(backend, name)(user, obj))
    return permissions

def _user_has_perm(user, perm, obj):
    """
    A backend can raise `PermissionDenied` to short-circuit permission checking.
    """
    for backend in auth.get_backends():
        if not hasattr(backend, 'has_perm'):
            continue
        try:
            if backend.has_perm(user, perm, obj):
                return True
        except PermissionDenied:
            return False
    return False

def _user_has_module_perms(user, app_label):
    """
    A backend can raise `PermissionDenied` to short-circuit permission checking.
    """
    for backend in auth.get_backends():
        if not hasattr(backend, 'has_module_perms'):
            continue
        try:
            if backend.has_module_perms(user, app_label):
                return True
        except PermissionDenied:
            return False
    return False

    
class UserAccount(AbstractBaseUser, PermissionsMixin):

    def profile_image_upload_location(self, file_name):
        return f'users_image/{file_name}'

    email = models.EmailField(verbose_name="Email Field", unique=True)
    title = models.ForeignKey(Title, on_delete=models.CASCADE, blank=True, null=True, help_text="Your professional title, if any.")
    first_name = models.CharField(verbose_name="First Name", max_length=150, validators = [MinLengthValidator(2)])
    last_name = models.CharField(verbose_name="Last Name", max_length=150, validators = [MinLengthValidator(2)])
    full_name = models.CharField(verbose_name="Full Name", max_length=300, blank=True, editable=False,
                help_text=" This is a system generated value, since it is mostly used it's better to store it once and access it without"
                            "evaluating it for every page, cz when evaluated another sql query is need to fetch the name of the title. (not fair!) " )
    phone_number = models.CharField(max_length=150, blank=True, default="", null=True )
    sex = models.CharField(choices=GENDERS, max_length=6, blank=True)
    profile_image = models.ImageField(upload_to = 'Accounts/ProfileImages', blank = True, 
                                    validators =[FileExtensionValidator(allowed_extensions=allowed_image_extensions)] )

    # is_superuser will be added from PermissionsMixin
    is_active = models.BooleanField(default=False,help_text=('Designates whether this user should be treated as active. '),)
    status = models.IntegerField(default = 0, choices=USER_STATUS, help_text= "Identifies the status of each user")
    is_staff = models.BooleanField(default=False)
    # is_superuser = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    
    #!!! Think about the models.CASCADE
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, blank=True, null=True)

    date_joined = models.DateTimeField( auto_now_add=True, editable=False)
    created_by = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE, help_text=('If a user is created by another user'))
    
    objects = UserAccountManager()
    
    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        # return "{} {} ".format(self.first_name,self.last_name)
        return self.full_name

    class Meta:
        verbose_name = 'User Account'
        verbose_name_plural = 'User Accounts'
        ordering=('-date_joined',)
        


    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)
    
    def save(self, *args, **kwargs):
        full_name = ''
        if self.title != None:
            full_name = self.title.name+ " "
        full_name = full_name+'%s %s' % (self.first_name, self.last_name)
        self.full_name = full_name.strip()
        if self.profile_image == "": # if profile image is not given, save the default 
            self.profile_image = 'Accounts/ProfileImages/user.png'
        return super().save(*args, **kwargs)

    
    def get_user_permissions(self, obj=None):
        return  _user_get_permissions(self, obj, 'user')

    def get_group_permissions(self, obj=None):
        return _user_get_permissions(self, obj, 'group')
    
    # this is a custom method for returning permissions by user position, the return type is the same 
    # with the return type of django's default methods get_group_permissions and get_user_permission.
    def get_position_permissions(self, obj=None):
        permissions = set()
        if self.position:
            perms = self.position.permissions.values_list('content_type__app_label', 'codename').order_by()
            permissions.update({"%s.%s" % (ct, name) for ct, name in perms})
        return permissions
        
    def get_all_permissions(self, obj=None):
        default = _user_get_permissions(self, obj, 'user') #django's default return value, then add the permission owned by his position
        default.update(self.get_position_permissions())
        return default
               
    def has_position_perm(self, perm):
        if self.is_active and perm in self.get_position_permissions():
            return True 
        return False

    def has_perm(self, perm, obj=None):
        if self.is_active and self.is_superuser:
            return True
        
        # else, if the django user has perm method returns True or the user has a permission through his position
        elif _user_has_perm(self, perm, obj) or self.has_position_perm(perm):
            return True
        
        return False

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        if self.is_active and self.is_superuser:
            return True

        return _user_has_module_perms(self, app_label)


def get_position_users(pos_name):
    try:
        pos = Position.objects.get(name = pos_name)
        return pos.useraccount_set.all()
    except Exception as e:
        print("@@@@@ get_position_users ", e)
        return []


def get_permitted_staffs(perm_codename, exclude_ids =None):
    try: 
        perm = Permission.objects.get(codename = perm_codename )
        staffs = UserAccount.objects.filter(is_staff=True, is_active=True, status =2)
        if exclude_ids:
            return staffs.filter(Q(position__permissions = perm) | Q(user_permissions = perm) ).exclude(id__in =exclude_ids).distinct()
        return staffs.filter(Q(position__permissions = perm) | Q(user_permissions = perm) ).distinct()
    except Exception as e:
        print(" @@@ Exception while getting permited staff for {code_name}: exception is ",e)
        return []
        

def get_permitted_positions(permission):
    try:
        return Position.objects.filter(permissions = permission)
    except Exception as e:
        return []  
