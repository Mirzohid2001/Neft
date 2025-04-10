from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Movement, AuditLog
from apps.accounting.models import Transaction, Category, Account

@receiver(post_save, sender=Movement)
def movement_audit_log_on_save(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    description = f"Movement ID {instance.id}: {instance.get_movement_type_display()} {instance.quantity} units."
    AuditLog.objects.create(
        action=action,
        model_name='Movement',
        object_id=instance.id,
        description=description
    )
    print(f"AuditLog: Movement {instance.id} {action}.")

@receiver(post_save, sender=Movement)
def create_accounting_transaction(sender, instance, created, **kwargs):
    """
    Создает финансовую транзакцию при создании/изменении складского движения
    """
    if created or instance.price_sum or instance.price_usd:
        with transaction.atomic():
            # Определяем тип транзакции на основе типа движения
            if instance.movement_type == 'in':
                transaction_type = 'expense'  # Расход при закупке
                category = Category.objects.get_or_create(
                    name='Закупка товаров',
                    type='expense',
                    defaults={'description': 'Расходы на закупку товаров'}
                )[0]
            elif instance.movement_type == 'out':
                transaction_type = 'income'  # Доход при продаже
                category = Category.objects.get_or_create(
                    name='Продажа товаров',
                    type='income',
                    defaults={'description': 'Доходы от продажи товаров'}
                )[0]
            else:
                return  # Для перемещений не создаем финансовых транзакций

            # Получаем или создаем счет для товарных операций
            account = Account.objects.get_or_create(
                name='Товарные операции',
                defaults={
                    'type': 'operational',
                    'currency': 'UZS',
                    'description': 'Счет для учета товарных операций'
                }
            )[0]

            # Создаем транзакцию
            Transaction.objects.create(
                date=instance.date,
                transaction_type=transaction_type,
                amount=instance.price_sum or 0,
                amount_usd=instance.price_usd or 0,
                account=account,
                category=category,
                description=f"Товар: {instance.product.name}, Количество: {instance.quantity}",
                reference=f"Movement#{instance.id}",
                status='completed'
            )

@receiver(post_delete, sender=Movement)
def movement_audit_log_on_delete(sender, instance, **kwargs):
    description = f"Movement ID {instance.id} deleted."
    AuditLog.objects.create(
        action='deleted',
        model_name='Movement',
        object_id=instance.id,
        description=description
    )
    print(f"AuditLog: Movement {instance.id} deleted.")
