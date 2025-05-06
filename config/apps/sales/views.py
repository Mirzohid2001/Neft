from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db.models import Sum, Count, Q, F
from .models import SalesMovement, SalesContract, SalesContractProduct, Order, Client, Contract, Payment, OrderItem
from .forms import SalesMovementForm, OrderForm, ClientForm, ContractForm, PaymentForm, OrderItemForm
from apps.warehouse.models import Movement, Product, Client, Reservoir, Wagon, WagonType, Transport, Inventory, ReservoirMovement, Placement
from apps.warehouse.forms import MovementForm
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from .decorators import sales_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from datetime import timedelta, datetime
import json
from django.db import transaction

# Функция для генерации номера документа с префиксом
def generate_document_number(prefix):
    now = timezone.now()
    date_part = now.strftime('%Y%m%d')
    # Получаем последний номер документа с этим префиксом и датой
    last_movement = Movement.objects.filter(
        document_number__startswith=f"{prefix}{date_part}"
    ).order_by('-document_number').first()
    
    if last_movement:
        # Извлекаем последний номер и увеличиваем его на 1
        try:
            last_num = int(last_movement.document_number[len(prefix + date_part):])
            new_num = last_num + 1
        except ValueError:
            new_num = 1
    else:
        new_num = 1
    
    return f"{prefix}{date_part}{new_num:03d}"

@sales_required
def dashboard(request):
    """
    Панель управления продажами с общей статистикой и последними операциями
    """
    recent_sales = SalesMovement.objects.select_related('movement', 'client').order_by('-movement__date')[:10]
    
    # Статистика продаж
    total_sales = SalesMovement.objects.count()
    
    context = {
        'recent_sales': recent_sales,
        'total_sales': total_sales,
    }
    return render(request, 'sales/dashboard_new.html', context)

@sales_required
def sales_list(request):
    """
    Список всех продаж
    """
    sales = SalesMovement.objects.select_related('movement', 'movement__product', 'client').order_by('-movement__date')
    
    context = {
        'sales': sales,
    }
    return render(request, 'sales/sales_list.html', context)

@sales_required
def sales_detail(request, pk):
    """
    Детальная информация о конкретной продаже
    """
    sale = get_object_or_404(
        SalesMovement.objects.select_related('movement', 'movement__product', 'client'), 
        pk=pk
    )
    
    context = {
        'sale': sale,
    }
    return render(request, 'sales/sales_detail.html', context)

@sales_required
def sales_create(request):
    if request.method == 'POST':
        form = SalesMovementForm(request.POST, user=request.user)
        if form.is_valid():
            sale = form.save()
            messages.success(request, 'Продажа успешно создана.')
            return redirect('sales:sales_detail', pk=sale.pk)
    else:
        form = SalesMovementForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Создание продажи',
    }
    return render(request, 'sales/sales_form.html', context)

@sales_required
def sales_edit(request, pk):
    sale = get_object_or_404(SalesMovement, pk=pk)
    
    if request.method == 'POST':
        form = SalesMovementForm(request.POST, instance=sale, user=request.user)
        if form.is_valid():
            sale = form.save()
            messages.success(request, 'Продажа успешно обновлена.')
            return redirect('sales:sales_detail', pk=sale.pk)
    else:
        form = SalesMovementForm(instance=sale, user=request.user)
    
    context = {
        'form': form,
        'sale': sale,
        'title': 'Редактирование продажи',
    }
    return render(request, 'sales/sales_form.html', context)

@sales_required
def sales_delete(request, pk):
    sale = get_object_or_404(SalesMovement, pk=pk)
    
    if request.method == 'POST':
        # Сохраняем ID основного движения, чтобы его тоже удалить
        main_movement_id = sale.movement.id if sale.movement else None
        
        # Удаляем сначала продажу
        sale.delete()
        
        # Если было связанное основное движение, удаляем и его
        if main_movement_id:
            Movement.objects.filter(id=main_movement_id).delete()
        
        messages.success(request, 'Продажа успешно удалена.')
        return redirect('sales:sales_list')
    
    context = {
        'sale': sale,
    }
    return render(request, 'sales/sales_confirm_delete.html', context)

@method_decorator(sales_required, name='dispatch')
class DashboardView(LoginRequiredMixin, ListView):
    """
    Панель управления для отдела продаж
    """
    template_name = 'sales/dashboard.html'
    context_object_name = 'recent_orders'
    model = Order
    
    def get_queryset(self):
        return Order.objects.all().order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        context['total_orders'] = Order.objects.count()
        context['pending_shipments'] = Order.objects.filter(delivery_status='pending').count()
        context['in_progress_shipments'] = Order.objects.filter(delivery_status='in_progress').count()
        context['completed_today'] = Order.objects.filter(
            delivery_status='completed', 
            completed_date=today
        ).count()
        
        return context

@method_decorator(sales_required, name='dispatch')
class OrderListView(LoginRequiredMixin, ListView):
    """
    Список всех заказов
    """
    template_name = 'sales/order_list.html'
    context_object_name = 'orders'
    model = Order
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')
        
        # Фильтры
        filters = {}
        
        delivery_status = self.request.GET.get('delivery_status')
        if delivery_status:
            filters['delivery_status'] = delivery_status
            
        payment_status = self.request.GET.get('payment_status')
        if payment_status:
            filters['payment_status'] = payment_status
            
        date_from = self.request.GET.get('date_from')
        if date_from:
            filters['created_at__date__gte'] = date_from
            
        date_to = self.request.GET.get('date_to')
        if date_to:
            filters['created_at__date__lte'] = date_to
            
        client_id = self.request.GET.get('client')
        if client_id:
            filters['client_id'] = client_id
            
        return queryset.filter(**filters)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clients'] = Client.objects.all()
        return context

@method_decorator(sales_required, name='dispatch')
class OrderDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная информация о заказе
    """
    template_name = 'sales/order_detail.html'
    context_object_name = 'order'
    model = Order
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = Payment.objects.filter(order=self.object)
        
        # Проверяем наличие связанной операции эстокады
        if hasattr(self.object, 'estokada_operation'):
            context['estokada_operation'] = self.object.estokada_operation
            
        return context

@method_decorator(sales_required, name='dispatch')
class OrderCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового заказа
    """
    template_name = 'sales/order_form.html'
    model = Order
    form_class = OrderForm
    success_url = reverse_lazy('sales:order_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Заказ успешно создан')
        return super().form_valid(form)

@method_decorator(sales_required, name='dispatch')
class OrderUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование заказа
    """
    template_name = 'sales/order_form.html'
    model = Order
    form_class = OrderForm
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.pk})
    
    def get_queryset(self):
        # Запрещаем редактирование заказов, которые не находятся в статусе ожидания
        return Order.objects.filter(delivery_status='pending')

@method_decorator(sales_required, name='dispatch')
class ClientListView(LoginRequiredMixin, ListView):
    """
    Список клиентов
    """
    template_name = 'sales/client_list.html'
    context_object_name = 'clients'
    model = Client
    paginate_by = 20

@method_decorator(sales_required, name='dispatch')
class ClientCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового клиента
    """
    template_name = 'sales/client_form.html'
    model = Client
    form_class = ClientForm
    success_url = reverse_lazy('sales:client_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Клиент успешно создан')
        return super().form_valid(form)

@method_decorator(sales_required, name='dispatch')
class ContractListView(LoginRequiredMixin, ListView):
    """
    Список контрактов
    """
    template_name = 'sales/contract_list.html'
    context_object_name = 'contracts'
    model = Contract
    paginate_by = 20

@method_decorator(sales_required, name='dispatch')
class ContractCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового контракта
    """
    template_name = 'sales/contract_form.html'
    model = Contract
    form_class = ContractForm
    success_url = reverse_lazy('sales:contract_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Контракт успешно создан')
        return super().form_valid(form)

@method_decorator(sales_required, name='dispatch')
class SalesListView(LoginRequiredMixin, ListView):
    """Представление списка продаж"""
    template_name = 'sales/sales_list.html'
    context_object_name = 'sales'
    model = SalesMovement
    paginate_by = 20
    
    def get_queryset(self):
        queryset = SalesMovement.objects.all().select_related(
            'movement', 'movement__product', 'client'
        ).order_by('-movement__date')
        
        # Фильтрация
        client = self.request.GET.get('client')
        if client:
            queryset = queryset.filter(client_id=client)
            
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(movement__date__gte=date_from)
            
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(movement__date__lte=date_to)
            
        product = self.request.GET.get('product')
        if product:
            queryset = queryset.filter(movement__product_id=product)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clients'] = Client.objects.all()
        context['products'] = Product.objects.all()
        return context

@method_decorator(sales_required, name='dispatch')
class SalesDetailView(LoginRequiredMixin, DetailView):
    """Представление детальной информации о продаже"""
    template_name = 'sales/sales_detail.html'
    context_object_name = 'sale'
    model = SalesMovement
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

@method_decorator(sales_required, name='dispatch')
class SalesCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания новой продажи"""
    model = SalesMovement
    form_class = SalesMovementForm
    template_name = 'sales/sales_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание новой продажи'
        return context
    
    def form_valid(self, form):
        # Установка текущего пользователя как создателя
        sale = form.save(commit=False)
        if hasattr(sale, 'created_by') and not sale.created_by:
            sale.created_by = self.request.user
        
        # Сохраняем объект Sales
        response = super().form_valid(form)
        
        # Получаем только что созданный объект
        sales_movement = self.object
        
        messages.success(self.request, 'Продажа успешно создана')
        return response
    
    def get_success_url(self):
        return reverse_lazy('sales:sales_detail', kwargs={'pk': self.object.pk})

@method_decorator(sales_required, name='dispatch')
class SalesUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для обновления продажи"""
    model = SalesMovement
    form_class = SalesMovementForm
    template_name = 'sales/sales_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование продажи'
        return context
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, "Продажа успешно обновлена")
            return response
        except Exception as e:
            messages.error(self.request, f"Ошибка при обновлении продажи: {str(e)}")
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('sales:sales_detail', kwargs={'pk': self.object.pk})

@method_decorator(sales_required, name='dispatch')
class SalesStatsView(LoginRequiredMixin, ListView):
    """Представление статистики продаж"""
    template_name = 'sales/stats.html'
    context_object_name = 'sales_stats'
    model = SalesMovement
    
    def get_queryset(self):
        # Базовый запрос не используется, так как мы переопределяем context_data
        return SalesMovement.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем параметры для фильтрации
        date_from = self.request.GET.get('date_from', 
                               (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d'))
        date_to = self.request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
        
        # Базовый запрос с фильтрацией по датам
        base_query = SalesMovement.objects.filter(
            movement__date__gte=date_from,
            movement__date__lte=date_to
        )
        
        # Статистика по клиентам
        context['client_stats'] = base_query.values(
            'client__title'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('movement__quantity'),
            total_amount=Sum('total_price')
        ).order_by('-total_amount')
        
        # Статистика по продуктам
        context['product_stats'] = base_query.values(
            'movement__product__name'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('movement__quantity'),
            total_amount=Sum('total_price')
        ).order_by('-total_quantity')
        
        # Ежедневная статистика
        context['daily_stats'] = base_query.values(
            'movement__date'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('movement__quantity'),
            total_amount=Sum('total_price')
        ).order_by('movement__date')
        
        # Общая сумма продаж за период
        context['total_sales_amount'] = base_query.aggregate(total=Sum('total_price'))['total'] or 0
        
        # Общее количество продаж за период
        context['total_sales_quantity'] = base_query.aggregate(total=Sum('movement__quantity'))['total'] or 0
        
        context['date_from'] = date_from
        context['date_to'] = date_to
        
        return context

@method_decorator(sales_required, name='dispatch')
class EstokadaProcessedListView(LoginRequiredMixin, ListView):
    """Представление для просмотра заказов, обработанных эстокадой"""
    template_name = 'sales/estokada_processed_list.html'
    context_object_name = 'processed_orders'
    
    def get_queryset(self):
        # Получаем все продажи с типом движения 'out'
        sales_movements = SalesMovement.objects.select_related(
            'movement', 'movement__product', 'client'
        ).filter(
            movement__movement_type='out'
        )
        
        # Находим те, которые уже обработаны эстокадой
        processed_movements = EstokadaMovement.objects.values_list('movement_id', flat=True)
        return sales_movements.filter(movement_id__in=processed_movements).order_by('-movement__date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Заказы, обработанные эстокадой'
        
        # Для каждого заказа получим данные эстокады
        processed_data = {}
        for sale in context['processed_orders']:
            try:
                estokada_data = EstokadaMovement.objects.get(movement_id=sale.movement_id)
                processed_data[sale.id] = {
                    'document_weight': estokada_data.document_weight,
                    'actual_weight': estokada_data.actual_weight,
                    'weight_difference': estokada_data.weight_difference,
                    'temperature': estokada_data.temperature,
                    'density': estokada_data.density,
                    'estokada_id': estokada_data.id
                }
            except EstokadaMovement.DoesNotExist:
                pass
        
        context['processed_data'] = processed_data
        return context

@method_decorator(sales_required, name='dispatch')
class EstokadaProcessedDetailView(LoginRequiredMixin, DetailView):
    """Представление для детального просмотра заказа, обработанного эстокадой"""
    template_name = 'sales/estokada_processed_detail.html'
    context_object_name = 'sale'
    model = SalesMovement
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sale = self.object
        
        # Получаем связанную запись из эстокады
        from apps.estokada.models import EstokadaMovement
        try:
            estokada_movement = EstokadaMovement.objects.select_related(
                'movement', 'source_reservoir', 'target_reservoir', 'source_wagon', 'target_wagon'
            ).get(movement=sale.movement)
            context['estokada_movement'] = estokada_movement
            
            # Получаем историю обработки
            context['estokada_history'] = []
            
            # Если есть информация о источнике и назначении, добавляем в историю
            if estokada_movement.source_reservoir:
                context['estokada_history'].append({
                    'timestamp': sale.movement.date,
                    'action': 'Источник - резервуар',
                    'details': f'Наименование: {estokada_movement.source_reservoir.name}, Ёмкость: {estokada_movement.source_reservoir.capacity} т'
                })
            
            if estokada_movement.target_reservoir:
                context['estokada_history'].append({
                    'timestamp': sale.movement.date,
                    'action': 'Назначение - резервуар',
                    'details': f'Наименование: {estokada_movement.target_reservoir.name}, Ёмкость: {estokada_movement.target_reservoir.capacity} т'
                })
                
            if estokada_movement.source_wagon:
                context['estokada_history'].append({
                    'timestamp': sale.movement.date,
                    'action': 'Источник - вагон',
                    'details': f'Номер: {estokada_movement.source_wagon.number}, Ёмкость: {estokada_movement.source_wagon.capacity} т'
                })
                
            if estokada_movement.target_wagon:
                context['estokada_history'].append({
                    'timestamp': sale.movement.date,
                    'action': 'Назначение - вагон',
                    'details': f'Номер: {estokada_movement.target_wagon.number}, Ёмкость: {estokada_movement.target_wagon.capacity} т'
                })
            
            # Добавляем информацию о весе, температуре и плотности
            context['estokada_history'].append({
                'timestamp': sale.movement.date,
                'action': 'Информация о грузе',
                'details': f'Вес по документам: {estokada_movement.document_weight/1000:.2f} т, Фактический вес: {estokada_movement.actual_weight/1000:.2f} т, Разница: {estokada_movement.weight_difference/1000:.2f} т'
            })
            
            if estokada_movement.temperature:
                context['estokada_history'].append({
                    'timestamp': sale.movement.date,
                    'action': 'Параметры груза',
                    'details': f'Температура: {estokada_movement.temperature}°C, Плотность: {estokada_movement.density or "Н/Д"}'
                })
                
        except EstokadaMovement.DoesNotExist:
            context['estokada_movement'] = None
            context['estokada_history'] = []
            context['error_message'] = 'Нет связанной записи в эстокаде'
            
        return context

@method_decorator(sales_required, name='dispatch')
class ReceiveCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания операции приемки"""
    model = SalesMovement
    form_class = SalesMovementForm
    template_name = 'sales/sales_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание операции приемки'
        context['operation_type'] = 'receive'
        return context
    
    def get_initial(self):
        return {'movement_type': 'in'}
        
    def form_valid(self, form):
        # Установка текущего пользователя как создателя
        sale = form.save(commit=False)
        if hasattr(sale, 'created_by') and not sale.created_by:
            sale.created_by = self.request.user
        
        # Создаем запись типа "приемка" (in)
        sale.movement.movement_type = 'in'
        sale.movement.save()
        
        # Сохраняем объект Sales
        response = super().form_valid(form)
        
        messages.success(self.request, "Операция приемки успешно создана")
        return response
    
    def get_success_url(self):
        return reverse_lazy('sales:sales_detail', kwargs={'pk': self.object.pk})

@method_decorator(sales_required, name='dispatch')
class TransferCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания операции перемещения"""
    model = SalesMovement
    form_class = SalesMovementForm
    template_name = 'sales/sales_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание операции перемещения'
        context['operation_type'] = 'transfer'
        return context
    
    def get_initial(self):
        return {'movement_type': 'transfer'}
        
    def form_valid(self, form):
        # Установка текущего пользователя как создателя
        sale = form.save(commit=False)
        if hasattr(sale, 'created_by') and not sale.created_by:
            sale.created_by = self.request.user
        
        # Создаем запись типа "перемещение" (transfer)
        sale.movement.movement_type = 'transfer'
        sale.movement.save()
        
        # Сохраняем объект Sales
        response = super().form_valid(form)
        
        messages.success(self.request, "Операция перемещения успешно создана")
        return response
    
    def get_success_url(self):
        return reverse_lazy('sales:sales_detail', kwargs={'pk': self.object.pk})

@method_decorator(sales_required, name='dispatch')
class ProductionCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания операции производства"""
    model = SalesMovement
    form_class = SalesMovementForm
    template_name = 'sales/sales_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание операции производства'
        context['operation_type'] = 'production'
        return context
    
    def get_initial(self):
        return {'movement_type': 'production'}
        
    def form_valid(self, form):
        # Установка текущего пользователя как создателя
        sale = form.save(commit=False)
        if hasattr(sale, 'created_by') and not sale.created_by:
            sale.created_by = self.request.user
        
        # Создаем запись типа "производство" (production)
        sale.movement.movement_type = 'production'
        sale.movement.save()
        
        # Сохраняем объект Sales
        response = super().form_valid(form)
        
        messages.success(self.request, "Операция производства успешно создана")
        return response
    
    def get_success_url(self):
        return reverse_lazy('sales:sales_detail', kwargs={'pk': self.object.pk})

@method_decorator(sales_required, name='dispatch')
class PendingEstokadaListView(LoginRequiredMixin, ListView):
    """Представление для просмотра заказов, ожидающих обработки эстокадой"""
    template_name = 'sales/pending_estokada_list.html'
    context_object_name = 'pending_orders'
    
    def get_queryset(self):
        # Получаем все записи Sales
        sales_movements = SalesMovement.objects.select_related(
            'movement', 'movement__product', 'client'
        )
        
        # Исключаем те, которые уже обработаны эстокадой
        processed_movements = EstokadaMovement.objects.values_list('movement_id', flat=True)
        return sales_movements.exclude(movement_id__in=processed_movements).order_by('-movement__date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Заказы, ожидающие обработки эстокадой'
        
        # Группируем по типу движения
        type_counts = {}
        for order in context['pending_orders']:
            movement_type = order.movement.movement_type
            if movement_type not in type_counts:
                type_counts[movement_type] = 0
            type_counts[movement_type] += 1
        
        context['type_counts'] = type_counts
        return context

@method_decorator(sales_required, name='dispatch')
class ContractDetailView(LoginRequiredMixin, DetailView):
    """Представление детальной информации о контракте"""
    template_name = 'sales/contract_detail.html'
    context_object_name = 'contract'
    model = SalesContract
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.object
        
        # Продукты по контракту
        context['contract_products'] = contract.products.all().select_related('product')
        
        # Продажи, связанные с этим контрактом
        context['related_sales'] = SalesMovement.objects.filter(
            contract_number=contract.contract_number
        ).select_related('movement', 'client', 'movement__product').order_by('-movement__date')
        
        # Вычисление выполнения контракта по каждому продукту
        contract_products = {}
        for cp in context['contract_products']:
            contract_products[cp.product_id] = {
                'name': cp.product.name,
                'contracted_quantity': cp.quantity,
                'delivered_quantity': 0,
                'remaining_quantity': cp.quantity,
                'completion_percent': 0
            }
        
        # Подсчет уже доставленного количества
        for sale in context['related_sales']:
            product_id = sale.movement.product_id
            if product_id in contract_products:
                quantity = sale.movement.quantity
                contract_products[product_id]['delivered_quantity'] += quantity
                contract_products[product_id]['remaining_quantity'] = max(
                    0, contract_products[product_id]['contracted_quantity'] - contract_products[product_id]['delivered_quantity']
                )
                # Вычисление процента выполнения
                if contract_products[product_id]['contracted_quantity'] > 0:
                    contract_products[product_id]['completion_percent'] = min(
                        100,
                        (contract_products[product_id]['delivered_quantity'] / contract_products[product_id]['contracted_quantity']) * 100
                    )
        
        context['contract_fulfillment'] = list(contract_products.values())
        
        # Общий процент выполнения контракта
        total_contracted = sum(cp.quantity for cp in context['contract_products'])
        total_delivered = sum(sale.movement.quantity for sale in context['related_sales'])
        
        context['overall_completion'] = 0
        if total_contracted > 0:
            context['overall_completion'] = min(100, (total_delivered / total_contracted) * 100)
        
        return context

@method_decorator(sales_required, name='dispatch')
class SalesChartDataView(LoginRequiredMixin, View):
    """API для получения данных для графиков"""
    
    def get(self, request, *args, **kwargs):
        chart_type = request.GET.get('type', 'sales')
        period = request.GET.get('period', 'week')
        
        today = timezone.now().date()
        
        # Определение периода
        if period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'quarter':
            start_date = today - timedelta(days=90)
        else:
            start_date = today - timedelta(days=7)
            
        # Получение данных в зависимости от типа графика
        if chart_type == 'sales':
            # Данные по продажам
            sales_data = SalesMovement.objects.filter(
                movement__date__gte=start_date,
                movement__date__lte=today
            ).values('movement__date').annotate(
                quantity=Sum('movement__quantity')
            ).order_by('movement__date')
            
            dates = []
            quantities = []
            
            # Форматирование данных для графика
            for item in sales_data:
                dates.append(item['movement__date'].strftime('%d.%m'))
                quantities.append(float(item['quantity']))
                
            return JsonResponse({
                'dates': dates,
                'quantities': quantities
            })
            
        elif chart_type == 'products':
            # Данные по продуктам
            product_data = SalesMovement.objects.filter(
                movement__date__gte=start_date,
                movement__date__lte=today
            ).values('movement__product__name').annotate(
                quantity=Sum('movement__quantity')
            ).order_by('-quantity')[:5]
            
            labels = []
            data = []
            
            # Форматирование данных для графика
            for item in product_data:
                labels.append(item['movement__product__name'])
                data.append(float(item['quantity']))
                
            return JsonResponse({
                'labels': labels,
                'data': data
            })
            
        return JsonResponse({'error': 'Invalid chart type'}, status=400)

# Представления для управления заказами
@method_decorator(sales_required, name='dispatch')
class OrderDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление заказа
    """
    model = Order
    template_name = 'sales/order_confirm_delete.html'
    success_url = reverse_lazy('sales:order_list')
    
    def delete(self, request, *args, **kwargs):
        order = self.get_object()
        messages.success(self.request, f'Заказ №{order.order_number} успешно удален.')
        return super().delete(request, *args, **kwargs)
    
    def get_queryset(self):
        # Запрещаем удаление заказов, которые не находятся в статусе ожидания
        return Order.objects.filter(delivery_status='pending')


@method_decorator(sales_required, name='dispatch')
class OrderItemCreateView(LoginRequiredMixin, CreateView):
    """
    Добавление товарной позиции в заказ
    """
    model = OrderItem
    form_class = OrderItemForm
    template_name = 'sales/order_item_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        self.order = get_object_or_404(Order, pk=self.kwargs['order_id'])
        initial['order'] = self.order
        return initial
    
    def form_valid(self, form):
        form.instance.order = self.order
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.order
        context['title'] = 'Добавление товарной позиции'
        return context
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.order.pk})


@method_decorator(sales_required, name='dispatch')
class OrderItemUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование товарной позиции заказа
    """
    model = OrderItem
    form_class = OrderItemForm
    template_name = 'sales/order_item_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.object.order
        context['title'] = 'Редактирование товарной позиции'
        return context
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.order.pk})


@method_decorator(sales_required, name='dispatch')
class OrderItemDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление товарной позиции заказа
    """
    model = OrderItem
    template_name = 'sales/order_item_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.order.pk})
    
    def delete(self, request, *args, **kwargs):
        item = self.get_object()
        order = item.order
        messages.success(request, f'Товарная позиция {item.product} успешно удалена.')
        response = super().delete(request, *args, **kwargs)
        # Обновляем общую сумму заказа после удаления позиции
        order.update_total_amount()
        return response


@method_decorator(sales_required, name='dispatch')
class PaymentCreateView(LoginRequiredMixin, CreateView):
    """
    Добавление платежа к заказу
    """
    model = Payment
    form_class = PaymentForm
    template_name = 'sales/payment_form.html'
    
    def get_initial(self):
        initial = super().get_initial()
        self.order = get_object_or_404(Order, pk=self.kwargs['order_id'])
        initial['order'] = self.order
        # Предлагаем оставшуюся сумму к оплате как сумму платежа
        remaining = self.order.total_amount - self.order.paid_amount if self.order.total_amount else 0
        if remaining > 0:
            initial['amount'] = remaining
        return initial
    
    def form_valid(self, form):
        form.instance.order = self.order
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.order
        context['title'] = 'Добавление платежа'
        return context
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.order.pk})


@method_decorator(sales_required, name='dispatch')
class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    """
    Редактирование платежа
    """
    model = Payment
    form_class = PaymentForm
    template_name = 'sales/payment_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order'] = self.object.order
        context['title'] = 'Редактирование платежа'
        return context
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.order.pk})


@method_decorator(sales_required, name='dispatch')
class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление платежа
    """
    model = Payment
    template_name = 'sales/payment_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.order.pk})
    
    def delete(self, request, *args, **kwargs):
        payment = self.get_object()
        order = payment.order
        messages.success(request, f'Платеж №{payment.payment_number} успешно удален.')
        response = super().delete(request, *args, **kwargs)
        # Обновляем статус оплаты заказа
        total_paid = Payment.objects.filter(order=order, status='completed').aggregate(
            total=Sum('amount'))['total'] or 0
        order.paid_amount = total_paid
        if total_paid >= order.total_amount:
            order.payment_status = 'paid'
        elif total_paid > 0:
            order.payment_status = 'partial'
        else:
            order.payment_status = 'pending'
        order.save(update_fields=['paid_amount', 'payment_status'])
        return response


@sales_required
def get_client_contracts(request):
    """
    AJAX-представление для получения контрактов клиента
    """
    client_id = request.GET.get('client_id')
    contracts = []
    
    if client_id:
        contracts_qs = SalesContract.objects.filter(client_id=client_id, status='active')
        contracts = [{'id': contract.id, 'text': f"{contract.contract_number} ({contract.start_date} - {contract.end_date})"} 
                    for contract in contracts_qs]
    
    return JsonResponse({'contracts': contracts})


@sales_required
def get_product_price(request):
    """
    AJAX-представление для получения последней цены продукта
    """
    product_id = request.GET.get('product_id')
    price = None
    
    if product_id:
        # Ищем последнюю продажу с этим продуктом, у которой указана цена
        last_sale = SalesMovement.objects.filter(
            movement__product_id=product_id, 
            price_per_unit__isnull=False
        ).order_by('-movement__date').first()
        
        if last_sale:
            price = float(last_sale.price_per_unit)
    
    return JsonResponse({'price': price})

class ReceptionCreateView(LoginRequiredMixin, CreateView):
    model = Movement
    template_name = 'sales/reception_form.html'
    form_class = MovementForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'].initial = {
            'movement_type': 'reception',
            'date': timezone.now().date(),
            'document_number': generate_document_number('REC')
        }
        context['reservoirs'] = Reservoir.objects.all()
        context['wagons'] = Wagon.objects.all()
        context['wagon_types'] = WagonType.objects.all()
        return context
    
    def form_valid(self, form):
        form.instance.movement_type = 'reception'
        form.instance.created_by = self.request.user
        
        # Получаем данные о транспорте из JSON
        transports_json = self.request.POST.get('transports_json', '[]')
        if not transports_json:
            messages.error(self.request, 'Необходимо добавить хотя бы один транспорт')
            return self.form_invalid(form)
        
        transports_data = json.loads(transports_json)
        
        # Получаем данные о размещении
        placement_type = self.request.POST.get('placement_type')
        if placement_type == 'reservoir':
            reservoir_id = self.request.POST.get('reservoir')
            if not reservoir_id:
                messages.error(self.request, 'Выберите резервуар для размещения товара')
                return self.form_invalid(form)
        elif placement_type == 'wagon':
            wagon_id = self.request.POST.get('wagon')
            if not wagon_id:
                messages.error(self.request, 'Выберите вагон для размещения товара')
                return self.form_invalid(form)
        
        try:
            with transaction.atomic():
                # Сохраняем основную запись движения
                movement = form.save()
                
                # Создаем записи о транспорте
                total_quantity = 0
                for transport_data in transports_data:
                    transport = Transport.objects.create(
                        movement=movement,
                        transport_type=transport_data.get('transport_type'),
                        transport_number=transport_data.get('transport_number'),
                        quantity=transport_data.get('quantity'),
                        doc_ton=transport_data.get('doc_ton', 0)
                    )
                    
                    # Для автомобильного транспорта
                    if transport_data.get('transport_type') == 'truck':
                        transport.density = transport_data.get('density', 0)
                        transport.temperature = transport_data.get('temperature', 20)
                        transport.liter = transport_data.get('liter', 0)
                    
                    # Для железнодорожного транспорта
                    elif transport_data.get('transport_type') == 'wagon':
                        if transport_data.get('wagon_type'):
                            transport.wagon_type_id = transport_data.get('wagon_type')
                        transport.capacity = transport_data.get('capacity', 0)
                        transport.tare_weight = transport_data.get('tare_weight', 0)
                    
                    transport.save()
                    total_quantity += float(transport_data.get('quantity', 0))
                
                # Обновляем общее количество
                movement.quantity = total_quantity
                movement.save()
                
                # Обрабатываем размещение товара
                if placement_type == 'reservoir':
                    reservoir = Reservoir.objects.get(id=reservoir_id)
                    reservoir.current_quantity += total_quantity
                    reservoir.save()
                    
                    # Создаем запись о движении резервуара
                    ReservoirMovement.objects.create(
                        reservoir=reservoir,
                        movement=movement,
                        quantity=total_quantity,
                        operation_type='in'
                    )
                elif placement_type == 'wagon':
                    wagon = Wagon.objects.get(id=wagon_id)
                    wagon.current_quantity += total_quantity
                    wagon.save()
                    
                    # Создаем запись о размещении в вагоне
                    Placement.objects.create(
                        wagon=wagon,
                        movement=movement,
                        quantity=total_quantity,
                        operation_type='in'
                    )
                
                # Обновляем инвентарь продукта
                product = form.cleaned_data['product']
                inventory, created = Inventory.objects.get_or_create(product=product)
                inventory.quantity += total_quantity
                inventory.save()
                
                messages.success(self.request, f'Приемка успешно создана. Принято {total_quantity} кг продукта.')
                
                return redirect('sales:movement_list')
                
        except Exception as e:
            messages.error(self.request, f'Ошибка при создании приемки: {str(e)}')
            return self.form_invalid(form)


class MovementListView(LoginRequiredMixin, ListView):
    model = Movement
    template_name = 'sales/movement_list.html'
    context_object_name = 'movements'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-date', '-id')
        
        # Фильтрация по типу движения
        movement_type = self.request.GET.get('type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        # Фильтрация по продукту
        product_id = self.request.GET.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Фильтрация по дате
        date_from = self.request.GET.get('date_from')
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=date_from)
            except ValueError:
                pass
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=date_to)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        context['movement_types'] = Movement.MOVEMENT_TYPES
        
        # Сохраняем параметры фильтрации для пагинации
        context['current_type'] = self.request.GET.get('type', '')
        context['current_product'] = self.request.GET.get('product', '')
        context['current_date_from'] = self.request.GET.get('date_from', '')
        context['current_date_to'] = self.request.GET.get('date_to', '')
        
        return context

# Добавьте сюда дополнительные представления по мере необходимости
