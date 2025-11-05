from decimal import Decimal
from typing import Any, Optional, Self, Callable

from django.db.models import DecimalField, Case, When, FloatField, Value, Q, F, QuerySet
from django.db.models.functions import Cast
from django.http import HttpRequest

from apps.catalog.models import Product


class ProductQuerysetBuilder:
    """
    Provides a configurable builder for constructing complex product querysets
    based on request parameters such as category, gender, season, price range,
    availability, discount, and ordering options.
    """

    request: HttpRequest

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the builder with optional queryset and request."""
        super().__init__(*args, **kwargs)
        self.queryset: Optional[QuerySet[Product]] = None
        self.request: Optional[HttpRequest] = None # type: ignore[assignment]
        self._ordering_annotations: dict[str, bool] = {}

    def set_queryset_and_request(
            self,
            queryset: QuerySet[Product],
            request: HttpRequest,
    ) -> Self:
        """
        Assign the initial queryset and request to the builder.

        Args:
            queryset (QuerySet[Product]): The base queryset to filter.
            request (HttpRequest): The current HTTP request containing filter parameters.

        Returns:
            Self: The current instance of the builder.
        """
        self.queryset = queryset
        self.request = request
        return self

    def filter_by_category(
            self,
            category_filter_method: Optional[
                Callable[[QuerySet[Product]], QuerySet[Product]]
            ] = None,
            *args: Any,
            **kwargs: Any,
    ) -> Self:
        """
        Apply a category filter method to the queryset if provided.

        Args:
            category_filter_method (Callable | None): A callable that applies category filters.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Self: The current instance of the builder.
        """
        if category_filter_method and self.queryset is not None:
            self.queryset = category_filter_method(self.queryset, *args, **kwargs)
        return self

    def filter_by_gender(self) -> Self:
        """Filter products by gender based on the 'gender' query parameter."""
        assert self.request is not None
        assert self.queryset is not None

        gender_param = self.request.GET.get("gender")
        if gender_param:
            genders = [g.strip() for g in gender_param.split(",") if g.strip()]
            if genders:
                self.queryset = self.queryset.filter(gender__in=genders)
        return self

    def filter_by_season(self) -> Self:
        """Filter products by season slug from the 'season' query parameter."""
        assert self.request is not None
        assert self.queryset is not None

        season_param = self.request.GET.get("season")
        if season_param:
            season_slugs = [s.strip() for s in season_param.split(",") if s.strip()]
            if season_slugs:
                self.queryset = self.queryset.filter(season__slug__in=season_slugs)
        return self

    def filter_by_price_range(self) -> Self:
        """Filter products by minimum and maximum price parameters."""
        assert self.request is not None
        assert self.queryset is not None

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

    def filter_by_availability(self) -> Self:
        """Filter products by stock availability based on 'availability' query parameter."""
        assert self.request is not None
        assert self.queryset is not None

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

    def filter_by_discount(self) -> Self:
        """Filter products by discount status ('on_sale' or 'no_discount')."""
        assert self.request is not None
        assert self.queryset is not None

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

    def add_rating_annotation(self) -> Self:
        """Annotate the queryset with the average product rating value."""
        assert self.queryset is not None

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

    def add_price_annotation(self) -> Self:
        """Annotate the queryset with an effective price field (sale or base price)."""
        assert self.queryset is not None

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

    def apply_ordering(self) -> Self:
        """Apply ordering to the queryset based on the 'ordering' query parameter."""
        assert self.request is not None
        assert self.queryset is not None

        ordering = str(self.request.GET.get("ordering"))
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

    def build(self) -> QuerySet[Product]:
        """Return the final constructed queryset."""
        assert self.queryset is not None

        return self.queryset

    @staticmethod
    def _parse_decimal(value: Any) -> Optional[Decimal]:
        """
        Safely parse a decimal value from any input.

        Args:
            value (Any): The value to parse.

        Returns:
            Optional[Decimal]: Parsed Decimal or None if parsing fails.
        """
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, ArithmeticError):
            return None
