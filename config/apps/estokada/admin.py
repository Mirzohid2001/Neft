from django.contrib import admin
from .models import EstokadaMovement

@admin.register(EstokadaMovement)
class EstokadaMovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_date', 'get_product', 'get_quantity', 'get_status', 'get_actual_volume', 'get_density', 'get_temperature')
    search_fields = ('operator_notes', 'movement__document_number')
    
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
        return obj.movement.get_status_display() if obj.movement else None
    get_status.short_description = 'Статус'
    get_status.admin_order_field = 'movement__status'
    
    def get_actual_volume(self, obj):
        return obj.actual_volume
    get_actual_volume.short_description = 'Фактический объем'
    
    def get_density(self, obj):
        return obj.density
    get_density.short_description = 'Плотность'
    
    def get_temperature(self, obj):
        return obj.temperature
    get_temperature.short_description = 'Температура'
