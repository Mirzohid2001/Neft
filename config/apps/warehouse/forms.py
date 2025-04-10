from django import forms
from django.utils import timezone
from .models import Movement, Product, Wagon, Batch, Reservoir, ReservoirMovement,LocalClient, LocalMovement,Placement,Client, WagonType, Warehouse, InventoryAudit, InventoryAuditItem, ProductMinLevel, PurchasePlan, PurchasePlanItem, Supplier, SupplierRating, ProductSupplier, OrderPoint, PurchaseNotification
import json
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

class MovementForm(forms.ModelForm):
    class Meta:
        model = Movement
        fields = [
            'movement_type', 'date', 'document_number', 'product', 
            'client_type', 'client', 'quantity', 'expected_quantity',
            'temperature', 'density', 'liter', 
            'source_warehouse', 'source_reservoir', 'source_wagon',
            'target_warehouse', 'target_reservoir', 'target_wagon',
            'transport_number', 'transport_photo',
            'production_loss', 'production_loss_reason',
            'price_sum', 'price_usd', 'note', 'status',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'document_number': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'expected_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'density': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'liter': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'price_sum': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'production_loss': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'production_loss_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.fields['product'].queryset = Product.objects.all()
        self.fields['client'].queryset = Client.objects.all()
        self.fields['source_warehouse'].queryset = Warehouse.objects.all()
        self.fields['source_reservoir'].queryset = Reservoir.objects.all()
        self.fields['source_wagon'].queryset = Wagon.objects.all()
        self.fields['target_warehouse'].queryset = Warehouse.objects.all()
        self.fields['target_reservoir'].queryset = Reservoir.objects.all()
        self.fields['target_wagon'].queryset = Wagon.objects.all()
        
        # Динамически скрываем/показываем поля в зависимости от типа движения в JavaScript
        
        # Если форма инициализирована с пользователем, сохраняем его
        if user:
            self.user = user
    
    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get('movement_type')
        
        # Проверки для приемки
        if movement_type == 'in':
            target_warehouse = cleaned_data.get('target_warehouse')
            target_reservoir = cleaned_data.get('target_reservoir')
            target_wagon = cleaned_data.get('target_wagon')
            
            if not (target_warehouse or target_reservoir or target_wagon):
                self.add_error(None, 'Для приёмки необходимо указать целевое место хранения')
        
        # Проверки для продажи
        elif movement_type == 'out':
            source_warehouse = cleaned_data.get('source_warehouse')
            source_reservoir = cleaned_data.get('source_reservoir')
            source_wagon = cleaned_data.get('source_wagon')
            client = cleaned_data.get('client')
            
            if not (source_warehouse or source_reservoir or source_wagon):
                self.add_error(None, 'Для продажи необходимо указать источник')
                
            if not client:
                self.add_error('client', 'Для продажи необходимо указать клиента')
        
        # Проверки для производства
        elif movement_type == 'production':
            source_reservoir = cleaned_data.get('source_reservoir')
            source_wagon = cleaned_data.get('source_wagon')
            target_reservoir = cleaned_data.get('target_reservoir')
            target_wagon = cleaned_data.get('target_wagon')
            
            if not (source_reservoir or source_wagon):
                self.add_error(None, 'Для производства необходимо указать исходный резервуар или вагон')
                
            if not (target_reservoir or target_wagon):
                self.add_error(None, 'Для производства необходимо указать целевой резервуар или вагон')
        
        # Проверки для перемещения
        elif movement_type == 'transfer':
            source_reservoir = cleaned_data.get('source_reservoir')
            source_wagon = cleaned_data.get('source_wagon')
            target_reservoir = cleaned_data.get('target_reservoir')
            target_wagon = cleaned_data.get('target_wagon')
            
            if not (source_reservoir or source_wagon):
                self.add_error(None, 'Для перемещения необходимо указать исходный резервуар или вагон')
                
            if not (target_reservoir or target_wagon):
                self.add_error(None, 'Для перемещения необходимо указать целевой резервуар или вагон')
                
            if source_reservoir and target_reservoir and source_reservoir == target_reservoir:
                self.add_error(None, 'Исходный и целевой резервуары не могут быть одинаковыми')
                
            if source_wagon and target_wagon and source_wagon == target_wagon:
                self.add_error(None, 'Исходный и целевой вагоны не могут быть одинаковыми')
        
        return cleaned_data
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Устанавливаем пользователя, создавшего движение
        if hasattr(self, 'user') and not instance.created_by:
            instance.created_by = self.user
        
        # Если статус изменен на "confirmed", устанавливаем пользователя, подтвердившего
        if instance.status == 'confirmed' and hasattr(self, 'user'):
            instance.confirmed_by = self.user
            
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
