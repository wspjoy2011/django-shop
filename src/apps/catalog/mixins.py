from decimal import Decimal, InvalidOperation
from typing import Generic, Any, Optional, Sequence

from django import forms
from django.contrib import messages
from django.db.models import Prefetch, F, Exists, OuterRef, QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import redirect
from django.utils.http import urlencode
from django.views import View

from apps.cart.models import CartItem
from apps.catalog.models import Season
from apps.catalog.pgviews import PriceRangesMV, GenderFilterOptionsMV
from apps.catalog.protocols import ModelT, ModelClassWithManager
from apps.favorites.models import FavoriteItem
from apps.ratings.models import Rating, Like, Dislike


class ProductAccessMixin(View):
    """
    Restricts access to product modification views for non-staff users.

    Displays an error message and redirects to the catalog home page
    if the user is not authenticated or not a staff member.
    """

    error_message = "You do not have permission to add/edit/delete products."

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """
        Intercept incoming requests and enforce staff-only access.

        Args:
            request: Current HTTP request.
            *args: Positional view arguments.
            **kwargs: Keyword view arguments.

        Returns:
            HttpResponse: Redirects unauthorized users to catalog home.
        """
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, self.error_message)
            return redirect("catalog:home")
        return super().dispatch(request, *args, **kwargs)


class CategoryAccessMixin(ProductAccessMixin):
    """
    Restricts access to category modification views for non-staff users.
    Inherits permission enforcement from ProductAccessMixin.
    """

    error_message = "You do not have permission to add/edit/delete categories."


class ProductQuerysetMixin(Generic[ModelT]):
    """
    Provides optimized base querysets for product views.

    Adds prefetches for likes, dislikes, favorites, cart items, and
    optionally user-specific ratings when authenticated.
    """

    request: HttpRequest
    model: ModelClassWithManager[ModelT]

    def get_base_queryset(self) -> QuerySet[ModelT]:
        """
        Build a queryset with all required prefetch and select-related fields.

        Returns:
            QuerySet[ModelT]: Optimized queryset containing related data.
        """
        user = self.request.user

        prefetch_list: list[Prefetch] = [
            Prefetch(
                'likes',
                queryset=Like.objects.only('product_id', 'user_id'),
                to_attr='likes_list'
            ),
            Prefetch(
                'dislikes',
                queryset=Dislike.objects.only('product_id', 'user_id'),
                to_attr='dislikes_list'
            ),
            Prefetch(
                'favorite_items',
                queryset=FavoriteItem.objects.select_related('collection').only(
                    'product_id', 'collection__user_id'
                ),
                to_attr='favorites_list'
            ),
            Prefetch(
                'cart_items',
                queryset=CartItem.objects.select_related('cart').only(
                    'product_id', 'cart_id', 'cart__user_id'
                ),
                to_attr='cart_items_list'
            )
        ]

        if user.is_authenticated:
            prefetch_list.append(
                Prefetch(
                    'ratings',
                    queryset=Rating.objects.filter(user=user),
                    to_attr='ratings_list'
                )
            )

        queryset = (
            self.model.objects.only(
                "id",
                "slug",
                "image_url",
                "product_display_name",
                "product_id",
                "year",
                "gender",
                "ratings_sum",
                "ratings_count",

                "article_type__name",
                "base_colour__name",
                "season__name",
                "usage_type__name",
                "inventory__is_active",
                "inventory__stock_quantity",
                "inventory__reserved_quantity",
                "inventory__base_price",
                "inventory__sale_price",
                "inventory__currency__symbol",
                "inventory__currency__decimals"
            )
            .select_related(
                "article_type",
                "base_colour",
                "season",
                "usage_type",
                "inventory",
                "inventory__currency",
            )
            .prefetch_related(*prefetch_list)
        )

        return queryset

    def use_projection(self, only_fields: Optional[Sequence[str]] = None) -> QuerySet[ModelT]:
        """
        Create a lightweight queryset limited to selected fields.

        Args:
            only_fields: Optional list of field names to project.

        Returns:
            QuerySet[ModelT]: Projected queryset containing only given fields.
        """
        if not only_fields:
            meta = self.model._meta
            ordering_fields: Sequence[str] = meta.ordering or ()
            only_fields = [f.lstrip('-') for f in ordering_fields]

        queryset: QuerySet[ModelT] = self.model.objects.only(*only_fields)

        return queryset


class ProductFilterContextMixin:
    """
    Provides reusable filter-context logic for product list views.

    Builds UI filter state and available options (gender, season,
    availability, discount, and price range) based on the current queryset.
    """

    request: HttpRequest
    kwargs: dict

    def get_filter_context_data(self, queryset: QuerySet[Any]) -> dict[str, Any]:
        """
        Build context for filter controls and their current state.

        Args:
            queryset: Base queryset used to derive filter options.

        Returns:
            dict[str, Any]: Context with current selections and options.
        """
        context: dict[str, Any] = {}

        context["current_order"] = self.request.GET.get("ordering", "")

        per_page = self.request.GET.get("per_page")
        if hasattr(self, 'PER_PAGE_ALLOWED'):
            context["current_per_page"] = per_page if per_page in self.PER_PAGE_ALLOWED else ""

        context["selected_genders"] = self._parse_csv_param("gender")
        context["selected_seasons"] = self._parse_csv_param("season")
        context["selected_availability"] = self._parse_csv_param("availability")
        context["selected_discount"] = self._parse_csv_param("discount")

        context["price_range"] = self._get_price_range_context()

        context["gender_options"] = self._get_gender_options()
        context["season_options"] = self._get_season_options(queryset)
        context["availability_options"] = self._get_availability_options(queryset)
        context["discount_options"] = self._get_discount_options(queryset)

        context["filter_query_string"] = self._get_filter_query_string()

        return context

    def _parse_csv_param(self, param_name: str) -> list[str]:
        """Split a comma-separated query parameter into a list of clean values."""
        param_value = self.request.GET.get(param_name, "")
        return [item.strip() for item in param_value.split(",") if item.strip()]

    def _get_price_range_context(self) -> dict[str, float]:
        """
        Compute available and current price range values for filter UI.

        Returns:
            dict[str, float]: A mapping with min/max and current_min/current_max values.
        """
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        article_slug = self.kwargs.get("article_slug")

        min_price, max_price = PriceRangesMV.get_for_context(
            master_slug=master_slug,
            sub_slug=sub_slug,
            article_slug=article_slug,
        )

        min_price = min_price or Decimal("0.00")
        max_price = max_price or Decimal("1000.00")

        min_price_param = self.request.GET.get("min_price")
        max_price_param = self.request.GET.get("max_price")

        try:
            current_min_price: Decimal = (
                Decimal(str(min_price_param)) if min_price_param is not None else min_price
            )
            current_max_price: Decimal = (
                Decimal(str(max_price_param)) if max_price_param is not None else max_price
            )
        except (InvalidOperation, ValueError, TypeError):
            current_min_price = min_price
            current_max_price = max_price

        return {
            "min": float(min_price),
            "max": float(max_price),
            "current_min": float(current_min_price),
            "current_max": float(current_max_price),
        }

    def _get_gender_options(self) -> list[str]:
        """Fetch available gender filter options based on slugs in context."""
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        article_slug = self.kwargs.get("article_slug")

        return GenderFilterOptionsMV.get_for_context(
            master_slug=master_slug,
            sub_slug=sub_slug,
            article_slug=article_slug
        )

    @staticmethod
    def _get_season_options(queryset: QuerySet) -> list[tuple[str, str]]:
        """Return seasons present in the given queryset."""
        seasons = (
            Season.objects
            .annotate(present=Exists(queryset.filter(season_id=OuterRef('pk'))))
            .filter(present=True)
            .values_list('name', 'slug')
            .order_by('name')
        )
        return list(seasons)

    @staticmethod
    def _get_availability_options(queryset: QuerySet) -> list[tuple[str, str]]:
        """Determine which availability states exist within the queryset."""
        options = []

        if queryset.filter(
                inventory__is_active=True,
                inventory__stock_quantity__gt=F('inventory__reserved_quantity')
        ).exists():
            options.append(("available", "Available"))

        if queryset.filter(
                inventory__is_active=True,
                inventory__stock_quantity__lte=F('inventory__reserved_quantity')
        ).exists():
            options.append(("out_of_stock", "Out of Stock"))

        if queryset.filter(inventory__is_active=False).exists():
            options.append(("not_active", "Not Active"))

        return options

    @staticmethod
    def _get_discount_options(queryset: QuerySet) -> list[tuple[str, str]]:
        """Determine discount filter states based on sale/base price conditions."""
        options = []

        if queryset.filter(
                inventory__sale_price__isnull=False,
                inventory__sale_price__lt=F('inventory__base_price')
        ).exists():
            options.append(("on_sale", "On Sale"))

        if queryset.filter(inventory__sale_price__isnull=True).exists():
            options.append(("no_discount", "No Discount"))

        return options

    def _get_filter_query_string(self) -> str:
        """Rebuild query string excluding pagination parameters."""
        params = self.request.GET.copy()
        params.pop("page", None)
        filter_query_string = urlencode(params, doseq=True)
        return f"&{filter_query_string}" if filter_query_string else ""


class CategoryFormMixin:
    """
    Common styling and constraints for all category forms.

    Adds Bootstrap classes, sets max length on name fields,
    and extends help text consistently.
    """

    fields: dict

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the mixin and apply form-wide field adjustments."""
        super().__init__(*args, **kwargs)
        self.set_field_styles()
        self.set_name_field_maxlength()
        self.update_name_help_text()

    def set_field_styles(self) -> None:
        """Apply consistent form-control or select CSS classes to widgets."""
        for name, field in self.fields.items():
            css_class = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            field.widget.attrs.setdefault("class", css_class)
            field.widget.attrs.setdefault("placeholder", field.label)

    def set_name_field_maxlength(self) -> None:
        """Set maximum input length for 'name' fields if present."""
        if 'name' in self.fields:
            self.fields['name'].widget.attrs.setdefault('maxlength', 50)

    def update_name_help_text(self) -> None:
        """Append standard max-length information to the 'name' help text."""
        if 'name' in self.fields:
            current_help_text = self.fields['name'].help_text or ''
            self.fields['name'].help_text = f"{current_help_text} Maximum 50 characters."
