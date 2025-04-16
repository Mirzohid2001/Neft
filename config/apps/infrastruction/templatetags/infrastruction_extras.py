from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    return dictionary.get(key)

@register.filter(name='add_class')
def add_class(field, css_class):
    """Add a CSS class to a form field"""
    return field.as_widget(attrs={"class": css_class})

@register.filter
def percentage(value, total):
    """
    Calculate what percentage value is of total
    """
    try:
        return float(value) / float(total) * 100
    except (ValueError, ZeroDivisionError):
        return 0 