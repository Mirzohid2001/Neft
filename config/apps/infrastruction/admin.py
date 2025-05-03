from django.contrib import admin
from .models import (
    Product, Receiving, Giving, Stock,
    CanteenExpense, Project, ProjectItem, ReceivingItem, ProjectProduct,
    TelegramGroup, Order, OrderItem
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_price', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)

class ReceivingItemInline(admin.TabularInline):
    model = ReceivingItem
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'comment')
    readonly_fields = ('total_price',)

@admin.register(Receiving)
class ReceivingAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'total_price', 'created_by')
    list_filter = ('date', 'created_by')
    search_fields = ('id', 'notes')
    ordering = ('-date',)
    inlines = [ReceivingItemInline]

@admin.register(ReceivingItem)
class ReceivingItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'receiving', 'quantity', 'unit_price', 'total_price')
    list_filter = ('receiving__date',)
    search_fields = ('product__name', 'comment')
    ordering = ('-receiving__date',)

@admin.register(Giving)
class GivingAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'total_price', 'given_to', 'date')
    list_filter = ('date', 'created_by')
    search_fields = ('product__name', 'given_to')
    ordering = ('-date',)

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'total_value', 'last_updated')
    search_fields = ('product__name',)
    ordering = ('product__name',)

@admin.register(CanteenExpense)
class CanteenExpenseAdmin(admin.ModelAdmin):
    list_display = ('product', 'unit_price', 'quantity', 'total_cost', 'date')
    list_filter = ('date', 'created_by')
    search_fields = ('product',)
    ordering = ('-date',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'start_date', 'end_date', 'total_cost')
    list_filter = ('status', 'start_date', 'created_by')
    search_fields = ('name', 'description')
    ordering = ('-start_date',)

@admin.register(ProjectItem)
class ProjectItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'unit_price', 'quantity', 'total_cost')
    list_filter = ('project',)
    search_fields = ('name', 'project__name')
    ordering = ('project', 'name')

@admin.register(ProjectProduct)
class ProjectProductAdmin(admin.ModelAdmin):
    list_display = ('project', 'product', 'quantity', 'total_cost', 'date_used')
    list_filter = ('project', 'product', 'date_used')
    search_fields = ('project__name', 'product__name', 'notes')
    ordering = ('-date_used',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'date', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('order_number', 'notes')
    inlines = [OrderItemInline]

@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'chat_id', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'chat_id')
