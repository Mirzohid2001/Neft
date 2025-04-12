from django import forms
from django.utils import timezone
from .models import Movement, Product, Wagon, Batch, Reservoir, ReservoirMovement,LocalClient, LocalMovement,Placement,Client, WagonType, Warehouse, InventoryAudit, InventoryAuditItem, ProductMinLevel, PurchasePlan, PurchasePlanItem, Supplier, SupplierRating, ProductSupplier, OrderPoint, PurchaseNotification, Transport
import json
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

class MovementForm(forms.ModelForm):
    movement_type = forms.ChoiceField(choices=Movement.MOVEMENT_TYPES, required=True)
    date = forms.DateField(initial=timezone.now, required=True)
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=True)
    source_product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False)
    document_number = forms.CharField(max_length=100, required=False)
    client_type = forms.ChoiceField(
        choices=[('local', 'Местный'), ('international', 'Международный')],
        required=False
    )
    client = forms.ModelChoiceField(queryset=Client.objects.all(), required=False)
    source_reservoir = forms.ModelChoiceField(queryset=None, required=False)
    source_wagon = forms.ModelChoiceField(queryset=None, required=False)
    target_reservoir = forms.ModelChoiceField(queryset=None, required=False)
    target_wagon = forms.ModelChoiceField(queryset=None, required=False)
    source_quantity = forms.FloatField(required=False)
    target_quantity = forms.FloatField(required=False)
    material_quantity = forms.FloatField(required=False)
    expected_quantity = forms.FloatField(required=False)
    note = forms.CharField(widget=forms.Textarea, required=False)
    transports_json = forms.CharField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Movement
        fields = [
            'movement_type', 'date', 'product', 'source_product', 'document_number', 'client_type', 'client',
            'source_reservoir', 'source_wagon', 'target_reservoir', 'target_wagon',
            'expected_quantity', 'note'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.department = kwargs.pop('department', None)
        super().__init__(*args, **kwargs)
        
        # Получаем все резервуары и вагоны для использования в шаблоне
        self.reservoirs = Reservoir.objects.all()
        self.wagons = Wagon.objects.all()
        self.wagon_types = WagonType.objects.all()
        
        # Установим источники данных для полей выбора
        self.fields['source_reservoir'].queryset = self.reservoirs
        self.fields['target_reservoir'].queryset = self.reservoirs
        self.fields['source_wagon'].queryset = self.wagons
        self.fields['target_wagon'].queryset = self.wagons
        
        # Скрываем поля в зависимости от роли пользователя
        if self.user and self.department == 'sales':
            # Для отдела продаж фокусируемся на транспортных операциях
            # Устанавливаем только клиентов, которые относятся к отделу продаж
            try:
                self.fields['client'].queryset = Client.objects.filter(
                    Q(client_type='local') | Q(client_type='international')
                )
            except:
                # Оставляем всех клиентов, если поля client_type нет
                pass
        elif self.user and self.department == 'factory':
            # Для производства скрываем поля, связанные с клиентами и вагонами
            pass
        
        # Если это существующая операция (редактирование)
        if self.instance and self.instance.pk:
            # Заполняем JSON с транспортными средствами из существующих данных
            transports_data = []
            for transport in Transport.objects.filter(movement=self.instance):
                transport_data = {
                    'transport_number': transport.transport_number,
                    'mass': transport.quantity,
                    'doc_mass': transport.doc_ton * 1000 if transport.doc_ton else 0,
                    'diff': (transport.quantity - (transport.doc_ton * 1000)) if transport.doc_ton else transport.quantity
                }
                transports_data.append(transport_data)
            
            if transports_data:
                self.fields['transports_json'].initial = json.dumps(transports_data)
            
            # Установим тип клиента на основе существующего клиента
            client = self.instance.client
            if client:
                # Логика определения типа клиента (местный/международный)
                try:
                    client_type = getattr(client, 'client_type', None)
                    if client_type:
                        self.fields['client_type'].initial = client_type
                except:
                    pass
                
            # Установим поля для источника/назначения
            if self.instance.source_reservoir:
                self.fields['source_reservoir'].initial = self.instance.source_reservoir.id
            if self.instance.source_wagon:
                self.fields['source_wagon'].initial = self.instance.source_wagon.id
            if self.instance.target_reservoir:
                self.fields['target_reservoir'].initial = self.instance.target_reservoir.id
            if self.instance.target_wagon:
                self.fields['target_wagon'].initial = self.instance.target_wagon.id

    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get('movement_type')
        product = cleaned_data.get('product')
        transports_json = cleaned_data.get('transports_json', '[]')
        
        if not movement_type:
            self.add_error('movement_type', 'Тип операции обязателен')
            
        if not product:
            self.add_error('product', 'Продукт обязателен')
        
        # Проверка клиента для приемки и продажи
        if movement_type in ['in', 'out']:
            client_type = cleaned_data.get('client_type')
            client = cleaned_data.get('client')
            
            if not client_type:
                self.add_error('client_type', 'Тип клиента обязателен для приемки/продажи')
                
            if not client:
                self.add_error('client', 'Клиент обязателен для приемки/продажи')
        
        # Проверка транспортных данных для приемки и продажи
        if movement_type in ['in', 'out']:
            try:
                transports_data = json.loads(transports_json)
                
                if not transports_data:
                    self.add_error(None, 'Необходимо добавить хотя бы один транспорт')
                    
                for i, transport_data in enumerate(transports_data):
                    transport_type = transport_data.get('transport_type')
                    transport_number = transport_data.get('transport_number')
                    mass = transport_data.get('mass')
                    doc_mass = transport_data.get('doc_mass')
                    
                    if not transport_type:
                        self.add_error(None, f'Транспорт #{i+1}: Тип транспорта обязателен')
                        
                    if not transport_number:
                        self.add_error(None, f'Транспорт #{i+1}: Номер транспорта обязателен')
                        
                    if not mass or float(mass) <= 0:
                        self.add_error(None, f'Транспорт #{i+1}: Фактический вес должен быть больше 0')
                        
                    if not doc_mass or float(doc_mass) <= 0:
                        self.add_error(None, f'Транспорт #{i+1}: Вес по документу должен быть больше 0')
                    
                    # Проверка для вагонов
                    if transport_type == 'wagon':
                        wagon_type = transport_data.get('wagon_type')
                        if not wagon_type:
                            self.add_error(None, f'Транспорт #{i+1}: Тип вагона обязателен для вагонов')
            
            except json.JSONDecodeError:
                self.add_error(None, 'Ошибка в данных о транспорте. Неверный JSON-формат.')
        
        # Проверка для производства
        if movement_type == 'production':
            source_product = cleaned_data.get('source_product')
            material_quantity = cleaned_data.get('material_quantity')
            source_quantity = cleaned_data.get('source_quantity')
            source_reservoir = cleaned_data.get('source_reservoir')
            target_reservoir = cleaned_data.get('target_reservoir')
            
            if not source_product:
                self.add_error('source_product', 'Продукт источника обязателен для производства')
                
            if not material_quantity or material_quantity <= 0:
                self.add_error('material_quantity', 'Вес продукта должен быть больше 0')
                
            if not source_quantity or source_quantity <= 0:
                self.add_error('source_quantity', 'Вес источника должен быть больше 0')
                
            if not source_reservoir:
                self.add_error('source_reservoir', 'Источник обязателен для производства')
                
            if not target_reservoir:
                self.add_error('target_reservoir', 'Назначение обязательно для производства')
        
        # Проверка для перемещения
        if movement_type == 'transfer':
            source_quantity = cleaned_data.get('source_quantity')
            target_quantity = cleaned_data.get('target_quantity')
            
            # Должен быть указан или source_reservoir или source_wagon
            source_reservoir = cleaned_data.get('source_reservoir')
            source_wagon = cleaned_data.get('source_wagon')
            
            # Должен быть указан или target_reservoir или target_wagon
            target_reservoir = cleaned_data.get('target_reservoir')
            target_wagon = cleaned_data.get('target_wagon')
            
            if not (source_reservoir or source_wagon):
                self.add_error(None, 'Для перемещения нужно указать источник (резервуар или вагон)')
                
            if not (target_reservoir or target_wagon):
                self.add_error(None, 'Для перемещения нужно указать назначение (резервуар или вагон)')
                
            if not source_quantity or source_quantity <= 0:
                self.add_error('source_quantity', 'Количество источника должно быть больше 0')
                
            if not target_quantity or target_quantity <= 0:
                self.add_error('target_quantity', 'Количество назначения должно быть больше 0')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        movement_type = self.cleaned_data.get('movement_type')
        transports_json = self.cleaned_data.get('transports_json', '[]')
        expected_quantity = self.cleaned_data.get('expected_quantity') or 0
        
        # Сохраняем информацию о транспортных средствах
        instance.transports_json = transports_json
        
        # Устанавливаем количество в тоннах (все поля ввода в кг, но храним в тоннах)
        if movement_type == 'in' or movement_type == 'out':
            # Для приёмки и продажи берем значение из total-mass в кг и конвертируем в тонны
            instance.quantity = expected_quantity  # уже в тоннах
        elif movement_type == 'transfer':
            # Для перемещения берем значение из source_quantity в кг и конвертируем в тонны
            source_quantity = self.cleaned_data.get('source_quantity') or 0
            instance.quantity = source_quantity / 1000  # конвертируем из кг в тонны
        elif movement_type == 'production':
            # Для производства берем значение из material_quantity в кг и конвертируем в тонны
            material_quantity = self.cleaned_data.get('material_quantity') or 0
            source_quantity = self.cleaned_data.get('source_quantity') or 0
            instance.quantity = material_quantity / 1000  # конвертируем из кг в тонны
            instance.source_quantity = source_quantity / 1000  # источник в тоннах
            instance.source_product = self.cleaned_data.get('source_product')
        
        # Сохраняем источник и назначение
        instance.source_reservoir = self.cleaned_data.get('source_reservoir')
        instance.source_wagon = self.cleaned_data.get('source_wagon')
        instance.target_reservoir = self.cleaned_data.get('target_reservoir')
        instance.target_wagon = self.cleaned_data.get('target_wagon')
        
        if commit:
            instance.save()
        
        return instance

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'code',
            'name',
            'category',
            'description'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
        }

class WagonForm(forms.ModelForm):
    class Meta:
        model = Wagon
        fields = ['wagon_number', 'wagon_type', 'net_weight', 'meter_weight', 'capacity', 'volume', 'price_sum', 'condition']
        widgets = {
            'wagon_number': forms.TextInput(attrs={'class': 'form-control'}),
            'wagon_type': forms.Select(attrs={'class': 'form-select'}),
            'net_weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'meter_weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'volume': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_sum': forms.NumberInput(attrs={'class': 'form-control'}),
            'condition': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BatchForm(forms.ModelForm):
    manufacture_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    class Meta:
        model = Batch
        fields = ['product', 'batch_number', 'manufacture_date', 'expiry_date']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'batch_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ReservoirForm(forms.ModelForm):
    meter_shtok_map_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = Reservoir
        fields = ['warehouse', 'name', 'capacity', 'product']
        widgets = {
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.meter_shtok_map:
            # Калибровочные данные будут загружены через JavaScript
            pass
            
    def save(self, commit=True):
        instance = super().save(commit=False)
        meter_shtok_map_json = self.cleaned_data.get('meter_shtok_map_json')
        
        if meter_shtok_map_json:
            try:
                instance.meter_shtok_map = json.loads(meter_shtok_map_json)
            except json.JSONDecodeError:
                instance.meter_shtok_map = {}
        
        if commit:
            instance.save()
        return instance

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'location', 'zone', 'location_code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'zone': forms.TextInput(attrs={'class': 'form-control'}),
            'location_code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if self.fields[field].required:
                self.fields[field].label = f"{self.fields[field].label} *"

class ReservoirMovementForm(forms.ModelForm):
    class Meta:
        model = ReservoirMovement
        fields = ['reservoir', 'product', 'date', 'movement_type', 'quantity', 'note']
        widgets = {
            'reservoir': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class LocalClientForm(forms.ModelForm):
    class Meta:
        model = LocalClient
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }


class LocalMovementForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    doc_ton = forms.FloatField(
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_doc_ton'})
    )
    density = forms.FloatField(
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_density'})
    )
    liter = forms.FloatField(
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_liter'})
    )
    mass = forms.FloatField(
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_mass'})
    )
    specific_weight = forms.FloatField(
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id':'id_specific_weight'})
    )
    quantity = forms.FloatField(
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_quantity'})
    )

    class Meta:
        model = LocalMovement
        fields = [
            'client', 'wagon','reservoir','product', 'date',
            'density', 'temperature', 'liter', 'mass', 'specific_weight',
            'doc_ton', 'quantity', 'note'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'wagon': forms.Select(attrs={'class': 'form-select'}),
            'reservoir': forms.Select(attrs={'class': 'form-select'}), 
            'product': forms.Select(attrs={'class': 'form-select'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows':3}),
        }

class PlacementForm(forms.ModelForm):
    class Meta:
        model = Placement
        fields = ['product', 'wagon', 'reservoir', 'quantity', 'movement']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'wagon': forms.Select(attrs={'class': 'form-select'}),
            'reservoir': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'movement': forms.Select(attrs={'class': 'form-select'}),
        }

class WagonTypeForm(forms.ModelForm):
    meter_shtok_map_json = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = WagonType
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.meter_shtok_map:
            # No need to set initial value for meter_shtok_map_json as we'll load it via JavaScript
            pass
            
    def save(self, commit=True):
        instance = super().save(commit=False)
        meter_shtok_map_json = self.cleaned_data.get('meter_shtok_map_json')
        
        if meter_shtok_map_json:
            try:
                instance.meter_shtok_map = json.loads(meter_shtok_map_json)
            except json.JSONDecodeError:
                instance.meter_shtok_map = {}
        
        if commit:
            instance.save()
        return instance

class InventoryAuditForm(forms.ModelForm):
    class Meta:
        model = InventoryAudit
        fields = ['name', 'start_date', 'description']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'status':
                self.fields[field].widget.attrs.update({'class': 'form-control'})


class InventoryAuditItemForm(forms.ModelForm):
    class Meta:
        model = InventoryAuditItem
        fields = ['product', 'location', 'actual_quantity', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class ProductMinLevelForm(forms.ModelForm):
    class Meta:
        model = ProductMinLevel
        fields = ['min_quantity', 'optimal_quantity', 'max_quantity', 'alert_enabled', 'alert_threshold']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field != 'alert_enabled':
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            else:
                self.fields[field].widget.attrs.update({'class': 'form-check-input'})


class PurchasePlanForm(forms.ModelForm):
    class Meta:
        model = PurchasePlan
        fields = ['name', 'plan_date', 'notes']
        widgets = {
            'plan_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class PurchasePlanItemForm(forms.ModelForm):
    class Meta:
        model = PurchasePlanItem
        fields = ['product', 'quantity', 'priority', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


PurchasePlanItemFormSet = forms.inlineformset_factory(
    PurchasePlan, 
    PurchasePlanItem, 
    form=PurchasePlanItemForm,
    extra=1, 
    can_delete=True
)


class GenerateForecastForm(forms.Form):
    start_date = forms.DateField(
        label='Дата начала', 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        label='Дата окончания', 
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
        label='Продукты (если не выбраны, будут использованы все)',
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError('Дата окончания не может быть раньше даты начала')
            
        return cleaned_data

class SupplierForm(forms.ModelForm):
    """Форма для создания и редактирования поставщика"""
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_person', 'phone', 'email',
            'address', 'website', 'is_active', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError('Введите корректный email адрес.')
        return email

class SupplierRatingForm(forms.ModelForm):
    """Форма для создания оценки поставщика"""
    class Meta:
        model = SupplierRating
        fields = ['supplier', 'category', 'rating', 'comment']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating and (rating < 1 or rating > 5):
            raise forms.ValidationError('Оценка должна быть от 1 до 5.')
        return rating

class ProductSupplierForm(forms.ModelForm):
    """Форма для создания связи продукта с поставщиком"""
    class Meta:
        model = ProductSupplier
        fields = [
            'supplier', 'product', 'price', 'is_preferred',
            'min_order_quantity', 'lead_time', 'notes'
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_preferred': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_order_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'lead_time': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

    def clean(self):
        cleaned_data = super().clean()
        min_order_quantity = cleaned_data.get('min_order_quantity')
        if min_order_quantity and min_order_quantity <= 0:
            self.add_error('min_order_quantity', 'Минимальное количество заказа должно быть больше 0.')
        
        lead_time = cleaned_data.get('lead_time')
        if lead_time and lead_time <= 0:
            self.add_error('lead_time', 'Срок поставки должен быть больше 0 дней.')
        
        return cleaned_data


class OrderPointForm(forms.ModelForm):
    class Meta:
        model = OrderPoint
        fields = ['product', 'reorder_point', 'safety_stock', 'order_quantity', 
                 'lead_time_demand', 'auto_order', 'notify_emails']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control'}),
            'safety_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'order_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'lead_time_demand': forms.NumberInput(attrs={'class': 'form-control'}),
            'auto_order': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_emails': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 
                                                'placeholder': 'Введите email адреса через запятую'})
        }
    
    def clean_notify_emails(self):
        emails = self.cleaned_data['notify_emails']
        if not emails:
            return emails
        
        email_list = [e.strip() for e in emails.split(',')]
        for email in email_list:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError(f'"{email}" не является корректным email адресом.')
        
        return emails


class PurchaseNotificationForm(forms.ModelForm):
    class Meta:
        model = PurchaseNotification
        fields = ['product', 'quantity_needed', 'recommended_supplier', 
                 'recommended_order_date', 'expected_delivery_date', 'status', 'note']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity_needed': forms.NumberInput(attrs={'class': 'form-control'}),
            'recommended_supplier': forms.Select(attrs={'class': 'form-select'}),
            'recommended_order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }
