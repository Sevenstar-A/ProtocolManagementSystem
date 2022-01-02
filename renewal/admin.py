from django.contrib import admin
from .models import *
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered

models = apps.get_app_config('renewal').get_models()
for model in models:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass

