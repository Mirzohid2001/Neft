from django import forms
from .models import (
    ProductionProcess, RawMaterialProcessing, GasolineMixing,
    ProductionInput, ProductionOutput, ProductionType
)
from ..warehouse.models import Product, Reservoir

class ProductionProcessForm(forms.ModelForm):
    class Meta:
        model = ProductionProcess
        fields = [
            'process_number', 'process_type', 'start_date', 
            'input_source_type', 'input_reservoir', 'input_wagon',
            'output_source_type', 'output_reservoir', 'output_wagon',
            'notes'
        ]
        widgets = {
            'process_number': forms.TextInput(attrs={'class': 'form-control'}),
            'process_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'input_source_type': forms.Select(attrs={'class': 'form-select', 'id': 'input_source_type'}),
            'input_reservoir': forms.Select(attrs={'class': 'form-select', 'id': 'input_reservoir'}),
            'input_wagon': forms.Select(attrs={'class': 'form-select', 'id': 'input_wagon'}),
            'output_source_type': forms.Select(attrs={'class': 'form-select', 'id': 'output_source_type'}),
            'output_reservoir': forms.Select(attrs={'class': 'form-select', 'id': 'output_reservoir'}),
            'output_wagon': forms.Select(attrs={'class': 'form-select', 'id': 'output_wagon'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class RawMaterialProcessingForm(forms.ModelForm):
    class Meta:
        model = RawMaterialProcessing
        fields = [
            'raw_material', 'output_type', 'raw_material_quantity',
            'temperature', 'density', 'liter_volume', 'loss_percentage'
        ]
        widgets = {
            'raw_material': forms.Select(attrs={'class': 'form-select'}),
            'output_type': forms.Select(attrs={'class': 'form-select'}),
            'raw_material_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control'}),
            'density': forms.NumberInput(attrs={'class': 'form-control'}),
            'liter_volume': forms.NumberInput(attrs={'class': 'form-control'}),
            'loss_percentage': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class GasolineMixingForm(forms.ModelForm):
    class Meta:
        model = GasolineMixing
        fields = [
            'gasoline_type', 'output_quantity', 'temperature',
            'density', 'liter_volume'
        ]
        widgets = {
            'gasoline_type': forms.Select(attrs={'class': 'form-select'}),
            'output_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control'}),
            'density': forms.NumberInput(attrs={'class': 'form-control'}),
            'liter_volume': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ProductionInputForm(forms.ModelForm):
    class Meta:
        model = ProductionInput
        fields = ['material', 'quantity', 'temperature', 'density', 'liter_volume']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control'}),
            'density': forms.NumberInput(attrs={'class': 'form-control'}),
            'liter_volume': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ProductionOutputForm(forms.ModelForm):
    class Meta:
        model = ProductionOutput
        fields = ['product', 'quantity', 'temperature', 'density', 'liter_volume']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control'}),
            'density': forms.NumberInput(attrs={'class': 'form-control'}),
            'liter_volume': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ProductionTypeForm(forms.ModelForm):
    class Meta:
        model = ProductionType
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        } 