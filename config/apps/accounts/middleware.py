from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.contrib import messages

class SuperuserRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Paths that should be accessible without being a superuser
        exempt_paths = [
            reverse('accounts:login'), 
            '/admin/login/',
            '/admin/'
        ]
        
        # Allow access to static and media files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
            
        # Allow access to the admin login page and exempt paths
        if request.path in exempt_paths or request.path.startswith('/admin/'):
            return self.get_response(request)
            
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему для доступа к этой странице.')
            return redirect('accounts:login')
            
        return self.get_response(request)

class RoleBasedAccessMiddleware:
    """Middleware для контроля доступа на основе ролей пользователей"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Пути, которые должны быть доступны без авторизации
        exempt_paths = [
            reverse('accounts:login'),
            '/admin/login/',
            '/admin/',
            '/accounts/login/',
            '/static/',
            '/media/',
            '/infrastruction/',  # Allow infrastructure paths
        ]
        
        # Разрешаем доступ к статическим файлам и медиа
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
            
        # Разрешаем доступ к странице входа и исключенным путям
        if (request.path in exempt_paths or 
            request.path.startswith('/admin/') or 
            request.path.startswith('/accounts/login/') or
            request.path.startswith('/infrastruction/')):  # Allow all infrastructure paths
            return self.get_response(request)
            
        # Проверяем аутентификацию пользователя
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему для доступа к этой странице.')
            return redirect('accounts:login')

        return self.get_response(request) 