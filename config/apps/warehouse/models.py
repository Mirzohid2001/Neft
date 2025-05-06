from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.warehouse.utils import send_telegram_message
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
import uuid
import json
from datetime import datetime, timedelta

class Warehouse(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ombor nomi")
    location = models.CharField(max_length=200, verbose_name="Manzil", blank=True, null=True)
    zone = models.CharField(max_length=50, verbose_name="Zona", blank=True, null=True)
    location_code = models.CharField(max_length=20, verbose_name="Location Code", blank=True, null=True)
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Ombor"
        verbose_name_plural = "Omborlar"


class Product(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Kod")
    name = models.CharField(max_length=100, verbose_name="Mahsulot nomi")
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="Kategoriya")
    volume = models.FloatField(verbose_name="Hajmi (l)", default=0)
    weight = models.FloatField(verbose_name="Og'irligi (kg)", default=0)
    density = models.FloatField(verbose_name="Zichlik (kg/l)", default=0)
    specific_weight = models.FloatField(verbose_name="Udel Og'irligi", default=0)
    price_usd = models.FloatField(verbose_name="Narx (USD)", default=0, null=True, blank=True)
    price_sum = models.FloatField(verbose_name="Narx (so'm)", default=0, null=True, blank=True)
    in_qty = models.FloatField(verbose_name="Umumiy kirim (qty)", default=0)
    min_stock = models.FloatField(verbose_name="Minimum ruxsat etilgan qoldiq", default=0)
    out_qty = models.FloatField(verbose_name="Umumiy chiqim (qty)", default=0)
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Ombor", blank=True, null=True)
    zone = models.CharField(max_length=50, verbose_name="Zona", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    def save(self, *args, **kwargs):
        if self.volume and self.weight:
            self.density = self.weight / self.volume
            self.specific_weight = self.density
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

    def net_quantity(self):
        """Рассчитывает текущее количество продукта динамически"""
        # Используем движения для расчета вместо сохраненных значений
        movements = Movement.objects.filter(product=self)
        total_in = movements.filter(movement_type='in').aggregate(total=Sum('quantity'))['total'] or 0
        total_out = movements.filter(movement_type='out').aggregate(total=Sum('quantity'))['total'] or 0
        return total_in - total_out
    
    def get_total_in(self):
        """Рассчитывает общее количество поступлений динамически"""
        return Movement.objects.filter(product=self, movement_type='in').aggregate(total=Sum('quantity'))['total'] or 0
    
    def get_total_out(self):
        """Рассчитывает общее количество расходов динамически"""
        return Movement.objects.filter(product=self, movement_type='out').aggregate(total=Sum('quantity'))['total'] or 0

    def check_threshold(self):
        current_qty = self.net_quantity()
        if current_qty < self.min_stock:
            message = f"Ogohlantirish: Mahsulot '{self.name}' (Kod: {self.code}) qoldigi {current_qty} ga tushdi. Minimum: {self.min_stock}. Iltimos, to'ldiring!"
            send_telegram_message(message)

    class Meta:
        ordering = ['code']
        verbose_name = "продукт"
        verbose_name_plural = "продукты"


class Batch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    batch_number = models.CharField(max_length=50, verbose_name="Partiya raqami")
    manufacture_date = models.DateField(blank=True, null=True, verbose_name="Ishlab chiqarilgan sana")
    expiry_date = models.DateField(blank=True, null=True, verbose_name="Yaroqlilik muddati")
    in_qty = models.FloatField(default=0, verbose_name="Kirim (qty)")
    out_qty = models.FloatField(default=0, verbose_name="Chiqim (qty)")
    quantity = models.FloatField(default=0, verbose_name="Joriy qoldiq (qty)")

    def __str__(self):
        return f"{self.batch_number} - {self.product.name}"

    def net_quantity(self):
        return (self.in_qty or 0) - (self.out_qty or 0)

    class Meta:
        unique_together = ('product', 'batch_number')
        verbose_name = "Партия"
        verbose_name_plural = "Партиялар"

class WagonType(models.Model):
    name = models.CharField(max_length=100, verbose_name="Vagon turi")
    meter_shtok_map = models.JSONField(blank=True, null=True, 
        help_text="Masalan: {'1.0': 1000, '1.2':1200}, meter → litr")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Vagon turi"
        verbose_name_plural = "Vagon turlari"


class Wagon(models.Model):
    wagon_number = models.CharField(max_length=20, unique=True, verbose_name="Vagon raqami")
    wagon_type = models.ForeignKey(WagonType, on_delete=models.SET_NULL, null=True, verbose_name="Vagon tipi")
    net_weight = models.FloatField(verbose_name="Netto og'irligi", default=0)
    meter_weight = models.FloatField(verbose_name="Meter og'irligi", default=0)
    capacity = models.FloatField(verbose_name="Sig'im (tonna)", default=0)
    volume = models.FloatField(verbose_name="Hajmi (L)", default=0)
    price_sum = models.FloatField(verbose_name="Umumiy summa (so'm)", default=0)
    condition = models.CharField(max_length=50, verbose_name="Holati", default="Yaxshi")
    current_quantity = models.FloatField(verbose_name="Joriy miqdor (qty)", default=0)

    def __str__(self):
        return f"{self.wagon_number} ({self.wagon_type})"
    
    def calculate_litr_from_meter(self, meter_value: float) -> float:
        if not self.wagon_type or not self.wagon_type.meter_shtok_map:
            return 0
        best_key = str(meter_value)
        return self.wagon_type.meter_shtok_map.get(best_key, 0)

    class Meta:
        ordering = ['wagon_number']
        verbose_name = "Вагон"
        verbose_name_plural = "Вагонлар"

class LocalClient(models.Model):
    name = models.CharField(max_length=200, verbose_name="Klient nomi")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Mahalliy Klient"
        verbose_name_plural = " Mahalliy Klientlar"

class Client(models.Model):
    title = models.CharField(max_length=200, verbose_name="Klient nomi")

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = "Klient"
        verbose_name_plural = "Klientlar"
    


class LocalMovement(models.Model):
    MOVEMENT_TYPES = (
        ('in', "Kirim"),
        ('out', "Chiqim"),
    )

    client = models.ForeignKey('warehouse.LocalClient', on_delete=models.CASCADE, verbose_name="Klient")
    wagon = models.ForeignKey('Wagon', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vagon")
    reservoir = models.ForeignKey('Reservoir', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Rezervuar")
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mahsulot")
    date = models.DateField(verbose_name="Sana", default=timezone.now)
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, verbose_name="Harakat turi", default='in')
    temperature = models.FloatField(verbose_name="Temperatura (C)", default=0, null=True, blank=True)
    density = models.FloatField(verbose_name="Zichlik", default=0, null=True, blank=True)
    liter = models.FloatField(verbose_name="Litr", default=0, null=True, blank=True)
    specific_weight = models.FloatField(verbose_name="Udel og'irlik", default=0, null=True, blank=True)
    quantity = models.FloatField(verbose_name="Fakt tonna (qty)", default=0)
    doc_ton = models.FloatField(verbose_name="Hujjat bo'yicha ton", default=0)
    difference_ton = models.FloatField(verbose_name="Farq (ton)", default=0, editable=False)

    note = models.TextField(verbose_name="Izoh", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    def clean(self):
        if self.movement_type == 'out' and self.product:
            available = self.product.net_quantity() or 0
            if self.quantity > available:
                raise ValidationError(
                    f"Mavjud qoldiq ({available}) dan oshiq chiqim kiritish mumkin emas!"
                )

        if not (self.wagon or self.reservoir):
            raise ValidationError(
                "Mahalliy harakatda ham Vagon yoki Rezervuarni tanlashingiz shart."
            )
        if self.wagon and self.reservoir:
            raise ValidationError("Faqat bitta joy (Vagon yoki Rezervuar) tanlashingiz mumkin!")

    def save(self, *args, **kwargs):
        if self.density and self.liter:
            computed_value = self.density * self.liter
            self.quantity = computed_value
            self.specific_weight = self.density

        self.difference_ton = self.doc_ton - self.quantity

        self.full_clean()
        super().save(*args, **kwargs)

        if self.product:
            total_in = LocalMovement.objects.filter(
                product=self.product, movement_type='in'
            ).aggregate(s=Sum('quantity'))['s'] or 0
            total_out = LocalMovement.objects.filter(
                product=self.product, movement_type='out'
            ).aggregate(s=Sum('quantity'))['s'] or 0

            self.product.in_qty = total_in
            self.product.out_qty = total_out
            self.product.save()

            inv, _ = Inventory.objects.get_or_create(product=self.product)
            inv.quantity = total_in - total_out
            inv.save()
            self.product.check_threshold()

    def __str__(self):
        client_str = f" - {self.client}" if self.client else ""
        wagon_str = f"Vagon: {self.wagon.wagon_number}" if self.wagon else ""
        reservoir_str = f"Rezervuar: {self.reservoir.name}" if self.reservoir else ""
        place_str = wagon_str or reservoir_str or "-"
        return (
            f"{self.date} - {self.product}{client_str} - "
            f"{self.get_movement_type_display()} - {self.quantity} ({place_str})"
        )

    class Meta:
        verbose_name = "Mahalliy Harakat"
        verbose_name_plural = "Mahalliy Harakatlar"

class Reservoir(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Ombor")
    name = models.CharField(max_length=100, verbose_name="Nomi")
    capacity = models.FloatField(verbose_name="Sig'im (tonna)")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Mahsulot")
    current_volume = models.FloatField(default=0, verbose_name="Joriy hajm")
    meter_shtok_map = models.JSONField(default=dict, blank=True, verbose_name="Kalibrovka ma'lumotlari")
    current_quantity = models.FloatField(verbose_name="Joriy miqdor (qty)", default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Rezervuar"
        verbose_name_plural = "Rezervuarlar"


class ReservoirMovement(models.Model):
    MOVEMENT_TYPES = (
        ('in', "Kirim (to'ldirish)"),
        ('out', "Chiqim (bo'shatish)"),
    )
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE, verbose_name="Rezervuar")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, verbose_name="Mahsulot", blank=True, null=True)
    date = models.DateField(verbose_name="Sana", default=timezone.now)
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, verbose_name="Harakat turi")
    quantity = models.FloatField(verbose_name="Miqdor (qty)")
    note = models.TextField(verbose_name="Izoh", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    def __str__(self):
        return f"{self.date} - {self.reservoir.name} - {self.get_movement_type_display()} - {self.quantity}"

    def clean(self):
        if self.movement_type == 'out':
            available = self.reservoir.in_qty - self.reservoir.out_qty
            if self.quantity > available:
                raise ValidationError(
                    f"Rezervuarda faqat {available} mavjud, lekin {self.quantity} chiqim qilinmoqda!"
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        res = self.reservoir
        total_in = ReservoirMovement.objects.filter(reservoir=res, movement_type='in').aggregate(total=Sum('quantity'))['total'] or 0
        total_out = ReservoirMovement.objects.filter(reservoir=res, movement_type='out').aggregate(total=Sum('quantity'))['total'] or 0
        res.in_qty = total_in
        res.out_qty = total_out
        res.quantity = total_in - total_out
        res.save()

class Movement(models.Model):
    MOVEMENT_TYPES = (
        ('in', "Приёмка"),
        ('out', "Продажа"),
        ('production', "Производство"),
        ('transfer', "Перемещение"),
        ('return', "Возврат"),
        ('adjustment', "Корректировка"),
    )
    
    STATUS_CHOICES = (
        ('draft', "Черновик"),
        ('pending', "Ожидает обработки"),
        ('in_progress', "В обработке"),
        ('completed', "Завершен"),
        ('cancelled', "Отменен"),
    )
    
    # Основные поля
    document_number = models.CharField(max_length=50, verbose_name="Номер документа", blank=True, null=True)
    date = models.DateField(verbose_name="Дата", default=timezone.now)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name="Тип движения")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Статус")
    
    # Продукт и количество
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    quantity = models.FloatField(verbose_name="Количество (тонн)", default=0)
    
    # Склады
    source_warehouse = models.ForeignKey(
        Warehouse, 
        related_name='source_movements',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Исходный склад"
    )
    target_warehouse = models.ForeignKey(
        Warehouse,
        related_name='target_movements',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Целевой склад"
    )
    
    # Дополнительные поля
    note = models.TextField(verbose_name="Примечание", blank=True, null=True)
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_movements',
        verbose_name="Создано пользователем"
    )
    confirmed_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_movements',
        verbose_name="Подтверждено пользователем"
    )
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def clean(self):
        if self.movement_type in ['in', 'transfer'] and not self.target_warehouse:
            raise ValidationError("Для приемки и перемещения необходимо указать целевой склад")
        
        if self.movement_type in ['out', 'transfer'] and not self.source_warehouse:
            raise ValidationError("Для продажи и перемещения необходимо указать исходный склад")
        
        if self.movement_type == 'transfer' and self.source_warehouse == self.target_warehouse:
            raise ValidationError("Исходный и целевой склад не могут быть одинаковыми")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_movement_type_display()} №{self.document_number or self.id}"

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Движение"
        verbose_name_plural = "Движения"
        indexes = [
            models.Index(fields=['movement_type', 'status']),
            models.Index(fields=['date']),
            models.Index(fields=['created_at']),
        ]

class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    quantity = models.FloatField(verbose_name="Qoldiq (qty)", default=0)

    def __str__(self):
        return f"{self.product.name} qoldiq: {self.quantity}"




class Placement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    wagon = models.ForeignKey('Wagon', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vagon")
    reservoir = models.ForeignKey('Reservoir', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Rezervuar")
    quantity = models.FloatField(verbose_name="Qisman miqdor (litr yoki kg)", default=0)
    movement = models.ForeignKey('Movement', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Harakat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.wagon and not self.reservoir:
            raise ValidationError("Vagon yoki Rezervuarni tanlashingiz kerak.")
        if self.wagon and self.reservoir:
            raise ValidationError("Faqat bitta joy tanlanishi mumkin: vagon yoki rezervuar.")
        if self.quantity <= 0:
            raise ValidationError("Miqdor manfiy yoki 0 bo'lishi mumkin emas.")
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        place = self.wagon.wagon_number if self.wagon else self.reservoir.name
        return f"{self.product.name}: {self.quantity} → {place}"



class AuditLog(models.Model):
    action = models.CharField(max_length=20)
    model_name = models.CharField(max_length=50)
    object_id = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.model_name} [{self.object_id}] {self.action} at {self.timestamp}"

class EstokadaOperation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает обработки'),
        ('measuring', 'Измерение'),
        ('processing', 'Обработка данных'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    )

    OPERATION_RESULT = (
        ('match', 'Совпадает'),
        ('positive_diff', 'Положительная разница'),
        ('negative_diff', 'Отрицательная разница'),
    )

    movement = models.OneToOneField(Movement, on_delete=models.CASCADE, related_name='estokada_operation', verbose_name='Операция движения')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    result = models.CharField(max_length=20, choices=OPERATION_RESULT, null=True, blank=True, verbose_name='Результат')
    
    # Фактические данные эстокады
    actual_quantity = models.FloatField(verbose_name='Фактическое количество (тонн)', default=0)
    actual_density = models.FloatField(verbose_name='Фактическая плотность', null=True, blank=True)
    actual_temperature = models.FloatField(verbose_name='Фактическая температура', null=True, blank=True)
    
    # Расчетные поля
    difference_quantity = models.FloatField(verbose_name='Разница в количестве (тонн)', default=0)
    difference_percentage = models.FloatField(verbose_name='Разница в процентах', default=0)
    
    # Метаданные
    processed_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_estokada_operations',
        verbose_name='Обработано пользователем'
    )
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата обработки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    notes = models.TextField(verbose_name='Примечания', blank=True, null=True)

    def clean(self):
        if self.actual_quantity < 0:
            raise ValidationError('Фактическое количество не может быть отрицательным')
        
        if self.actual_density and self.actual_density <= 0:
            raise ValidationError('Плотность должна быть положительным числом')
            
        if self.actual_temperature and (self.actual_temperature < -50 or self.actual_temperature > 100):
            raise ValidationError('Температура должна быть в диапазоне от -50 до 100 градусов')

    def calculate_differences(self):
        """Расчет разницы между документальным и фактическим количеством"""
        self.difference_quantity = self.actual_quantity - self.movement.quantity
        
        if self.movement.quantity != 0:
            self.difference_percentage = (self.difference_quantity / self.movement.quantity) * 100
        else:
            self.difference_percentage = 0
            
        # Определение результата
        if abs(self.difference_percentage) <= 0.1:  # Допустимая погрешность 0.1%
            self.result = 'match'
        else:
            self.result = 'positive_diff' if self.difference_quantity > 0 else 'negative_diff'

    def process_operation(self, user):
        """Обработка операции эстокады"""
        if self.status not in ['pending', 'measuring']:
            raise ValidationError('Невозможно обработать операцию в текущем статусе')
            
        self.calculate_differences()
        self.processed_by = user
        self.processed_at = timezone.now()
        self.status = 'completed'

    def cancel_operation(self, user, reason=None):
        """Отмена операции"""
        if self.status == 'completed':
            raise ValidationError('Невозможно отменить завершенную операцию')
            
        self.status = 'cancelled'
        self.processed_by = user
        self.processed_at = timezone.now()
        if reason:
            self.notes = f"Отменено: {reason}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Новая запись
            self.calculate_differences()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Эстокада {self.movement.document_number} ({self.get_status_display()})"

    class Meta:
        verbose_name = 'Операция эстокады'
        verbose_name_plural = 'Операции эстокады'
        ordering = ['-created_at']

# Обновляем модель Transport
class Transport(models.Model):
    TRANSPORT_TYPES = (
        ('truck', 'Грузовик'),
        ('wagon', 'Вагон'),
    )

    movement = models.ForeignKey(Movement, on_delete=models.CASCADE, related_name='transports')
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_TYPES, verbose_name='Тип транспорта')
    transport_number = models.CharField(max_length=100, verbose_name='Номер транспорта')
    
    # Поля для вагона
    wagon = models.ForeignKey('Wagon', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Вагон')
    wagon_type = models.ForeignKey('WagonType', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Тип вагона')
    
    # Общие поля для измерений
    density = models.FloatField(verbose_name='Плотность', null=True, blank=True)
    temperature = models.FloatField(verbose_name='Температура', default=20)
    volume = models.FloatField(verbose_name='Объем (л)', null=True, blank=True)
    quantity = models.FloatField(verbose_name='Количество (тонн)')
    
    # Документальные данные
    doc_quantity = models.FloatField(verbose_name='Количество по документам (тонн)', null=True, blank=True)
    difference = models.FloatField(verbose_name='Разница (тонн)', default=0)
    
    # Дополнительные поля
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Склад')
    notes = models.TextField(verbose_name='Примечания', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    def save(self, *args, **kwargs):
        if self.doc_quantity:
            self.difference = self.quantity - self.doc_quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transport_type_display()} {self.transport_number}"

    class Meta:
        verbose_name = 'Транспорт'
        verbose_name_plural = 'Транспорт'
        ordering = ['-created_at']

class ProductionSource(models.Model):
    """
    Модель для хранения информации о связи между операцией производства 
    и источниками сырья (промежуточная таблица).
    """
    movement = models.ForeignKey(Movement, on_delete=models.CASCADE, related_name='raw_materials')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Компонент")
    
    # Источник сырья (только один из них должен быть заполнен)
    source_reservoir = models.ForeignKey(Reservoir, null=True, blank=True, on_delete=models.SET_NULL, related_name='production_sources')
    source_wagon = models.ForeignKey('Wagon', null=True, blank=True, on_delete=models.SET_NULL, related_name='production_sources')
    source_warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.SET_NULL, related_name='production_sources')
    
    # Количество и процентное содержание
    quantity = models.FloatField(verbose_name="Количество (тонны)")
    percentage = models.FloatField(verbose_name="Процентное содержание (%)")
    
    class Meta:
        verbose_name = "Источник сырья для производства"
        verbose_name_plural = "Источники сырья для производства"
    
    def __str__(self):
        return f"{self.product.name} ({self.percentage}%) для {self.movement.id}"

class AnalyticsReport(models.Model):
    REPORT_TYPES = (
        ('daily', 'Ежедневный'),
        ('weekly', 'Еженедельный'),
        ('monthly', 'Ежемесячный'),
    )
    
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES)
    date_from = models.DateField()
    date_to = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Аналитический отчет'
        verbose_name_plural = 'Аналитические отчеты'

class AnalyticsData(models.Model):
    date = models.DateField()
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    total_received = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_shipped = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_produced = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_transferred = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_stock = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ('date', 'product')
        ordering = ['-date']
        verbose_name = 'Аналитические данные'
        verbose_name_plural = 'Аналитические данные'

class InventoryAudit(models.Model):
    STATUS_CHOICES = (
        ('planned', 'Запланирована'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('cancelled', 'Отменена'),
    )

    name = models.CharField(max_length=255, verbose_name='Название')
    start_date = models.DateTimeField(verbose_name='Дата начала')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name='Статус')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='created_audits', verbose_name='Создал')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    
    class Meta:
        verbose_name = 'Инвентаризация'
        verbose_name_plural = 'Инвентаризации'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def calculate_discrepancies(self):
        """Расчет расхождений между учетными и фактическими данными"""
        discrepancies = []
        for item in self.items.all():
            if item.expected_quantity != item.actual_quantity:
                discrepancy = item.actual_quantity - item.expected_quantity
                percentage = (discrepancy / item.expected_quantity * 100) if item.expected_quantity > 0 else 0
                discrepancies.append({
                    'item': item,
                    'discrepancy': discrepancy,
                    'percentage': percentage
                })
        return discrepancies
    
    def total_items(self):
        return self.items.count()
    
    def discrepancy_items(self):
        return self.items.filter(~Q(expected_quantity=F('actual_quantity'))).count()


class InventoryAuditItem(models.Model):
    audit = models.ForeignKey(InventoryAudit, on_delete=models.CASCADE, related_name='items', verbose_name='Инвентаризация')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    location = models.CharField(max_length=100, verbose_name='Местоположение')
    expected_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Учетное количество')
    actual_quantity = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='Фактическое количество')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')
    
    class Meta:
        verbose_name = 'Позиция инвентаризации'
        verbose_name_plural = 'Позиции инвентаризации'
        unique_together = ('audit', 'product', 'location')
        
    def __str__(self):
        return f"{self.product.name} в {self.location}"
    
    def discrepancy(self):
        if self.actual_quantity is None:
            return None
        return self.actual_quantity - self.expected_quantity
    
    def discrepancy_percentage(self):
        if self.expected_quantity == 0 or self.actual_quantity is None:
            return 0
        return (self.discrepancy() / self.expected_quantity) * 100


class ProductMinLevel(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='min_level', verbose_name='Продукт')
    min_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Минимальный остаток')
    optimal_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Оптимальный остаток')
    max_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Максимальный остаток')
    alert_enabled = models.BooleanField(default=True, verbose_name='Уведомления включены')
    alert_threshold = models.IntegerField(default=10, verbose_name='Порог уведомления (%)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Минимальный уровень продукта'
        verbose_name_plural = 'Минимальные уровни продуктов'
        
    def __str__(self):
        return f"Минимальный уровень для {self.product.name}"
    
    def is_below_min(self):
        current_quantity = self.product.current_quantity()
        return current_quantity < self.min_quantity
    
    def get_percentage(self):
        current_quantity = self.product.current_quantity()
        if self.min_quantity == 0:
            return 100
        return min(100, (current_quantity / self.min_quantity) * 100)


class StockForecast(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='forecasts', verbose_name='Продукт')
    date = models.DateField(verbose_name='Дата')
    forecasted_quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Прогнозируемое количество')
    confidence_level = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Уровень уверенности (%)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Прогноз запасов'
        verbose_name_plural = 'Прогнозы запасов'
        unique_together = ('product', 'date')
        ordering = ['date']
        
    def __str__(self):
        return f"Прогноз {self.product.name} на {self.date}"


class PurchasePlan(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('approved', 'Утвержден'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    )
    
    name = models.CharField(max_length=255, verbose_name='Название')
    plan_date = models.DateField(verbose_name='Дата плана')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='created_plans', verbose_name='Создал')
    approved_by = models.ForeignKey('accounts.CustomUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_plans', verbose_name='Утвердил')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата утверждения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'План закупок'
        verbose_name_plural = 'Планы закупок'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())
    
    def total_items(self):
        return self.items.count()


class PurchasePlanItem(models.Model):
    plan = models.ForeignKey(PurchasePlan, on_delete=models.CASCADE, related_name='items', verbose_name='План закупок')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    quantity = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='Количество')
    priority = models.IntegerField(default=1, verbose_name='Приоритет')
    is_automatic = models.BooleanField(default=False, verbose_name='Автоматически сформирован')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')
    
    class Meta:
        verbose_name = 'Позиция плана закупок'
        verbose_name_plural = 'Позиции плана закупок'
        unique_together = ('plan', 'product')
        ordering = ['priority']
        
    def __str__(self):
        return f"{self.product.name} ({self.quantity})"

class Supplier(models.Model):
    """Модель поставщика продукции"""
    name = models.CharField(max_length=255, verbose_name='Название')
    contact_person = models.CharField(max_length=255, verbose_name='Контактное лицо', blank=True)
    phone = models.CharField(max_length=50, verbose_name='Телефон', blank=True)
    email = models.EmailField(verbose_name='Email', blank=True)
    address = models.TextField(verbose_name='Адрес', blank=True)
    website = models.URLField(verbose_name='Вебсайт', blank=True)
    notes = models.TextField(verbose_name='Примечания', blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def get_average_rating(self):
        ratings = self.ratings.all()
        if not ratings:
            return 0
        return sum(r.rating for r in ratings) / len(ratings)
    
    def get_average_lead_time(self):
        """Возвращает среднее время поставки в днях"""
        lead_times = self.product_suppliers.filter(lead_time__isnull=False)
        if not lead_times:
            return None
        return lead_times.aggregate(avg_lead_time=models.Avg('lead_time'))['avg_lead_time']


class SupplierRating(models.Model):
    """Модель оценки поставщика"""
    RATING_CHOICES = [
        (1, '1 - Очень плохо'),
        (2, '2 - Плохо'),
        (3, '3 - Удовлетворительно'),
        (4, '4 - Хорошо'),
        (5, '5 - Отлично'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='ratings', verbose_name='Поставщик')
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='Оценка')
    category = models.CharField(max_length=100, verbose_name='Категория оценки', 
                              choices=[
                                  ('quality', 'Качество продукции'),
                                  ('delivery', 'Своевременность поставки'),
                                  ('price', 'Цена'),
                                  ('communication', 'Коммуникация'),
                                  ('overall', 'Общая оценка'),
                              ])
    comment = models.TextField(verbose_name='Комментарий', blank=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, 
                                 related_name='supplier_ratings', verbose_name='Кто оценил')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата оценки')

    class Meta:
        verbose_name = 'Оценка поставщика'
        verbose_name_plural = 'Оценки поставщиков'
        unique_together = ['supplier', 'category', 'created_by', 'created_at']
    
    def __str__(self):
        return f"{self.supplier} - {self.get_category_display()}: {self.rating}"


class ProductSupplier(models.Model):
    """Связь между продуктом и поставщиком с дополнительной информацией"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='suppliers', verbose_name='Продукт')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='product_suppliers', verbose_name='Поставщик')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена закупки', null=True, blank=True)
    is_preferred = models.BooleanField(default=False, verbose_name='Предпочтительный поставщик')
    min_order_quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Минимальное количество заказа', 
                                          null=True, blank=True)
    lead_time = models.IntegerField(verbose_name='Срок поставки (дни)', null=True, blank=True)
    last_order_date = models.DateField(verbose_name='Дата последнего заказа', null=True, blank=True)
    last_price_update = models.DateField(verbose_name='Дата последнего обновления цены', null=True, blank=True)
    notes = models.TextField(verbose_name='Примечания', blank=True)

    class Meta:
        verbose_name = 'Поставщик продукта'
        verbose_name_plural = 'Поставщики продуктов'
        unique_together = ['product', 'supplier']
    
    def __str__(self):
        return f"{self.product} - {self.supplier}"


class OrderPoint(models.Model):
    """Модель для определения точки заказа продукта"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='order_point', 
                                 verbose_name='Продукт')
    reorder_point = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Точка заказа', 
                                     help_text='Количество, при котором нужно делать заказ')
    safety_stock = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Страховой запас',
                                    help_text='Минимальный запас для непредвиденных ситуаций')
    order_quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Количество заказа',
                                      help_text='Рекомендуемое количество для заказа')
    lead_time_demand = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Потребление за время поставки',
                                        help_text='Среднее потребление за время ожидания поставки')
    auto_order = models.BooleanField(default=False, verbose_name='Автоматический заказ',
                                  help_text='Формировать заказ автоматически при достижении точки заказа')
    last_calculation = models.DateTimeField(verbose_name='Последний расчет', null=True, blank=True)
    notify_emails = models.TextField(verbose_name='Email для уведомлений', blank=True,
                                 help_text='Перечислите email через запятую')
    
    class Meta:
        verbose_name = 'Точка заказа'
        verbose_name_plural = 'Точки заказа'
    
    def __str__(self):
        return f"Точка заказа для {self.product}"
    
    def is_below_reorder_point(self):
        """Проверяет, не пора ли заказывать товар"""
        current_quantity = self.product.current_quantity()
        return current_quantity <= self.reorder_point
    
    def get_optimal_supplier(self):
        """Определяет оптимального поставщика на основе цены, времени доставки и рейтинга"""
        suppliers = ProductSupplier.objects.filter(product=self.product)
        if not suppliers:
            return None
        
        # Если есть предпочтительный поставщик, возвращаем его
        preferred = suppliers.filter(is_preferred=True).first()
        if preferred:
            return preferred
        
        # Иначе находим оптимального по комбинации факторов
        best_supplier = None
        best_score = 0
        
        for supplier in suppliers:
            # Получаем средний рейтинг поставщика
            avg_rating = supplier.supplier.get_average_rating()
            
            # Расчет очков (можно настроить веса для разных факторов)
            price_score = 5 if supplier.price else 0
            if price_score > 0 and suppliers.count() > 1:
                min_price = suppliers.filter(price__isnull=False).order_by('price').first().price
                if min_price and supplier.price:
                    price_score = 5 * (min_price / supplier.price)
            
            lead_time_score = 0
            if supplier.lead_time:
                max_lead_time = 30  # Максимальное время поставки в днях для нормализации
                lead_time_score = 5 * (1 - min(supplier.lead_time, max_lead_time) / max_lead_time)
            
            # Общая оценка (можно настроить веса)
            score = (price_score * 0.4) + (lead_time_score * 0.3) + (avg_rating * 0.3)
            
            if score > best_score:
                best_score = score
                best_supplier = supplier
        
        return best_supplier
    
    def calculate_optimal_order_time(self):
        """Рассчитывает оптимальное время заказа на основе скорости потребления и времени поставки"""
        # Получаем данные о потреблении за последние 30 дней
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        consumption = Movement.objects.filter(
            product=self.product,
            movement_type__in=['sale', 'production_usage'],
            created_at__gte=thirty_days_ago
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        # Среднее дневное потребление
        daily_consumption = consumption / 30
        
        if daily_consumption <= 0:
            return None
        
        # Получаем оптимального поставщика
        optimal_supplier = self.get_optimal_supplier()
        lead_time = optimal_supplier.lead_time if optimal_supplier else 7  # По умолчанию 7 дней
        
        # Расчет дней до точки заказа
        current_quantity = self.product.current_quantity()
        days_to_reorder = (current_quantity - self.reorder_point) / daily_consumption
        
        # Учитываем страховой запас и время поставки
        optimal_order_days = max(0, days_to_reorder - lead_time)
        
        return {
            'days': round(optimal_order_days),
            'date': timezone.now().date() + timezone.timedelta(days=round(optimal_order_days)),
            'supplier': optimal_supplier.supplier if optimal_supplier else None,
            'lead_time': lead_time
        }
    
    def save(self, *args, **kwargs):
        """Переопределяем метод save для автоматического расчета некоторых полей"""
        # Если страховой запас не указан, устанавливаем его как 50% от точки заказа
        if self.reorder_point and not self.safety_stock:
            self.safety_stock = self.reorder_point * Decimal('0.5')
            
        # Обновляем время последнего расчета
        self.last_calculation = timezone.now()
        
        super().save(*args, **kwargs)


class PurchaseNotification(models.Model):
    """Модель для хранения уведомлений о необходимости закупки"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchase_notifications',
                             verbose_name='Продукт')
    quantity_needed = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Необходимое количество')
    recommended_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, 
                                          related_name='purchase_recommendations', verbose_name='Рекомендуемый поставщик')
    recommended_order_date = models.DateField(verbose_name='Рекомендуемая дата заказа')
    expected_delivery_date = models.DateField(verbose_name='Ожидаемая дата поставки')
    status = models.CharField(max_length=50, verbose_name='Статус', 
                           choices=[
                               ('pending', 'Ожидает обработки'),
                               ('acknowledged', 'Принято к сведению'),
                               ('ordered', 'Заказано'),
                               ('canceled', 'Отменено'),
                           ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    note = models.TextField(verbose_name='Примечание', blank=True)
    notified_users = models.ManyToManyField('accounts.CustomUser', blank=True, 
                                         related_name='purchase_notifications',
                                         verbose_name='Уведомленные пользователи')
    
    class Meta:
        verbose_name = 'Уведомление о закупке'
        verbose_name_plural = 'Уведомления о закупках'
        ordering = ['recommended_order_date', 'status']
    
    def __str__(self):
        return f"Уведомление о закупке {self.product} ({self.quantity_needed})"
    
    def mark_as_ordered(self):
        """Отмечает уведомление как обработанное (заказ размещен)"""
        self.status = 'ordered'
        self.save()
    
    def cancel(self):
        """Отменяет уведомление"""
        self.status = 'canceled'
        self.save()
