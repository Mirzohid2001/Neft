from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, DecimalField
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal
from apps.accounts.views import infrastructure_required
from .models import (
    Product, Receiving, Giving, Stock,
    CanteenExpense, Project, ProjectItem
)
from .forms import (
    ProductForm, ReceivingForm, GivingForm,
    CanteenExpenseForm, ProjectForm, ProjectItemForm
)
import json
from django.db.models.deletion import ProtectedError
from django.db.models.fields.json import JSONField
from django.db.models.fields.related import (
    ForeignKey, ManyToManyField, OneToOneField
)
from django.db import models

@login_required
@infrastructure_required
def dashboard(request):
    # Get today's date
    today = timezone.now().date()
    
    # Get daily expenses - calculate total_cost as quantity * unit_price
    daily_expenses = CanteenExpense.objects.filter(date=today).annotate(
        item_cost=models.F('quantity') * models.F('unit_price')
    ).aggregate(total=Sum('item_cost'))['total'] or 0
    
    # Get total stock value - calculate as quantity * product__unit_price
    stocks = Stock.objects.select_related('product').all()
    total_stock_value = sum(stock.quantity * stock.product.unit_price for stock in stocks)
    
    # Get project summaries
    projects = Project.objects.all()
    
    return render(request, 'infrastruction/dashboard.html', {
        'daily_expenses': daily_expenses,
        'total_stock_value': total_stock_value,
        'projects': projects
    })

@login_required
@infrastructure_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'infrastruction/product_list.html', {
        'products': products,
        'title': 'Список продуктов'
    })

@login_required
@infrastructure_required
def product_add(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Продукт успешно добавлен.')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'infrastruction/product_form.html', {
        'form': form,
        'title': 'Добавить продукт'
    })

@login_required
@infrastructure_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Продукт успешно обновлен.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'infrastruction/product_form.html', {
        'form': form,
        'title': 'Редактировать продукт'
    })

@login_required
@infrastructure_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
        messages.success(request, 'Продукт успешно удален.')
    except ProtectedError:
        messages.error(request, 'Невозможно удалить продукт, так как он используется в других записях.')
    return redirect('product_list')

@login_required
@infrastructure_required
def receiving_list(request):
    receivings = Receiving.objects.all().order_by('-date')
    return render(request, 'infrastruction/receiving_list.html', {
        'receivings': receivings,
        'title': 'Список приходов'
    })

@login_required
@infrastructure_required
def receiving_form(request):
    if request.method == 'POST':
        form = ReceivingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    receiving = form.save(commit=False)
                    receiving.created_by = request.user
                    receiving.save()

                    # Get or create product
                    product_name = form.cleaned_data['product_name']
                    product, created = Product.objects.get_or_create(
                        name=product_name,
                        defaults={
                            'unit': form.cleaned_data.get('unit', 'шт'),
                            'unit_price': form.cleaned_data['unit_price']
                        }
                    )

                    # Update stock
                    stock, created = Stock.objects.get_or_create(
                        product=product,
                        defaults={'quantity': form.cleaned_data['quantity']}
                    )
                    if not created:
                        stock.quantity += form.cleaned_data['quantity']
                        stock.save()

                    messages.success(request, 'Приход успешно добавлен.')
                    return redirect('receiving_list')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {str(e)}')
    else:
        form = ReceivingForm(initial={'date': timezone.now().date()})
    
    return render(request, 'infrastruction/receiving_form.html', {
        'form': form,
        'title': 'Добавить приход'
    })

# Alias for receiving_form to match URL pattern
receiving_add = receiving_form

@login_required
@infrastructure_required
def receiving_detail(request, pk):
    receiving = get_object_or_404(Receiving, pk=pk)
    return render(request, 'infrastruction/receiving_detail.html', {
        'receiving': receiving,
        'title': f'Приход #{receiving.pk}'
    })

@login_required
@infrastructure_required
def receiving_edit(request, pk):
    receiving = get_object_or_404(Receiving, pk=pk)
    if request.method == 'POST':
        form = ReceivingForm(request.POST, instance=receiving)
        if form.is_valid():
            try:
                with transaction.atomic():
                    receiving = form.save(commit=False)
                    receiving.save()

                    # Update stock if quantity changed
                    if 'quantity' in form.changed_data:
                        old_quantity = form.initial['quantity']
                        new_quantity = form.cleaned_data['quantity']
                        quantity_diff = new_quantity - old_quantity
                        
                        stock = Stock.objects.get(product=receiving.product)
                        stock.quantity += quantity_diff
                        stock.save()

                    messages.success(request, 'Приход успешно обновлен.')
                    return redirect('receiving_list')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {str(e)}')
    else:
        form = ReceivingForm(instance=receiving)
    
    return render(request, 'infrastruction/receiving_form.html', {
        'form': form,
        'title': 'Редактировать приход'
    })

@login_required
@infrastructure_required
def receiving_delete(request, pk):
    receiving = get_object_or_404(Receiving, pk=pk)
    try:
        with transaction.atomic():
            # Update stock quantity
            stock = Stock.objects.get(product=receiving.product)
            stock.quantity -= receiving.quantity
            stock.save()
            
            # Delete the receiving record
            receiving.delete()
            
            messages.success(request, 'Приход успешно удален.')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении: {str(e)}')
    
    return redirect('receiving_list')

@login_required
@infrastructure_required
def canteen_expenses_list(request):
    expenses = CanteenExpense.objects.all().order_by('-date')
    return render(request, 'infrastruction/canteen_expenses_list.html', {
        'expenses': expenses,
        'title': 'Расходы столовой'
    })

@login_required
@infrastructure_required
def canteen_expense_add(request):
    if request.method == 'POST':
        form = CanteenExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, 'Расход успешно добавлен.')
            return redirect('canteen_expenses_list')
    else:
        form = CanteenExpenseForm(initial={'date': timezone.now().date()})
    
    return render(request, 'infrastruction/canteen_expense_form.html', {
        'form': form,
        'title': 'Добавить расход'
    })

@login_required
@infrastructure_required
def canteen_expense_edit(request, pk):
    expense = get_object_or_404(CanteenExpense, pk=pk)
    if request.method == 'POST':
        form = CanteenExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Расход успешно обновлен.')
            return redirect('canteen_expenses_list')
    else:
        form = CanteenExpenseForm(instance=expense)
    
    return render(request, 'infrastruction/canteen_expense_form.html', {
        'form': form,
        'title': 'Редактировать расход'
    })

@login_required
@infrastructure_required
def canteen_expense_detail(request, pk):
    expense = get_object_or_404(CanteenExpense, pk=pk)
    return render(request, 'infrastruction/canteen_expense_detail.html', {
        'expense': expense,
        'title': f'Расход #{expense.pk}'
    })

@login_required
@infrastructure_required
def canteen_expense_delete(request, pk):
    expense = get_object_or_404(CanteenExpense, pk=pk)
    try:
        expense.delete()
        messages.success(request, 'Расход столовой успешно удален.')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении: {str(e)}')
    return redirect('canteen_expenses_list')

@login_required
@infrastructure_required
def project_list(request):
    projects = Project.objects.all().order_by('-start_date')
    return render(request, 'infrastruction/project_list.html', {
        'projects': projects,
        'title': 'Проекты'
    })

@login_required
@infrastructure_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render(request, 'infrastruction/project_detail.html', {
        'project': project,
        'title': project.name
    })

@login_required
@infrastructure_required
def project_add(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, 'Проект успешно создан.')
            return redirect('project_list')
    else:
        form = ProjectForm()
    
    return render(request, 'infrastruction/project_form.html', {
        'form': form,
        'title': 'Создать проект'
    })

@login_required
@infrastructure_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Проект успешно обновлен.')
            return redirect('project_list')
    else:
        form = ProjectForm(instance=project)
    
    return render(request, 'infrastruction/project_form.html', {
        'form': form,
        'title': 'Редактировать проект'
    })

@login_required
@infrastructure_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    try:
        project.delete()
        messages.success(request, 'Проект успешно удален.')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении проекта: {str(e)}')
    
    return redirect('project_list')

@login_required
@infrastructure_required
def project_item_add(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.method == 'POST':
        form = ProjectItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.project = project
            item.save()
            messages.success(request, 'Элемент проекта успешно добавлен.')
            return redirect('project_detail', pk=project_pk)
    else:
        form = ProjectItemForm()
    
    return render(request, 'infrastruction/project_item_form.html', {
        'form': form,
        'project': project,
        'title': 'Добавить элемент проекта'
    })

@login_required
@infrastructure_required
def project_item_edit(request, project_pk, item_pk):
    project = get_object_or_404(Project, pk=project_pk)
    item = get_object_or_404(ProjectItem, pk=item_pk, project=project)
    if request.method == 'POST':
        form = ProjectItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Элемент проекта успешно обновлен.')
            return redirect('project_detail', pk=project_pk)
    else:
        form = ProjectItemForm(instance=item)
    
    return render(request, 'infrastruction/project_item_form.html', {
        'form': form,
        'project': project,
        'title': 'Редактировать элемент проекта'
    })

@login_required
@infrastructure_required
def project_item_delete(request, project_pk, item_pk):
    project = get_object_or_404(Project, pk=project_pk)
    item = get_object_or_404(ProjectItem, pk=item_pk, project=project)
    item.delete()
    messages.success(request, 'Элемент проекта успешно удален.')
    return redirect('project_detail', pk=project_pk)

@login_required
@infrastructure_required
def giving_list(request):
    givings = Giving.objects.all().order_by('-date')
    return render(request, 'infrastruction/giving_list.html', {
        'givings': givings,
        'title': 'Список расходов'
    })

@login_required
@infrastructure_required
def giving_add(request):
    if request.method == 'POST':
        form = GivingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    giving = form.save(commit=False)
                    giving.created_by = request.user
                    
                    # Check stock availability
                    product = form.cleaned_data['product']
                    quantity = form.cleaned_data['quantity']
                    
                    try:
                        stock = Stock.objects.get(product=product)
                        if stock.quantity < quantity:
                            messages.error(request, f'Недостаточно {product.name} на складе. Доступно: {stock.quantity} {product.unit}')
                            return render(request, 'infrastruction/giving_form.html', {
                                'form': form,
                                'title': 'Добавить расход'
                            })
                            
                        # Update stock
                        stock.quantity -= quantity
                        stock.save()
                        
                    except Stock.DoesNotExist:
                        messages.error(request, f'Продукт {product.name} отсутствует на складе.')
                        return render(request, 'infrastruction/giving_form.html', {
                            'form': form,
                            'title': 'Добавить расход'
                        })
                    
                    giving.save()
                    messages.success(request, 'Расход успешно добавлен.')
                    return redirect('giving_list')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {str(e)}')
    else:
        form = GivingForm(initial={'date': timezone.now().date()})
    
    return render(request, 'infrastruction/giving_form.html', {
        'form': form,
        'title': 'Добавить расход'
    })

@login_required
@infrastructure_required
def giving_detail(request, pk):
    giving = get_object_or_404(Giving, pk=pk)
    return render(request, 'infrastruction/giving_detail.html', {
        'giving': giving,
        'title': f'Расход #{giving.pk}'
    })

@login_required
@infrastructure_required
def giving_edit(request, pk):
    giving = get_object_or_404(Giving, pk=pk)
    if request.method == 'POST':
        form = GivingForm(request.POST, instance=giving)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Check if quantity changed
                    if 'quantity' in form.changed_data or 'product' in form.changed_data:
                        # Revert old quantity
                        old_product = giving.product
                        old_quantity = giving.quantity
                        old_stock = Stock.objects.get(product=old_product)
                        old_stock.quantity += old_quantity
                        old_stock.save()
                        
                        # Apply new quantity
                        new_product = form.cleaned_data['product']
                        new_quantity = form.cleaned_data['quantity']
                        
                        # If product changed, we need to update the new product's stock
                        if 'product' in form.changed_data:
                            new_stock = Stock.objects.get(product=new_product)
                        else:
                            new_stock = old_stock
                            
                        # Check if enough stock available
                        if new_stock.quantity < new_quantity:
                            # Rollback the old stock change
                            old_stock.quantity -= old_quantity
                            old_stock.save()
                            
                            messages.error(request, f'Недостаточно {new_product.name} на складе. Доступно: {new_stock.quantity} {new_product.unit}')
                            return render(request, 'infrastruction/giving_form.html', {
                                'form': form,
                                'title': 'Редактировать расход'
                            })
                            
                        # Update new stock
                        new_stock.quantity -= new_quantity
                        new_stock.save()
                    
                    giving = form.save()
                    messages.success(request, 'Расход успешно обновлен.')
                    return redirect('giving_list')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении: {str(e)}')
    else:
        form = GivingForm(instance=giving)
    
    return render(request, 'infrastruction/giving_form.html', {
        'form': form,
        'title': 'Редактировать расход'
    })

@login_required
@infrastructure_required
def giving_delete(request, pk):
    giving = get_object_or_404(Giving, pk=pk)
    try:
        with transaction.atomic():
            # Return the quantity to stock
            stock = Stock.objects.get(product=giving.product)
            stock.quantity += giving.quantity
            stock.save()
            
            # Delete the giving record
            giving.delete()
            
            messages.success(request, 'Расход успешно удален.')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении: {str(e)}')
    
    return redirect('giving_list')

@login_required
@infrastructure_required
def stock_list(request):
    stocks = Stock.objects.all().select_related('product').order_by('product__name')
    total_value = sum(stock.total_value for stock in stocks)
    
    return render(request, 'infrastruction/stock_list.html', {
        'stocks': stocks,
        'total_value': total_value,
        'title': 'Склад'
    })

@login_required
@infrastructure_required
def canteen_monthly_report(request):
    # Get the current month and year or use GET parameters
    now = timezone.now()
    year = int(request.GET.get('year', now.year))
    month = int(request.GET.get('month', now.month))
    
    # Create date range for the selected month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # Get all expenses for the selected month
    expenses = CanteenExpense.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Calculate totals
    total_cost = expenses.aggregate(total=Sum('total_cost'))['total'] or 0
    
    # Group expenses by product name
    product_totals = {}
    for expense in expenses:
        product_name = expense.product_name
        if product_name not in product_totals:
            product_totals[product_name] = 0
        product_totals[product_name] += expense.total_cost
    
    # Convert to list for the template
    product_summary = [
        {'name': name, 'total': total} 
        for name, total in product_totals.items()
    ]
    # Sort by total cost (descending)
    product_summary.sort(key=lambda x: x['total'], reverse=True)
    
    # Get available months for the dropdown
    year_month_pairs = CanteenExpense.objects.dates('date', 'month')
    available_months = [
        (pair.year, pair.month) for pair in year_month_pairs
    ]
    
    context = {
        'expenses': expenses,
        'total_cost': total_cost,
        'product_summary': product_summary,
        'year': year,
        'month': month,
        'month_name': start_date.strftime('%B'),
        'available_months': available_months,
        'title': f'Отчет за {start_date.strftime("%B %Y")}'
    }
    
    return render(request, 'infrastruction/canteen_monthly_report.html', context)

# ... rest of the views ... 