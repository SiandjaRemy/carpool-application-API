import django_filters

from carpool.models import Ride


class RideFilter(django_filters.FilterSet):
    # Custom filter examples
    min_price = django_filters.NumberFilter(
        field_name="price_per_seat", lookup_expr="gte"
    )
    max_price = django_filters.NumberFilter(
        field_name="price_per_seat", lookup_expr="lte"
    )

    # Case-insensitive partial matches for towns
    departure_town = django_filters.CharFilter(lookup_expr="icontains")
    arrival_town = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Ride()
        fields = ["status", "departure_town", "arrival_town"]
