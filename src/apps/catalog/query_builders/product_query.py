from decimal import Decimal

from django.db.models import DecimalField, Case, When, FloatField, Value, Subquery, Avg, OuterRef, Q, F
from django.db.models.functions import Cast


class ProductQuerysetBuilder:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = None
        self.request = None
        self._ordering_annotations = {}

    def set_queryset_and_request(self, queryset, request):
        self.queryset = queryset
        self.request = request
        return self

    def filter_by_category(self, category_filter_method=None, *args, **kwargs):
        if category_filter_method and self.queryset is not None:
            self.queryset = category_filter_method(self.queryset, *args, **kwargs)
        return self

    def filter_by_gender(self):
        gender_param = self.request.GET.get("gender")
        if gender_param:
            genders = [g.strip() for g in gender_param.split(",") if g.strip()]
            if genders:
                self.queryset = self.queryset.filter(gender__in=genders)
        return self

    def filter_by_season(self):
        season_param = self.request.GET.get("season")
        if season_param:
            season_slugs = [s.strip() for s in season_param.split(",") if s.strip()]
            if season_slugs:
                self.queryset = self.queryset.filter(season__slug__in=season_slugs)
        return self

    def filter_by_price_range(self):
        min_price_param = self.request.GET.get("min_price")
        max_price_param = self.request.GET.get("max_price")

        if min_price_param or max_price_param:
            price_filter = Q()
            min_price = self._parse_decimal(min_price_param)
            max_price = self._parse_decimal(max_price_param)

            if min_price is not None:
                price_filter &= Q(
                    Q(inventory__sale_price__gte=min_price) |
                    Q(inventory__sale_price__isnull=True, inventory__base_price__gte=min_price)
                )

            if max_price is not None:
                price_filter &= Q(
                    Q(inventory__sale_price__lte=max_price) |
                    Q(inventory__sale_price__isnull=True, inventory__base_price__lte=max_price)
                )

            if min_price is not None or max_price is not None:
                self.queryset = self.queryset.filter(
                    Q(inventory__isnull=False) & price_filter
                ).distinct()
        return self

    def filter_by_availability(self):
        availability_param = self.request.GET.get("availability")

        if availability_param:
            availability_options = [a.strip() for a in availability_param.split(",") if a.strip()]

            if availability_options:
                all_availability_options = {"available", "out_of_stock", "not_active"}
                selected_availability_set = set(availability_options)

                if selected_availability_set != all_availability_options:
                    availability_filter = Q()

                    for option in availability_options:
                        if option == "available":
                            availability_filter |= Q(
                                inventory__is_active=True,
                                inventory__stock_quantity__gt=F('inventory__reserved_quantity')
                            )
                        elif option == "out_of_stock":
                            availability_filter |= Q(
                                inventory__is_active=True,
                                inventory__stock_quantity__lte=F('inventory__reserved_quantity')
                            )
                        elif option == "not_active":
                            availability_filter |= Q(inventory__is_active=False)

                    if availability_filter:
                        self.queryset = self.queryset.filter(
                            Q(inventory__isnull=False) & availability_filter
                        ).distinct()
        return self

    def filter_by_discount(self):
        discount_param = self.request.GET.get("discount")

        if discount_param:
            discount_options = [d.strip() for d in discount_param.split(",") if d.strip()]

            if discount_options:
                all_discount_options = {"on_sale", "no_discount"}
                selected_discount_set = set(discount_options)

                if selected_discount_set != all_discount_options:
                    discount_filter = Q()

                    for option in discount_options:
                        if option == "on_sale":
                            discount_filter |= Q(
                                inventory__sale_price__isnull=False,
                                inventory__sale_price__lt=F('inventory__base_price')
                            )
                        elif option == "no_discount":
                            discount_filter |= Q(inventory__sale_price__isnull=True)

                    if discount_filter:
                        self.queryset = self.queryset.filter(
                            Q(inventory__isnull=False) & discount_filter
                        ).distinct()
        return self

    def add_rating_annotation(self):
        if 'avg_rating' not in self._ordering_annotations:
            self.queryset = self.queryset.annotate(
                avg_rating=Case(
                    When(ratings_count__gt=0, then=Cast(F('ratings_sum'), FloatField()) / F('ratings_count')),
                    default=Value(0.0),
                    output_field=FloatField()
                )
            )
            self._ordering_annotations['avg_rating'] = True
        return self

    def add_price_annotation(self):
        if 'effective_price' not in self._ordering_annotations:
            self.queryset = self.queryset.annotate(
                effective_price=Case(
                    When(inventory__sale_price__isnull=False, then='inventory__sale_price'),
                    default='inventory__base_price',
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
            self._ordering_annotations['effective_price'] = True
        return self

    def apply_ordering(self):
        ordering = self.request.GET.get("ordering")
        ordering_map = {
            "name_asc": ("product_display_name", "pk"),
            "name_desc": ("-product_display_name", "-pk"),
            "year_desc": ("-year", "-pk"),
            "year_asc": ("year", "pk"),
            "created_desc": ("-created_at", "-pk"),
            "created_asc": ("created_at", "pk"),
            "rating_desc": ("-avg_rating", "-pk"),
            "rating_asc": ("avg_rating", "pk"),
            "price_desc": ("-effective_price", "-pk"),
            "price_asc": ("effective_price", "pk"),
        }

        if ordering in ["rating_desc", "rating_asc"]:
            self.add_rating_annotation()

        if ordering in ["price_desc", "price_asc"]:
            self.add_price_annotation()

        if ordering in ordering_map:
            self.queryset = self.queryset.order_by(*ordering_map[ordering])

        return self

    def build(self):
        return self.queryset

    @staticmethod
    def _parse_decimal(value):
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, ArithmeticError):
            return None
