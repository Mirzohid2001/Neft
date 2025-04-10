import django_filters
from .models import FinancialRecord
from apps.warehouse.models import Warehouse

class FinancialRecordFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(label="Sana oralig‘i")
    warehouse = django_filters.ModelChoiceFilter(queryset=Warehouse.objects.all())
    movement_type = django_filters.ChoiceFilter(choices=(('in', 'Kirim'), ('out', 'Chiqim')))

    class Meta:
        model = FinancialRecord
        fields = ['date', 'warehouse', 'movement_type']
