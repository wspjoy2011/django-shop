from decimal import Decimal

from django.contrib import messages
from django.db.models import Prefetch, DecimalField, When, Case, Max, Min, F
from django.shortcuts import redirect
from django.utils.http import urlencode
from django.views import View

from apps.favorites.models import FavoriteItem
from apps.ratings.models import Rating, Like, Dislike


class ProductAccessMixin(View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "You do not have permission to add/edit/delete products.")
            return redirect("catalog:home")
        return super().dispatch(request, *args, **kwargs)


class ProductQuerysetMixin:

    def get_base_queryset(self):
        user = self.request.user

        prefetch_list = [
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
                queryset=FavoriteItem.objects.select_related('collection__user'),
                to_attr='favorites_list'
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

        return (
            super()
            .get_queryset()
            .select_related(
                "article_type",
                "article_type__sub_category",
                "article_type__sub_category__master_category",
                "base_colour",
                "season",
                "usage_type",
                "inventory",
                "inventory__currency",
            )
            .prefetch_related(*prefetch_list)
        )


class ProductFilterContextMixin:

    def get_filter_context_data(self, queryset):
        context = {}

        context["current_order"] = self.request.GET.get("ordering", "")

        per_page = self.request.GET.get("per_page")
        if hasattr(self, 'PER_PAGE_ALLOWED'):
            context["current_per_page"] = per_page if per_page in self.PER_PAGE_ALLOWED else ""

        context["selected_genders"] = self._parse_csv_param("gender")
        context["selected_seasons"] = self._parse_csv_param("season")
        context["selected_availability"] = self._parse_csv_param("availability")
        context["selected_discount"] = self._parse_csv_param("discount")

        context["price_range"] = self._get_price_range_context(queryset)

        context["gender_options"] = self._get_gender_options(queryset)
        context["season_options"] = self._get_season_options(queryset)
        context["availability_options"] = self._get_availability_options(queryset)
        context["discount_options"] = self._get_discount_options(queryset)

        context["filter_query_string"] = self._get_filter_query_string()

        return context

    def _parse_csv_param(self, param_name):
        param_value = self.request.GET.get(param_name, "")
        return [item.strip() for item in param_value.split(",") if item.strip()]

    def _get_price_range_context(self, queryset):
        price_range = queryset.aggregate(
            min_price=Min(
                Case(
                    When(inventory__sale_price__isnull=False, then='inventory__sale_price'),
                    default='inventory__base_price',
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ),
            max_price=Max(
                Case(
                    When(inventory__sale_price__isnull=False, then='inventory__sale_price'),
                    default='inventory__base_price',
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )
        )

        min_price = price_range['min_price'] or Decimal('0.00')
        max_price = price_range['max_price'] or Decimal('1000.00')

        current_min_price = self.request.GET.get("min_price", str(min_price))
        current_max_price = self.request.GET.get("max_price", str(max_price))

        try:
            current_min_price = Decimal(str(current_min_price))
            current_max_price = Decimal(str(current_max_price))
        except (ValueError, TypeError):
            current_min_price = min_price
            current_max_price = max_price

        return {
            "min": float(min_price),
            "max": float(max_price),
            "current_min": float(current_min_price),
            "current_max": float(current_max_price)
        }

    @staticmethod
    def _get_gender_options(queryset):
        return list(
            queryset.values_list("gender", flat=True).distinct().order_by("gender")
        )

    @staticmethod
    def _get_season_options(queryset):
        return list(
            queryset.values_list("season__name", "season__slug").distinct().order_by("season__name")
        )

    @staticmethod
    def _get_availability_options(queryset):
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
    def _get_discount_options(queryset):
        options = []

        if queryset.filter(
                inventory__sale_price__isnull=False,
                inventory__sale_price__lt=F('inventory__base_price')
        ).exists():
            options.append(("on_sale", "On Sale"))

        if queryset.filter(inventory__sale_price__isnull=True).exists():
            options.append(("no_discount", "No Discount"))

        return options

    def _get_filter_query_string(self):
        params = self.request.GET.copy()
        params.pop("page", None)
        filter_query_string = urlencode(params, doseq=True)
        return f"&{filter_query_string}" if filter_query_string else ""
