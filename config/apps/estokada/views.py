from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Sum, Count, Q
from .models import EstokadaMovement
from .forms import (
    EstokadaMovementForm, 
    EstokadaReceiveForm, 
    EstokadaShipmentForm, 
    EstokadaTransferForm, 
    EstokadaProductionForm,
    SalesProcessForm
)
from apps.warehouse.models import Movement, Reservoir, Wagon, Product
from apps.sales.models import SalesMovement, Order
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .decorators import estokada_required
from django.utils.decorators import method_decorator

# ----------------------------------------------------------------------
# Базовые классы представлений (должны быть определены первыми)
# ----------------------------------------------------------------------

@method_decorator(estokada_required, name='dispatch')
class MovementCreateView(LoginRequiredMixin, CreateView):
    """Базовый класс для создания операций эстокады"""
    model = EstokadaMovement
    form_class = EstokadaMovementForm
    template_name = 'estokada/movement_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f"Операция успешно создана")
            return response
        except Exception as e:
            messages.error(self.request, f"Ошибка при создании операции: {str(e)}")
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('estokada:movement_detail', kwargs={'pk': self.object.pk})


# ----------------------------------------------------------------------
# Классы представлений, наследуемые от базовых
# ----------------------------------------------------------------------

@method_decorator(estokada_required, name='dispatch')
class ReceiveCreateView(MovementCreateView):
    """Представление для создания операции приемки"""
    form_class = EstokadaReceiveForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание операции приемки на эстокаде'
        context['form_type'] = 'receive'
        context['operation_type'] = 'receive'
        return context

    def get_initial(self):
        return {'movement_type': 'in'}
        
    def form_valid(self, form):
        # Вызываем родительский метод, который сохраняет форму
        response = super().form_valid(form)
        
        # Получаем только что созданный объект
        estokada_movement = self.object
        
        # Отправляем уведомление в модуль Sales о новой операции приемки
        from django.db.models.signals import post_save
        from apps.sales.signals import notify_sales_about_estokada_operation
        
        # Вызываем сигнал вручную, так как объект уже создан
        post_save.send(sender=EstokadaMovement, instance=estokada_movement, created=True)
        
        messages.success(self.request, 'Операция приемки успешно создана и отправлена в отдел продаж')
        
        return response

@method_decorator(estokada_required, name='dispatch')
class ShipmentCreateView(MovementCreateView):
    """Представление для создания операции отгрузки"""
    form_class = EstokadaShipmentForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание операции отгрузки'
        context['form_type'] = 'shipment'
        context['operation_type'] = 'shipment'
        return context

    def get_initial(self):
        return {'movement_type': 'out'}
        
    def form_valid(self, form):
        # Вызываем родительский метод, который сохраняет форму
        response = super().form_valid(form)
        
        # Получаем только что созданный объект
        estokada_movement = self.object
        
        # Создаем соответствующую запись в Sales
        try:
            from apps.warehouse.models import Client
            from django.utils import timezone
            import datetime
            
            # Проверяем, не существует ли уже запись для этого движения
            if not SalesMovement.objects.filter(movement=estokada_movement.movement).exists():
                # Получаем первого клиента для примера
                default_client = Client.objects.first()
                
                if default_client and estokada_movement.movement.movement_type == 'out':
                    # Создаем базовую запись Sales в соответствии с новой моделью
                    sales_movement = SalesMovement.objects.create(
                        movement=estokada_movement.movement,
                        document_number=f"OUT-{estokada_movement.movement.pk}",
                        document_date=timezone.now().date(),
                        client_name=default_client.title,
                        product=estokada_movement.movement.product,
                        type='sale',
                        status='created',
                        estimated_volume=float(estokada_movement.movement.quantity)
                    )
                    
                    # Создаем запись эстокады, связанную с SalesMovement
                    EstokadaMovement.objects.create(
                        sales_movement=sales_movement,
                        movement=estokada_movement.movement
                    )
                    
                    messages.success(self.request, 'Отгрузка создана и автоматически отправлена в отдел продаж')
        except Exception as e:
            messages.warning(self.request, f'Отгрузка создана, но произошла ошибка при отправке в отдел продаж: {e}')
        
        return response

@method_decorator(estokada_required, name='dispatch')
class TransferCreateView(MovementCreateView):
    """Представление для создания операции перемещения"""
    form_class = EstokadaTransferForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание операции перемещения'
        context['form_type'] = 'transfer'
        context['operation_type'] = 'transfer'
        return context
    
    def get_initial(self):
        return {'movement_type': 'transfer'}

@method_decorator(estokada_required, name='dispatch')
class ProductionCreateView(MovementCreateView):
    """Представление для создания операции производства"""
    form_class = EstokadaProductionForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание операции производства'
        context['form_type'] = 'production'
        context['operation_type'] = 'production'
        return context
    
    def get_initial(self):
        return {'movement_type': 'production'}

# ----------------------------------------------------------------------
# Остальные классы представлений
# ----------------------------------------------------------------------

@method_decorator(estokada_required, name='dispatch')
class DashboardView(LoginRequiredMixin, ListView):
    """
    Панель управления эстокады
    """
    template_name = 'estokada/dashboard.html'
    context_object_name = 'recent_movements'
    model = EstokadaMovement
    
    def get_queryset(self):
        return EstokadaMovement.objects.all().order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Общее количество операций
        context['total_movements'] = EstokadaMovement.objects.count()
        
        # Временно отключаем запросы, использующие operation__status
        try:
            # Операции, ожидающие обработки
            pending_count = EstokadaMovement.objects.filter(
                status='in_progress'  # Используем прямое поле status в EstokadaMovement
            ).count()
            context['pending_operations'] = pending_count
            
            # Заказы от отдела продаж
            sales_count = EstokadaMovement.objects.filter(
                status='created'  # Используем прямое поле status
            ).count()
            context['sales_orders'] = sales_count
            
            # Завершенные сегодня
            completed_count = EstokadaMovement.objects.filter(
                status='completed',
                updated_at__date=today
            ).count()
            context['completed_today'] = completed_count
            
        except Exception as e:
            # Если запросы с operation__status вызывают ошибку, используем нули
            context['pending_operations'] = 0
            context['sales_orders'] = 0
            context['completed_today'] = 0
        
        return context

@method_decorator(estokada_required, name='dispatch')
class MovementListView(LoginRequiredMixin, ListView):
    """
    Список всех операций эстокады
    """
    template_name = 'estokada/movement_list.html'
    context_object_name = 'movements'
    model = EstokadaMovement
    paginate_by = 20
    
    def get_queryset(self):
        queryset = EstokadaMovement.objects.all().order_by('-created_at')
        
        # Фильтрация по типу движения (если указан)
        movement_type = self.request.GET.get('movement_type')
        if movement_type:
            queryset = queryset.filter(operation__movement__movement_type=movement_type)
            
        # Фильтрация по статусу
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Все операции эстокады'
        context['movement_type'] = self.request.GET.get('movement_type', '')
        context['status'] = self.request.GET.get('status', '')
        return context

@method_decorator(estokada_required, name='dispatch')
class ReceiveListView(MovementListView):
    """
    Список операций приемки
    """
    def get_queryset(self):
        return super().get_queryset().filter(operation__movement__movement_type='in')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Операции приемки'
        context['movement_type'] = 'receive'
        return context

@method_decorator(estokada_required, name='dispatch')
class ProductionListView(MovementListView):
    """
    Список операций производства
    """
    def get_queryset(self):
        return super().get_queryset().filter(operation__movement__movement_type='production')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Операции производства'
        context['movement_type'] = 'production'
        return context

@method_decorator(estokada_required, name='dispatch')
class TransferListView(MovementListView):
    """
    Список операций перемещения
    """
    def get_queryset(self):
        return super().get_queryset().filter(operation__movement__movement_type='transfer')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Операции перемещения'
        context['movement_type'] = 'transfer'
        return context

@method_decorator(estokada_required, name='dispatch')
class MovementDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная информация об операции
    """
    template_name = 'estokada/movement_detail.html'
    context_object_name = 'movement'
    model = EstokadaMovement
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Если операция связана с заказом от отдела продаж
        if self.object.movement.source_order:
            context['order'] = self.object.movement.source_order
        
        return context

@method_decorator(estokada_required, name='dispatch')
class MovementUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для обновления операции эстокады"""
    template_name = 'estokada/movement_form.html'
    model = EstokadaMovement
    form_class = EstokadaMovementForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование операции эстокады'
        context['operation_type'] = self.object.movement.movement_type
        return context
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f"Операция успешно обновлена")
            return response
        except Exception as e:
            messages.error(self.request, f"Ошибка при обновлении операции: {str(e)}")
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('estokada:movement_detail', kwargs={'pk': self.object.pk})

@method_decorator(estokada_required, name='dispatch')
class EstokadaStatsView(LoginRequiredMixin, ListView):
    """Представление статистики эстокады"""
    template_name = 'estokada/stats.html'
    context_object_name = 'stats'
    model = EstokadaMovement
    
    def get_queryset(self):
        # Базовый запрос не используется, так как мы переопределяем context_data
        return EstokadaMovement.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем параметры для фильтрации
        date_from = self.request.GET.get('date_from', 
                                   (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d'))
        date_to = self.request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
        
        # Базовый запрос с фильтрацией по датам
        base_query = EstokadaMovement.objects.filter(
            movement__date__gte=date_from,
            movement__date__lte=date_to
        )
        
        # Статистика по типам операций
        context['operation_stats'] = base_query.values(
            'movement__movement_type'
        ).annotate(
            count=Count('id'), 
            total_quantity=Sum('movement__quantity')
        ).order_by('movement__movement_type')
        
        # Статистика по продуктам
        context['product_stats'] = base_query.values(
            'movement__product__name'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('movement__quantity')
        ).order_by('-total_quantity')
        
        # Статистика по типам транспорта
        context['transport_stats'] = base_query.values(
            'transport_type'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('movement__quantity')
        ).order_by('-total_quantity')
        
        # Ежедневная статистика
        context['daily_stats'] = base_query.values(
            'movement__date'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('movement__quantity')
        ).order_by('movement__date')
        
        context['date_from'] = date_from
        context['date_to'] = date_to
        
        return context

@method_decorator(estokada_required, name='dispatch')
class SalesOrdersListView(LoginRequiredMixin, ListView):
    """
    Список заказов от отдела продаж, ожидающих обработки
    """
    template_name = 'estokada/sales_orders_list.html'
    context_object_name = 'orders'
    
    def get_queryset(self):
        # Получаем заказы, которые уже отправлены в эстокаду, но еще не обработаны
        return Order.objects.filter(
            delivery_status='in_progress'
        ).order_by('-created_at')

@estokada_required
def process_sales_order(request, pk):
    """
    Обработка заказа от отдела продаж
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Проверяем, что заказ находится в нужном статусе
    if order.delivery_status != 'in_progress':
        messages.error(request, 'Этот заказ не может быть обработан')
        return redirect('estokada:sales_orders')
    
    # Проверяем наличие операции эстокады для этого заказа
    try:
        estokada_movement = EstokadaMovement.objects.get(movement__source_order=order)
    except EstokadaMovement.DoesNotExist:
        messages.error(request, 'Для этого заказа не найдена операция эстокады')
        return redirect('estokada:sales_orders')
    
    # Если GET запрос - показываем форму
    if request.method == 'GET':
        form = SalesProcessForm(instance=estokada_movement.movement)
        return render(request, 'estokada/process_sales_order.html', {
            'form': form,
            'order': order,
            'estokada_movement': estokada_movement
        })
    
    # Если POST запрос - обрабатываем форму
    form = SalesProcessForm(request.POST, instance=estokada_movement.movement)
    if form.is_valid():
        movement = form.save(commit=False)
        movement.status = 'completed'  # Меняем статус на "завершено"
        movement.completed_date = timezone.now()
        movement.updated_by = request.user
        movement.save()
        
        # Обновляем статус заказа
        order.delivery_status = 'completed'
        order.completed_date = timezone.now()
        order.save()
        
        messages.success(request, 'Заказ успешно обработан')
        return redirect('estokada:sales_orders')
    
    return render(request, 'estokada/process_sales_order.html', {
        'form': form,
        'order': order,
        'estokada_movement': estokada_movement
    })

@estokada_required
def change_movement_status(request, pk, status):
    """
    Изменение статуса операции
    """
    estokada_movement = get_object_or_404(EstokadaMovement, pk=pk)
    
    # Проверяем, можно ли изменить статус
    if estokada_movement.movement.status == 'completed':
        messages.error(request, 'Нельзя изменить статус завершенной операции')
        return redirect('estokada:movement_detail', pk=estokada_movement.pk)
    
    if status not in ['in_progress', 'completed', 'cancelled']:
        messages.error(request, 'Недопустимый статус')
        return redirect('estokada:movement_detail', pk=estokada_movement.pk)
    
    # Обновляем статус
    movement = estokada_movement.movement
    movement.status = status
    
    if status == 'completed':
        movement.completed_date = timezone.now()
        
        # Если операция связана с заказом - обновляем его статус
        if movement.source_order:
            order = movement.source_order
            order.delivery_status = 'completed'
            order.completed_date = timezone.now()
            order.save()
    
    movement.updated_by = request.user
    movement.save()
    
    status_display = {
        'in_progress': 'В процессе',
        'completed': 'Завершено',
        'cancelled': 'Отменено'
    }
    
    messages.success(request, f'Статус изменен на "{status_display[status]}"')
    return redirect('estokada:movement_detail', pk=estokada_movement.pk)

# ----------------------------------------------------------------------
# Функции представлений
# ----------------------------------------------------------------------

@login_required
def dashboard(request):
    """
    Панель управления эстокадой с общей статистикой и последними операциями
    """
    # Получаем последние операции каждого типа
    recent_movements = EstokadaMovement.objects.select_related('movement').order_by('-movement__date')[:10]
    
    # Статистика по типам операций
    operation_stats = EstokadaMovement.objects.select_related('movement').values(
        'movement__movement_type'
    ).annotate(
        count=Count('id'),
        total_quantity=Sum('movement__quantity')
    ).order_by('movement__movement_type')
    
    # Статистика по транспорту
    transport_stats = EstokadaMovement.objects.values(
        'transport_type'
    ).annotate(
        count=Count('id'),
        total_quantity=Sum('movement__quantity')
    ).order_by('transport_type')
    
    # Статистика по продуктам
    product_stats = EstokadaMovement.objects.select_related('movement__product').values(
        'movement__product__name'
    ).annotate(
        count=Count('id'),
        total_quantity=Sum('movement__quantity')
    ).order_by('-total_quantity')[:5]
    
    context = {
        'recent_movements': recent_movements,
        'total_movements': EstokadaMovement.objects.count(),
        'operation_stats': operation_stats,
        'transport_stats': transport_stats,
        'product_stats': product_stats,
    }
    return render(request, 'estokada/dashboard.html', context)

@login_required
def movement_list(request):
    """
    Список всех движений через эстокаду с возможностью фильтрации
    """
    # Получаем параметры фильтрации из запроса
    movement_type = request.GET.get('movement_type', '')
    transport_type = request.GET.get('transport_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Базовый QuerySet
    movements = EstokadaMovement.objects.select_related(
        'movement', 'movement__product', 'source_reservoir', 'target_reservoir',
        'source_wagon', 'target_wagon'
    ).order_by('-movement__date')
    
    # Применяем фильтры
    if movement_type:
        movements = movements.filter(operation__movement__movement_type=movement_type)
    
    if transport_type:
        movements = movements.filter(transport_type=transport_type)
    
    if date_from:
        movements = movements.filter(movement__date__gte=date_from)
    
    if date_to:
        movements = movements.filter(movement__date__lte=date_to)
    
    context = {
        'movements': movements,
        'movement_types': Movement.MOVEMENT_TYPES,
        'transport_types': EstokadaMovement.TRANSPORT_TYPES,
        'current_filters': {
            'movement_type': movement_type,
            'transport_type': transport_type,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    return render(request, 'estokada/movement_list.html', context)

@login_required
def movement_create(request):
    """
    Создание нового движения через эстокаду (общая форма)
    """
    if request.method == 'POST':
        form = EstokadaMovementForm(request.POST, user=request.user)
        if form.is_valid():
            movement = form.save()
            messages.success(request, 'Движение через эстокаду успешно создано.')
            return redirect('estokada:movement_detail', pk=movement.pk)
    else:
        form = EstokadaMovementForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Создание движения через эстокаду',
    }
    return render(request, 'estokada/movement_form.html', context)

@login_required
def movement_edit(request, pk):
    """
    Редактирование существующего движения через эстокаду
    """
    movement = get_object_or_404(EstokadaMovement, pk=pk)
    
    if request.method == 'POST':
        form = EstokadaMovementForm(request.POST, instance=movement, user=request.user)
        if form.is_valid():
            movement = form.save()
            messages.success(request, 'Движение через эстокаду успешно обновлено.')
            return redirect('estokada:movement_detail', pk=movement.pk)
    else:
        # Выбираем форму в зависимости от типа операции
        if movement.movement and movement.movement.movement_type:
            movement_type = movement.movement.movement_type
            if movement_type == 'in':
                form = EstokadaReceiveForm(instance=movement, user=request.user)
            elif movement_type == 'out':
                form = EstokadaShipmentForm(instance=movement, user=request.user)
            elif movement_type == 'transfer':
                form = EstokadaTransferForm(instance=movement, user=request.user)
            elif movement_type == 'production':
                form = EstokadaProductionForm(instance=movement, user=request.user)
            else:
                form = EstokadaMovementForm(instance=movement, user=request.user)
        else:
            form = EstokadaMovementForm(instance=movement, user=request.user)
    
    context = {
        'form': form,
        'movement': movement,
        'title': 'Редактирование движения через эстокаду',
    }
    return render(request, 'estokada/movement_form.html', context)

@login_required
def movement_delete(request, pk):
    """
    Удаление движения через эстокаду
    """
    movement = get_object_or_404(EstokadaMovement, pk=pk)
    
    if request.method == 'POST':
        # Сохраняем ID основного движения, чтобы его тоже удалить
        main_movement_id = movement.movement.id if movement.movement else None
        
        # Удаляем сначала движение эстокады
        movement.delete()
        
        # Если было связанное основное движение, удаляем и его
        if main_movement_id:
            Movement.objects.filter(id=main_movement_id).delete()
        
        messages.success(request, 'Движение через эстокаду успешно удалено.')  
        return redirect('estokada:movement_list')
    
    context = {
        'movement': movement,
    }
    return render(request, 'estokada/movement_confirm_delete.html', context)
