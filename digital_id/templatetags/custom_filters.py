from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Safely get a key from a dict, return '0.00' if missing."""
    try:
        return d.get(key, "0.00")
    except:
        return "0.00"
