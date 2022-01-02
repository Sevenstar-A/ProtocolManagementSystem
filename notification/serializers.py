from rest_framework import serializers
from .models import *
from django.utils.timesince import timesince as timesince_
from django.utils import timezone
import datetime     

class NotiSerializer(serializers.ModelSerializer):
    created_date =  serializers.SerializerMethodField('timesince')
    
    class Meta:
        model = Notification
        fields = ['tag', 'noti','desc','link', 'created_date', 'id']

    
    def timesince(self, noti):
        return str(timesince_(noti.created_date, timezone.now()) )
    
class UserNotificationSerializer(serializers.ModelSerializer):
    noti = NotiSerializer()
    class Meta:
        model = UserNotification
        fields = ['id','noti']   