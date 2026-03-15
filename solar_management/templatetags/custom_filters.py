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

@register.filter(name='sub')
def sub(value, arg):
    """
    Subtracts the arg from the value and returns positive absolute difference.
    Usage: {{ value|sub:arg }}
    """
    try:
        # handle potential None values
        val1 = float(value) if value is not None and value != '' else 0.0
        val2 = float(arg) if arg is not None and arg != '' else 0.0
        res = abs(val1 - val2)
        # return int if it essentially is an int
        return int(res) if res.is_integer() else round(res, 2)
    except (ValueError, TypeError):
        return 0
