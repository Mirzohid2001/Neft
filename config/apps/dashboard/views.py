from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

# Create your views here.

def dashboard(request):
    """
    Главная страница-маршрутизатор, которая перенаправляет пользователей 
    в зависимости от их роли
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Пожалуйста, войдите в систему для доступа к этой странице.')
        return redirect('accounts:login')
        
    context = {}
    
    # Маршрутизация на основе роли пользователя
    if request.user.is_superuser or request.user.role == 'admin':
        return render(request, 'dashboard/dashboard.html', context)
    elif request.user.role == 'boss':
        return render(request, 'dashboard/dashboard.html', context)
    elif request.user.role == 'sales':
        return redirect('warehouse:sales_department_dashboard')
    elif request.user.role == 'estokada':
        return redirect('warehouse:estokada_dashboard')
    elif request.user.role == 'finance':
        return redirect('accounting:financial_dashboard')
    elif request.user.role == 'accounting':
        return redirect('accounting:financial_dashboard')
    elif request.user.role == 'customs':
        return redirect('customs:dashboard')
    else:
        # Если роль не определена, показываем общую информацию
        messages.warning(request, 'Для вашей роли не настроена специальная панель управления.')
        return render(request, 'dashboard/dashboard.html', context)

def index(request):
    # Здесь может быть код, который проверяет доступность модулей
    # и включает их в контекст. Убедимся, что production включен.
    context = {
        'modules': [
            {
                'name': 'Производство',
                'icon': 'bi-gear-wide-connected',
                'url': reverse('production:index'),
                'description': 'Управление производственными процессами'
            },
            # другие модули...
        ]
    }
    return render(request, 'dashboard/index.html', context)

