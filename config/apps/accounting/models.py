from django.db import models
from apps.warehouse.models import Product, Warehouse

class FinancialRecord(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField()
    movement_type = models.CharField(max_length=3, choices=(('in', 'Kirim'), ('out', 'Chiqim')))
    quantity = models.FloatField(default=0)
    total_price_usd = models.FloatField(default=0)
    total_price_sum = models.FloatField(default=0)

    class Meta:
        verbose_name = "Moliyaviy yozuv"
        verbose_name_plural = "Moliyaviy yozuvlar"
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.product.name} - {self.movement_type} - {self.total_price_sum} so'm"
