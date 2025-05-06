from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.warehouse.models import Movement, Product, Client

class SalesMovement(models.Model):
    """
    Модель для хранения специфической информации о продажах.
    Связана с общей моделью Movement.
    """
    PRIORITY_CHOICES = [
        ('low', "Низкий"),
        ('medium', "Средний"),
        ('high', "Высокий"),
        ('urgent', "Срочный"),
    ]
    
    movement = models.OneToOneField(
        Movement, 
        on_delete=models.CASCADE, 
        related_name='sales_details',
        verbose_name="Основное движение"
    )
    
    # Поля, специфичные для продаж
    client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        verbose_name="Клиент"
    )
    invoice_number = models.CharField(
        max_length=100, 
        verbose_name="Номер счета-фактуры", 
        blank=True, 
        null=True
    )
    price_per_unit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Цена за единицу",
        blank=True,
        null=True
    )
    currency = models.CharField(
        max_length=3, 
        verbose_name="Валюта", 
        default="UZS",
        choices=[
            ('UZS', "Сум"),
            ('USD', "Доллар США"),
            ('EUR', "Евро"),
            ('RUB', "Рубль"),
        ]
    )
    total_price = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        verbose_name="Общая сумма",
        blank=True,
        null=True
    )
    discount_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name="Скидка (%)",
        blank=True,
        null=True,
        default=0
    )
    discount_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Сумма скидки",
        blank=True,
        null=True,
        default=0
    )
    tax_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        verbose_name="Налог (%)",
        blank=True,
        null=True,
        default=0
    )
    tax_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Сумма налога",
        blank=True,
        null=True,
        default=0
    )
    shipping_address = models.TextField(
        verbose_name="Адрес доставки",
        blank=True,
        null=True
    )
    transport_type = models.CharField(
        max_length=50,
        verbose_name="Тип транспорта",
        blank=True,
        null=True,
        choices=[
            ('auto', "Автомобильный"),
            ('rail', "Железнодорожный"),
            ('sea', "Морской"),
            ('air', "Воздушный"),
            ('pipeline', "Трубопроводный"),
            ('other', "Другой"),
        ]
    )
    transport_number = models.CharField(
        max_length=50,
        verbose_name="Номер транспорта",
        blank=True,
        null=True
    )
    contract_number = models.CharField(
        max_length=100,
        verbose_name="Номер контракта",
        blank=True,
        null=True
    )
    priority = models.CharField(
        max_length=10,
        verbose_name="Приоритет",
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    responsible_person = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_sales',
        verbose_name="Ответственное лицо"
    )
    comments = models.TextField(
        verbose_name="Комментарии",
        blank=True,
        null=True
    )
    estimated_profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Расчетная прибыль",
        blank=True,
        null=True
    )
    estokada_processed = models.BooleanField(
        verbose_name="Обработано эстокадой",
        default=False
    )
    is_export = models.BooleanField(
        verbose_name="Экспортная продажа",
        default=False
    )
    
    def clean(self):
        # Проверка, что движение имеет тип "out" (продажа)
        if self.movement and self.movement.movement_type != 'out':
            raise ValidationError("Продажа может быть связана только с движением типа 'Продажа'")
            
        # Проверка наличия клиента
        if not self.client:
            raise ValidationError("Необходимо указать клиента для продажи")
            
        # Проверка цены
        if self.price_per_unit is not None and self.price_per_unit <= 0:
            raise ValidationError("Цена за единицу должна быть положительной")
        
    def save(self, *args, **kwargs):
        # Рассчитываем общую сумму, если указана цена за единицу
        if self.price_per_unit and self.movement and self.movement.quantity:
            base_price = self.price_per_unit * self.movement.quantity
            
            # Применяем скидку, если она указана
            if self.discount_percent:
                self.discount_amount = base_price * (self.discount_percent / 100)
            else:
                self.discount_amount = 0
                
            # Применяем налог, если он указан
            if self.tax_percent:
                self.tax_amount = (base_price - self.discount_amount) * (self.tax_percent / 100)
            else:
                self.tax_amount = 0
                
            # Итоговая сумма
            self.total_price = base_price - self.discount_amount + self.tax_amount
            
            # Расчетная прибыль (простая модель: цена продажи минус стоимость продукта)
            if self.movement.product.price_sum and self.movement.product.price_sum > 0:
                cost = self.movement.product.price_sum * self.movement.quantity
                self.estimated_profit = self.total_price - cost
            
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        client_name = self.client.title if self.client else "Без клиента"
        return f"Продажа: {self.movement} - {client_name}"
    
    class Meta:
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"
        ordering = ['-movement__date']
        indexes = [
            models.Index(fields=['estokada_processed']),
        ]


class SalesContract(models.Model):
    """
    Модель контракта на продажу
    """
    contract_number = models.CharField(
        max_length=100, 
        verbose_name="Номер контракта",
        unique=True
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name="Клиент"
    )
    start_date = models.DateField(
        verbose_name="Дата начала"
    )
    end_date = models.DateField(
        verbose_name="Дата окончания"
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Общая сумма",
        null=True,
        blank=True
    )
    currency = models.CharField(
        max_length=3,
        verbose_name="Валюта",
        default="UZS",
        choices=[
            ('UZS', "Сум"),
            ('USD', "Доллар США"),
            ('EUR', "Евро"),
            ('RUB', "Рубль"),
        ]
    )
    status = models.CharField(
        max_length=20,
        verbose_name="Статус",
        choices=[
            ('draft', "Черновик"),
            ('active', "Активный"),
            ('fulfilled', "Выполнен"),
            ('expired', "Истек"),
            ('terminated', "Расторгнут"),
        ],
        default='draft'
    )
    payment_terms = models.TextField(
        verbose_name="Условия оплаты",
        blank=True,
        null=True
    )
    delivery_terms = models.TextField(
        verbose_name="Условия доставки",
        blank=True,
        null=True
    )
    file = models.FileField(
        upload_to='contracts/',
        verbose_name="Файл контракта",
        blank=True,
        null=True
    )
    responsible_person = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_contracts',
        verbose_name="Ответственное лицо"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Дата обновления"
    )
    
    def __str__(self):
        return f"Контракт {self.contract_number} - {self.client}"
    
    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Дата начала не может быть позже даты окончания")
    
    def is_active(self):
        today = timezone.now().date()
        return (
            self.status == 'active' and 
            self.start_date <= today <= self.end_date
        )
    
    class Meta:
        verbose_name = "Контракт"
        verbose_name_plural = "Контракты"
        ordering = ['-created_at']


class SalesContractProduct(models.Model):
    """
    Модель для связи контракта с продуктами
    """
    contract = models.ForeignKey(
        SalesContract,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Контракт"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Продукт"
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Количество"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Цена за единицу"
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Общая сумма",
        blank=True,
        null=True
    )
    
    def save(self, *args, **kwargs):
        # Рассчитываем общую сумму
        if self.quantity and self.unit_price:
            self.total_price = self.quantity * self.unit_price
            
        super().save(*args, **kwargs)
        
        # Обновляем общую сумму контракта
        contract = self.contract
        total = contract.products.aggregate(total=models.Sum('total_price'))['total'] or 0
        contract.total_amount = total
        contract.save(update_fields=['total_amount'])
    
    def __str__(self):
        return f"{self.product} - {self.quantity} ед."
    
    class Meta:
        verbose_name = "Продукт контракта"
        verbose_name_plural = "Продукты контракта"
        unique_together = ('contract', 'product')


class Order(models.Model):
    """
    Модель заказа для модуля продаж
    """
    DELIVERY_STATUS_CHOICES = [
        ('pending', "Ожидает отправки"),
        ('in_progress', "В процессе доставки"),
        ('completed', "Выполнен"),
        ('canceled', "Отменен"),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', "Ожидает оплаты"),
        ('partial', "Частично оплачен"),
        ('paid', "Полностью оплачен"),
        ('overdue', "Просрочен"),
        ('refunded', "Возвращен"),
    ]
    
    order_number = models.CharField(
        max_length=100, 
        verbose_name="Номер заказа",
        unique=True
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Клиент"
    )
    order_date = models.DateField(
        verbose_name="Дата заказа",
        default=timezone.now
    )
    delivery_date = models.DateField(
        verbose_name="Дата доставки",
        null=True,
        blank=True
    )
    completed_date = models.DateField(
        verbose_name="Дата выполнения",
        null=True,
        blank=True
    )
    delivery_status = models.CharField(
        max_length=20,
        verbose_name="Статус доставки",
        choices=DELIVERY_STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        verbose_name="Статус оплаты",
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Общая сумма",
        null=True,
        blank=True
    )
    paid_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Оплаченная сумма",
        null=True,
        blank=True,
        default=0
    )
    shipping_address = models.TextField(
        verbose_name="Адрес доставки",
        blank=True,
        null=True
    )
    shipping_method = models.CharField(
        max_length=100,
        verbose_name="Способ доставки",
        blank=True,
        null=True
    )
    payment_method = models.CharField(
        max_length=100,
        verbose_name="Способ оплаты",
        blank=True,
        null=True
    )
    notes = models.TextField(
        verbose_name="Примечания",
        blank=True,
        null=True
    )
    contract = models.ForeignKey(
        SalesContract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name="Контракт"
    )
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_orders',
        verbose_name="Создал"
    )
    updated_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_orders',
        verbose_name="Обновил"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Дата обновления"
    )
    
    def __str__(self):
        return f"Заказ №{self.order_number} ({self.client})"
    
    def save(self, *args, **kwargs):
        # Генерируем номер заказа, если его нет
        if not self.order_number:
            last_order = Order.objects.order_by('-id').first()
            next_id = 1 if not last_order else last_order.id + 1
            self.order_number = f"ORD-{timezone.now().year}-{next_id:04d}"
        
        # Если статус доставки изменился на 'completed', устанавливаем дату выполнения
        if self.delivery_status == 'completed' and not self.completed_date:
            self.completed_date = timezone.now().date()
            
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.pk})
    
    def get_total_items(self):
        return self.items.count()
    
    def get_items_total(self):
        return self.items.aggregate(total=models.Sum(
            F('quantity') * F('unit_price')
        ))['total'] or 0
    
    def update_total_amount(self):
        self.total_amount = self.get_items_total()
        self.save(update_fields=['total_amount'])
    
    def is_overdue(self):
        """Проверяет, просрочен ли заказ"""
        if self.delivery_status in ['completed', 'canceled']:
            return False
        if not self.delivery_date:
            return False
        return self.delivery_date < timezone.now().date()
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['delivery_status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['order_date']),
            models.Index(fields=['client']),
        ]


class OrderItem(models.Model):
    """
    Модель элемента заказа (товарной позиции)
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Заказ"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name="Продукт"
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Количество"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Цена за единицу"
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Скидка (%)",
        default=0
    )
    total_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Общая сумма",
        null=True,
        blank=True
    )
    note = models.TextField(
        verbose_name="Примечание",
        blank=True,
        null=True
    )
    
    def __str__(self):
        return f"{self.product} - {self.quantity} ({self.order})"
    
    def save(self, *args, **kwargs):
        # Расчет итоговой цены с учетом скидки
        self.total_price = self.unit_price * self.quantity * (1 - self.discount_percent / 100)
        super().save(*args, **kwargs)
        
        # Обновляем общую сумму заказа
        self.order.update_total_amount()
    
    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        unique_together = ('order', 'product')


class Payment(models.Model):
    """
    Модель платежа по заказу
    """
    PAYMENT_TYPE_CHOICES = [
        ('cash', "Наличные"),
        ('bank_transfer', "Банковский перевод"),
        ('card', "Карта"),
        ('online', "Онлайн платеж"),
        ('credit', "Кредит/Рассрочка"),
        ('other', "Другое"),
    ]
    
    STATUS_CHOICES = [
        ('pending', "В обработке"),
        ('completed', "Выполнен"),
        ('failed', "Ошибка"),
        ('refunded', "Возвращен"),
    ]
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Заказ"
    )
    payment_number = models.CharField(
        max_length=100,
        verbose_name="Номер платежа",
        unique=True
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Сумма"
    )
    payment_date = models.DateField(
        verbose_name="Дата платежа",
        default=timezone.now
    )
    payment_type = models.CharField(
        max_length=20,
        verbose_name="Тип платежа",
        choices=PAYMENT_TYPE_CHOICES,
        default='bank_transfer'
    )
    status = models.CharField(
        max_length=20,
        verbose_name="Статус",
        choices=STATUS_CHOICES,
        default='pending'
    )
    reference = models.CharField(
        max_length=200,
        verbose_name="Реквизиты платежа",
        blank=True,
        null=True
    )
    notes = models.TextField(
        verbose_name="Примечания",
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_created_payments',
        verbose_name="Создал"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    
    def __str__(self):
        return f"Платеж {self.payment_number} для заказа {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        # Генерируем номер платежа, если его нет
        if not self.payment_number:
            last_payment = Payment.objects.order_by('-id').first()
            next_id = 1 if not last_payment else last_payment.id + 1
            self.payment_number = f"PAY-{timezone.now().year}-{next_id:04d}"
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Если платеж выполнен, обновляем оплаченную сумму заказа
        if is_new or self._state.adding or self.status == 'completed':
            # Рассчитываем общую сумму выполненных платежей
            paid_amount = Payment.objects.filter(
                order=self.order,
                status='completed'
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            # Обновляем сумму и статус оплаты заказа
            self.order.paid_amount = paid_amount
            
            # Определяем статус оплаты
            if paid_amount >= self.order.total_amount:
                self.order.payment_status = 'paid'
            elif paid_amount > 0:
                self.order.payment_status = 'partial'
            else:
                self.order.payment_status = 'pending'
                
            self.order.save(update_fields=['paid_amount', 'payment_status'])
    
    class Meta:
        verbose_name = "Платеж"
        verbose_name_plural = "Платежи"
        ordering = ['-payment_date', '-created_at']


class Contract(models.Model):
    """
    Модель контракта (упрощенная версия SalesContract для ссылок из представлений)
    """
    contract_number = models.CharField(
        max_length=100,
        verbose_name="Номер контракта",
        unique=True
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='simple_contracts',
        verbose_name="Клиент"
    )
    start_date = models.DateField(
        verbose_name="Дата начала"
    )
    end_date = models.DateField(
        verbose_name="Дата окончания"
    )
    status = models.CharField(
        max_length=20,
        verbose_name="Статус",
        choices=[
            ('draft', "Черновик"),
            ('active', "Активный"),
            ('fulfilled', "Выполнен"),
            ('expired', "Истек"),
            ('terminated', "Расторгнут"),
        ],
        default='draft'
    )
    
    def __str__(self):
        return f"Контракт №{self.contract_number} ({self.client})"
    
    class Meta:
        verbose_name = "Простой контракт"
        verbose_name_plural = "Простые контракты"
