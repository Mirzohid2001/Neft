from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..warehouse.models import Product, Reservoir, Warehouse

class ProductionType(models.Model):
    """Тип производственного процесса"""
    name = models.CharField(max_length=100, verbose_name="Nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsifi")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Ishlab chiqarish turi"
        verbose_name_plural = "Ishlab chiqarish turlari"

class ProductionProcess(models.Model):
    """Основная модель производственного процесса"""
    PROCESS_TYPES = (
        ('raw_processing', 'Xom-ashyoni qayta ishlash'),
        ('mixing', 'Qo\'shimchalar qo\'shish'),
    )
    
    SOURCE_TYPES = (
        ('reservoir', 'Rezervuar'),
        ('wagon', 'Vagon'),
    )
    
    process_number = models.CharField(max_length=50, verbose_name="Jarayon raqami")
    process_type = models.CharField(max_length=20, choices=PROCESS_TYPES, verbose_name="Jarayon turi")
    start_date = models.DateTimeField(default=timezone.now, verbose_name="Boshlanish sanasi")
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Tugash sanasi")
    
    # Поля для источника (input)
    input_source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default='reservoir', 
                                       verbose_name="Kirish manba turi")
    input_reservoir = models.ForeignKey(Reservoir, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='production_inputs', verbose_name="Kirish rezervuari")
    input_wagon = models.ForeignKey('warehouse.Wagon', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='production_inputs', verbose_name="Kirish vagoni")
    
    # Поля для назначения (output)
    output_source_type = models.CharField(max_length=10, choices=SOURCE_TYPES, default='reservoir',
                                        verbose_name="Chiqish manba turi")
    output_reservoir = models.ForeignKey(Reservoir, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='production_outputs', verbose_name="Chiqish rezervuari")
    output_wagon = models.ForeignKey('warehouse.Wagon', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='production_outputs', verbose_name="Chiqish vagoni")
    
    notes = models.TextField(blank=True, null=True, verbose_name="Izohlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan sana")
    
    def clean(self):
        # Проверка валидности источника
        if self.input_source_type == 'reservoir' and not self.input_reservoir:
            raise ValidationError("Kirish rezervuari tanlanishi kerak")
        elif self.input_source_type == 'wagon' and not self.input_wagon:
            raise ValidationError("Kirish vagoni tanlanishi kerak")
            
        # Проверка валидности назначения
        if self.output_source_type == 'reservoir' and not self.output_reservoir:
            raise ValidationError("Chiqish rezervuari tanlanishi kerak")
        elif self.output_source_type == 'wagon' and not self.output_wagon:
            raise ValidationError("Chiqish vagoni tanlanishi kerak")
    
    def __str__(self):
        return f"{self.get_process_type_display()} - {self.process_number}"
    
    class Meta:
        verbose_name = "Ishlab chiqarish jarayoni"
        verbose_name_plural = "Ishlab chiqarish jarayonlari"

class RawMaterialProcessing(models.Model):
    """Модель для переработки сырья"""
    production_process = models.OneToOneField(ProductionProcess, on_delete=models.CASCADE, 
                                             related_name='raw_processing', verbose_name="Ishlab chiqarish jarayoni")
    raw_material = models.ForeignKey(Product, on_delete=models.CASCADE, 
                                     related_name='as_raw_material', verbose_name="Xom-ashyo")
    output_type = models.CharField(max_length=20, choices=(
        ('additive', 'Qo\'shimcha'),
        ('product', 'Tayyor mahsulot'),
    ), verbose_name="Ishlab chiqarilgan mahsulot turi")
    
    raw_material_quantity = models.FloatField(verbose_name="Xom-ashyo miqdori (tonna)")
    temperature = models.FloatField(default=20, verbose_name="Harorat (C)")
    density = models.FloatField(verbose_name="Zichlik (kg/m³)")
    liter_volume = models.FloatField(verbose_name="Hajm (litr)")
    
    # Информация о потерях
    loss_percentage = models.FloatField(default=0, verbose_name="Yo'qotish foizi (%)")
    calculated_loss = models.FloatField(default=0, verbose_name="Hisoblangan yo'qotish (tonna)")
    
    def save(self, *args, **kwargs):
        # Расчет потерь при сохранении
        self.calculated_loss = self.raw_material_quantity * (self.loss_percentage / 100)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Xom-ashyoni qayta ishlash: {self.raw_material.name} ({self.raw_material_quantity} tonna)"
    
    class Meta:
        verbose_name = "Xom-ashyoni qayta ishlash"
        verbose_name_plural = "Xom-ashyoni qayta ishlash jarayonlari"

class GasolineMixing(models.Model):
    """Модель для производства бензина путем смешивания"""
    production_process = models.OneToOneField(ProductionProcess, on_delete=models.CASCADE, 
                                             related_name='gasoline_mixing', verbose_name="Ishlab chiqarish jarayoni")
    gasoline_type = models.ForeignKey(Product, on_delete=models.CASCADE, 
                                      related_name='as_gasoline_type', verbose_name="Benzin turi")
    output_quantity = models.FloatField(verbose_name="Ishlab chiqarilgan miqdor (tonna)")
    temperature = models.FloatField(default=20, verbose_name="Harorat (C)")
    density = models.FloatField(verbose_name="Zichlik (kg/m³)")
    liter_volume = models.FloatField(verbose_name="Hajm (litr)")
    
    def __str__(self):
        return f"Benzin aralashmasini tayyorlash: {self.gasoline_type.name} ({self.output_quantity} tonna)"
    
    class Meta:
        verbose_name = "Benzin aralashmasini tayyorlash"
        verbose_name_plural = "Benzin aralashmasini tayyorlash jarayonlari"

class ProductionInput(models.Model):
    """Компоненты, входящие в производственный процесс"""
    production_process = models.ForeignKey(ProductionProcess, on_delete=models.CASCADE, 
                                          related_name='inputs', verbose_name="Ishlab chiqarish jarayoni")
    material = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Material")
    quantity = models.FloatField(verbose_name="Miqdor (tonna)")
    temperature = models.FloatField(default=20, verbose_name="Harorat (C)")
    density = models.FloatField(verbose_name="Zichlik (kg/m³)")
    liter_volume = models.FloatField(verbose_name="Hajm (litr)")
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity} tonna"
    
    class Meta:
        verbose_name = "Ishlab chiqarish uchun kiruvchi material"
        verbose_name_plural = "Ishlab chiqarish uchun kiruvchi materiallar"

class ProductionOutput(models.Model):
    """Результаты производства"""
    production_process = models.ForeignKey(ProductionProcess, on_delete=models.CASCADE, 
                                          related_name='outputs', verbose_name="Ishlab chiqarish jarayoni")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    quantity = models.FloatField(verbose_name="Miqdor (tonna)")
    temperature = models.FloatField(default=20, verbose_name="Harorat (C)")
    density = models.FloatField(verbose_name="Zichlik (kg/m³)")
    liter_volume = models.FloatField(verbose_name="Hajm (litr)")
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} tonna"
    
    class Meta:
        verbose_name = "Ishlab chiqarilgan mahsulot"
        verbose_name_plural = "Ishlab chiqarilgan mahsulotlar"
