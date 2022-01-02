
from django.contrib import admin
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered

models  = apps.get_app_config('customer').get_models()

for m in models:
    try:
        admin.site.register(m)
    except:
        pass