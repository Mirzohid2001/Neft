from django.contrib import admin
from .models import (
    Warehouse, Product, Batch, WagonType, Wagon,
    LocalClient, Client, LocalMovement, Reservoir,
    ReservoirMovement, Movement, Inventory,
    Placement, AuditLog, Transport, ProductionSource
)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "location_code")
    search_fields = ("name", "zone", "location_code")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "volume", "weight", "density", "specific_weight", "net_quantity")
    search_fields = ("code", "name", "category")
    list_filter = ("category", "warehouse", "zone")
    readonly_fields = ("density", "specific_weight", "created_at", "updated_at")
    autocomplete_fields = ["warehouse"]
    actions = ["check_thresholds"]

    @admin.action(description="Check all product thresholds and send alerts")
    def check_thresholds(self, request, queryset):
        for product in queryset:
            product.check_threshold()


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "product", "manufacture_date", "expiry_date", "quantity", "net_quantity")
    search_fields = ("batch_number", "product__name")
    autocomplete_fields = ["product"]


@admin.register(WagonType)
class WagonTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Wagon)
class WagonAdmin(admin.ModelAdmin):
    list_display = ("wagon_number", "wagon_type", "net_weight", "meter_weight", "current_quantity")
    search_fields = ("wagon_number",)
    autocomplete_fields = ["wagon_type"]


@admin.register(LocalClient)
class LocalClientAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)


@admin.register(LocalMovement)
class LocalMovementAdmin(admin.ModelAdmin):
    list_display = ("date", "client", "product", "movement_type", "quantity", "wagon", "reservoir")
    list_filter = ("movement_type", "date")
    search_fields = ("product__name", "client__name")
    readonly_fields = ("difference_ton", "created_at")
    autocomplete_fields = ["client", "product", "wagon", "reservoir"]


@admin.register(Reservoir)
class ReservoirAdmin(admin.ModelAdmin):
    list_display = ("name", "warehouse", "capacity", "current_volume", "current_quantity")
    autocomplete_fields = ["warehouse", "product"]
    search_fields = ("name",)


@admin.register(ReservoirMovement)
class ReservoirMovementAdmin(admin.ModelAdmin):
    list_display = ("date", "reservoir", "movement_type", "quantity", "note")
    list_filter = ("movement_type",)
    search_fields = ("reservoir__name",)
    autocomplete_fields = ["reservoir", "product"]


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ("date", "movement_type", "status", "product", "quantity")
    list_filter = ("movement_type", "status", "date")
    search_fields = ("document_number", "product__name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = [
        "product", "source_warehouse", "target_warehouse",
        "created_by", "confirmed_by"
    ]
    fieldsets = (
        ("Asosiy ma'lumotlar", {
            "fields": ("document_number", "date", "movement_type", "status")
        }),
        ("Mahsulot", {
            "fields": ("product", "quantity")
        }),
        ("Manbalar va Manzillar", {
            "fields": (
                ("source_warehouse", "target_warehouse"),
            )
        }),
        ("Narxlar va Izohlar", {
            "fields": ("note",)
        }),
        ("Audit", {
            "fields": ("created_by", "confirmed_by", "created_at", "updated_at")
        }),
    )


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity")
    search_fields = ("product__name",)


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ("product", "wagon", "reservoir", "quantity", "created_at")
    autocomplete_fields = ["product", "wagon", "reservoir", "movement"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("model_name", "object_id", "action", "timestamp")
    search_fields = ("model_name", "object_id", "action")
    readonly_fields = ("model_name", "object_id", "action", "timestamp")


@admin.register(Transport)
class TransportAdmin(admin.ModelAdmin):
    list_display = ['transport_type', 'transport_number', 'quantity', 'doc_quantity', 'difference']
    list_filter = ['transport_type', 'warehouse']
    search_fields = ['transport_number']
    readonly_fields = ['difference']


@admin.register(ProductionSource)
class ProductionSourceAdmin(admin.ModelAdmin):
    list_display = ("movement", "product", "quantity", "percentage")
    autocomplete_fields = ["movement", "product", "source_reservoir", "source_wagon", "source_warehouse"]

