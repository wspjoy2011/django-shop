from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Prefetch, Avg, FloatField, Value, OuterRef, Subquery, F, Q, Min, Case, When, DecimalField, \
    Max
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.http import urlencode
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)

from .forms import ProductForm
from .mixins import ProductAccessMixin
from .models import (
    Product,
    MasterCategory,
    SubCategory,
    ArticleType,
    BaseColour,
    Season,
    UsageType,
)
from apps.ratings.models import Rating, Like, Dislike
from ..favorites.models import FavoriteItem

User = get_user_model()


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            master_categories_count=MasterCategory.objects.count(),
            sub_categories_count=SubCategory.objects.count(),
            article_types_count=ArticleType.objects.count(),
            products_count=Product.objects.count(),
            base_colours_count=BaseColour.objects.count(),
            seasons_count=Season.objects.count(),
            usage_types_count=UsageType.objects.count(),
        )

        users_count = User.objects.count()
        ratings_count = Rating.objects.count()
        likes_count = Like.objects.count()
        dislikes_count = Dislike.objects.count()
        total_interactions = ratings_count + likes_count + dislikes_count

        context.update(
            users_count=users_count,
            ratings_count=ratings_count,
            likes_count=likes_count,
            dislikes_count=dislikes_count,
            total_interactions=total_interactions,
        )

        return context


class ProductListView(ListView):
    model = Product
    template_name = "pages/catalog/product/list.html"
    context_object_name = "products"
    paginate_by = 24
    PER_PAGE_ALLOWED = {"8", "12", "16", "20", "24"}


    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("per_page")
        if per_page in self.PER_PAGE_ALLOWED:
            return int(per_page)
        return self.paginate_by

    def _get_base_queryset(self):
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
            .prefetch_related(
                Prefetch(
                    'ratings',
                    queryset=Rating.objects.only('score', 'product_id', 'user_id'),
                    to_attr='ratings_list'
                ),
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
            )
        )

        # .annotate(
        #     avg_rating=Coalesce(Avg("ratings__score", output_field=FloatField()), Value(0.0)),
        #     ratings_count=Coalesce(Count("ratings", output_field=IntegerField()), Value(0)),
        # )

    def apply_category_filters_queryset(self, queryset):
        return queryset

    def get_options_scope_queryset(self):
        queryset = self._get_base_queryset()
        return self.apply_category_filters_queryset(queryset)

    def get_queryset(self):
        queryset = self._get_base_queryset()

        queryset = self.apply_category_filters_queryset(queryset)

        gender_param = self.request.GET.get("gender")
        if gender_param:
            genders = [g.strip() for g in gender_param.split(",") if g.strip()]
            if genders:
                queryset = queryset.filter(gender__in=genders)

        season_param = self.request.GET.get("season")
        if season_param:
            season_slugs = [s.strip() for s in season_param.split(",") if s.strip()]
            if season_slugs:
                queryset = queryset.filter(season__slug__in=season_slugs)

        min_price_param = self.request.GET.get("min_price")
        max_price_param = self.request.GET.get("max_price")

        if min_price_param or max_price_param:
            price_filter = Q()
            min_price = None
            max_price = None

            if min_price_param is not None:
                try:
                    min_price = Decimal(str(min_price_param))
                except (ValueError, TypeError, ArithmeticError):
                    min_price = None

            if max_price_param is not None:
                try:
                    max_price = Decimal(str(max_price_param))
                except (ValueError, TypeError, ArithmeticError):
                    max_price = None

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
                queryset = queryset.filter(
                    Q(inventory__isnull=False) & price_filter
                ).distinct()

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
                        queryset = queryset.filter(
                            Q(inventory__isnull=False) & availability_filter
                        ).distinct()

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
                        queryset = queryset.filter(
                            Q(inventory__isnull=False) & discount_filter
                        ).distinct()

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

        # if ordering in ["rating_desc", "rating_asc"]:
        #     queryset = queryset.annotate(
        #         avg_rating=Coalesce(Avg("ratings__score", output_field=FloatField()), Value(0.0))
        #     )

        if ordering in ["rating_desc", "rating_asc"]:
            avg_rating_subquery = Rating.objects.filter(
                product=OuterRef('pk')
            ).values('product').annotate(
                avg_score=Avg('score')
            ).values('avg_score')

            queryset = queryset.annotate(
                avg_rating=Coalesce(
                    Subquery(avg_rating_subquery[:1]),
                    Value(0.0),
                    output_field=FloatField()
                )
            )

        if ordering in ["price_desc", "price_asc"]:
            queryset = queryset.annotate(
                effective_price=Case(
                    When(inventory__sale_price__isnull=False, then='inventory__sale_price'),
                    default='inventory__base_price',
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            )

        if ordering in ordering_map:
            queryset = queryset.order_by(*ordering_map[ordering])

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["current_order"] = self.request.GET.get("ordering", "")

        per_page = self.request.GET.get("per_page")
        context["current_per_page"] = per_page if per_page in self.PER_PAGE_ALLOWED else ""

        gender_param = self.request.GET.get("gender", "")
        selected_genders = [g.strip() for g in gender_param.split(",") if g.strip()]
        context["selected_genders"] = selected_genders

        season_param = self.request.GET.get("season", "")
        selected_seasons = [s.strip() for s in season_param.split(",") if s.strip()]
        context["selected_seasons"] = selected_seasons

        availability_param = self.request.GET.get("availability", "")
        selected_availability = [a.strip() for a in availability_param.split(",") if a.strip()]
        context["selected_availability"] = selected_availability

        scope_queryset = self.get_options_scope_queryset()

        price_range = scope_queryset.aggregate(
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

        context["price_range"] = {
            "min": float(min_price),
            "max": float(max_price),
            "current_min": float(current_min_price),
            "current_max": float(current_max_price)
        }

        context["gender_options"] = list(
            scope_queryset.values_list("gender", flat=True).distinct().order_by("gender")
        )

        context["season_options"] = list(
            scope_queryset.values_list("season__name", "season__slug").distinct().order_by("season__name")
        )

        availability_options = []

        if scope_queryset.filter(
                inventory__is_active=True,
                inventory__stock_quantity__gt=F('inventory__reserved_quantity')
        ).exists():
            availability_options.append(("available", "Available"))

        if scope_queryset.filter(
                inventory__is_active=True,
                inventory__stock_quantity__lte=F('inventory__reserved_quantity')
        ).exists():
            availability_options.append(("out_of_stock", "Out of Stock"))

        if scope_queryset.filter(inventory__is_active=False).exists():
            availability_options.append(("not_active", "Not Active"))

        context["availability_options"] = availability_options

        discount_param = self.request.GET.get("discount", "")
        selected_discount = [d.strip() for d in discount_param.split(",") if d.strip()]
        context["selected_discount"] = selected_discount

        discount_options = []

        if scope_queryset.filter(
                inventory__sale_price__isnull=False,
                inventory__sale_price__lt=F('inventory__base_price')
        ).exists():
            discount_options.append(("on_sale", "On Sale"))

        if scope_queryset.filter(inventory__sale_price__isnull=True).exists():
            discount_options.append(("no_discount", "No Discount"))

        context["discount_options"] = discount_options

        params = self.request.GET.copy()
        params.pop("page", None)
        filter_query_string = urlencode(params, doseq=True)
        context["filter_query_string"] = f"&{filter_query_string}" if filter_query_string else ""

        return context


class ProductByMasterCategoryListView(ProductListView):

    def apply_category_filters_queryset(self, queryset):
        master_slug = self.kwargs.get("master_slug")
        return queryset.filter(article_type__sub_category__master_category__slug=master_slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        master_slug = self.kwargs.get("master_slug")
        context["master_category"] = get_object_or_404(
            MasterCategory.objects.prefetch_related(
                Prefetch("sub_categories", queryset=SubCategory.objects.order_by("name"))
            ),
            slug=master_slug,
        )
        return context


class ProductBySubCategoryListView(ProductListView):

    def apply_category_filters_queryset(self, queryset):
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        return queryset.filter(
            article_type__sub_category__master_category__slug=master_slug,
            article_type__sub_category__slug=sub_slug,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        master = get_object_or_404(
            MasterCategory.objects.prefetch_related(
                Prefetch("sub_categories", queryset=SubCategory.objects.order_by("name"))
            ),
            slug=master_slug,
        )
        sub = get_object_or_404(
            SubCategory.objects.prefetch_related(
                Prefetch("article_types", queryset=ArticleType.objects.order_by("name"))
            ),
            slug=sub_slug,
            master_category=master,
        )
        context["master_category"] = master
        context["sub_category"] = sub
        return context


class ProductByArticleTypeListView(ProductListView):

    def apply_category_filters_queryset(self, queryset):
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        article_slug = self.kwargs.get("article_slug")
        return queryset.filter(
            article_type__sub_category__master_category__slug=master_slug,
            article_type__sub_category__slug=sub_slug,
            article_type__slug=article_slug,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        article_slug = self.kwargs.get("article_slug")

        master = get_object_or_404(
            MasterCategory.objects.prefetch_related(
                Prefetch("sub_categories", queryset=SubCategory.objects.order_by("name"))
            ),
            slug=master_slug,
        )
        sub = get_object_or_404(
            SubCategory.objects.prefetch_related(
                Prefetch("article_types", queryset=ArticleType.objects.order_by("name"))
            ),
            slug=sub_slug,
            master_category=master,
        )
        article = get_object_or_404(ArticleType, slug=article_slug, sub_category=sub)

        context["master_category"] = master
        context["sub_category"] = sub
        context["article_type"] = article
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "pages/catalog/product/detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
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
            .prefetch_related(
                Prefetch(
                    'ratings',
                    queryset=Rating.objects.only('score', 'product_id', 'user_id'),
                    to_attr='ratings_list'
                ),
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
            )
        )


class ProductCreateView(ProductAccessMixin, LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "pages/catalog/product/create.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Product has been created successfully."
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "There were errors in your form. Please check the fields and try again."
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class ProductUpdateView(ProductAccessMixin, LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "pages/catalog/product/update.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        slug = self.kwargs.get(self.slug_url_kwarg)
        return get_object_or_404(Product, slug=slug)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["product"] = self.object
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Product has been updated successfully."
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "There were errors in your form. Please check the fields and try again."
        )
        return super().form_invalid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class ProductDeleteView(ProductAccessMixin, LoginRequiredMixin, DeleteView):
    model = Product
    template_name = "pages/catalog/product/delete.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("catalog:product_list")

    def get_object(self, queryset=None):
        slug = self.kwargs.get(self.slug_url_kwarg)
        return get_object_or_404(Product, slug=slug)

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Product "{self.object.product_display_name}" has been deleted successfully.'
        )
        return super().form_valid(form)
