from typing import Any, Optional, Type, Sequence, cast

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Prefetch, Case, When, QuerySet, Model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from numpy import ceil

from fixtures.utils import get_approximate_table_count
from .forms import ProductForm, MasterCategoryForm, SubCategoryForm, ArticleTypeForm
from .mixins import ProductAccessMixin, ProductQuerysetMixin, ProductFilterContextMixin, CategoryAccessMixin
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
from .paginator import AdaptiveKeysPaginator, QuerySetWithCount
from .protocols import SupportsCountSlice
from .query_builders.product_query import ProductQuerysetBuilder

User = get_user_model()


class HomeView(TemplateView):
    """
    Displays a landing page with aggregate counters for catalog entities and
    user interactions to provide a quick overview of platform activity.
    """

    template_name = "pages/home.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Build context with aggregate counters.

        Args:
            **kwargs: Extra context from parent.

        Returns:
            dict[str, Any]: Context dictionary with counters.

        Side Effects:
            Executes COUNT/approximate COUNT queries on multiple tables.
        """
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

        users_count = get_approximate_table_count(User)
        ratings_count = get_approximate_table_count(Rating)
        likes_count = get_approximate_table_count(Like)
        dislikes_count = get_approximate_table_count(Dislike)
        total_interactions = ratings_count + likes_count + dislikes_count

        context.update(
            users_count=users_count,
            ratings_count=ratings_count,
            likes_count=likes_count,
            dislikes_count=dislikes_count,
            total_interactions=total_interactions,
        )

        return context


class ProductListView(
    ProductQuerysetBuilder,
    ProductFilterContextMixin,
    ProductQuerysetMixin,
    ListView
):
    """
    Displays a list of products with support for filtering, ordering, and
    adaptive pagination. Integrates product queryset builder and filter context.
    """

    model = Product
    template_name = "pages/catalog/product/list.html"
    context_object_name = "products"
    paginate_by = 24
    PER_PAGE_ALLOWED = {"8", "12", "16", "20", "24"}
    MIN_PAGES_FOR_ADAPTIVE_PAGINATION = 100

    def get_paginate_by(self, queryset: QuerySet[Product]) -> int:
        """
        Resolve page size from query params constrained by allowed values.

        Args:
            queryset: Provided by Django for signature compatibility.

        Returns:
            int: Page size to use.
        """
        assert self.request is not None

        per_page = self.request.GET.get("per_page")
        if per_page in self.PER_PAGE_ALLOWED:
            return int(per_page)
        return self.paginate_by

    def apply_category_filters_queryset(self, queryset: QuerySet[Product]) -> QuerySet[Product]:
        """
        Hook to apply category-level filters.

        Args:
            queryset: Base products queryset.

        Returns:
            QuerySet[Product]: Filtered queryset.
        """
        return queryset

    def get_options_scope_queryset(self) -> QuerySet[Product]:
        """
        Return scope queryset used to build filter options.

        Returns:
            QuerySet[Product]: Queryset for computing filter facets.
        """
        queryset = self.get_base_queryset()
        return self.apply_category_filters_queryset(queryset)

    def get_queryset(self) -> QuerySet[Product]:
        """
        Build filtered and ordered queryset using the builder pipeline.

        Returns:
            QuerySet[Product]: Final queryset for the list view.
        """
        assert self.request is not None
        return (self
                .set_queryset_and_request(self.get_base_queryset(), self.request)
                .filter_by_category(self.apply_category_filters_queryset)
                .filter_by_gender()
                .filter_by_season()
                .filter_by_price_range()
                .filter_by_availability()
                .filter_by_discount()
                .apply_ordering()
                .build())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Inject filter options metadata into context.

        Args:
            **kwargs: Parent context parts.

        Returns:
            dict[str, Any]: Context with filter metadata.
        """

        context = super().get_context_data(**kwargs)
        context.update(self.get_filter_context_data(self.get_options_scope_queryset()))
        return context

    def get_paginator(
            self,
            queryset: Any,
            per_page: int,
            orphans: int = 0,
            allow_empty_first_page: bool = True,
            **kwargs: Any,
    ) -> Paginator:
        """
        Return a standard or adaptive paginator based on total pages.

        Args:
            queryset: Source queryset.
            per_page: Items per page.
            orphans: Orphans threshold.
            allow_empty_first_page: Whether empty first page is allowed.
            **kwargs: Extra paginator options.

        Returns:
            Paginator: Configured paginator.

        Side Effects:
            Executes COUNT on queryset. In adaptive mode, page fetch triggers
            additional DB reads via the data strategy.
        """
        queryset = cast(QuerySet[Product], queryset)
        count = queryset.count()
        wrapped_queryset: SupportsCountSlice[Product] = QuerySetWithCount[Product](queryset, count)

        num_pages = ceil(count / per_page) if count > 0 else 0

        if num_pages <= self.MIN_PAGES_FOR_ADAPTIVE_PAGINATION:
            return Paginator(wrapped_queryset, per_page, orphans, allow_empty_first_page)

        def data_strategy(page_number: int, page_size: int) -> Optional[Sequence[Product]]:
            """
            Load PKs from a projected queryset, then hydrate rows preserving order.

            Args:
                page_number: 1-based page number.
                page_size: Items per page.

            Returns:
                Optional[Sequence[Product]]: Hydrated page slice or None.

            Side Effects:
                Issues DB queries for PK slice and hydration in preserved order.
            """
            assert self.request is not None

            builder = ProductQuerysetBuilder()
            light_queryset = (builder
                              .set_queryset_and_request(self.use_projection(), self.request)
                              .filter_by_category(self.apply_category_filters_queryset)
                              .filter_by_gender()
                              .filter_by_season()
                              .filter_by_price_range()
                              .filter_by_availability()
                              .filter_by_discount()
                              .apply_ordering()
                              .build())

            start = (page_number - 1) * page_size
            end = start + page_size
            pks = list(light_queryset.values_list('pk', flat=True)[start:end])

            if not pks:
                return []

            heavy_queryset = self.get_base_queryset().filter(pk__in=pks)
            preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pks)])
            return list(heavy_queryset.order_by(preserved_order))

        return AdaptiveKeysPaginator(
            wrapped_queryset,
            per_page,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
            data_strategy=data_strategy
        )


class ProductByMasterCategoryListView(ProductListView):
    """
    Displays products filtered by master category and enriches context with the
    selected master category and its ordered subcategories.
    """

    def apply_category_filters_queryset(self, queryset: QuerySet[Product]) -> QuerySet[Product]:
        """
        Filter queryset by master category from URL.

        Args:
            queryset: Base products queryset.

        Returns:
            QuerySet[Product]: Filtered queryset.
        """
        master_slug = self.kwargs.get("master_slug")
        return queryset.filter(article_type__sub_category__master_category__slug=master_slug)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Attach master category object with ordered subcategories.

        Args:
            **kwargs: Parent context parts.

        Returns:
            dict[str, Any]: Context including 'master_category'.
        """
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
    """
    Displays products filtered by master and subcategory, adding both objects
    to the context for breadcrumbing and page headings.
    """

    def apply_category_filters_queryset(self, queryset: QuerySet[Product]) -> QuerySet[Product]:
        """
        Filter queryset by master and subcategory from URL.

        Args:
            queryset: Base products queryset.

        Returns:
            QuerySet[Product]: Filtered queryset.
        """
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        return queryset.filter(
            article_type__sub_category__master_category__slug=master_slug,
            article_type__sub_category__slug=sub_slug,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Attach master and subcategory objects to context.

        Args:
            **kwargs: Parent context parts.

        Returns:
            dict[str, Any]: Context with 'master_category' and 'sub_category'.
        """
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
    """
    Displays products filtered by master category, subcategory, and article type,
    enriching context with all three for navigation and headings.
    """

    def apply_category_filters_queryset(self, queryset: QuerySet[Product]) -> QuerySet[Product]:
        """
        Filter queryset by master, subcategory and article type.

        Args:
            queryset: Base products queryset.

        Returns:
            QuerySet[Product]: Filtered queryset.
        """
        master_slug = self.kwargs.get("master_slug")
        sub_slug = self.kwargs.get("sub_slug")
        article_slug = self.kwargs.get("article_slug")
        return queryset.filter(
            article_type__sub_category__master_category__slug=master_slug,
            article_type__sub_category__slug=sub_slug,
            article_type__slug=article_slug,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Attach master, subcategory and article type objects to context.

        Args:
            **kwargs: Parent context parts.

        Returns:
            dict[str, Any]: Context with 'master_category', 'sub_category',
            and 'article_type'.
        """
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


class ProductDetailView(ProductQuerysetMixin[Product], DetailView):
    """
    Displays a single product page using a preconfigured base queryset to
    ensure related data is efficiently loaded.
    """

    model = Product
    template_name = "pages/catalog/product/detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self) -> QuerySet[Product]:
        """
        Provide base queryset with necessary prefetch/select-related.

        Returns:
            QuerySet[Product]: Queryset used by DetailView.
        """
        return self.get_base_queryset()


class ProductCreateView(ProductAccessMixin, LoginRequiredMixin, CreateView):
    """
    Handles creation of a new product with access control and user feedback
    through Django messages upon success or failure.
    """

    model = Product
    form_class = ProductForm
    template_name = "pages/catalog/product/create.html"

    def form_valid(self, form: ProductForm) -> HttpResponse:
        """
        Handle successful product creation.

        Args:
            form: Bound and valid ProductForm instance.

        Returns:
            HttpResponse: Redirect to success URL.

        Side Effects:
            Enqueues a success message via django.contrib.messages.
        """
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Product has been created successfully."
        )
        return response

    def form_invalid(self, form: ProductForm) -> HttpResponse:
        """
        Handle invalid form submission.

        Args:
            form: Bound but invalid ProductForm.

        Returns:
            HttpResponse: Response with errors.

        Side Effects:
            Enqueues an error message via django.contrib.messages.
        """
        messages.error(
            self.request,
            "There were errors in your form. Please check the fields and try again."
        )
        return super().form_invalid(form)

    def get_success_url(self) -> str:
        """
        Resolve redirect URL after creation.

        Returns:
            str: Absolute URL of the created product.
        """
        obj = cast(Product, self.object)
        return obj.get_absolute_url()


class ProductUpdateView(ProductAccessMixin, LoginRequiredMixin, UpdateView):
    """
    Handles updating an existing product with access control, providing
    user feedback through Django messages.
    """

    model = Product
    form_class = ProductForm
    template_name = "pages/catalog/product/update.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset: Optional[QuerySet[Product]] = None) -> Product:
        """
        Fetch product by slug with access checks performed by mixin.

        Args:
            queryset: Optional queryset override.

        Returns:
            Product: Target product instance.
        """
        slug = self.kwargs.get(self.slug_url_kwarg)
        return get_object_or_404(Product, slug=slug)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Add product instance into context under 'product'.

        Args:
            **kwargs: Parent context.

        Returns:
            dict[str, Any]: Context including product reference.
        """
        ctx = super().get_context_data(**kwargs)
        ctx["product"] = self.object
        return ctx

    def form_valid(self, form: ProductForm) -> HttpResponse:
        """
        Handle successful product update.

        Args:
            form: Bound and valid ProductForm.

        Returns:
            HttpResponse: Redirect to success URL.

        Side Effects:
            Enqueues a success message via django.contrib.messages.
        """
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Product has been updated successfully."
        )
        return response

    def form_invalid(self, form: ProductForm) -> HttpResponse:
        """
        Handle invalid update submission.

        Args:
            form: Bound but invalid ProductForm.

        Returns:
            HttpResponse: Response with errors.

        Side Effects:
            Enqueues an error message via django.contrib.messages.
        """
        messages.error(
            self.request,
            "There were errors in your form. Please check the fields and try again."
        )
        return super().form_invalid(form)

    def get_success_url(self) -> str:
        """
        Resolve redirect URL after update.

        Returns:
            str: Absolute URL of the updated product.
        """
        obj = cast(Product, self.object)
        return obj.get_absolute_url()


class ProductDeleteView(ProductAccessMixin, DeleteView):
    """
    Handles deletion of a product using access control and provides user
    feedback messages upon success.
    """

    model = Product
    template_name = "pages/catalog/product/delete.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("catalog:product_list")

    def get_object(self, queryset: Optional[QuerySet[Product]] = None) -> Product:
        """
        Fetch product by slug for deletion.

        Args:
            queryset: Optional queryset override.

        Returns:
            Product: Target product instance.
        """
        slug = self.kwargs.get(self.slug_url_kwarg)
        return get_object_or_404(Product, slug=slug)

    def form_valid(self, form: Any) -> HttpResponse:
        """
        Handle confirmed deletion.

        Args:
            form: Bound form (unused).

        Returns:
            HttpResponse: Redirect to success URL.

        Side Effects:
            Deletes the product from DB and enqueues a success message.
        """
        messages.success(
            self.request,
            f'Product "{self.object.product_display_name}" has been deleted successfully.'
        )
        return super().form_valid(form)


class CategoryCreateView(CategoryAccessMixin, CreateView):
    """
    Creates catalog taxonomy entities (master, subcategory, article type) based
    on the URL parameter, wiring appropriate forms, models, and context labels.
    """

    template_name = "pages/catalog/category/create.html"

    def get_form_class(self) -> Type[MasterCategoryForm | SubCategoryForm | ArticleTypeForm]:
        """
        Map URL param to form class.

        Returns:
            type[ModelForm]: One of MasterCategoryForm/SubCategoryForm/ArticleTypeForm.
        """
        category_type = self.kwargs.get('category_type')
        form_mapping: dict[
            str,
            type[MasterCategoryForm | SubCategoryForm | ArticleTypeForm]
        ] = {
            "master": MasterCategoryForm,
            "sub": SubCategoryForm,
            "article": ArticleTypeForm,
        }
        return form_mapping.get(category_type, MasterCategoryForm)

    def get_model(self) -> Type[Model]:
        """
        Map URL param to model class.

        Returns:
            type[Model]: One of MasterCategory/SubCategory/ArticleType.
        """
        category_type = self.kwargs.get('category_type')
        model_mapping = {
            'master': MasterCategory,
            'sub': SubCategory,
            'article': ArticleType,
        }
        return model_mapping.get(category_type, MasterCategory)

    def get_form_kwargs(self) -> dict[str, Any]:
        """
        Inject IDs for dependent dropdowns when present.

        Returns:
            dict[str, Any]: Form kwargs extended with *_category_id.

        Side Effects:
            Parses GET params to integers when applicable.
        """
        kwargs = super().get_form_kwargs()
        category_type = self.kwargs.get('category_type')

        if category_type == 'sub' and 'master_category_id' in self.request.GET:
            master_id = self.request.GET.get('master_category_id', '')
            kwargs['master_category_id'] = int(master_id) if master_id.isdigit() else None
        elif category_type == 'article' and 'sub_category_id' in self.request.GET:
            sub_id = self.request.GET.get('sub_category_id', '')
            kwargs['sub_category_id'] = int(sub_id) if sub_id.isdigit() else None

        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Provide human-readable category type labels for the template.

        Args:
            **kwargs: Parent context.

        Returns:
            dict[str, Any]: Context with type and display labels.
        """
        context = super().get_context_data(**kwargs)
        category_type = self.kwargs.get('category_type')

        context.update({
            'category_type': category_type,
            'category_type_display': {
                'master': 'Master Category',
                'sub': 'Subcategory',
                'article': 'Article Type'
            }.get(category_type, 'Category')
        })

        return context

    def form_valid(self, form: Any) -> HttpResponse:
        """
        Handle successful category creation.

        Args:
            form: Bound and valid category form.

        Returns:
            HttpResponse: Redirect to computed success URL.

        Side Effects:
            Enqueues a success message via django.contrib.messages.
        """
        response = super().form_valid(form)
        category_type = self.kwargs.get('category_type')
        category_name = form.cleaned_data.get('name')

        messages.success(
            self.request,
            f'{category_type.title()} category "{category_name}" has been created successfully.'
        )
        return response

    def form_invalid(self, form: Any) -> HttpResponse:
        """
        Handle invalid category form submission.

        Args:
            form: Bound but invalid form.

        Returns:
            HttpResponse: Response with errors.

        Side Effects:
            Enqueues an error message via django.contrib.messages.
        """
        messages.error(
            self.request,
            "There were errors in your form. Please check the fields and try again."
        )
        return super().form_invalid(form)

    def get_success_url(self) -> str:
        """
        Compute redirect depending on created category type.

        Returns:
            str: Absolute URL to navigate after success.
        """
        category_type = self.kwargs.get('category_type')

        assert self.object is not None

        if category_type == 'master':
            return reverse("catalog:product_list")
        elif category_type == 'sub':
            master_slug = self.object.master_category.slug
            return reverse("catalog:product_list_by_master", kwargs={"master_slug": master_slug})
        elif category_type == 'article':
            master_slug = self.object.sub_category.master_category.slug
            sub_slug = self.object.sub_category.slug
            return reverse("catalog:product_list_by_sub", kwargs={
                "master_slug": master_slug,
                "sub_slug": sub_slug
            })
        return reverse("catalog:product_list")
