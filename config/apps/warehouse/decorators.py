from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.urls import reverse

def warehouse_required(view_func=None):
    """
    Декоратор, проверяющий, имеет ли пользователь роль "warehouse".
    Если нет - перенаправляет на страницу с сообщением о доступе.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'warehouse':
                return view_func(request, *args, **kwargs)
            else:
                # Если нет доступа, перенаправляем на страницу с сообщением
                return redirect(reverse('access_denied'))
        return _wrapped_view
    
    if view_func:
        return decorator(view_func)
    return decorator 