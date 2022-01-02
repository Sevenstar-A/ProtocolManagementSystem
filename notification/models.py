from django.db import models
from django.conf import settings

from accounts.models import UserAccount

TAGS = [('info', 'info'),('success', 'success'),('warning', 'warning'),('error', 'error')]


class Notification(models.Model):
    tag = models.CharField(max_length=10, choices=TAGS,)
    noti = models.CharField(max_length=500)
    desc = models.TextField(blank=True, null=True)
    link = models.CharField(max_length = 500, blank=True,default="")
    receivers = models.ManyToManyField(to= settings.AUTH_USER_MODEL, through='UserNotification')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="sender", on_delete=models.CASCADE, blank=True, null=True) #sender = null for system notifications
    created_date = models.DateTimeField(auto_now_add=True)
    # noti_type = individual or group notification

    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        from django.utils.timesince import timesince as timesince_
        return timesince_(self.created_date, now)

    def get_users(self):
        return [ i.user for i in  self.usernotification_set.all()]          

    
    class Meta:
        ordering = ('-created_date',)


class UserNotification(models.Model):
    noti = models.ForeignKey( Notification, on_delete=models.CASCADE)
    user = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)

    class Meta:
        ordering = ['-id']


def notify(rec, tag, noti, desc= '', sender=None, link=''):
    try:
        n = Notification.objects.create(tag=tag, noti =noti, desc=desc, link =link, sender =sender)
        n.save()
        n.receivers.add(rec) if isinstance(rec, UserAccount) else n.receivers.set(rec)
        n.save()
        return n
    except Exception as e:
        print("### Exception ", e)
        return False


def get_usernotification(user, read=None):
    try:
        if read != None:
            return   UserNotification.objects.filter(user=user, read = read).prefetch_related('noti')
        return UserNotification.objects.filter(user=user).prefetch_related('noti')
    except Exception as e:
        print("@@@ Exception",e)
        return []

def get_read_usernotification(user):
    try:
       return UserNotification.objects.filter(user=user, read = True)
    except Exception as e:
        print("@@@ Exception",e)
        return []

def get_read(user):
    try:
       return user.notification_set.filter(usernotification__read = True, usernotification__delete = False)
    except Exception as e:
        print("@@@ Exception",e)
        return []

def get_all_user_notifications(user):
    try:
       return user.notification_set.filter(usernotification__delete = False)
    except Exception as e:
        print("@@@ Exception",e)
        return []


