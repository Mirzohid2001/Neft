from django import forms
from django.forms import inlineformset_factory
from .models import (
    Product, Receiving, Giving, Stock,
    CanteenExpense, Project, ProjectItem, ReceivingItem, ProjectProduct,
    Order, OrderItem
)
from django.db import models

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'unit_price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ReceivingForm(forms.ModelForm):
    class Meta:
        model = Receiving
        fields = ['date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ReceivingItemForm(forms.ModelForm):
    class Meta:
        model = ReceivingItem
        fields = ['product', 'quantity', 'unit_price', 'comment']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class GivingForm(forms.ModelForm):
    class Meta:
        model = Giving
        fields = ['product', 'quantity', 'given_to', 'date', 'comment']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'given_to': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter products to only show those with available stock
        products_with_stock = Stock.objects.filter(quantity__gt=0).values_list('product', flat=True)
        
        # If we're editing an existing record, include its product in the queryset
        instance = kwargs.get('instance')
        if instance and instance.pk:
            # Create a queryset that includes both products with stock and the current product
            self.fields['product'].queryset = Product.objects.filter(
                models.Q(id__in=products_with_stock) | models.Q(id=instance.product_id)
            )
        else:
            # For new records, only show products with stock
            self.fields['product'].queryset = Product.objects.filter(id__in=products_with_stock)

class CanteenExpenseForm(forms.ModelForm):
    class Meta:
        model = CanteenExpense
        fields = ['product', 'unit_price', 'quantity', 'date']
        widgets = {
            'product': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'start_date', 'end_date', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class ProjectItemForm(forms.ModelForm):
    class Meta:
        model = ProjectItem
        fields = ['name', 'unit_price', 'quantity', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ProjectProductForm(forms.ModelForm):
    class Meta:
        model = ProjectProduct
        fields = ['product', 'quantity', 'date_used', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_used': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show products that have stock available
        products_with_stock = Stock.objects.filter(quantity__gt=0).values_list('product', flat=True)
        self.fields['product'].queryset = Product.objects.filter(id__in=products_with_stock)

class OrderForm(forms.ModelForm):
    """Form for creating and editing orders"""
    class Meta:
        model = Order
        fields = ['order_number', 'date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class OrderItemForm(forms.ModelForm):
    """Form for order items"""
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'unit', 'comment']
        widgets = {
            'product': forms.TextInput(attrs={'class': 'form-control product-input'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

# Create formset for OrderItems
OrderItemFormSet = inlineformset_factory(
    Order, OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True
) 