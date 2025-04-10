from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.warehouse.models import Movement, LocalMovement, ReservoirMovement
from .models import FinancialRecord, JournalEntry, Invoice
from .services import generate_journal_entry_from_movement, generate_invoice_from_movement

@receiver(post_save, sender=Movement)
def movement_to_accounting(sender, instance, created, **kwargs):
    """
    Обработчик сигнала создания/обновления операции склада (Movement).
    Создает соответствующие бухгалтерские записи.
    """
    # Если операция только что создана, создаем бухгалтерскую проводку
    if created:
        # Создаем бухгалтерскую проводку
        journal_entry = generate_journal_entry_from_movement(instance, instance.created_by)
        
        # Для операций приемки и отгрузки создаем счет-фактуру
        if instance.movement_type in ['in', 'out']:
            generate_invoice_from_movement(instance, instance.created_by)
    else:
        # Если операция обновлена, обновляем связанные финансовые записи
        financial_records = FinancialRecord.objects.filter(
            product=instance.product,
            date=instance.date,
            movement_type=instance.movement_type
        )
        
        for record in financial_records:
            record.quantity = instance.quantity
            record.total_price_sum = instance.quantity * (instance.product.price_sum or 0)
            record.total_price_usd = instance.quantity * (instance.product.price_usd or 0)
            record.save()
        
        # Обновляем связанные проводки
        journal_entries = JournalEntry.objects.filter(movement=instance)
        if journal_entries.exists() and instance.status == 'cancelled':
            # Если операция отменена, отменяем и проводки
            for entry in journal_entries:
                if entry.status == 'posted':
                    entry.cancel(instance.created_by)
        
        # Обновляем связанные счета-фактуры
        invoices = Invoice.objects.filter(movement=instance)
        for invoice in invoices:
            # Отмена счета при отмене операции
            if instance.status == 'cancelled' and invoice.status != 'cancelled':
                invoice.cancel()
            
            # Если количество или цена изменились, обновляем позиции счета
            for item in invoice.items.all():
                if item.quantity != instance.quantity or item.unit_price != instance.price_sum:
                    item.quantity = instance.quantity
                    item.unit_price = instance.price_sum or instance.product.price_sum or 0
                    item.save()  # Это автоматически пересчитает итоги счета

@receiver(post_delete, sender=Movement)
def movement_delete_accounting(sender, instance, **kwargs):
    """
    Обработчик сигнала удаления операции склада (Movement).
    Удаляет соответствующие бухгалтерские записи.
    """
    # Удаляем связанные финансовые записи
    FinancialRecord.objects.filter(
        product=instance.product,
        date=instance.date,
        movement_type=instance.movement_type
    ).delete()
    
    # Удаляем связанные проводки
    JournalEntry.objects.filter(movement=instance).delete()
    
    # Удаляем связанные счета-фактуры
    Invoice.objects.filter(movement=instance).delete()

@receiver(post_save, sender=LocalMovement)
def localmovement_to_accounting(sender, instance, created, **kwargs):
    """
    Обработчик сигнала создания/обновления локальной операции склада.
    Создает соответствующие бухгалтерские записи.
    """
    if created:
        # Создаем финансовую запись для отчетов
        FinancialRecord.objects.create(
            product=instance.product,
            warehouse=None,  # LocalMovement может не иметь склада
            date=instance.date,
            movement_type=instance.movement_type,
            quantity=instance.quantity,
            total_price_sum=instance.quantity * (instance.product.price_sum or 0),
            total_price_usd=instance.quantity * (instance.product.price_usd or 0)
        )
        
        # Для локальных операций не создаем проводки и счета-фактуры,
        # так как они обычно вспомогательные
    else:
        # Обновляем существующие финансовые записи
        financial_records = FinancialRecord.objects.filter(
            product=instance.product,
            date=instance.date,
            movement_type=instance.movement_type
        )
        
        for record in financial_records:
            record.quantity = instance.quantity
            record.total_price_sum = instance.quantity * (instance.product.price_sum or 0)
            record.total_price_usd = instance.quantity * (instance.product.price_usd or 0)
            record.save()

@receiver(post_delete, sender=LocalMovement)
def localmovement_delete_accounting(sender, instance, **kwargs):
    """
    Обработчик сигнала удаления локальной операции склада.
    Удаляет соответствующие бухгалтерские записи.
    """
    FinancialRecord.objects.filter(
        product=instance.product,
        date=instance.date,
        movement_type=instance.movement_type
    ).delete()

@receiver(post_save, sender=ReservoirMovement)
def reservoirmovement_to_accounting(sender, instance, created, **kwargs):
    """
    Обработчик сигнала создания/обновления операции резервуара.
    Создает соответствующие бухгалтерские записи.
    """
    if created:
        # Создаем финансовую запись для отчетов
        FinancialRecord.objects.create(
            product=instance.product,
            warehouse=instance.reservoir.warehouse if instance.reservoir and hasattr(instance.reservoir, 'warehouse') else None,
            date=instance.date,
            movement_type=instance.movement_type,
            quantity=instance.quantity,
            total_price_sum=instance.quantity * (instance.product.price_sum or 0),
            total_price_usd=instance.quantity * (instance.product.price_usd or 0)
        )
        
        # Проводки для операций резервуара обычно не создаются,
        # так как они являются внутренними перемещениями
    else:
        # Обновляем существующие финансовые записи
        financial_records = FinancialRecord.objects.filter(
            product=instance.product,
            date=instance.date,
            movement_type=instance.movement_type
        )
        
        for record in financial_records:
            record.quantity = instance.quantity
            record.total_price_sum = instance.quantity * (instance.product.price_sum or 0)
            record.total_price_usd = instance.quantity * (instance.product.price_usd or 0)
            record.save()

@receiver(post_delete, sender=ReservoirMovement)
def reservoirmovement_delete_accounting(sender, instance, **kwargs):
    """
    Обработчик сигнала удаления операции резервуара.
    Удаляет соответствующие бухгалтерские записи.
    """
    FinancialRecord.objects.filter(
        product=instance.product,
        date=instance.date,
        movement_type=instance.movement_type
    ).delete()
