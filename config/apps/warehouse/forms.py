from django import forms
from django.utils import timezone
from .models import Movement, Product, Wagon, Batch, Reservoir, ReservoirMovement,LocalClient, LocalMovement,Placement,Client, WagonType, Warehouse, InventoryAudit, InventoryAuditItem, ProductMinLevel, PurchasePlan, PurchasePlanItem, Supplier, SupplierRating, ProductSupplier, OrderPoint, PurchaseNotification, Transport, EstokadaOperation
import json
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

class MovementForm(forms.ModelForm):
    movement_type = forms.ChoiceField(choices=Movement.MOVEMENT_TYPES, required=True)
    date = forms.DateField(initial=timezone.now, required=True)
    product = forms.ModelChoiceField(queryset=Product.objects.all(), required=True)
    document_number = forms.CharField(max_length=100, required=False)
    
    # Общие поля
    source_warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.all(), required=False)
    target_warehouse = forms.ModelChoiceField(queryset=Warehouse.objects.all(), required=False)
    quantity = forms.FloatField(required=True)
    note = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = Movement
        fields = [
            'movement_type', 'date', 'product', 'document_number',
            'source_warehouse', 'target_warehouse', 'quantity', 'note', 'status'
        ]

    def __init__(self, *args, **kwargs):
        # Сохраняем параметр user для использования при сохранении
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Инициализируем поля со значениями по умолчанию
        if self.instance and self.instance.pk:
            if self.instance.source_warehouse:
                self.fields['source_warehouse'].initial = self.instance.source_warehouse.id
            if self.instance.target_warehouse:
                self.fields['target_warehouse'].initial = self.instance.target_warehouse.id

    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get('movement_type')
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if not movement_type:
            self.add_error('movement_type', 'Тип операции обязателен')
            
        if not product:
            self.add_error('product', 'Продукт обязателен')
            
        if not quantity or quantity <= 0:
            self.add_error('quantity', 'Количество должно быть положительным числом')
        
        # Проверяем наличие необходимых полей в зависимости от типа операции
        if movement_type == 'in' and not cleaned_data.get('target_warehouse'):
            self.add_error('target_warehouse', 'Для приемки необходимо указать целевой склад')
            
        if movement_type == 'out' and not cleaned_data.get('source_warehouse'):
            self.add_error('source_warehouse', 'Для продажи необходимо указать исходный склад')
            
        if movement_type == 'transfer':
            if not cleaned_data.get('source_warehouse'):
                self.add_error('source_warehouse', 'Для перемещения необходимо указать исходный склад')
            if not cleaned_data.get('target_warehouse'):
                self.add_error('target_warehouse', 'Для перемещения необходимо указать целевой склад')
                
        # Проверяем наличие продукта, если это расход или перемещение
        if movement_type in ['out', 'transfer'] and product:
            available = product.net_quantity()
            if quantity > available:
                self.add_error('quantity', f'Недостаточно продукта на складе. Доступно: {available}')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Устанавливаем пользователя, создавшего запись
        if self.user:
            instance.created_by = self.user
        
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

class EstokadaOperationForm(forms.ModelForm):
    class Meta:
        model = EstokadaOperation
        fields = [
            'actual_quantity', 
            'actual_density', 
            'actual_temperature', 
            'status', 
            'notes'
        ]
        widgets = {
            'actual_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0'
            }),
            'actual_density': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0'
            }),
            'actual_temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Введите примечания к операции'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ограничиваем выбор статусов в зависимости от текущего статуса
        instance = kwargs.get('instance')
        if instance:
            if instance.status == 'pending':
                self.fields['status'].choices = [
                    ('pending', 'Ожидает обработки'),
                    ('measuring', 'Измерение')
                ]
            elif instance.status == 'measuring':
                self.fields['status'].choices = [
                    ('measuring', 'Измерение'),
                    ('processing', 'Обработка данных')
                ]
            elif instance.status == 'processing':
                self.fields['status'].choices = [
                    ('processing', 'Обработка данных'),
                    ('completed', 'Завершен'),
                    ('cancelled', 'Отменен')
                ]
            elif instance.status in ['completed', 'cancelled']:
                self.fields['status'].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        cleaned_data = super().clean()
        actual_quantity = cleaned_data.get('actual_quantity')
        actual_density = cleaned_data.get('actual_density')
        actual_temperature = cleaned_data.get('actual_temperature')
        status = cleaned_data.get('status')

        if actual_quantity is not None and actual_quantity < 0:
            self.add_error('actual_quantity', 'Фактическое количество не может быть отрицательным')

        if actual_density is not None and actual_density <= 0:
            self.add_error('actual_density', 'Плотность должна быть положительным числом')

        if actual_temperature is not None:
            if actual_temperature < -50 or actual_temperature > 100:
                self.add_error('actual_temperature', 'Температура должна быть в диапазоне от -50 до 100 градусов')

        # Проверка заполнения обязательных полей при смене статуса
        if status in ['processing', 'completed']:
            if not actual_quantity:
                self.add_error('actual_quantity', 'Необходимо указать фактическое количество')
            if not actual_density:
                self.add_error('actual_density', 'Необходимо указать плотность')
            if actual_temperature is None:
                self.add_error('actual_temperature', 'Необходимо указать температуру')

        return cleaned_data

class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ['transport_type', 'transport_number', 'wagon', 'wagon_type',
                 'density', 'temperature', 'volume', 'quantity', 'doc_quantity',
                 'warehouse', 'notes']
        widgets = {
            'transport_type': forms.Select(attrs={'class': 'form-select'}),
            'transport_number': forms.TextInput(attrs={'class': 'form-control'}),
            'wagon': forms.Select(attrs={'class': 'form-select'}),
            'wagon_type': forms.Select(attrs={'class': 'form-select'}),
            'density': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control'}),
            'volume': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'doc_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['wagon'].required = False
        self.fields['wagon_type'].required = False
        
        # Динамически обновляем поля в зависимости от типа транспорта
        if self.instance.transport_type == 'truck':
            del self.fields['wagon']
            del self.fields['wagon_type']
        elif self.instance.transport_type == 'wagon':
            self.fields['wagon'].required = True
            self.fields['wagon_type'].required = True
