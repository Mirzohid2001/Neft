import django_filters
from .models import Movement, Product, Wagon , Reservoir, ReservoirMovement , LocalMovement,Placement

class MovementFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(label="Sana oralig'i")
    product = django_filters.CharFilter(lookup_expr='icontains', label="Mahsulot nomi")
    movement_type = django_filters.ChoiceFilter(choices=Movement.MOVEMENT_TYPES, label="Harakat turi")
    warehouse = django_filters.CharFilter(field_name='warehouse__name', lookup_expr='icontains', label="Ombor nomi")

    class Meta:
        model = Movement
        fields = ['date', 'product', 'movement_type', 'warehouse']


class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains', label="Mahsulot nomi")
    category = django_filters.CharFilter(field_name="category", lookup_expr='icontains', label="Kategoriya")
    warehouse = django_filters.CharFilter(field_name="warehouse__name", lookup_expr='icontains', label="Ombor nomi")

    class Meta:
        model = Product
        fields = ['name', 'category', 'warehouse']



class WagonFilter(django_filters.FilterSet):
    wagon_number = django_filters.CharFilter(field_name="wagon_number", lookup_expr='icontains', label="Vagon raqami")
    wagon_type = django_filters.CharFilter(field_name="wagon_type", lookup_expr='icontains', label="Vagon turi")

    class Meta:
        model = Wagon
        fields = ['wagon_number', 'wagon_type']

class ReservoirFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr='icontains', label="Rezervuar nomi")
    product = django_filters.CharFilter(field_name="product__name", lookup_expr='icontains', label="Mahsulot nomi")

    class Meta:
        model = Reservoir
        fields = ['name', 'product']


class ReservoirMovementFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(field_name="date", label="Sana oralig'i")
    reservoir = django_filters.CharFilter(field_name="reservoir__name", lookup_expr='icontains', label="Rezervuar nomi")
    product = django_filters.CharFilter(field_name="product__name", lookup_expr='icontains', label="Mahsulot nomi")
    movement_type = django_filters.ChoiceFilter(choices=ReservoirMovement.MOVEMENT_TYPES, label="Harakat turi")

    class Meta:
        model = ReservoirMovement
        fields = ['date', 'reservoir', 'product', 'movement_type']


class LocalMovementFilter(django_filters.FilterSet):
    date = django_filters.DateFromToRangeFilter(label="Sana oralig'i")
    client = django_filters.CharFilter(field_name='client__name', lookup_expr='icontains', label="Klient nomi")
    product = django_filters.CharFilter(field_name='product__name', lookup_expr='icontains', label="Mahsulot nomi")
    doc_ton = django_filters.RangeFilter(label="Doc ton oralig'i")
    fact_ton = django_filters.RangeFilter(label="Fact ton oralig'i")
    

    class Meta:
        model = LocalMovement
        fields = ['date', 'client', 'product', 'doc_ton', 'fact_ton']


class PlacementFilter(django_filters.FilterSet):
    product = django_filters.CharFilter(field_name='product__name', lookup_expr='icontains', label="Mahsulot nomi")
    quantity = django_filters.RangeFilter(field_name='quantity', label="Miqdor oralig'i")
    wagon = django_filters.CharFilter(field_name='wagon__wagon_number', lookup_expr='icontains', label="Vagon raqami")
    reservoir = django_filters.CharFilter(field_name='reservoir__name', lookup_expr='icontains', label="Rezervuar nomi")

    class Meta:
        model = Placement
        fields = ['product', 'quantity', 'wagon', 'reservoir']
