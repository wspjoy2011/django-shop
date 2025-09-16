from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Prefetch, Case, When
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
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
from .query_builders.product_query import ProductQuerysetBuilder

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
    model = Product
    template_name = "pages/catalog/product/list.html"
    context_object_name = "products"
    paginate_by = 24
    PER_PAGE_ALLOWED = {"8", "12", "16", "20", "24"}
    MIN_PAGES_FOR_ADAPTIVE_PAGINATION = 100

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("per_page")
        if per_page in self.PER_PAGE_ALLOWED:
            return int(per_page)
        return self.paginate_by

    def apply_category_filters_queryset(self, queryset):
        return queryset

    def get_options_scope_queryset(self):
        queryset = self.get_base_queryset()
        return self.apply_category_filters_queryset(queryset)

    def get_queryset(self):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_filter_context_data(self.get_options_scope_queryset()))
        return context

    def get_paginator(
            self, queryset, per_page, orphans=0, allow_empty_first_page=True, **kwargs
    ):
        count = queryset.count()
        wrapped_queryset = QuerySetWithCount(queryset, count)

        num_pages = ceil(count / per_page) if count > 0 else 0

        if num_pages <= self.MIN_PAGES_FOR_ADAPTIVE_PAGINATION:
            return Paginator(wrapped_queryset, per_page, orphans, allow_empty_first_page)

        def data_strategy(page_number, page_size):
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
            return heavy_queryset.order_by(preserved_order)

        return AdaptiveKeysPaginator(
            wrapped_queryset,
            per_page,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
            data_strategy=data_strategy
        )


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


class ProductDetailView(ProductQuerysetMixin, DetailView):
    model = Product
    template_name = "pages/catalog/product/detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return self.get_base_queryset()


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


class CategoryCreateView(CategoryAccessMixin, CreateView):
    template_name = "pages/catalog/category/create.html"

    def get_form_class(self):
        category_type = self.kwargs.get('category_type')
        form_mapping = {
            'master': MasterCategoryForm,
            'sub': SubCategoryForm,
            'article': ArticleTypeForm,
        }
        return form_mapping.get(category_type, MasterCategoryForm)

    def get_model(self):
        category_type = self.kwargs.get('category_type')
        model_mapping = {
            'master': MasterCategory,
            'sub': SubCategory,
            'article': ArticleType,
        }
        return model_mapping.get(category_type, MasterCategory)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        category_type = self.kwargs.get('category_type')

        if category_type == 'sub' and 'master_id' in self.request.GET:
            kwargs['master_category_id'] = self.request.GET.get('master_id')
        elif category_type == 'article' and 'sub_id' in self.request.GET:
            kwargs['sub_category_id'] = self.request.GET.get('sub_id')

        return kwargs

    def get_context_data(self, **kwargs):
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

    def form_valid(self, form):
        response = super().form_valid(form)
        category_type = self.kwargs.get('category_type')
        category_name = form.cleaned_data.get('name')

        messages.success(
            self.request,
            f'{category_type.title()} category "{category_name}" has been created successfully.'
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "There were errors in your form. Please check the fields and try again."
        )
        return super().form_invalid(form)

    def get_success_url(self):
        category_type = self.kwargs.get('category_type')
        if category_type == 'master':
            return reverse_lazy("catalog:product_list")
        elif category_type == 'sub':
            master_slug = self.object.master_category.slug
            return reverse_lazy("catalog:product_list_by_master", kwargs={"master_slug": master_slug})
        elif category_type == 'article':
            master_slug = self.object.sub_category.master_category.slug
            sub_slug = self.object.sub_category.slug
            return reverse_lazy("catalog:product_list_by_sub", kwargs={
                "master_slug": master_slug,
                "sub_slug": sub_slug
            })
        return reverse_lazy("catalog:product_list")
