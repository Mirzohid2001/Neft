from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Movement, AuditLog

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
