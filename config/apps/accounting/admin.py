from django.contrib import admin
from .models import FinancialRecord


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    fields = ['product', 'warehouse', 'date', 'movement_type', 'quantity', 'total_price_usd', 'total_price_sum']
    list_display = ('product', 'warehouse', 'date', 'movement_type', 'quantity', 'total_price_usd', 'total_price_sum')
    search_fields = ('product__name', 'warehouse__name', 'date')