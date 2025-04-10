from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    AccountCategory, Account, JournalEntry, Transaction, 
    Invoice, InvoiceItem, Payment, TaxRate, FinancialPeriod,
    FinancialSetting, Category
)
from apps.warehouse.models import Movement, Product, Client, Supplier

class AccountCategoryForm(forms.ModelForm):
    """Форма для категории счетов"""
    class Meta:
        model = AccountCategory
        fields = ['name', 'code', 'type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class AccountForm(forms.ModelForm):
    """Форма для счета"""
    class Meta:
        model = Account
        fields = ['category', 'name', 'code', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class JournalEntryForm(forms.ModelForm):
    """Форма для бухгалтерской проводки"""
    class Meta:
        model = JournalEntry
        fields = ['date', 'reference_number', 'description', 'movement', 'local_movement', 'reservoir_movement']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Фильтруем движения, которые еще не имеют проводок
        used_movement_ids = JournalEntry.objects.exclude(
            id=self.instance.id if self.instance and self.instance.id else None
        ).values_list('movement_id', flat=True)
        
        self.fields['movement'].queryset = Movement.objects.exclude(
            id__in=used_movement_ids
        ).filter(status='completed')

class TransactionForm(forms.ModelForm):
    """Форма для отдельной транзакции"""
    class Meta:
        model = Transaction
        fields = ['account', 'date', 'debit', 'credit', 'description', 'reference']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        # journal_entry передается из представления
        self.journal_entry = kwargs.pop('journal_entry', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        debit = cleaned_data.get('debit')
        credit = cleaned_data.get('credit')
        
        # Проверяем, что заполнено только одно из полей: дебет или кредит
        if debit and credit:
            raise ValidationError("Заполните только одно из полей: дебет или кредит")
        
        if not debit and not credit:
            raise ValidationError("Необходимо заполнить либо дебет, либо кредит")
        
        return cleaned_data
    
    def save(self, commit=True):
        transaction = super().save(commit=False)
        
        if self.journal_entry:
            transaction.journal_entry = self.journal_entry
        
        if commit:
            transaction.save()
        
        return transaction

class JournalEntryTransactionFormSet(forms.BaseInlineFormSet):
    """Набор форм для транзакций в проводке"""
    def clean(self):
        super().clean()
        
        # Проверяем баланс дебета и кредита
        if any(self.errors):
            return
        
        total_debit = sum(form.cleaned_data.get('debit', 0) for form in self.forms if form.cleaned_data)
        total_credit = sum(form.cleaned_data.get('credit', 0) for form in self.forms if form.cleaned_data)
        
        if total_debit != total_credit:
            raise ValidationError("Сумма дебета должна быть равна сумме кредита")

class InvoiceForm(forms.ModelForm):
    """Форма для счета-фактуры"""
    class Meta:
        model = Invoice
        fields = [
            'invoice_type', 'number', 'date', 'due_date', 
            'client', 'supplier', 'movement',
            'tax_amount', 'discount_amount', 'notes', 'terms'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'terms': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Динамически обновляем queryset для client и supplier в зависимости от invoice_type
        if self.instance and self.instance.pk:
            if self.instance.invoice_type == 'sales':
                self.fields['supplier'].disabled = True
                self.fields['client'].required = True
            else:  # purchase
                self.fields['client'].disabled = True
                self.fields['supplier'].required = True
        
        # Фильтруем движения, которые еще не имеют счетов
        if not self.instance or not self.instance.pk:
            used_movement_ids = Invoice.objects.values_list('movement_id', flat=True)
            self.fields['movement'].queryset = Movement.objects.exclude(
                id__in=used_movement_ids
            ).filter(movement_type__in=['in', 'out'])
    
    def clean(self):
        cleaned_data = super().clean()
        invoice_type = cleaned_data.get('invoice_type')
        client = cleaned_data.get('client')
        supplier = cleaned_data.get('supplier')
        
        if invoice_type == 'sales' and not client:
            self.add_error('client', 'Для счета продажи требуется указать клиента')
        
        if invoice_type == 'purchase' and not supplier:
            self.add_error('supplier', 'Для счета закупки требуется указать поставщика')
        
        return cleaned_data

class InvoiceItemForm(forms.ModelForm):
    """Форма для позиции счета-фактуры"""
    class Meta:
        model = InvoiceItem
        fields = ['product', 'description', 'quantity', 'unit_price', 'tax_rate']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        # invoice передается из представления
        self.invoice = kwargs.pop('invoice', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        item = super().save(commit=False)
        
        if self.invoice:
            item.invoice = self.invoice
        
        if commit:
            item.save()
        
        return item

class PaymentForm(forms.ModelForm):
    """Форма для платежа"""
    class Meta:
        model = Payment
        fields = ['invoice', 'date', 'amount', 'payment_method', 'reference', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        # Опциональный параметр для фильтрации счетов
        invoice_type = kwargs.pop('invoice_type', None)
        super().__init__(*args, **kwargs)
        
        # Фильтруем счета по типу (если указан) и статусу (не оплачены)
        queryset = Invoice.objects.filter(status__in=['draft', 'sent'])
        if invoice_type:
            queryset = queryset.filter(invoice_type=invoice_type)
        
        self.fields['invoice'].queryset = queryset
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        invoice = self.cleaned_data.get('invoice')
        
        if invoice and amount:
            # Сумма всех существующих платежей для этого счета
            existing_payments = Payment.objects.filter(invoice=invoice)
            if self.instance and self.instance.pk:
                existing_payments = existing_payments.exclude(pk=self.instance.pk)
            
            total_paid = sum(payment.amount for payment in existing_payments)
            
            if total_paid + amount > invoice.total:
                raise ValidationError(
                    f"Сумма платежей ({total_paid + amount}) превышает сумму счета ({invoice.total})"
                )
        
        return amount

class TaxRateForm(forms.ModelForm):
    """Форма для ставки налога"""
    class Meta:
        model = TaxRate
        fields = ['name', 'rate', 'is_default', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class FinancialPeriodForm(forms.ModelForm):
    """Форма для финансового периода"""
    class Meta:
        model = FinancialPeriod
        fields = ['name', 'start_date', 'end_date', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and start_date >= end_date:
            raise ValidationError("Дата начала должна быть меньше даты окончания")
        
        if start_date and end_date:
            overlapping = FinancialPeriod.objects.filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            )
            
            if self.instance and self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            
            if overlapping.exists():
                raise ValidationError("Период пересекается с существующими периодами")
        
        return cleaned_data

class FinancialSettingForm(forms.ModelForm):
    """Форма для настроек бухгалтерии"""
    class Meta:
        model = FinancialSetting
        fields = [
            'company_name', 'default_payment_term', 'invoice_prefix',
            'next_invoice_number', 'default_debit_account', 'default_credit_account',
            'default_tax_rate', 'fiscal_year_start', 'currency_symbol'
        ]
        widgets = {
            'fiscal_year_start': forms.DateInput(attrs={'type': 'date'}),
        }

class FinancialReportForm(forms.Form):
    """Форма для генерации финансовых отчетов"""
    REPORT_TYPES = (
        ('summary', 'Сводный отчет'),
        ('product', 'По продуктам'),
        ('client', 'По клиентам'),
        ('supplier', 'По поставщикам'),
        ('balance', 'Баланс счетов'),
    )
    
    report_type = forms.ChoiceField(choices=REPORT_TYPES, label='Тип отчета')
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label='Дата с')
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label='Дата по')
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), 
        required=False, 
        label='Продукт',
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(), 
        required=False, 
        label='Клиент',
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(), 
        required=False, 
        label='Поставщик',
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(), 
        required=False, 
        label='Счет',
        widget=forms.Select(attrs={'class': 'select2'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Устанавливаем начальные значения дат
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        if not self.initial.get('date_from'):
            self.initial['date_from'] = month_start
        
        if not self.initial.get('date_to'):
            self.initial['date_to'] = today
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        report_type = cleaned_data.get('report_type')
        if report_type == 'product' and not cleaned_data.get('product'):
            self.add_error('product', 'Для отчета по продуктам необходимо выбрать продукт')
        
        if report_type == 'client' and not cleaned_data.get('client'):
            self.add_error('client', 'Для отчета по клиентам необходимо выбрать клиента')
        
        if report_type == 'supplier' and not cleaned_data.get('supplier'):
            self.add_error('supplier', 'Для отчета по поставщикам необходимо выбрать поставщика')
        
        if report_type == 'balance' and not cleaned_data.get('account'):
            self.add_error('account', 'Для отчета по балансу необходимо выбрать счет')
        if date_from and date_to and date_from > date_to:
            raise ValidationError("Дата начала должна быть меньше или равна дате окончания")
        
        return cleaned_data 

class CategoryForm(forms.ModelForm):
    """Форма для категорий доходов и расходов"""
    class Meta:
        model = Category
        fields = ['name', 'type', 'description', 'icon', 'color']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
        } 