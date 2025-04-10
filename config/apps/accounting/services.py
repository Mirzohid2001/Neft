from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import uuid

from apps.warehouse.models import Movement, LocalMovement, ReservoirMovement, Client, Supplier, Product
from .models import (
    FinancialRecord, JournalEntry, Transaction, Account, AccountCategory,
    Invoice, InvoiceItem, Payment, FinancialSetting
)

def create_financial_records(date_from=None, date_to=None):
    """Создает финансовые записи на основе операций склада за указанный период.
    Если период не указан, обрабатываются все операции."""
    # Очищаем существующие записи, если нужно полное пересоздание
    FinancialRecord.objects.all().delete()

    filters = Q()
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)

    # Обработка Movement (основные операции)
    movements = Movement.objects.filter(filters)
    for move in movements:
        # Выбираем источник и назначение для определения склада
        warehouse = None
        if move.source_warehouse:
            warehouse = move.source_warehouse
        elif move.target_warehouse:
            warehouse = move.target_warehouse
            
        FinancialRecord.objects.create(
            product=move.product,
            warehouse=warehouse,
            date=move.date,
            movement_type=move.movement_type,
            quantity=move.quantity,
            total_price_sum=move.quantity * (move.product.price_sum or 0),
            total_price_usd=move.quantity * (move.product.price_usd or 0)
        )

    # Обработка LocalMovement (локальные операции)
    local_moves = LocalMovement.objects.filter(filters)
    for lmove in local_moves:
        FinancialRecord.objects.create(
            product=lmove.product,
            warehouse=None,  # Локальные движения могут не иметь склада
            date=lmove.date,
            movement_type=lmove.movement_type,
            quantity=lmove.quantity,
            total_price_sum=lmove.quantity * (lmove.product.price_sum or 0),
            total_price_usd=lmove.quantity * (lmove.product.price_usd or 0)
        )
        
    # Обработка ReservoirMovement (операции резервуаров)
    reservoir_moves = ReservoirMovement.objects.filter(filters)
    for rmove in reservoir_moves:
        FinancialRecord.objects.create(
            product=rmove.product,
            warehouse=rmove.reservoir.warehouse if rmove.reservoir else None,
            date=rmove.date,
            movement_type=rmove.movement_type,
            quantity=rmove.quantity,
            total_price_sum=rmove.quantity * (rmove.product.price_sum or 0),
            total_price_usd=rmove.quantity * (rmove.product.price_usd or 0)
        )

def calculate_summary(date_from=None, date_to=None):
    """Рассчитывает финансовый итог за указанный период"""
    filters = Q()
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)
        
    total_in_sum = FinancialRecord.objects.filter(filters, movement_type='in').aggregate(
        Sum('total_price_sum'))['total_price_sum__sum'] or 0
    total_out_sum = FinancialRecord.objects.filter(filters, movement_type='out').aggregate(
        Sum('total_price_sum'))['total_price_sum__sum'] or 0

    net_profit_loss = total_in_sum - total_out_sum
    status = 'Прибыль' if net_profit_loss >= 0 else 'Убыток'

    # Дополнительная информация
    total_in_usd = FinancialRecord.objects.filter(filters, movement_type='in').aggregate(
        Sum('total_price_usd'))['total_price_usd__sum'] or 0
    total_out_usd = FinancialRecord.objects.filter(filters, movement_type='out').aggregate(
        Sum('total_price_usd'))['total_price_usd__sum'] or 0
    net_profit_loss_usd = total_in_usd - total_out_usd

    # Количество операций
    total_operations = FinancialRecord.objects.filter(filters).count()
    in_operations = FinancialRecord.objects.filter(filters, movement_type='in').count()
    out_operations = FinancialRecord.objects.filter(filters, movement_type='out').count()

    return {
        'total_in_sum': total_in_sum,
        'total_out_sum': total_out_sum,
        'total_in_usd': total_in_usd,
        'total_out_usd': total_out_usd,
        'net_profit_loss': net_profit_loss,
        'net_profit_loss_usd': net_profit_loss_usd,
        'status': status,
        'total_operations': total_operations,
        'in_operations': in_operations,
        'out_operations': out_operations,
    }

def generate_journal_entry_from_movement(movement, created_by=None):
    """Создает бухгалтерскую проводку на основе операции склада"""
    # Генерируем уникальный номер операции
    ref_number = f"MOV-{movement.id}-{uuid.uuid4().hex[:6]}"
    
    # Определяем тип операции для описания
    if movement.movement_type == 'in':
        description = f"Приемка товара: {movement.product.name}, кол-во: {movement.quantity}"
    elif movement.movement_type == 'out':
        description = f"Отгрузка товара: {movement.product.name}, кол-во: {movement.quantity}"
    elif movement.movement_type == 'production':
        description = f"Производство: {movement.product.name}, кол-во: {movement.quantity}"
    elif movement.movement_type == 'transfer':
        description = f"Перемещение: {movement.product.name}, кол-во: {movement.quantity}"
    else:
        description = f"Операция с товаром: {movement.product.name}, кол-во: {movement.quantity}"
    
    # Создаем проводку
    journal_entry = JournalEntry.objects.create(
        date=movement.date,
        reference_number=ref_number,
        status='draft',
        description=description,
        movement=movement,
        created_by=created_by
    )
    
    # Получаем настройки по умолчанию
    settings = FinancialSetting.get_settings()
    
    # Находим нужные счета в зависимости от типа операции
    try:
        if movement.movement_type == 'in':
            # Приход товара - дебет товары, кредит поставщики
            debit_account = Account.objects.get(code='1410')  # Товары на складе
            credit_account = Account.objects.get(code='6010')  # Счета к оплате поставщикам
        elif movement.movement_type == 'out':
            # Отгрузка товара - дебет себестоимость, кредит товары + дебет дебиторка, кредит выручка
            debit_account = Account.objects.get(code='9020')  # Себестоимость продаж
            credit_account = Account.objects.get(code='1410')  # Товары на складе
        elif movement.movement_type == 'production':
            # Производство - дебет готовая продукция, кредит сырье
            debit_account = Account.objects.get(code='1440')  # Готовая продукция
            credit_account = Account.objects.get(code='1415')  # Сырье и материалы
        elif movement.movement_type == 'transfer':
            # Перемещение - дебет товары (новое место), кредит товары (старое место)
            debit_account = Account.objects.get(code='1410')  # Товары на складе
            credit_account = Account.objects.get(code='1410')  # Товары на складе
        else:
            # По умолчанию
            debit_account = settings.default_debit_account
            credit_account = settings.default_credit_account
    except Account.DoesNotExist:
        # Если счета не найдены, используем настройки по умолчанию
        debit_account = settings.default_debit_account
        credit_account = settings.default_credit_account
        
    if not debit_account or not credit_account:
        # Если счета не настроены, создаем проводку без транзакций
        return journal_entry
    
    # Сумма операции
    amount = movement.quantity * (movement.product.price_sum or 0)
    
    # Создаем транзакции
    Transaction.objects.create(
        account=debit_account,
        date=movement.date,
        debit=amount,
        credit=0,
        description=f"Дебет по операции {ref_number}",
        journal_entry=journal_entry
    )
    
    Transaction.objects.create(
        account=credit_account,
        date=movement.date,
        debit=0,
        credit=amount,
        description=f"Кредит по операции {ref_number}",
        journal_entry=journal_entry
    )
    
    # Если это продажа, создаем дополнительные транзакции для выручки
    if movement.movement_type == 'out' and movement.price_sum:
        revenue = movement.quantity * movement.price_sum
        # Если есть прибыль, добавляем еще две проводки
        if revenue > amount:
            try:
                receivable_account = Account.objects.get(code='1210')  # Дебиторская задолженность
                revenue_account = Account.objects.get(code='9010')     # Выручка от продаж
                
                Transaction.objects.create(
                    account=receivable_account,
                    date=movement.date,
                    debit=revenue,
                    credit=0,
                    description=f"Дебиторская задолженность по операции {ref_number}",
                    journal_entry=journal_entry
                )
                
                Transaction.objects.create(
                    account=revenue_account,
                    date=movement.date,
                    debit=0,
                    credit=revenue,
                    description=f"Выручка по операции {ref_number}",
                    journal_entry=journal_entry
                )
            except Account.DoesNotExist:
                pass  # Пропускаем если счета не найдены
    
    return journal_entry

def generate_invoice_from_movement(movement, created_by=None):
    """Создает счет-фактуру на основе операции склада"""
    settings = FinancialSetting.get_settings()
    
    # Определяем тип счета
    if movement.movement_type == 'in':
        invoice_type = 'purchase'
    elif movement.movement_type == 'out':
        invoice_type = 'sales'
    else:
        return None  # Для других типов операций счета не создаем
    
    # Генерируем номер счета
    if invoice_type == 'sales':
        prefix = settings.invoice_prefix or 'INV'
        next_num = settings.next_invoice_number or 1
        invoice_number = f"{prefix}-{next_num:05d}"
        
        # Увеличиваем счетчик номеров
        settings.next_invoice_number = next_num + 1
        settings.save()
    else:
        # Для закупок используем другой формат
        invoice_number = f"PUR-{movement.id}-{datetime.now().strftime('%Y%m%d')}"
    
    # Определяем срок оплаты
    due_date = movement.date + timedelta(days=settings.default_payment_term)
    
    # Создаем счет
    invoice = Invoice.objects.create(
        invoice_type=invoice_type,
        number=invoice_number,
        date=movement.date,
        due_date=due_date,
        client=movement.client if invoice_type == 'sales' else None,
        supplier=movement.supplier if invoice_type == 'purchase' else None,
        movement=movement,
        status='draft',
        created_by=created_by
    )
    
    # Создаем позицию счета
    unit_price = movement.price_sum or movement.product.price_sum or 0
    
    # Получаем ставку налога по умолчанию
    tax_rate = 0
    if settings.default_tax_rate:
        tax_rate = settings.default_tax_rate.rate
    
    InvoiceItem.objects.create(
        invoice=invoice,
        product=movement.product,
        description=f"{movement.product.name} ({movement.date})",
        quantity=movement.quantity,
        unit_price=unit_price,
        tax_rate=tax_rate
    )
    
    # Рассчитываем итоги (сработает автоматически при сохранении позиции)
    invoice.calculate_totals()
    
    return invoice

def get_product_financial_report(product_id, date_from=None, date_to=None):
    """Получает финансовый отчет по конкретному продукту"""
    product = Product.objects.get(id=product_id)
    
    filters = Q(product_id=product_id)
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)
    
    records = FinancialRecord.objects.filter(filters)
    
    total_in_qty = records.filter(movement_type='in').aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_out_qty = records.filter(movement_type='out').aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    total_in_sum = records.filter(movement_type='in').aggregate(Sum('total_price_sum'))['total_price_sum__sum'] or 0
    total_out_sum = records.filter(movement_type='out').aggregate(Sum('total_price_sum'))['total_price_sum__sum'] or 0
    
    # Средняя цена
    avg_in_price = total_in_sum / total_in_qty if total_in_qty > 0 else 0
    avg_out_price = total_out_sum / total_out_qty if total_out_qty > 0 else 0
    
    # Текущий остаток
    current_qty = total_in_qty - total_out_qty
    current_value = current_qty * product.price_sum if product.price_sum else 0
    
    return {
        'product': product,
        'total_in_qty': total_in_qty,
        'total_out_qty': total_out_qty,
        'current_qty': current_qty,
        'total_in_sum': total_in_sum,
        'total_out_sum': total_out_sum,
        'avg_in_price': avg_in_price,
        'avg_out_price': avg_out_price,
        'current_value': current_value,
        'records': records
    }

def get_client_report(client_id, date_from=None, date_to=None):
    """Получает отчет по клиенту с историей операций и финансовыми показателями"""
    client = Client.objects.get(id=client_id)
    
    # Получаем все движения для клиента
    filters = Q(client=client)
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)
    
    movements = Movement.objects.filter(filters)
    
    # Получаем счета-фактуры
    invoices = Invoice.objects.filter(client=client)
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
    
    # Расчет общих сумм
    total_sales = movements.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_sales_amount = movements.aggregate(Sum('price_sum'))['price_sum__sum'] or 0
    
    # Получаем платежи
    payments = Payment.objects.filter(invoice__client=client)
    if date_from:
        payments = payments.filter(date__gte=date_from)
    if date_to:
        payments = payments.filter(date__lte=date_to)
    
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Дебиторская задолженность
    accounts_receivable = total_sales_amount - total_paid
    
    return {
        'client': client,
        'movements': movements,
        'invoices': invoices,
        'payments': payments,
        'total_sales': total_sales,
        'total_sales_amount': total_sales_amount,
        'total_paid': total_paid,
        'accounts_receivable': accounts_receivable
    }

def get_supplier_report(supplier_id, date_from=None, date_to=None):
    """Получает отчет по поставщику с историей операций и финансовыми показателями"""
    supplier = Supplier.objects.get(id=supplier_id)
    
    # Получаем все движения для поставщика
    filters = Q(supplier=supplier)
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)
    
    movements = Movement.objects.filter(filters)
    
    # Получаем счета-фактуры
    invoices = Invoice.objects.filter(supplier=supplier)
    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
    
    # Расчет общих сумм
    total_purchases = movements.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_purchases_amount = movements.aggregate(Sum('price_sum'))['price_sum__sum'] or 0
    
    # Получаем платежи
    payments = Payment.objects.filter(invoice__supplier=supplier)
    if date_from:
        payments = payments.filter(date__gte=date_from)
    if date_to:
        payments = payments.filter(date__lte=date_to)
    
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Кредиторская задолженность
    accounts_payable = total_purchases_amount - total_paid
    
    return {
        'supplier': supplier,
        'movements': movements,
        'invoices': invoices,
        'payments': payments,
        'total_purchases': total_purchases,
        'total_purchases_amount': total_purchases_amount,
        'total_paid': total_paid,
        'accounts_payable': accounts_payable
    }

def create_initial_accounts():
    """Создает начальные бухгалтерские счета, если они не существуют"""
    # Создаем категории счетов
    categories = {
        'asset': ('1000', 'Активы'),
        'liability': ('2000', 'Обязательства'),
        'equity': ('3000', 'Капитал'),
        'income': ('9000', 'Доходы'),
        'expense': ('8000', 'Расходы'),
    }
    
    category_objects = {}
    for cat_type, (code, name) in categories.items():
        cat, created = AccountCategory.objects.get_or_create(
            code=code,
            defaults={'name': name, 'type': cat_type}
        )
        category_objects[cat_type] = cat
    
    # Создаем основные счета
    accounts = [
        # Активы
        ('1100', 'Денежные средства', category_objects['asset']),
        ('1110', 'Касса', category_objects['asset']),
        ('1120', 'Расчетный счет', category_objects['asset']),
        ('1210', 'Дебиторская задолженность', category_objects['asset']),
        ('1410', 'Товары на складе', category_objects['asset']),
        ('1415', 'Сырье и материалы', category_objects['asset']),
        ('1440', 'Готовая продукция', category_objects['asset']),
        
        # Обязательства
        ('2100', 'Краткосрочные обязательства', category_objects['liability']),
        ('2110', 'Краткосрочные кредиты и займы', category_objects['liability']),
        ('2210', 'Кредиторская задолженность', category_objects['liability']),
        ('6010', 'Счета к оплате поставщикам', category_objects['liability']),
        
        # Капитал
        ('3100', 'Уставный капитал', category_objects['equity']),
        ('3410', 'Нераспределенная прибыль', category_objects['equity']),
        
        # Доходы
        ('9010', 'Выручка от продаж', category_objects['income']),
        ('9110', 'Прочие доходы', category_objects['income']),
        
        # Расходы
        ('9020', 'Себестоимость продаж', category_objects['expense']),
        ('9130', 'Коммерческие расходы', category_objects['expense']),
        ('9140', 'Административные расходы', category_objects['expense']),
    ]
    
    for code, name, category in accounts:
        Account.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'category': category,
                'is_active': True
            }
        )
