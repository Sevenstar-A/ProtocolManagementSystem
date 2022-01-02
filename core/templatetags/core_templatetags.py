import os

from django import template

register = template.Library()

@register.filter
def get_filename(value):
    try:
        return os.path.basename(value.file.name)
    except :
        return '-'

     
@register.simple_tag
def subtract(a, b):
    try:
        return a - b
    except:
        return 0