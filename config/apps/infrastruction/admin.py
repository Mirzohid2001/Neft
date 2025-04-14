from django.contrib import admin
from .models import (
    Product, Receiving, Giving, Stock,
    CanteenExpense, Project, ProjectItem
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit_price', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Receiving)
class ReceivingAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'total_price', 'date', 'created_by')
    list_filter = ('date', 'created_by')
    search_fields = ('product__name',)
    ordering = ('-date',)

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
