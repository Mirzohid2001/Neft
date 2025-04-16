from django.db import models
from django.conf import settings
from django.utils import timezone

class Product(models.Model):
    """Model for products in stock"""
    name = models.CharField('Наименование', max_length=255, unique=True)
    unit_price = models.FloatField('Цена за единицу')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ['name']

    def __str__(self):
        return self.name

class Receiving(models.Model):
    """Model for receiving products into stock"""
    date = models.DateField('Дата', default=timezone.now)
    notes = models.TextField('Примечания', blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Создал')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Поступление'
        verbose_name_plural = 'Поступления'
        ordering = ['-date']

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    def __str__(self):
        return f"Поступление #{self.pk} ({self.date})"

class ReceivingItem(models.Model):
    """Model for individual items in a receiving transaction"""
    receiving = models.ForeignKey(Receiving, related_name='items', on_delete=models.CASCADE, verbose_name='Поступление')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    quantity = models.FloatField('Количество')
    unit_price = models.FloatField('Цена за единицу')
    comment = models.TextField('Комментарий', max_length=500, blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Элемент поступления'
        verbose_name_plural = 'Элементы поступления'
        ordering = ['id']

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class Giving(models.Model):
    """Model for giving products to workers"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    quantity = models.FloatField('Количество')
    given_to = models.CharField('Выдано (сотруднику)', max_length=255)
    comment = models.TextField('Комментарий', max_length=500, blank=True)
    date = models.DateField('Дата', default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Создал')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Выдача'
        verbose_name_plural = 'Выдачи'
        ordering = ['-date']

    @property
    def total_price(self):
        return self.quantity * self.product.unit_price

    def __str__(self):
        return f"{self.product.name} - {self.quantity} ({self.given_to})"

class Stock(models.Model):
    """Model for current stock levels"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    quantity = models.FloatField('Количество', default=0)
    last_updated = models.DateTimeField('Последнее обновление', auto_now=True)

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склад'
        ordering = ['product__name']

    @property
    def total_value(self):
        return self.quantity * self.product.unit_price

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class CanteenExpense(models.Model):
    """Model for canteen expenses"""
    product = models.CharField('Продукт/Услуга', max_length=255)
    unit_price = models.FloatField('Цена за единицу')
    quantity = models.FloatField('Количество')
    date = models.DateField('Дата', default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Создал')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Расход столовой'
        verbose_name_plural = 'Расходы столовой'
        ordering = ['-date']

    @property
    def total_cost(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product} - {self.total_cost} ({self.date})"

class Project(models.Model):
    """Model for infrastructure projects"""
    STATUS_CHOICES = [
        ('planned', 'Запланирован'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    name = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    start_date = models.DateField('Дата начала')
    end_date = models.DateField('Дата окончания')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='planned')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Создал')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        ordering = ['-start_date']

    @property
    def total_cost(self):
        return sum(item.total_cost for item in self.projectitem_set.all())

    def __str__(self):
        return self.name

class ProjectItem(models.Model):
    """Model for items/expenses in infrastructure projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='Проект')
    name = models.CharField('Наименование', max_length=255)
    unit_price = models.FloatField('Цена за единицу')
    quantity = models.FloatField('Количество')
    photo = models.ImageField('Фото', upload_to='project_items/', blank=True, null=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Элемент проекта'
        verbose_name_plural = 'Элементы проекта'
        ordering = ['project', 'name']

    @property
    def total_cost(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.project.name} - {self.name}"

class ProjectProduct(models.Model):
    """Model for tracking which warehouse products are used in projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='used_products', verbose_name='Проект')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    quantity = models.FloatField('Количество')
    date_used = models.DateField('Дата использования', default=timezone.now)
    notes = models.TextField('Примечания', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='Создал')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Использованный продукт'
        verbose_name_plural = 'Использованные продукты'
        ordering = ['-date_used', 'project']

    @property
    def total_cost(self):
        return self.quantity * self.product.unit_price

    def __str__(self):
        return f"{self.project.name} - {self.product.name} ({self.quantity})"
