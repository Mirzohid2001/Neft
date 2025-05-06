from django import forms
from django.utils import timezone
from .models import EstokadaMovement
from apps.warehouse.models import Movement, Product, Reservoir, Wagon, Transport

class EstokadaMovementForm(forms.ModelForm):
    """
    Форма для создания/редактирования движения через эстокаду.
    Включает поля из основной модели Movement и специфичные поля для эстокады.
    """
    # Общие поля движения (из основной модели Movement)
    movement_type = forms.ChoiceField(choices=Movement.MOVEMENT_TYPES, required=True, label="Тип операции")
    date = forms.DateField(initial=timezone.now, required=True, label="Дата", widget=forms.DateInput(attrs={'type': 'date'}))
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=True, label="Продукт")
    document_number = forms.CharField(max_length=100, required=False, label="Номер документа")
    quantity = forms.FloatField(required=True, label="Количество (тонн)")
    note = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Примечание")
    
    # Поля, специфичные для эстокады
    TRANSPORT_TYPES = [
        ('truck', 'Автомобильный транспорт'),
        ('wagon', 'Железнодорожный вагон'),
    ]
    
    transport_type = forms.ChoiceField(choices=TRANSPORT_TYPES, required=True, label="Тип транспорта")
    transport_number = forms.CharField(max_length=50, required=False, label="Номер транспорта")
    document_weight = forms.FloatField(required=False, label="Вес по документу (кг)")
    actual_weight = forms.FloatField(required=False, label="Фактический вес (кг)")
    
    source_reservoir = forms.ModelChoiceField(queryset=None, required=False, label="Исходный резервуар")
    source_wagon = forms.ModelChoiceField(queryset=None, required=False, label="Исходный вагон")
    target_reservoir = forms.ModelChoiceField(queryset=None, required=False, label="Целевой резервуар")
    target_wagon = forms.ModelChoiceField(queryset=None, required=False, label="Целевой вагон")
    
    temperature = forms.FloatField(required=False, label="Температура (°C)")
    density = forms.FloatField(required=False, label="Плотность")
    specific_weight = forms.FloatField(required=False, label="Удельный вес")
    meter_value = forms.FloatField(required=False, label="Показание метра")
    
    class Meta:
        model = EstokadaMovement
        fields = [
            'actual_weight', 'document_weight', 'temperature', 'density', 'notes'
        ]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.operation_type = kwargs.pop('operation_type', None)
        super().__init__(*args, **kwargs)
        
        # Настройка полей выбора для резервуаров и вагонов
        self.fields['source_reservoir'].queryset = Reservoir.objects.all()
        self.fields['target_reservoir'].queryset = Reservoir.objects.all()
        self.fields['source_wagon'].queryset = Wagon.objects.all()
        self.fields['target_wagon'].queryset = Wagon.objects.all()
        
        # Если это существующая запись, заполняем поля данными из связанной модели Movement
        if self.instance and self.instance.pk and self.instance.movement:
            movement = self.instance.movement
            self.fields['movement_type'].initial = movement.movement_type
            self.fields['date'].initial = movement.date
            self.fields['product'].initial = movement.product
            self.fields['document_number'].initial = movement.document_number
            self.fields['quantity'].initial = movement.quantity
            self.fields['note'].initial = movement.note
            
            # Если передан тип операции, устанавливаем его и делаем поле недоступным
            if self.operation_type:
                self.fields['movement_type'].initial = self.operation_type
                self.fields['movement_type'].widget.attrs['readonly'] = True
                
                # В зависимости от типа операции скрываем или показываем поля
                self._setup_fields_for_operation_type(self.operation_type)
    
    def _setup_fields_for_operation_type(self, operation_type):
        """
        Настраивает поля формы в зависимости от типа операции
        """
        if operation_type == 'in':  # Приемка
            self.fields['source_reservoir'].widget = forms.HiddenInput()
            self.fields['source_wagon'].widget = forms.HiddenInput()
            # Для приемки важны целевые объекты (куда принимаем)
            
        elif operation_type == 'out':  # Продажа/Отгрузка
            self.fields['target_reservoir'].widget = forms.HiddenInput()
            self.fields['target_wagon'].widget = forms.HiddenInput()
            # Для отгрузки важны исходные объекты (откуда отгружаем)
            
        elif operation_type == 'transfer':  # Перемещение
            # Для перемещения важны и исходные, и целевые объекты
            pass
            
        elif operation_type == 'production':  # Производство
            # Специфические настройки для производства
            pass
    
    def clean(self):
        cleaned_data = super().clean()
        
        movement_type = cleaned_data.get('movement_type')
        source_reservoir = cleaned_data.get('source_reservoir')
        source_wagon = cleaned_data.get('source_wagon')
        target_reservoir = cleaned_data.get('target_reservoir')
        target_wagon = cleaned_data.get('target_wagon')
        
        # Проверки в зависимости от типа операции
        if movement_type == 'in':  # Приемка
            if not (target_reservoir or target_wagon):
                self.add_error(None, "Для операции приемки необходимо указать целевой резервуар или вагон")
                
            # Для приемки обязательны вес по документу и транспорт
            if not cleaned_data.get('document_weight'):
                self.add_error('document_weight', "Для приемки необходимо указать вес по документу")
            
            if not cleaned_data.get('transport_number'):
                self.add_error('transport_number', "Для приемки необходимо указать номер транспорта")
                
        elif movement_type == 'out':  # Отгрузка
            if not (source_reservoir or source_wagon):
                self.add_error(None, "Для операции отгрузки необходимо указать исходный резервуар или вагон")
                
        elif movement_type == 'transfer':  # Перемещение
            if not ((source_reservoir or source_wagon) and (target_reservoir or target_wagon)):
                self.add_error(None, "Для операции перемещения необходимо указать и источник, и назначение")
            
            # Для перемещения важно количество
            if not cleaned_data.get('quantity'):
                self.add_error('quantity', "Для перемещения необходимо указать количество")
        
        # Проверка плотности и температуры для специфических операций
        if movement_type in ('in', 'transfer') and cleaned_data.get('transport_type') == 'wagon':
            density = cleaned_data.get('density')
            temperature = cleaned_data.get('temperature')
            
            if not density:
                self.add_error('density', "Для вагона необходимо указать плотность")
            
            if not temperature:
                self.add_error('temperature', "Для вагона необходимо указать температуру")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Сохраняем сначала основную модель Movement
        movement_data = {
            'movement_type': self.cleaned_data['movement_type'],
            'date': self.cleaned_data['date'],
            'product': self.cleaned_data['product'],
            'document_number': self.cleaned_data.get('document_number', ''),
            'quantity': self.cleaned_data['quantity'],
            'note': self.cleaned_data.get('note', ''),
        }
        
        if self.instance and self.instance.pk and self.instance.movement:
            # Обновляем существующую запись Movement
            for key, value in movement_data.items():
                setattr(self.instance.movement, key, value)
                
            if self.user:
                self.instance.movement.created_by = self.user
                
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
        
        # Затем сохраняем модель EstokadaMovement
        return super().save(commit)
    


# Специализированные формы для разных типов операций

class EstokadaReceiveForm(EstokadaMovementForm):
    """Форма для операции приемки (in)"""
    def __init__(self, *args, **kwargs):
        kwargs['operation_type'] = 'in'
        super().__init__(*args, **kwargs)
        self.fields['movement_type'].widget = forms.HiddenInput()  # Скрываем поле типа операции

class EstokadaShipmentForm(EstokadaMovementForm):
    """Форма для операции отгрузки (out)"""
    def __init__(self, *args, **kwargs):
        kwargs['operation_type'] = 'out'
        super().__init__(*args, **kwargs)
        self.fields['movement_type'].widget = forms.HiddenInput()

class EstokadaTransferForm(EstokadaMovementForm):
    """Форма для операции перемещения (transfer)"""
    def __init__(self, *args, **kwargs):
        kwargs['operation_type'] = 'transfer'
        super().__init__(*args, **kwargs)
        self.fields['movement_type'].widget = forms.HiddenInput()

class EstokadaProductionForm(forms.ModelForm):
    """Форма для создания операции производства"""
    date = forms.DateField(
        label='Дата',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    document_number = forms.CharField(
        label='Номер документа',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    product = forms.ModelChoiceField(
        label='Продукт',
        queryset=Product.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    quantity = forms.DecimalField(
        label='Количество (тонн)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=True
    )
    
    TRANSPORT_TYPES = [
        ('truck', 'Автомобильный транспорт'),
        ('wagon', 'Железнодорожный вагон'),
    ]
    
    transport_type = forms.ChoiceField(
        label='Тип транспорта',
        choices=TRANSPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    transport_number = forms.CharField(
        label='Номер транспорта',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )
    source_reservoir = forms.ModelChoiceField(
        label='Исходный резервуар',
        queryset=Reservoir.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    source_wagon = forms.ModelChoiceField(
        label='Исходный вагон',
        queryset=Wagon.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    target_reservoir = forms.ModelChoiceField(
        label='Целевой резервуар',
        queryset=Reservoir.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    target_wagon = forms.ModelChoiceField(
        label='Целевой вагон',
        queryset=Wagon.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    temperature = forms.DecimalField(
        label='Температура (°C)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        required=False
    )
    density = forms.DecimalField(
        label='Плотность',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        required=False
    )
    document_weight = forms.DecimalField(
        label='Вес по документу (кг)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=False
    )
    actual_weight = forms.DecimalField(
        label='Фактический вес (кг)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=False
    )
    note = forms.CharField(
        label='Примечание',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )

    class Meta:
        model = EstokadaMovement
        fields = [
            'transport_type', 'source_reservoir', 'source_wagon', 
            'target_reservoir', 'target_wagon', 'temperature', 
            'density', 'document_weight', 'actual_weight', 'note'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.operation_type = kwargs.pop('operation_type', None)
        super().__init__(*args, **kwargs)
        
        # Настройка полей выбора для резервуаров и вагонов
        self.fields['source_reservoir'].queryset = Reservoir.objects.all()
        self.fields['target_reservoir'].queryset = Reservoir.objects.all()
        self.fields['source_wagon'].queryset = Wagon.objects.all()
        self.fields['target_wagon'].queryset = Wagon.objects.all()
        
        # Если это существующая запись, заполняем поля данными из связанной модели Movement
        if self.instance and self.instance.pk and self.instance.movement:
            movement = self.instance.movement
            self.fields['movement_type'].initial = movement.movement_type
            self.fields['date'].initial = movement.date
            self.fields['product'].initial = movement.product
            self.fields['document_number'].initial = movement.document_number
            self.fields['quantity'].initial = movement.quantity
            self.fields['note'].initial = movement.note
            
            # Если передан тип операции, устанавливаем его и делаем поле недоступным
            if self.operation_type:
                self.fields['movement_type'].initial = self.operation_type
                self.fields['movement_type'].widget.attrs['readonly'] = True
                
                # В зависимости от типа операции скрываем или показываем поля
                self._setup_fields_for_operation_type(self.operation_type)
    
    def _setup_fields_for_operation_type(self, operation_type):
        """
        Настраивает поля формы в зависимости от типа операции
        """
        if operation_type == 'in':  # Приемка
            self.fields['source_reservoir'].widget = forms.HiddenInput()
            self.fields['source_wagon'].widget = forms.HiddenInput()
            # Для приемки важны целевые объекты (куда принимаем)
            
        elif operation_type == 'out':  # Продажа/Отгрузка
            self.fields['target_reservoir'].widget = forms.HiddenInput()
            self.fields['target_wagon'].widget = forms.HiddenInput()
            # Для отгрузки важны исходные объекты (откуда отгружаем)
            
        elif operation_type == 'transfer':  # Перемещение
            # Для перемещения важны и исходные, и целевые объекты
            pass
            
        elif operation_type == 'production':  # Производство
            # Специфические настройки для производства
            pass
    
    def clean(self):
        cleaned_data = super().clean()
        
        movement_type = cleaned_data.get('movement_type')
        source_reservoir = cleaned_data.get('source_reservoir')
        source_wagon = cleaned_data.get('source_wagon')
        target_reservoir = cleaned_data.get('target_reservoir')
        target_wagon = cleaned_data.get('target_wagon')
        
        # Проверки в зависимости от типа операции
        if movement_type == 'in':  # Приемка
            if not (target_reservoir or target_wagon):
                self.add_error(None, "Для операции приемки необходимо указать целевой резервуар или вагон")
                
            # Для приемки обязательны вес по документу и транспорт
            if not cleaned_data.get('document_weight'):
                self.add_error('document_weight', "Для приемки необходимо указать вес по документу")
            
            if not cleaned_data.get('transport_number'):
                self.add_error('transport_number', "Для приемки необходимо указать номер транспорта")
                
        elif movement_type == 'out':  # Отгрузка
            if not (source_reservoir or source_wagon):
                self.add_error(None, "Для операции отгрузки необходимо указать исходный резервуар или вагон")
                
        elif movement_type == 'transfer':  # Перемещение
            if not ((source_reservoir or source_wagon) and (target_reservoir or target_wagon)):
                self.add_error(None, "Для операции перемещения необходимо указать и источник, и назначение")
            
            # Для перемещения важно количество
            if not cleaned_data.get('quantity'):
                self.add_error('quantity', "Для перемещения необходимо указать количество")
        
        # Проверка плотности и температуры для специфических операций
        if movement_type in ('in', 'transfer') and cleaned_data.get('transport_type') == 'wagon':
            density = cleaned_data.get('density')
            temperature = cleaned_data.get('temperature')
            
            if not density:
                self.add_error('density', "Для вагона необходимо указать плотность")
            
            if not temperature:
                self.add_error('temperature', "Для вагона необходимо указать температуру")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Сохраняем сначала основную модель Movement
        movement_data = {
            'movement_type': self.cleaned_data['movement_type'],
            'date': self.cleaned_data['date'],
            'product': self.cleaned_data['product'],
            'document_number': self.cleaned_data.get('document_number', ''),
            'quantity': self.cleaned_data['quantity'],
            'note': self.cleaned_data.get('note', ''),
        }
        
        if self.instance and self.instance.pk and self.instance.movement:
            # Обновляем существующую запись Movement
            for key, value in movement_data.items():
                setattr(self.instance.movement, key, value)
                
            if self.user:
                self.instance.movement.created_by = self.user
                
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
        
        # Затем сохраняем модель EstokadaMovement
        return super().save(commit)

class SalesProcessForm(forms.ModelForm):
    """
    Форма для обработки заказа от отдела продаж
    """
    actual_quantity = forms.FloatField(
        label='Фактическое количество',
        required=True,
        help_text='Фактическое количество отгруженного товара'
    )
    
    transport_number = forms.CharField(
        label='Номер транспорта',
        required=True,
        max_length=50,
        help_text='Номер транспортного средства или вагона'
    )
    
    driver_name = forms.CharField(
        label='ФИО водителя',
        required=False,
        max_length=100,
        help_text='Имя водителя (если применимо)'
    )
    
    completed_notes = forms.CharField(
        label='Комментарий к отгрузке',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Дополнительная информация о выполнении заказа'
    )
    
    class Meta:
        model = Movement
        fields = [
            'actual_quantity',
            'transport_number',
            'driver_name',
            'completed_notes'
        ]
        
    def clean_actual_quantity(self):
        actual_quantity = self.cleaned_data.get('actual_quantity')
        if actual_quantity <= 0:
            raise forms.ValidationError('Фактическое количество должно быть положительным числом')
        return actual_quantity
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Устанавливаем статус завершено
        instance.status = 'completed'
        
        if commit:
            instance.save()
        return instance 