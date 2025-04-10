from django import template

register = template.Library()

@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value or 0) - float(arg or 0)
    except (ValueError, TypeError):
        return 0 