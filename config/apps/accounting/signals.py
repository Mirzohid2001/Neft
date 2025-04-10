# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from apps.warehouse.models import Movement, LocalMovement
# from .models import FinanceOperation

# @receiver(post_save, sender=Movement)
# def movement_to_finance(sender, instance, created, **kwargs):
#     if created:
#         op_type = 'income' if instance.movement_type == 'in' else 'expense'
#         amount = instance.quantity * instance.price_sum
#         FinanceOperation.objects.create(
#             movement=instance,
#             operation_type=op_type,
#             amount_sum=amount
#         )
#     else:
#         try:
#             finop = FinanceOperation.objects.get(movement=instance)
#             finop.amount_sum = instance.quantity * instance.price_sum
#             finop.save()
#         except FinanceOperation.DoesNotExist:
#             pass

# @receiver(post_delete, sender=Movement)
# def movement_delete_finance(sender, instance, **kwargs):
#     try:
#         FinanceOperation.objects.get(movement=instance).delete()
#     except FinanceOperation.DoesNotExist:
#         pass

# @receiver(post_save, sender=LocalMovement)
# def localmovement_to_finance(sender, instance, created, **kwargs):
#     if created:
#         op_type = 'income' 
#         amount = instance.mass * 1000 
#         FinanceOperation.objects.create(
#             local_movement=instance,
#             operation_type=op_type,
#             amount_sum=amount
#         )
#     else:
#         try:
#             finop = FinanceOperation.objects.get(local_movement=instance)
#             finop.amount_sum = instance.mass * 1000
#             finop.save()
#         except FinanceOperation.DoesNotExist:
#             pass

# @receiver(post_delete, sender=LocalMovement)
# def localmovement_delete_finance(sender, instance, **kwargs):
#     try:
#         FinanceOperation.objects.get(local_movement=instance).delete()
#     except FinanceOperation.DoesNotExist:
#         pass
