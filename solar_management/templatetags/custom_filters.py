from django import template

register = template.Library()

@register.filter(name='replace')
def replace(value, arg):
    """
    Replaces characters within a string.
    Usage: {{ value|replace:"_, " }}
    """
    if len(arg.split(',')) != 2:
        return value
        
    old, new = arg.split(',')
    return str(value).replace(old, new)
