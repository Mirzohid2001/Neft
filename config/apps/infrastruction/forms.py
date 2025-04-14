from django import forms
from .models import (
    Product, Receiving, Giving, Stock,
    CanteenExpense, Project, ProjectItem
)

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
        fields = ['product', 'quantity', 'date']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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