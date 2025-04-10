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
        ]
        
        # Разрешаем доступ к статическим файлам и медиа
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
            
        # Разрешаем доступ к странице входа и исключенным путям
        if request.path in exempt_paths or request.path.startswith('/admin/') or request.path.startswith('/accounts/login/'):
            return self.get_response(request)
            
        # Проверяем аутентификацию пользователя
        if not request.user.is_authenticated:
            messages.error(request, 'Пожалуйста, войдите в систему для доступа к этой странице.')
            return redirect('accounts:login')
            
        # Маршруты для разных ролей
        estokada_paths = ['/estokada/']
        sales_paths = ['/sales/']
        finance_paths = ['/finance/']
        accounting_paths = ['/accounting/']
        customs_paths = ['/customs/']
        
        # Проверяем доступ на основе роли
        
        # Админы и боссы имеют доступ ко всему
        if request.user.is_superuser or request.user.role in ['admin', 'boss']:
            return self.get_response(request)
            
        # Проверки для остальных ролей
        for path_prefix in estokada_paths:
            if request.path.startswith(path_prefix) and request.user.role != 'estokada':
                messages.error(request, 'Доступ ограничен. Требуется роль: Эстокада.')
                return redirect('dashboard:dashboard')
                
        for path_prefix in sales_paths:
            if request.path.startswith(path_prefix) and request.user.role != 'sales':
                messages.error(request, 'Доступ ограничен. Требуется роль: Отдел продаж.')
                return redirect('dashboard:dashboard')
                
        for path_prefix in finance_paths:
            if request.path.startswith(path_prefix) and request.user.role != 'finance':
                messages.error(request, 'Доступ ограничен. Требуется роль: Финансовый отдел.')
                return redirect('dashboard:dashboard')
                
        for path_prefix in accounting_paths:
            if request.path.startswith(path_prefix) and request.user.role != 'accounting':
                messages.error(request, 'Доступ ограничен. Требуется роль: Бухгалтерия.')
                return redirect('dashboard:dashboard')
                
        for path_prefix in customs_paths:
            if request.path.startswith(path_prefix) and request.user.role != 'customs':
                messages.error(request, 'Доступ ограничен. Требуется роль: Таможенный отдел.')
                return redirect('dashboard:dashboard')
                
        return self.get_response(request) 