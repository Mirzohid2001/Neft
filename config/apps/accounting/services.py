from django.db.models import Sum, Q
from apps.warehouse.models import Movement, LocalMovement, ReservoirMovement
from .models import FinancialRecord
from datetime import datetime

def create_financial_records(date_from=None, date_to=None):
    FinancialRecord.objects.all().delete()

    filters = Q()
    if date_from:
        filters &= Q(date__gte=date_from)
    if date_to:
        filters &= Q(date__lte=date_to)

    movements = Movement.objects.filter(filters)
    for move in movements:
        FinancialRecord.objects.create(
            product=move.product,
            warehouse=move.warehouse,
            date=move.date,
            movement_type=move.movement_type,
            quantity=move.quantity,
            total_price_sum=move.price_sum,
            total_price_usd=(move.product.price_usd or 0) * move.quantity
        )

    local_moves = LocalMovement.objects.filter(filters)
    for lmove in local_moves:
        FinancialRecord.objects.create(
            product=lmove.product,
            warehouse=None,
            date=lmove.date,
            movement_type='out',
            quantity=lmove.mass,
            total_price_sum=(lmove.product.price_sum or 0) * lmove.mass,
            total_price_usd=(lmove.product.price_usd or 0) * lmove.mass
        )
    reservoir_moves = ReservoirMovement.objects.filter(filters)
    for rmove in reservoir_moves:
        FinancialRecord.objects.create(
            product=rmove.product,
            warehouse=rmove.reservoir.warehouse,
            date=rmove.date,
            movement_type=rmove.movement_type,
            quantity=rmove.quantity,
            total_price_sum=(rmove.product.price_sum or 0) * rmove.quantity,
            total_price_usd=(rmove.product.price_usd or 0) * rmove.quantity
        )

def calculate_summary():
    total_in_sum = FinancialRecord.objects.filter(movement_type='in').aggregate(Sum('total_price_sum'))['total_price_sum__sum'] or 0
    total_out_sum = FinancialRecord.objects.filter(movement_type='out').aggregate(Sum('total_price_sum'))['total_price_sum__sum'] or 0

    net_profit_loss = total_in_sum - total_out_sum

    status = 'Foyda' if net_profit_loss >= 0 else 'Zarar'

    return {
        'total_in_sum': total_in_sum,
        'total_out_sum': total_out_sum,
        'net_profit_loss': net_profit_loss,
        'status': status,
    }
