from django import forms
from django.utils import timezone
from .models import SalesMovement, SalesContract, Order, OrderItem, Payment, Contract
from apps.warehouse.models import Movement, Product, Client, Reservoir, Wagon

class SalesMovementForm(forms.ModelForm):
    """
    Базовая форма для создания/редактирования операций.
    Включает общие поля для всех типов операций.
    """
    # Общие поля движения (из основной модели Movement)
    date = forms.DateField(
        initial=timezone.now, 
        required=True, 
        label="Дата операции",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), 
        required=True, 
        label="Продукт",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    document_number = forms.CharField(
        max_length=100, 
        required=False, 
        label="Номер документа",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    quantity = forms.FloatField(
        required=True, 
        label="Количество (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Поля для разницы в весе
    difference = forms.FloatField(
        required=False, 
        label="Разница (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control', 'readonly': 'readonly'})
    )
    
    # Транспорт
    transport_type = forms.ChoiceField(
        choices=[
            ('auto', "Автомобильный"),
            ('rail', "Железнодорожный"),
            ('sea', "Морской"),
            ('pipeline', "Трубопроводный"),
        ],
        required=False, 
        label="Тип транспорта",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    transport_number = forms.CharField(
        max_length=50,
        required=False,
        label="Номер транспорта",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # Для железнодорожного транспорта
    wagon_type = forms.ChoiceField(
        choices=[
            ('covered', "Крытый"),
            ('platform', "Платформа"),
            ('tank', "Цистерна"),
            ('hopper', "Хоппер"),
            ('other', "Другой"),
        ],
        required=False, 
        label="Тип вагона",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Комментарий (общий для всех типов)
    note = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}), 
        required=False, 
        label="Комментарий"
    )
    
    class Meta:
        model = SalesMovement
        fields = ['transport_type', 'transport_number']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Организуем логичные группы полей
        self.field_groups = {
            'basic_info': ['date', 'document_number', 'product', 'quantity'],
            'transport_info': ['transport_type', 'transport_number', 'wagon_type'],
            'other': ['note']
        }
        
        # Если это существующая запись, заполняем поля данными из связанной модели Movement
        if self.instance and self.instance.pk and self.instance.movement:
            movement = self.instance.movement
            self.fields['date'].initial = movement.date
            self.fields['product'].initial = movement.product
            self.fields['document_number'].initial = movement.document_number
            self.fields['quantity'].initial = movement.quantity
            self.fields['note'].initial = movement.note
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Проверяем наличие продукта и его количества
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity and quantity <= 0:
            self.add_error('quantity', "Количество должно быть положительным числом")
            
        return cleaned_data
    
    def save(self, commit=True):
        # Сохраняем сначала основную модель Movement
        movement_data = {
            'date': self.cleaned_data['date'],
            'product': self.cleaned_data.get('product'),
            'document_number': self.cleaned_data.get('document_number', ''),
            'quantity': self.cleaned_data.get('quantity'),
            'note': self.cleaned_data.get('note', ''),
        }
        
        if self.instance and self.instance.pk and self.instance.movement:
            # Обновляем существующую запись Movement
            for key, value in movement_data.items():
                setattr(self.instance.movement, key, value)
                
            if self.user:
                self.instance.movement.updated_by = self.user
                
            if commit:
                self.instance.movement.save()
        else:
            # Создаем новую запись Movement
            movement = Movement(**movement_data)
            
            if self.user:
                movement.created_by = self.user
                
            if commit:
                movement.save()
                
            self.instance.movement = movement
        
        # Затем сохраняем модель SalesMovement
        return super().save(commit)


class ReceiveForm(SalesMovementForm):
    """
    Форма для операций приемки
    """
    # Дополнительные поля для приемки
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(), 
        required=True, 
        label="Клиент/Поставщик",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Поля для фактического веса
    actual_weight = forms.FloatField(
        required=False, 
        label="Фактический вес (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Поле для выбора резервуара (куда складывать)
    target_reservoir = forms.ModelChoiceField(
        queryset=Reservoir.objects.all(),
        required=False,
        label="Резервуар",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Поле для выбора вагона (куда складывать)
    target_wagon = forms.ModelChoiceField(
        queryset=Wagon.objects.all(),
        required=False,
        label="Вагон",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = SalesMovement
        fields = ['client', 'transport_type', 'transport_number', 'target_reservoir', 'target_wagon']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Дополняем группы полей
        self.field_groups.update({
            'client_info': ['client'],
            'weight_info': ['actual_weight', 'difference'],
            'target_info': ['target_reservoir', 'target_wagon']
        })
        
        # Если это существующая запись, заполняем дополнительные поля
        if self.instance and self.instance.pk:
            self.fields['client'].initial = self.instance.client
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Проверяем, что указан либо резервуар, либо вагон для размещения товара
        target_reservoir = cleaned_data.get('target_reservoir')
        target_wagon = cleaned_data.get('target_wagon')
        
        if not target_reservoir and not target_wagon:
            self.add_error(None, "Необходимо указать либо резервуар, либо вагон для размещения товара")
            
        return cleaned_data
    
    def save(self, commit=True):
        # Установим тип операции для приемки
        if self.instance and self.instance.movement:
            self.instance.movement.movement_type = 'in'
            
        # Сохраняем основные данные через родительский метод
        instance = super().save(commit=False)
        
        # Сохраняем специфичные для приемки данные
        instance.client = self.cleaned_data['client']
        
        if commit:
            instance.save()
            
        return instance


class SaleForm(SalesMovementForm):
    """
    Форма для операций продажи
    """
    # Дополнительные поля для продажи
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(), 
        required=True, 
        label="Клиент",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    invoice_number = forms.CharField(
        max_length=100, 
        required=False, 
        label="Номер счета-фактуры",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    contract_number = forms.CharField(
        max_length=100, 
        required=False, 
        label="Номер контракта",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    price_per_unit = forms.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False, 
        label="Цена за единицу",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Поле для выбора резервуара (откуда брать)
    source_reservoir = forms.ModelChoiceField(
        queryset=Reservoir.objects.all(),
        required=False,
        label="Резервуар",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Поле для выбора вагона (откуда брать)
    source_wagon = forms.ModelChoiceField(
        queryset=Wagon.objects.all(),
        required=False,
        label="Вагон",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = SalesMovement
        fields = ['client', 'invoice_number', 'contract_number', 'price_per_unit', 
                 'transport_type', 'transport_number', 'source_reservoir', 'source_wagon']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Дополняем группы полей
        self.field_groups.update({
            'client_info': ['client', 'contract_number', 'invoice_number'],
            'price_info': ['price_per_unit'],
            'source_info': ['source_reservoir', 'source_wagon']
        })
        
        # Если это существующая запись, заполняем дополнительные поля
        if self.instance and self.instance.pk:
            self.fields['client'].initial = self.instance.client
            self.fields['invoice_number'].initial = self.instance.invoice_number
            self.fields['contract_number'].initial = self.instance.contract_number
            self.fields['price_per_unit'].initial = self.instance.price_per_unit
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Проверяем, что указан либо резервуар, либо вагон, откуда брать товар
        source_reservoir = cleaned_data.get('source_reservoir')
        source_wagon = cleaned_data.get('source_wagon')
        
        if not source_reservoir and not source_wagon:
            self.add_error(None, "Необходимо указать либо резервуар, либо вагон, откуда брать товар")
            
        # Проверка цены
        price_per_unit = cleaned_data.get('price_per_unit')
        if price_per_unit is not None and price_per_unit <= 0:
            self.add_error('price_per_unit', "Цена за единицу должна быть положительной")
            
        return cleaned_data
    
    def save(self, commit=True):
        # Установим тип операции для продажи
        if self.instance and self.instance.movement:
            self.instance.movement.movement_type = 'out'
            
        # Сохраняем основные данные через родительский метод
        instance = super().save(commit=False)
        
        # Сохраняем специфичные для продажи данные
        instance.client = self.cleaned_data['client']
        instance.invoice_number = self.cleaned_data.get('invoice_number')
        instance.contract_number = self.cleaned_data.get('contract_number')
        instance.price_per_unit = self.cleaned_data.get('price_per_unit')
        
        if commit:
            instance.save()
            
        return instance


class TransferForm(SalesMovementForm):
    """
    Форма для операций перемещения
    """
    # Поля для перемещения
    # Общий вес по документу
    total_weight = forms.FloatField(
        required=False, 
        label="Общий вес по документу (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Общий фактический вес
    actual_weight = forms.FloatField(
        required=False, 
        label="Общий фактический вес (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Поля для выбора источника (откуда брать)
    source_reservoir = forms.ModelChoiceField(
        queryset=Reservoir.objects.all(),
        required=False,
        label="Резервуар источника",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    source_wagon = forms.ModelChoiceField(
        queryset=Wagon.objects.all(),
        required=False,
        label="Вагон источника",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Поля для выбора назначения (куда класть)
    target_reservoir = forms.ModelChoiceField(
        queryset=Reservoir.objects.all(),
        required=False,
        label="Резервуар назначения",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    target_wagon = forms.ModelChoiceField(
        queryset=Wagon.objects.all(),
        required=False,
        label="Вагон назначения",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = SalesMovement
        fields = ['transport_type', 'transport_number', 
                 'source_reservoir', 'source_wagon', 
                 'target_reservoir', 'target_wagon']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Дополняем группы полей
        self.field_groups.update({
            'weight_info': ['total_weight', 'actual_weight', 'difference'],
            'source_info': ['source_reservoir', 'source_wagon'],
            'target_info': ['target_reservoir', 'target_wagon']
        })
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Проверяем, что указан либо резервуар, либо вагон, откуда брать товар
        source_reservoir = cleaned_data.get('source_reservoir')
        source_wagon = cleaned_data.get('source_wagon')
        
        if not source_reservoir and not source_wagon:
            self.add_error(None, "Необходимо указать либо резервуар, либо вагон, откуда брать товар")
            
        # Проверяем, что указан либо резервуар, либо вагон для размещения товара
        target_reservoir = cleaned_data.get('target_reservoir')
        target_wagon = cleaned_data.get('target_wagon')
        
        if not target_reservoir and not target_wagon:
            self.add_error(None, "Необходимо указать либо резервуар, либо вагон для размещения товара")
            
        # Проверяем, что источник и назначение не совпадают
        if (source_reservoir and target_reservoir and source_reservoir == target_reservoir) or \
           (source_wagon and target_wagon and source_wagon == target_wagon):
            self.add_error(None, "Источник и назначение не могут быть одинаковыми")
            
        return cleaned_data
    
    def save(self, commit=True):
        # Установим тип операции для перемещения
        if self.instance and self.instance.movement:
            self.instance.movement.movement_type = 'transfer'
            
        # Сохраняем основные данные через родительский метод
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
        return instance


class ProductionForm(SalesMovementForm):
    """
    Форма для операций производства (смешивания)
    """
    # Поля для производства
    # Производимый продукт
    produced_product = forms.ModelChoiceField(
        queryset=Product.objects.all(), 
        required=True, 
        label="Производимый продукт",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Предполагаемый вес
    expected_weight = forms.FloatField(
        required=True, 
        label="Предполагаемый вес (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Сырье (исходные продукты)
    raw_materials = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
        required=True,
        label="Сырье (продукты)",
        widget=forms.SelectMultiple(attrs={'class': 'form-control'})
    )
    
    # Общий вес по документу
    total_weight = forms.FloatField(
        required=False, 
        label="Общий вес сырья по документу (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Общий фактический вес
    actual_weight = forms.FloatField(
        required=False, 
        label="Общий фактический вес продукта (кг)",
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    # Поля для выбора источника сырья
    source_reservoir = forms.ModelChoiceField(
        queryset=Reservoir.objects.all(),
        required=False,
        label="Резервуар сырья",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    source_wagon = forms.ModelChoiceField(
        queryset=Wagon.objects.all(),
        required=False,
        label="Вагон сырья",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Поля для выбора назначения производимого продукта
    target_reservoir = forms.ModelChoiceField(
        queryset=Reservoir.objects.all(),
        required=False,
        label="Резервуар для продукта",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    target_wagon = forms.ModelChoiceField(
        queryset=Wagon.objects.all(),
        required=False,
        label="Вагон для продукта",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = SalesMovement
        fields = ['transport_type', 'transport_number',
                 'produced_product', 'expected_weight', 'raw_materials',
                 'source_reservoir', 'source_wagon', 
                 'target_reservoir', 'target_wagon']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Дополняем группы полей
        self.field_groups.update({
            'production_info': ['produced_product', 'expected_weight', 'raw_materials'],
            'weight_info': ['total_weight', 'actual_weight', 'difference'],
            'source_info': ['source_reservoir', 'source_wagon'],
            'target_info': ['target_reservoir', 'target_wagon']
        })
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Проверяем, что указан либо резервуар, либо вагон для размещения производимого продукта
        target_reservoir = cleaned_data.get('target_reservoir')
        target_wagon = cleaned_data.get('target_wagon')
        
        if not target_reservoir and not target_wagon:
            self.add_error(None, "Необходимо указать либо резервуар, либо вагон для размещения производимого продукта")
            
        # Проверяем, что выбрано хотя бы одно сырье
        raw_materials = cleaned_data.get('raw_materials')
        if not raw_materials or len(raw_materials) == 0:
            self.add_error('raw_materials', "Необходимо выбрать хотя бы один продукт в качестве сырья")
            
        # Проверяем, что производимый продукт отличается от сырья
        produced_product = cleaned_data.get('produced_product')
        if produced_product and raw_materials and produced_product in raw_materials:
            self.add_error('produced_product', "Производимый продукт не может быть одновременно сырьем")
            
        return cleaned_data
    
    def save(self, commit=True):
        # Установим тип операции для производства
        if self.instance and self.instance.movement:
            self.instance.movement.movement_type = 'production'
            
        # Сохраняем основные данные через родительский метод
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
            # Здесь можно добавить логику создания связей с сырьем и производимым продуктом
            
        return instance 


class OrderForm(forms.ModelForm):
    """
    Форма для создания и редактирования заказов
    """
    order_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    delivery_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    contract = forms.ModelChoiceField(
        queryset=SalesContract.objects.filter(status='active'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    shipping_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )
    
    shipping_method = forms.ChoiceField(
        choices=[
            ('', '---------'),
            ('road', 'Автотранспорт'),
            ('rail', 'Железная дорога'),
            ('air', 'Авиа'),
            ('sea', 'Морской транспорт'),
            ('pickup', 'Самовывоз'),
            ('other', 'Другой'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payment_method = forms.ChoiceField(
        choices=[
            ('', '---------'),
            ('bank_transfer', 'Банковский перевод'),
            ('cash', 'Наличные'),
            ('card', 'Карта'),
            ('online', 'Онлайн оплата'),
            ('credit', 'Кредит/Рассрочка'),
            ('other', 'Другой'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )
    
    class Meta:
        model = Order
        fields = [
            'client', 'order_date', 'delivery_date', 
            'shipping_address', 'shipping_method', 
            'payment_method', 'contract', 'notes'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Добавляем классы Bootstrap
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'attrs') or 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
        
        # Если есть выбранный клиент, фильтруем контракты только для этого клиента
        if 'client' in self.data:
            try:
                client_id = int(self.data.get('client'))
                self.fields['contract'].queryset = SalesContract.objects.filter(
                    client_id=client_id, 
                    status='active'
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.client:
            self.fields['contract'].queryset = SalesContract.objects.filter(
                client=self.instance.client, 
                status='active'
            )
    
    def clean_delivery_date(self):
        order_date = self.cleaned_data.get('order_date')
        delivery_date = self.cleaned_data.get('delivery_date')
        
        if order_date and delivery_date and delivery_date < order_date:
            raise forms.ValidationError("Дата доставки не может быть раньше даты заказа.")
        
        return delivery_date


class OrderItemForm(forms.ModelForm):
    """
    Форма для создания и редактирования позиций заказа
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    quantity = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    unit_price = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    discount_percent = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=100,
        initial=0,
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
    )
    
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit_price', 'discount_percent', 'note']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Получаем последние цены на продукты
        for product in Product.objects.all():
            last_movement = SalesMovement.objects.filter(
                movement__product=product, 
                price_per_unit__isnull=False
            ).order_by('-movement__date').first()
            
            if last_movement and last_movement.price_per_unit:
                product.last_price = last_movement.price_per_unit
            else:
                product.last_price = None
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity:
            # Проверяем наличие достаточного количества на складе
            available = product.current_quantity()
            if available < quantity:
                self.add_error('quantity', f"Недостаточно товара на складе. Доступно: {available}")
                
        return cleaned_data


class PaymentForm(forms.ModelForm):
    """
    Форма для создания и редактирования платежей
    """
    payment_date = forms.DateField(
        initial=timezone.now,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    amount = forms.DecimalField(
        min_value=0.01,
        widget=forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'})
    )
    
    payment_type = forms.ChoiceField(
        choices=Payment.PAYMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=Payment.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )
    
    class Meta:
        model = Payment
        fields = ['payment_date', 'amount', 'payment_type', 'status', 'reference', 'notes']


class ClientForm(forms.ModelForm):
    """
    Форма для создания и редактирования клиентов
    """
    title = forms.CharField(
        max_length=200,
        required=True,
        label="Название клиента",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Client
        fields = ['title']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Добавляем классы Bootstrap
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'attrs') or 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'


class ContractForm(forms.ModelForm):
    """
    Форма для создания и редактирования контрактов
    """
    contract_number = forms.CharField(
        max_length=100,
        required=True,
        label="Номер контракта",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        required=True,
        label="Клиент",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=True,
        label="Дата начала",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=True,
        label="Дата окончания",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[
            ('draft', "Черновик"),
            ('active', "Активный"),
            ('fulfilled', "Выполнен"),
            ('expired', "Истек"),
            ('terminated', "Расторгнут"),
        ],
        initial='draft',
        required=True,
        label="Статус",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Contract
        fields = ['contract_number', 'client', 'start_date', 'end_date', 'status']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Добавляем классы Bootstrap
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'attrs') or 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("Дата окончания не может быть раньше даты начала.")
        
        return cleaned_data 