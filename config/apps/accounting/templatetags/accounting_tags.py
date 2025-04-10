from django import template
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.numberformat import format
from django.utils import timezone
from datetime import datetime, timedelta

register = template.Library()

@register.simple_tag
def url_with_param(request, param_name, param_value):
    """
    Добавляет или заменяет параметр в URL
    Использование: {% url_with_param request 'page' 2 %}
    """
    query_dict = request.GET.copy()
    query_dict[param_name] = param_value
    return urlencode(query_dict)

@register.filter
def currency(value, currency_symbol='₽'):
    """
    Форматирование суммы с валютой
    Пример: {{ 1234.56|currency:"$" }} -> $1,234.56
    """
    try:
        value = float(value)
        formatted = format(value, ',', 2)
        return f'{formatted} {currency_symbol}'
    except (ValueError, TypeError):
        return value

@register.filter
def account_balance_class(value):
    """
    Возвращает CSS класс в зависимости от значения баланса счета
    """
    try:
        value = float(value)
        if value > 0:
            return 'text-success'
        elif value < 0:
            return 'text-danger'
        else:
            return 'text-muted'
    except (ValueError, TypeError):
        return ''

@register.filter
def transaction_type_badge(value):
    """
    Возвращает HTML-код для отображения типа транзакции
    """
    badges = {
        'income': '<span class="badge badge-success">Доход</span>',
        'expense': '<span class="badge badge-danger">Расход</span>',
        'transfer': '<span class="badge badge-primary">Перевод</span>',
    }
    return mark_safe(badges.get(value, f'<span class="badge badge-secondary">{escape(value)}</span>'))

@register.filter
def account_type_icon(value):
    """
    Возвращает иконку для различных типов счетов
    """
    icons = {
        'cash': '<i class="fas fa-money-bill-alt"></i>',
        'card': '<i class="fas fa-credit-card"></i>',
        'bank': '<i class="fas fa-university"></i>',
        'savings': '<i class="fas fa-piggy-bank"></i>',
        'debt': '<i class="fas fa-hand-holding-usd"></i>',
        'investment': '<i class="fas fa-chart-line"></i>',
    }
    return mark_safe(icons.get(value, '<i class="fas fa-wallet"></i>'))

@register.simple_tag
def get_date_range_options():
    """
    Возвращает набор предварительно определенных диапазонов дат для фильтров
    """
    today = timezone.now().date()
    
    # Начало и конец месяца
    month_start = today.replace(day=1)
    next_month = month_start.replace(month=month_start.month+1) if month_start.month < 12 else month_start.replace(year=month_start.year+1, month=1)
    month_end = next_month - timedelta(days=1)
    
    # Начало и конец года
    year_start = today.replace(month=1, day=1)
    year_end = today.replace(month=12, day=31)
    
    # Прошлый месяц
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    
    return {
        'today': {
            'name': 'Сегодня',
            'start': today,
            'end': today
        },
        'yesterday': {
            'name': 'Вчера',
            'start': today - timedelta(days=1),
            'end': today - timedelta(days=1)
        },
        'week': {
            'name': 'Текущая неделя',
            'start': today - timedelta(days=today.weekday()),
            'end': today
        },
        'month': {
            'name': 'Текущий месяц',
            'start': month_start,
            'end': today
        },
        'last_month': {
            'name': 'Прошлый месяц',
            'start': prev_month_start,
            'end': prev_month_end
        },
        'quarter': {
            'name': 'Текущий квартал',
            'start': today.replace(month=((today.month-1)//3)*3+1, day=1),
            'end': today
        },
        'year': {
            'name': 'Текущий год',
            'start': year_start,
            'end': today
        },
        'last_7_days': {
            'name': 'Последние 7 дней',
            'start': today - timedelta(days=6),
            'end': today
        },
        'last_30_days': {
            'name': 'Последние 30 дней',
            'start': today - timedelta(days=29),
            'end': today
        },
        'last_90_days': {
            'name': 'Последние 90 дней',
            'start': today - timedelta(days=89),
            'end': today
        },
        'all_time': {
            'name': 'Все время',
            'start': None,
            'end': None
        }
    }

@register.filter
def percentage(value, total):
    """
    Расчет процента от общего значения
    Пример: {{ 25|percentage:100 }} -> 25%
    """
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return '0%'
        percentage = (value / total) * 100
        return f'{int(percentage)}%' if percentage.is_integer() else f'{percentage:.1f}%'
    except (ValueError, TypeError, ZeroDivisionError):
        return '0%'

@register.filter
def progress_bar_class(value, total):
    """
    Возвращает класс для прогресс-бара в зависимости от процента выполнения
    """
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return 'bg-secondary'
        percentage = (value / total) * 100
        
        if percentage > 100:
            return 'bg-danger'
        elif percentage > 75:
            return 'bg-warning'
        elif percentage > 50:
            return 'bg-info'
        elif percentage > 25:
            return 'bg-primary'
        else:
            return 'bg-success'
    except (ValueError, TypeError, ZeroDivisionError):
        return 'bg-secondary'

@register.filter
def date_format(value, format_string='d.m.Y'):
    """
    Форматирование даты в заданный формат
    """
    if not value:
        return ''
    
    if isinstance(value, str):
        try:
            # Пытаемся преобразовать строку в дату
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return value
    
    try:
        return value.strftime(format_string)
    except (AttributeError, ValueError):
        return value 