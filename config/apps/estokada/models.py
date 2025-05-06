from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.warehouse.models import Movement, Reservoir, Wagon, Product
from apps.sales.models import SalesMovement

class EstokadaMovement(models.Model):
    """
    Модель для хранения специфической информации о движениях через эстокаду.
    Связана с общей моделью Movement.
    """
    operation = models.ForeignKey(SalesMovement, on_delete=models.CASCADE, verbose_name="Операция")
    actual_weight = models.FloatField(verbose_name="Фактический вес")
    document_weight = models.FloatField(verbose_name="Документальный вес")
    weight_difference = models.FloatField(verbose_name="Разница (авторасчет)", editable=False)
    temperature = models.FloatField(verbose_name="Температура", null=True, blank=True)
    density = models.FloatField(verbose_name="Удельный вес", null=True, blank=True)
    notes = models.TextField(verbose_name="Примечания", null=True, blank=True)
    photo = models.ImageField(upload_to='estokada_photos/', verbose_name="Фото", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    def save(self, *args, **kwargs):
        # Рассчитываем разницу веса
        self.weight_difference = self.actual_weight - self.document_weight
        super().save(*args, **kwargs)
        
        # Обновляем статус операции
        self.operation.status = 'completed'
        self.operation.save()
    
    def __str__(self):
        return f"Обработка {self.operation.get_type_display()} #{self.operation.document_number}"
    
    class Meta:
        verbose_name = "Движение через эстокаду"
        verbose_name_plural = "Движения через эстокаду"
        ordering = ['-created_at']
