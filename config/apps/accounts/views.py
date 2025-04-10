from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from functools import wraps

def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_superuser:
            messages.error(request, 'Доступ разрешен только для суперпользователя.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_admin or request.user.is_superuser):
            messages.error(request, 'Доступ разрешен только для администратора.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def boss_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_boss or request.user.is_admin or request.user.is_superuser):
            messages.error(request, 'Доступ разрешен только для руководства.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def sales_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_sales or request.user.is_admin or request.user.is_superuser):
            messages.error(request, 'Доступ разрешен только для отдела продаж.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def finance_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_finance or request.user.is_admin or request.user.is_superuser):
            messages.error(request, 'Доступ разрешен только для финансового отдела.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def estokada_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_estokada or request.user.is_admin or request.user.is_superuser):
            messages.error(request, 'Доступ разрешен только для сотрудников эстокады.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def accounting_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_accounting or request.user.is_admin or request.user.is_superuser):
            messages.error(request, 'Доступ разрешен только для бухгалтерии.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def customs_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not (request.user.is_customs or request.user.is_admin or request.user.is_superuser):
            messages.error(request, 'Доступ разрешен только для таможенного отдела.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:dashboard')
        return render(request, 'accounts/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard:dashboard')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
            
        return render(request, 'accounts/login.html')

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('accounts:login')
