from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.warehouse.models import Movement
from apps.estokada.models import EstokadaMovement
from apps.sales.models import SalesMovement
from django.utils import timezone

@receiver(post_save, sender=EstokadaMovement)
def notify_sales_about_estokada_operation(sender, instance, created, **kwargs):
    """
    Обрабатывает сигнал создания или обновления операции в Estokada и обновляет или создает
    соответствующую запись в модуле Sales при необходимости.
    """
    if not created:
        # Если это обновление существующей записи, просто сохраняем изменения в связанной записи Sales
        try:
            if instance.movement:
                sales_movement = SalesMovement.objects.filter(movement=instance.movement).first()
                if sales_movement:
                    # Обновляем только если есть связанное движение Sales
                    sales_movement.save()
        except Exception as e:
            print(f"Ошибка при обновлении записи Sales: {e}")
        return

    # Если это новая запись и это операция приемки (in)
    if instance.movement and instance.movement.movement_type == 'in':
        try:
            # Проверяем, не существует ли уже запись для этого движения
            if not SalesMovement.objects.filter(movement=instance.movement).exists():
                # Создаем новую запись продажи с предварительными данными
                movement = instance.movement
                
                # Получаем первого клиента для примера
                from apps.warehouse.models import Client
                default_client = Client.objects.first()
                
                if default_client:
                    # Создаем базовую запись Sales
                    sales_movement = SalesMovement.objects.create(
                        movement=movement,
                        client=default_client,
                        payment_status='pending',
                        delivery_status='pending',
                        price_per_unit=0,  # Нулевая цена, пока не заполнят
                        payment_due_date=timezone.now().date() + timezone.timedelta(days=30),  # Срок оплаты +30 дней
                        transport_type=instance.transport_type,
                        transport_number=instance.transport_number
                    )
                    print(f"Создана предварительная запись продажи: {sales_movement}")
        except Exception as e:
            print(f"Ошибка при создании предварительной записи Sales: {e}") 