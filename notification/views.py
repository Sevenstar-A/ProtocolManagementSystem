from datetime import datetime
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from .serializers import NotiSerializer, UserNotificationSerializer
from .models import *


@login_required
def ListNotifications(request, status ="All"):
        try:
                if status == "read":
                        notis = get_usernotification(request.user, read = True) 
                elif status == "unread":
                        notis = get_usernotification(request.user, read = False) 
                else:
                        notis = notis = get_usernotification(request.user)            
                return render(request, 'notification/notification_list.html',{'notis':notis, 'status':status})
        except Exception as e:
                print("### Exception ", e)
                messages.error(request, "Couldn't load notifications. Please try again later!")
                return redirect('irb:home')


def NotificationDetail(request, pk): #the pk is notification id, not user notification id
        # notify(UserAccount.objects.get(email = "admin@gmail.com"),'success', 'Test notification', desc="This is the test description", link="/proposal/proposal_list/")
        n = UserNotification.objects.prefetch_related('noti').get(id = pk)
        status = "Read" if n.read else "Unread"
        n.read = True
        n.save()
        notis = UserNotification.objects.prefetch_related('noti').filter(user = request.user, read = n.read) # all other messages with the same status
        # n.
        # updated.read = True 
        # updated.save()

        return render(request, 'notification/notification_list.html', {'notis':notis, 'status':status, 'detail':True, 'n':n})


########## api links
@login_required   
def GetUnread(request): # lists unread UserNotifications of the logged in user 
    try:
        unread  = get_usernotification(request.user, False)
        data = {'fetch_time':datetime.now(),'notis':UserNotificationSerializer(unread, many =True).data, 'num':unread.count(),'error':False}
        return JsonResponse( data, safe = False)
    except Exception as e:
        print("@@@@@@ Exception ", e)
        return JsonResponse( {'error':True, 'msg':str(e)})

 
@login_required
def MarkUserNotificationAsRead(request, pk):
        try:
                n = UserNotification.objects.get(id = pk)
                n.read = True 
                n.save()
                return JsonResponse(data = {'error':False, })
        except Exception as e:
                print("@@@ Exception ",e)
                return JsonResponse(data = {'error':True, 'msg':str(e)})


@login_required
def MarkAllAsRead(request):
        try:
                update_num = UserNotification.objects.filter(user = request.user, read = False).update(read = True)
                if update_num >= 0:
                        return JsonResponse({'error':False, 'update_num':update_num}) 
                else:
                        return JsonResponse({'error':True, 'update_num':update_num}) 


        except Exception as e:
                print(e)
                return JsonResponse( {'error':True, 'msg':str(e)}, safe = False)


@login_required
def GetLastNotiId(request):
        try:
                last_noti_id  = request.user.notification_set.filter(usernotification__read = False, usernotification__delete = False)[:1]
                return JsonResponse({'error':False, 'id':last_noti_id.id}) 
        except Exception as e:
                print("@@@@ Exception ", e)
                return JsonResponse({'error':True, 'msg':str(e)})



# def list_unread_messages(request):
#         try:
#             all_unread_messages = ChatMessages.objects.filter(receiver = request.user, seen =False , is_active = True).order_by('-created_date')        
#             sender_names = []
#             grouped_unread_messages = []
#             for m in all_unread_messages:
#                 if not m.sender.username in sender_names:
#                     latest_from_sender= ChatMessagesSerializer(m).data
#                     count = all_unread_messages.filter(sender__username = m.sender.username).count()
#                     # add the number of unread messages from a 
#                     latest_from_sender['count'] = count 
#                     grouped_unread_messages.append(latest_from_sender)
#                     sender_names.append(m.sender.username)

#             data = {'num':all_unread_messages.count(), 'unread_messages':grouped_unread_messages}
#             return JsonResponse( data, safe = False)
#         except Exception as e:
#             print("@@@ Exception at list_unread_messages ", e)
#             return JsonResponse( {'error':True})


