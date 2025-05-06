from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.core.validators import MinValueValidator
from django.conf import settings
from apps.warehouse.models import Product, Warehouse, Movement, LocalMovement, ReservoirMovement, Client, Supplier
from django.contrib.auth.models import User

class AccountCategory(models.Model):
    """Категории счетов бухгалтерского учета"""
    CATEGORY_TYPES = (
        ('asset', 'Актив'),
        ('liability', 'Пассив'),
        ('equity', 'Капитал'),
        ('income', 'Доход'),
        ('expense', 'Расход'),
    )
    
    name = models.CharField(max_length=255, verbose_name='Название')
    code = models.CharField(max_length=10, unique=True, verbose_name='Код')
    type = models.CharField(max_length=10, choices=CATEGORY_TYPES, verbose_name='Тип')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    class Meta:
        verbose_name = 'Категория счета'
        verbose_name_plural = 'Категории счетов'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Account(models.Model):
    """Счета бухгалтерского учета"""
    category = models.ForeignKey(AccountCategory, on_delete=models.CASCADE, related_name='accounts', verbose_name='Категория')
    name = models.CharField(max_length=255, verbose_name='Название')
    code = models.CharField(max_length=20, unique=True, verbose_name='Код счета')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Счет'
        verbose_name_plural = 'Счета'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_balance(self, date_from=None, date_to=None):
        """Получить текущий баланс счета"""
        transactions = self.transactions.all()
        
        if date_from:
            transactions = transactions.filter(date__gte=date_from)
        if date_to:
            transactions = transactions.filter(date__lte=date_to)
            
        debit_sum = transactions.aggregate(sum=Sum('debit'))['sum'] or 0
        credit_sum = transactions.aggregate(sum=Sum('credit'))['sum'] or 0
        
        if self.category.type in ['asset', 'expense']:
            return debit_sum - credit_sum
        else:
            return credit_sum - debit_sum

class Transaction(models.Model):
    """Транзакции между счетами"""
    TRANSACTION_TYPES = (
        ('income', 'Доход'),
        ('expense', 'Расход'),
        ('transfer', 'Перевод'),
    )
    
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='Тип транзакции')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions', verbose_name='Счет')
    to_account = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True, 
                                 related_name='incoming_transactions', verbose_name='Счет получателя')
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='transactions', verbose_name='Категория')
    date = models.DateField(default=timezone.now, verbose_name='Дата')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Сумма')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    notes = models.TextField(blank=True, null=True, verbose_name='Заметки')
    tags = models.CharField(max_length=255, blank=True, null=True, verbose_name='Теги')
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Номер ссылки')
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Дебет')
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Кредит')
    journal_entry = models.ForeignKey('JournalEntry', on_delete=models.CASCADE, related_name='transactions', 
                                    null=True, blank=True, verbose_name='Проводка')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.date} - {self.account.name} - {self.amount} ({self.get_transaction_type_display()})"
    
    def save(self, *args, **kwargs):
        """
        При сохранении транзакции устанавливаем сумму в дебет или кредит в зависимости от типа транзакции
        """
        if self.transaction_type == 'income':
            self.debit = self.amount
            self.credit = 0
        elif self.transaction_type == 'expense':
            self.debit = 0
            self.credit = self.amount
        elif self.transaction_type == 'transfer' and self.to_account:
            # Для переводов в текущей записи дебетуем сумму со счета
            self.debit = 0
            self.credit = self.amount
            
        super().save(*args, **kwargs)
        
        # Для переводов создаем вторую транзакцию на счет получателя
        if self.transaction_type == 'transfer' and self.to_account and not kwargs.get('_skip_transfer', False):
            # Проверяем наличие связанной транзакции, чтобы избежать бесконечной рекурсии
            related_transaction = Transaction.objects.filter(
                transaction_type='transfer',
                to_account=self.account,
                account=self.to_account,
                amount=self.amount,
                date=self.date,
                reference=f"Transfer-{self.id}"
            ).first()
            
            if not related_transaction:
                # Создаем связанную транзакцию для счета получателя
                Transaction.objects.create(
                    transaction_type='transfer',
                    account=self.to_account,
                    to_account=self.account,
                    amount=self.amount,
                    date=self.date,
                    description=f"Перевод со счета {self.account.name}",
                    reference=f"Transfer-{self.id}",
                    debit=self.amount,  # На счет получателя деньги поступают, поэтому в дебет
                    credit=0,
                    _skip_transfer=True  # Флаг для предотвращения рекурсии
                )

class JournalEntry(models.Model):
    """Бухгалтерские проводки"""
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('posted', 'Проведено'),
        ('cancelled', 'Отменено'),
    )
    
    date = models.DateField(default=timezone.now, verbose_name='Дата')
    reference_number = models.CharField(max_length=100, unique=True, verbose_name='Номер операции')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    movement = models.ForeignKey(Movement, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries', verbose_name='Операция склада')
    local_movement = models.ForeignKey(LocalMovement, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries', verbose_name='Локальная операция')
    reservoir_movement = models.ForeignKey(ReservoirMovement, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries', verbose_name='Операция резервуара')
    invoice = models.ForeignKey('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries', verbose_name='Счет-фактура')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_entries', verbose_name='Создано')
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_entries', verbose_name='Проведено')
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата проведения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Бухгалтерская проводка'
        verbose_name_plural = 'Бухгалтерские проводки'
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.date} - {self.reference_number}"
    
    def get_total_debit(self):
        return self.transactions.aggregate(sum=Sum('debit'))['sum'] or 0
    
    def get_total_credit(self):
        return self.transactions.aggregate(sum=Sum('credit'))['sum'] or 0
    
    def is_balanced(self):
        return self.get_total_debit() == self.get_total_credit()
    
    def post(self, user):
        """Проведение проводки"""
        if self.status == 'draft' and self.is_balanced():
            self.status = 'posted'
            self.posted_by = user
            self.posted_at = timezone.now()
            self.save()
            return True
        return False
    
    def cancel(self, user):
        """Отмена проводки"""
        if self.status == 'posted':
            # Создаем сторнирующую проводку
            reversal = JournalEntry.objects.create(
                date=timezone.now(),
                reference_number=f"REV-{self.reference_number}",
                status='draft',
                description=f"Сторно проводки {self.reference_number}",
                created_by=user
            )
            
            # Создаем сторнирующие транзакции
            for trans in self.transactions.all():
                Transaction.objects.create(
                    account=trans.account,
                    date=reversal.date,
                    debit=trans.credit,
                    credit=trans.debit,
                    description=f"Сторно транзакции {trans.id}",
                    journal_entry=reversal
                )
            
            self.status = 'cancelled'
            self.save()
            
            # Проводим сторнирующую проводку
            reversal.post(user)
            return True
        return False

class Invoice(models.Model):
    """Счета-фактуры"""
    INVOICE_TYPES = (
        ('sales', 'Продажа'),
        ('purchase', 'Закупка'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('sent', 'Отправлен'),
        ('paid', 'Оплачен'),
        ('cancelled', 'Отменен'),
    )
    
    invoice_type = models.CharField(max_length=10, choices=INVOICE_TYPES, verbose_name='Тип счета')
    number = models.CharField(max_length=100, unique=True, verbose_name='Номер счета')
    date = models.DateField(default=timezone.now, verbose_name='Дата выставления')
    due_date = models.DateField(verbose_name='Срок оплаты')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='client_invoices', verbose_name='Клиент')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True, related_name='supplier_invoices', verbose_name='Поставщик')
    movement = models.ForeignKey(Movement, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices', verbose_name='Операция склада')
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Подытог')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Сумма налога')
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Сумма скидки')
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Итого')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    terms = models.TextField(blank=True, null=True, verbose_name='Условия')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_invoices', verbose_name='Создано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Счет-фактура'
        verbose_name_plural = 'Счета-фактуры'
        ordering = ['-date', '-id']
    
    def __str__(self):
        return f"{self.number} - {self.get_invoice_type_display()}"
    
    def calculate_totals(self):
        """Расчет итоговых сумм"""
        items_total = self.items.aggregate(total=Sum('amount'))['total'] or 0
        self.subtotal = items_total
        self.total = self.subtotal + self.tax_amount - self.discount_amount
        self.save()
    
    def mark_as_sent(self):
        """Пометить как отправленный"""
        if self.status == 'draft':
            self.status = 'sent'
            self.save()
            return True
        return False
    
    def mark_as_paid(self):
        """Пометить как оплаченный"""
        if self.status in ['draft', 'sent']:
            self.status = 'paid'
            self.save()
            return True
        return False
    
    def cancel(self):
        """Отменить счет"""
        if self.status != 'paid':
            self.status = 'cancelled'
            self.save()
            return True
        return False

class InvoiceItem(models.Model):
    """Позиции счета-фактуры"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items', verbose_name='Счет-фактура')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    quantity = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Количество')
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Цена за единицу')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Сумма')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Ставка налога (%)')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Сумма налога')
    
    class Meta:
        verbose_name = 'Позиция счета'
        verbose_name_plural = 'Позиции счета'
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} x {self.unit_price}"
    
    def save(self, *args, **kwargs):
        """Автоматический расчет суммы"""
        self.amount = self.quantity * self.unit_price
        self.tax_amount = self.amount * (self.tax_rate / 100)
        super().save(*args, **kwargs)
        self.invoice.calculate_totals()

class Payment(models.Model):
    """Платежи по счетам"""
    PAYMENT_METHODS = (
        ('cash', 'Наличные'),
        ('bank', 'Банковский перевод'),
        ('card', 'Банковская карта'),
        ('other', 'Другое'),
    )
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments', verbose_name='Счет-фактура')
    date = models.DateField(default=timezone.now, verbose_name='Дата платежа')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Сумма')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS, verbose_name='Способ оплаты')
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Номер платежа')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='accounting_created_payments', verbose_name='Создано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.date} - {self.invoice.number} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """При сохранении платежа проверяем, не нужно ли пометить счет как оплаченный"""
        super().save(*args, **kwargs)
        
        # Проверяем общую сумму платежей
        total_paid = self.invoice.payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Если общая сумма платежей >= суммы счета, помечаем счет как оплаченный
        if total_paid >= self.invoice.total and self.invoice.status != 'paid':
            self.invoice.mark_as_paid()

class TaxRate(models.Model):
    """Ставки налогов"""
    name = models.CharField(max_length=100, verbose_name='Название')
    rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='Ставка (%)')
    is_default = models.BooleanField(default=False, verbose_name='По умолчанию')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    
    class Meta:
        verbose_name = 'Ставка налога'
        verbose_name_plural = 'Ставки налогов'
        ordering = ['rate']
    
    def __str__(self):
        return f"{self.name} ({self.rate}%)"
    
    def save(self, *args, **kwargs):
        """При установке ставки по умолчанию снимаем этот флаг с других ставок"""
        if self.is_default:
            TaxRate.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

class FinancialPeriod(models.Model):
    """Финансовые периоды"""
    name = models.CharField(max_length=100, verbose_name='Название')
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    is_closed = models.BooleanField(default=False, verbose_name='Закрыт')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата закрытия')
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_periods', verbose_name='Закрыто')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    
    class Meta:
        verbose_name = 'Финансовый период'
        verbose_name_plural = 'Финансовые периоды'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    def close(self, user):
        """Закрыть финансовый период"""
        if not self.is_closed:
            self.is_closed = True
            self.closed_at = timezone.now()
            self.closed_by = user
            self.save()
            return True
        return False

class FinancialRecord(models.Model):
    """Финансовая запись для отчетов и анализа"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Продукт')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Склад')
    date = models.DateField(verbose_name='Дата')
    movement_type = models.CharField(max_length=3, choices=(('in', 'Kirim'), ('out', 'Chiqim')), verbose_name='Тип движения')
    quantity = models.FloatField(default=0, verbose_name='Количество')
    total_price_usd = models.FloatField(default=0, verbose_name='Сумма (USD)')
    total_price_sum = models.FloatField(default=0, verbose_name='Сумма (сум)')
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='financial_records', verbose_name='Проводка')
    
    class Meta:
        verbose_name = "Финансовая запись"
        verbose_name_plural = "Финансовые записи"
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.date} - {self.product.name if self.product else 'Без продукта'} - {self.movement_type} - {self.total_price_sum} сум"

class FinancialSetting(models.Model):
    """Настройки бухгалтерии"""
    company_name = models.CharField(max_length=255, verbose_name='Название компании')
    default_payment_term = models.IntegerField(default=30, verbose_name='Срок оплаты по умолчанию (дни)')
    invoice_prefix = models.CharField(max_length=10, default='INV', verbose_name='Префикс номера счета')
    next_invoice_number = models.IntegerField(default=1, verbose_name='Следующий номер счета')
    default_debit_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_debit_settings', verbose_name='Счет дебета по умолчанию')
    default_credit_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_credit_settings', verbose_name='Счет кредита по умолчанию')
    default_tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True, related_name='default_settings', verbose_name='Ставка налога по умолчанию')
    fiscal_year_start = models.DateField(verbose_name='Начало финансового года')
    currency_symbol = models.CharField(max_length=5, default='UZS', verbose_name='Символ валюты')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')
    
    class Meta:
        verbose_name = 'Настройка бухгалтерии'
        verbose_name_plural = 'Настройки бухгалтерии'
    
    def __str__(self):
        return f"Настройки бухгалтерии {self.company_name}"
    
    def save(self, *args, **kwargs):
        """Гарантируем, что существует только одна запись настроек"""
        self.__class__.objects.exclude(id=self.id).delete()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Получить настройки бухгалтерии или создать по умолчанию"""
        obj, created = cls.objects.get_or_create(
            defaults={
                'company_name': 'Моя компания',
                'fiscal_year_start': timezone.now().replace(month=1, day=1)
            }
        )
        return obj

class Category(models.Model):
    """Модель для категорий доходов и расходов"""
    TYPE_CHOICES = (
        ('income', 'Daromad'),
        ('expense', 'Xarajat'),
    )

    name = models.CharField(max_length=100, verbose_name="Nomi")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Turi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ikonka")
    color = models.CharField(max_length=20, blank=True, null=True, verbose_name="Rang")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan sana")

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def get_transactions_count(self):
        """Возвращает количество транзакций в этой категории"""
        return self.transaction_set.count()
    
    def get_total_amount(self):
        """Возвращает общую сумму транзакций в этой категории"""
        return self.transaction_set.aggregate(total=Sum('amount'))['total'] or 0

class Budget(models.Model):
    """Модель для бюджетов"""
    PERIOD_CHOICES = (
        ('day', 'Kunlik'),
        ('week', 'Haftalik'),
        ('month', 'Oylik'),
        ('year', 'Yillik'),
    )

    name = models.CharField(max_length=100, verbose_name="Nomi")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Kategoriya")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Summa")
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, verbose_name="Davr")
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    end_date = models.DateField(verbose_name="Tugash sanasi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan sana")

    class Meta:
        verbose_name = "Byudjet"
        verbose_name_plural = "Byudjetlar"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} - {self.amount} UZS"
    
    def get_spent_amount(self):
        """Возвращает сумму расходов в рамках бюджета"""
        return Transaction.objects.filter(
            category=self.category,
            date__gte=self.start_date,
            date__lte=self.end_date
        ).aggregate(total=Sum('amount'))['total'] or 0
    
    def get_remaining_amount(self):
        """Возвращает оставшуюся сумму бюджета"""
        spent = self.get_spent_amount()
        return self.amount - spent
    
    def get_percentage_used(self):
        """Возвращает процент использования бюджета"""
        spent = self.get_spent_amount()
        if self.amount > 0:
            return (spent / self.amount) * 100
        return 0
