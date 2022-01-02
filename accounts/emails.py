from django.views import View
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

# for token generation

from django.core.mail import EmailMessage
import six
from .models import UserAccount


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return six.text_type(user.id) + six.text_type(timestamp) + six.text_type(user.is_active)

account_activation_token = TokenGenerator()

def email_acc_activation(user, request):
    current_site = get_current_site(request)
    mail_subject = 'Activate your PMS account. AAU CHS IRB'
    message = render_to_string('email/accounts/acc_activation.html', {
        'user': user,
        'domain': current_site.domain,
        'uid':urlsafe_base64_encode(force_bytes(user.id)),#encode user id
        'token':account_activation_token.make_token(user),
    })
    to_email = user.email
    email = EmailMessage(mail_subject, message, to=[to_email])
    try:
        email.send(fail_silently=False)
        print("sent the email")
        return True 
    except Exception as e:
        print("Email Exception ", e)
        return False

