from django.contrib import admin
from django.utils.html import format_html
from .models import SalesMovement, SalesContract, SalesContractProduct

@admin.register(SalesMovement)
class SalesMovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_date', 'client', 'get_product', 'get_quantity', 'total_price', 'get_status')
    list_filter = ('movement__status', 'movement__date', 'client')
    search_fields = ('movement__document_number', 'invoice_number', 'client__title', 'movement__product__name')
    date_hierarchy = 'movement__date'
    
    def get_date(self, obj):
        return obj.movement.date if obj.movement else None
    get_date.short_description = 'Дата'
    get_date.admin_order_field = 'movement__date'
    
    def get_product(self, obj):
        return obj.movement.product if obj.movement else None
    get_product.short_description = 'Продукт'
    get_product.admin_order_field = 'movement__product__name'
    
    def get_quantity(self, obj):
        return obj.movement.quantity if obj.movement else None
    get_quantity.short_description = 'Количество'
    get_quantity.admin_order_field = 'movement__quantity'
    
    def get_status(self, obj):
        status = obj.movement.get_status_display() if obj.movement else None
        if status:
            status_colors = {
                'Создан': 'blue',
                'Подтвержден': 'orange',
                'Обработан': 'purple',
                'Завершен': 'green',
                'Отменен': 'red',
            }
            color = status_colors.get(status, 'black')
            return format_html('<span style="color: {};">{}</span>', color, status)
        return None
    get_status.short_description = 'Статус движения'
    get_status.admin_order_field = 'movement__status'

class SalesContractProductInline(admin.TabularInline):
    model = SalesContractProduct
    extra = 0
    fields = ('product', 'quantity', 'unit_price', 'total_price')

@admin.register(SalesContract)
class SalesContractAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'client', 'start_date', 'end_date', 'total_amount', 'status')
    list_filter = ('status', 'start_date', 'end_date', 'client')
    search_fields = ('contract_number', 'client__title')
    date_hierarchy = 'start_date'
    inlines = [SalesContractProductInline]
